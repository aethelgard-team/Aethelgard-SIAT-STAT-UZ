"""
Aethelgard SIAT: Deterministic ML Time-Series Forecaster (ml/forecaster.py)
Author: Siddiq (Backend & ML Lead)

Implements lightweight, CPU-efficient time-series forecasting using:
1. Ridge Regression (scikit-learn) with polynomial/seasonal features
2. Holt-Winters Exponential Smoothing (statsmodels ETS)
3. Autoregressive Integrated Moving Average (statsmodels ARIMA)

Includes holdout backtest model selection (MAPE/MAE), 95% confidence intervals,
and strict validation guards.
"""

import warnings
import math
import re
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from sklearn.linear_model import Ridge

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        from statsmodels.tsa.arima.model import ARIMA
        STATSMODELS_AVAILABLE = True
    except ImportError:
        STATSMODELS_AVAILABLE = False


def _safe_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Percentage Error (MAPE) safely."""
    if len(y_true) == 0:
        return 0.0
    denom = np.where(np.abs(y_true) > 1e-6, np.abs(y_true), 1.0)
    mape = np.mean(np.abs((y_true - y_pred) / denom)) * 100.0
    if math.isnan(mape) or math.isinf(mape):
        return 0.0
    return float(mape)


def _safe_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Error (MAE)."""
    if len(y_true) == 0:
        return 0.0
    mae = float(np.mean(np.abs(y_true - y_pred)))
    if math.isnan(mae) or math.isinf(mae):
        return 0.0
    return mae


def _sanitize_float(val: Any, default: float = 0.0) -> float:
    """Ensure standard Python float without NaN/Inf for JSON serialization."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 2)
    except Exception:
        return default


def _build_features(
    indices: np.ndarray,
    total_len: int,
    is_periodic: bool = False,
    period_cycle: int = 12
) -> np.ndarray:
    """Build normalized polynomial and optional seasonal features for linear models."""
    t_norm = (indices / max(1, total_len)).reshape(-1, 1)
    feats = [t_norm, t_norm ** 2]

    if is_periodic and total_len >= 18:
        phase = 2.0 * np.pi * (indices % period_cycle) / float(period_cycle)
        sin_f = np.sin(phase).reshape(-1, 1)
        cos_f = np.cos(phase).reshape(-1, 1)
        feats.extend([sin_f, cos_f])

    return np.hstack(feats)


def _fit_ridge(
    y_train: np.ndarray,
    steps_ahead: int,
    is_periodic: bool = False,
    cycle: int = 12
) -> Tuple[np.ndarray, np.ndarray, str]:
    """Fit Ridge Regression on historical values and predict horizon steps."""
    n = len(y_train)
    idx_train = np.arange(n)
    X_train = _build_features(idx_train, n, is_periodic=is_periodic, period_cycle=cycle)

    model = Ridge(alpha=1.0, random_state=42)
    model.fit(X_train, y_train)

    train_pred = model.predict(X_train)

    idx_future = np.arange(n, n + steps_ahead)
    X_future = _build_features(idx_future, n, is_periodic=is_periodic, period_cycle=cycle)
    future_pred = model.predict(X_future)

    return train_pred, future_pred, "Ridge Regression"


def _fit_ets(
    y_train: np.ndarray,
    steps_ahead: int,
    is_periodic: bool = False,
    cycle: int = 12
) -> Optional[Tuple[np.ndarray, np.ndarray, str]]:
    """Fit Holt-Winters Exponential Smoothing model."""
    if not STATSMODELS_AVAILABLE or len(y_train) < 4:
        return None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            n = len(y_train)
            if is_periodic and n >= 2 * cycle:
                model = ExponentialSmoothing(
                    y_train,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=cycle,
                    damped_trend=(steps_ahead > 3),
                    initialization_method="estimated"
                )
            else:
                model = ExponentialSmoothing(
                    y_train,
                    trend="add",
                    seasonal=None,
                    damped_trend=(steps_ahead > 3 and n >= 6),
                    initialization_method="estimated"
                )

            fit_res = model.fit(disp=False)
            train_pred = fit_res.fittedvalues
            future_pred = fit_res.forecast(steps_ahead)
            return np.array(train_pred), np.array(future_pred), "Holt-Winters ETS"
    except Exception:
        return None


def _fit_arima(
    y_train: np.ndarray,
    steps_ahead: int,
    with_drift: bool = True
) -> Optional[Tuple[np.ndarray, np.ndarray, str]]:
    """Fit ARIMA model with linear drift for integrated series."""
    if not STATSMODELS_AVAILABLE or len(y_train) < 5:
        return None

    orders_to_try = []
    if with_drift:
        # Linear drift for integrated series (trend='t') to prevent flat-line collapse
        orders_to_try.extend([
            ((1, 1, 0), "t"),
            ((1, 1, 1), "t"),
            ((0, 1, 1), "t"),
            ((1, 1, 0), None),
            ((0, 1, 1), None),
            ((1, 0, 0), "c"),
        ])
    else:
        orders_to_try.extend([
            ((1, 1, 0), None),
            ((0, 1, 1), None),
            ((1, 0, 0), "c"),
        ])

    for order, trend in orders_to_try:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ARIMA(y_train, order=order, trend=trend)
                fit_res = model.fit()
                train_pred = fit_res.fittedvalues
                future_pred = fit_res.forecast(steps=steps_ahead)
                return np.array(train_pred), np.array(future_pred), f"ARIMA{order}"
        except Exception:
            continue
    return None


def downsample_forecast_timeline(
    combined_timeline: List[Dict[str, Any]],
    target_year: int,
    predicted_value: Optional[float] = None,
    lower_bound: Optional[float] = None,
    upper_bound: Optional[float] = None,
    model_used: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Downsample a multi-year forecast timeline into clean milestone points.
    If len(combined_timeline) <= 24, returns the timeline as-is (with forecast metadata).
    If len(combined_timeline) > 24, downsamples into annual milestones:
    - 1 representative point per historical year (the latest available month/quarter of each year,
      guaranteeing the latest actual historical DWH point like 2026-M09 is preserved)
    - 1 forecast point per future year (2027, 2028, 2029, ..., target_year with exact predicted_value)
    """
    if len(combined_timeline) <= 24:
        res = []
        for pt in combined_timeline:
            d = dict(pt)
            if d.get("is_forecast") and model_used and not d.get("model_used"):
                d["model_used"] = model_used
            res.append(d)
        return res

    hist_pts = [p for p in combined_timeline if not p.get("is_forecast")]
    fc_pts = [p for p in combined_timeline if p.get("is_forecast")]

    # 1. Historical milestones: 1 point per year (latest available month/quarter)
    hist_by_year = {}
    for p in hist_pts:
        y = p.get("year")
        if not y:
            m = re.match(r"^(\d{4})", str(p.get("period_key") or ""))
            y = int(m.group(1)) if m else None
        if y:
            hist_by_year[y] = p

    downsampled = []
    for y in sorted(hist_by_year.keys()):
        pt = dict(hist_by_year[y])
        pt["is_forecast"] = False
        pt["status"] = "valid"
        downsampled.append(pt)

    # 2. Future forecast points: 1 point per future year (years > max historical year)
    max_hist_year = max(hist_by_year.keys()) if hist_by_year else 2026
    fc_by_year = {}
    for p in fc_pts:
        y = p.get("year")
        if not y:
            m = re.match(r"^(\d{4})", str(p.get("period_key") or ""))
            y = int(m.group(1)) if m else None
        if y and y > max_hist_year:
            if y not in fc_by_year:
                fc_by_year[y] = []
            fc_by_year[y].append(p)

    for y in sorted(fc_by_year.keys()):
        pts = fc_by_year[y]
        if y == target_year and predicted_value is not None:
            val = float(predicted_value)
            lo = float(lower_bound) if lower_bound is not None else min(p.get("lower_bound", val) for p in pts)
            hi = float(upper_bound) if upper_bound is not None else max(p.get("upper_bound", val) for p in pts)
        else:
            val = float(np.mean([p["value"] for p in pts]))
            lo = float(np.mean([p.get("lower_bound", val) for p in pts]))
            hi = float(np.mean([p.get("upper_bound", val) for p in pts]))

        rep_pt = dict(pts[-1])
        rep_pt["period_key"] = str(y)
        rep_pt["year"] = y
        rep_pt["value"] = _sanitize_float(val)
        rep_pt["lower_bound"] = _sanitize_float(lo)
        rep_pt["upper_bound"] = _sanitize_float(hi)
        rep_pt["is_forecast"] = True
        rep_pt["status"] = "forecast"
        if model_used:
            rep_pt["model_used"] = model_used
        downsampled.append(rep_pt)

    return downsampled


def run_time_series_forecast(
    historical_points: List[Dict[str, Any]],
    target_year: int,
    indicator_name: str = "",
    item_code: Optional[str] = None,
    item_name: Optional[str] = None,
    unit: str = "",
    lang: str = "uz_latn"
) -> Dict[str, Any]:
    """
    Execute deterministic ML forecasting for a given indicator series.

    Args:
        historical_points: Historical records with period_key, value, year.
        target_year: Requested projection year (e.g. 2027 to 2036).
        indicator_name: Indicator title.
        item_code: Product or region item code.
        item_name: Product or region name.
        unit: Measurement unit (e.g., 'ming so'm', 'kishi').
        lang: Target language for textual fields.

    Returns:
        Structured forecast dictionary including predicted value, 95% CI,
        selected ML model, validation metrics, and combined timeline.
    """
    # 1. Horizon guard check
    if target_year > 2036:
        return {
            "status": "error",
            "error_code": "EXTREME_HORIZON",
            "message": "Prognozlash gorizonti maksimal 10 yil (2036-yilgacha) bilan cheklangan.",
            "target_year": target_year
        }

    # 2. Extract valid points
    valid_points = []
    for pt in historical_points:
        val = pt.get("value")
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            p_key = str(pt.get("period_key") or "")
            # Determine year
            y = pt.get("year")
            if not y and p_key:
                m_year = re.match(r"^(\d{4})", p_key)
                if m_year:
                    y = int(m_year.group(1))
            valid_points.append({
                "period_key": p_key,
                "year": y,
                "value": float(val),
                "status": pt.get("status", "valid"),
                "is_forecast": False
            })

    if len(valid_points) < 3:
        return {
            "status": "error",
            "error_code": "INSUFFICIENT_DATA",
            "message": f"Prognozlash uchun kamida 3 ta tarixiy davr ma'lumoti talab qilinadi (mavjud: {len(valid_points)} ta).",
            "history_count": len(valid_points)
        }

    # 3. Detect frequency
    sample_key = valid_points[-1]["period_key"]
    is_monthly = bool(re.search(r"-M\d{1,2}$", sample_key, re.IGNORECASE))
    is_quarterly = bool(re.search(r"-Q\d$", sample_key, re.IGNORECASE))

    # Sort chronologically
    if is_monthly:
        def _month_sort_key(p):
            m = re.search(r"^(\d{4})-M0?(\d{1,2})", p["period_key"], re.IGNORECASE)
            return (int(m.group(1)), int(m.group(2))) if m else (p["year"] or 0, 0)
        valid_points.sort(key=_month_sort_key)
    elif is_quarterly:
        def _quarter_sort_key(p):
            m = re.search(r"^(\d{4})-Q0?(\d)", p["period_key"], re.IGNORECASE)
            return (int(m.group(1)), int(m.group(2))) if m else (p["year"] or 0, 0)
        valid_points.sort(key=_quarter_sort_key)
    else:
        valid_points.sort(key=lambda p: (p["year"] or 0, p["period_key"]))

    y_all = np.array([p["value"] for p in valid_points], dtype=float)
    n_points = len(y_all)

    # Determine horizon steps
    last_pt = valid_points[-1]
    last_p_key = last_pt["period_key"]
    last_year = last_pt["year"] or int(last_p_key[:4])

    if target_year <= last_year:
        target_year = last_year + 1

    steps_ahead = 1
    new_periods: List[Dict[str, Any]] = []

    if is_monthly:
        # From last year/month to target_year-M12
        m_match = re.search(r"^(\d{4})-M0?(\d{1,2})", last_p_key, re.IGNORECASE)
        cur_y = int(m_match.group(1)) if m_match else last_year
        cur_m = int(m_match.group(2)) if m_match else 9

        period_keys = []
        while True:
            cur_m += 1
            if cur_m > 12:
                cur_m = 1
                cur_y += 1
            p_code = f"{cur_y}-M{cur_m:02d}"
            period_keys.append((p_code, cur_y, cur_m))
            if cur_y == target_year and cur_m == 12:
                break
            if cur_y > target_year:
                break

        steps_ahead = max(1, len(period_keys))
        new_periods = [{"period_key": pk, "year": yr, "month": mo} for pk, yr, mo in period_keys]
    elif is_quarterly:
        q_match = re.search(r"^(\d{4})-Q0?(\d)", last_p_key, re.IGNORECASE)
        cur_y = int(q_match.group(1)) if q_match else last_year
        cur_q = int(q_match.group(2)) if q_match else 4

        period_keys = []
        while True:
            cur_q += 1
            if cur_q > 4:
                cur_q = 1
                cur_y += 1
            p_code = f"{cur_y}-Q{cur_q}"
            period_keys.append((p_code, cur_y, cur_q))
            if cur_y == target_year and cur_q == 4:
                break
            if cur_y > target_year:
                break

        steps_ahead = max(1, len(period_keys))
        new_periods = [{"period_key": pk, "year": yr, "quarter": qtr} for pk, yr, qtr in period_keys]
    else:
        # Annual
        period_keys = []
        for y_step in range(last_year + 1, target_year + 1):
            period_keys.append(str(y_step))
        steps_ahead = max(1, len(period_keys))
        new_periods = [{"period_key": pk, "year": int(pk)} for pk in period_keys]

    # 4. Trend characteristics and multi-year horizon detection
    t_idx = np.arange(n_points)
    denom = np.sum((t_idx - np.mean(t_idx)) ** 2)
    slope = float(np.sum((t_idx - np.mean(t_idx)) * (y_all - np.mean(y_all))) / (denom if denom > 0 else 1.0))
    mean_val = float(np.mean(np.abs(y_all))) or 1.0
    total_hist_trend_pct = abs(slope * max(1, n_points - 1)) / mean_val
    has_clear_trend = bool(total_hist_trend_pct >= 0.05)

    is_multi_year = bool(
        (is_monthly and steps_ahead >= 12)
        or (is_quarterly and steps_ahead >= 4)
        or ((not is_monthly and not is_quarterly) and steps_ahead >= 2)
    )

    # 5. Holdout Backtest Model Selection
    holdout_size = 1
    if n_points >= 8:
        holdout_size = max(2, min(4, int(n_points * 0.2)))
    elif n_points >= 5:
        holdout_size = 2

    can_backtest = (n_points - holdout_size) >= 3

    best_model_name = "Ridge Regression"
    best_mape = 999.0
    best_mae = 999.0

    if can_backtest:
        train_y = y_all[:-holdout_size]
        test_y = y_all[-holdout_size:]

        candidate_fits = []

        # Candidate 1: Ridge
        try:
            _, r_pred, r_name = _fit_ridge(
                train_y, holdout_size, is_periodic=is_monthly, cycle=12
            )
            candidate_fits.append((r_name, r_pred))
        except Exception:
            pass

        # Candidate 2: Holt-Winters ETS
        try:
            ets_res = _fit_ets(train_y, holdout_size, is_periodic=is_monthly, cycle=12)
            if ets_res:
                candidate_fits.append((ets_res[2], ets_res[1]))
        except Exception:
            pass

        # Candidate 3: ARIMA
        try:
            arima_res = _fit_arima(train_y, holdout_size, with_drift=has_clear_trend)
            if arima_res:
                candidate_fits.append((arima_res[2], arima_res[1]))
        except Exception:
            pass

        for name, pred in candidate_fits:
            mape = _safe_mape(test_y, pred)
            mae = _safe_mae(test_y, pred)
            if mape < best_mape:
                best_mape = mape
                best_mae = mae
                best_model_name = name

    # 6. Fit selected model on full dataset
    final_future_pred = None
    final_train_pred = None

    if "Holt-Winters" in best_model_name:
        ets_res = _fit_ets(y_all, steps_ahead, is_periodic=is_monthly, cycle=12)
        if ets_res:
            final_train_pred, final_future_pred, _ = ets_res

    if final_future_pred is None and "ARIMA" in best_model_name:
        arima_res = _fit_arima(y_all, steps_ahead, with_drift=has_clear_trend)
        if arima_res:
            final_train_pred, final_future_pred, _ = arima_res

    if final_future_pred is None:
        best_model_name = "Ridge Regression"
        final_train_pred, final_future_pred, _ = _fit_ridge(
            y_all, steps_ahead, is_periodic=is_monthly, cycle=12
        )

    # 6.1 Trend-consistency guard: prevent flat-line collapse on multi-year horizons
    if has_clear_trend and is_multi_year and final_future_pred is not None:
        fc_change = abs(float(final_future_pred[-1]) - float(y_all[-1]))
        expected_drift = abs(float(slope) * steps_ahead)
        if fc_change < 0.15 * expected_drift:
            # Selected model flat-lined; switch to a trended model
            ets_res = _fit_ets(y_all, steps_ahead, is_periodic=is_monthly, cycle=12)
            if ets_res and abs(float(ets_res[1][-1]) - float(y_all[-1])) >= 0.15 * expected_drift:
                final_train_pred, final_future_pred, best_model_name = ets_res
            else:
                final_train_pred, final_future_pred, best_model_name = _fit_ridge(
                    y_all, steps_ahead, is_periodic=is_monthly, cycle=12
                )

    # In-sample metrics if holdout was not possible
    if not can_backtest:
        best_mape = _safe_mape(y_all, final_train_pred)
        best_mae = _safe_mae(y_all, final_train_pred)

    # 7. Residual Variance and 95% Confidence Interval
    residuals = y_all - final_train_pred
    sigma = float(np.std(residuals)) if len(residuals) > 0 else 1.0
    if sigma < 1e-4:
        sigma = float(np.mean(np.abs(y_all))) * 0.03 or 1.0

    forecast_series = []
    is_non_negative = bool(np.all(y_all >= 0))

    for idx, meta in enumerate(new_periods):
        h = idx + 1
        val_pred = float(final_future_pred[idx])

        # Confidence margin expands with forecast horizon sqrt(h)
        margin = 1.96 * sigma * math.sqrt(1.0 + 0.15 * h)
        lo_bound = val_pred - margin
        if is_non_negative and lo_bound < 0:
            lo_bound = 0.0
        hi_bound = val_pred + margin

        point = {
            "period_key": meta["period_key"],
            "year": int(meta["year"]) if meta.get("year") is not None else None,
            "value": _sanitize_float(val_pred),
            "lower_bound": _sanitize_float(lo_bound),
            "upper_bound": _sanitize_float(hi_bound),
            "status": "forecast",
            "is_forecast": True
        }
        forecast_series.append(point)

    # 7. Extract primary target year prediction
    target_year_points = [p for p in forecast_series if p.get("year") == target_year]
    if target_year_points:
        # If monthly/quarterly, compute target year average or final point
        if is_monthly or is_quarterly:
            vals = [p["value"] for p in target_year_points]
            prim_pred = float(np.mean(vals))
            prim_lo = float(np.mean([p["lower_bound"] for p in target_year_points]))
            prim_hi = float(np.mean([p["upper_bound"] for p in target_year_points]))
        else:
            prim_pt = target_year_points[0]
            prim_pred = prim_pt["value"]
            prim_lo = prim_pt["lower_bound"]
            prim_hi = prim_pt["upper_bound"]
    else:
        prim_pt = forecast_series[-1]
        prim_pred = prim_pt["value"]
        prim_lo = prim_pt["lower_bound"]
        prim_hi = prim_pt["upper_bound"]

    # Clamp bounds
    if is_non_negative and prim_lo < 0:
        prim_lo = 0.0

    history_start = valid_points[0]["period_key"]
    history_end = valid_points[-1]["period_key"]
    last_actual_pt = valid_points[-1]
    last_actual_val = _sanitize_float(last_actual_pt["value"])
    last_actual_period = last_actual_pt["period_key"]

    combined_timeline = list(valid_points) + forecast_series

    chart_timeline = downsample_forecast_timeline(
        combined_timeline,
        target_year=int(target_year),
        predicted_value=prim_pred,
        lower_bound=prim_lo,
        upper_bound=prim_hi,
        model_used=best_model_name
    )

    return {
        "status": "success",
        "indicator_name": indicator_name,
        "item_code": item_code,
        "item_name": item_name,
        "unit": unit,
        "target_year": int(target_year),
        "predicted_value": _sanitize_float(prim_pred),
        "lower_bound": _sanitize_float(prim_lo),
        "upper_bound": _sanitize_float(prim_hi),
        "last_actual_value": last_actual_val,
        "last_actual_period": last_actual_period,
        "confidence_level": 95,
        "model_used": str(best_model_name),
        "mape": _sanitize_float(best_mape),
        "mae": _sanitize_float(best_mae),
        "history_count": int(n_points),
        "history_start": history_start,
        "history_end": history_end,
        "history_range": f"{history_start} - {history_end}",
        "forecast_series": forecast_series,
        "combined_timeline": combined_timeline,
        "chart_timeline": chart_timeline
    }

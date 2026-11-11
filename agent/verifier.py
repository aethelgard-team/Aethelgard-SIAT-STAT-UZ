"""
=============================================================================
SIAT STAT DWH: Zero-Hallucination Number Verifier (agent/verifier.py)
Loyiha: siat.stat.uz MCP Loyihasi
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  LLM generatsiya qilgan matnni alohida jumlalarga ajratib, ulardagi barcha
  raqamlarni (o'zbekcha va xalqaro formatlar: 127 857,3, 127,857.3, 127857.3, 1.6%)
  DWH dan olingan xom faktlar bilan qat'iy tekshiradi.
  Agar jumlada to'qilgan (bazada yo'q) raqam uchrasa, jumla yakuniy javobdan
  butunlay olib tashlanadi (passed: False).
=============================================================================
"""

import re
from typing import List, Dict, Any, Set, Tuple, Optional


def parse_number_string(raw: str) -> List[float]:
    """
    Turli formatlardagi (bo'shliq, vergul, nuqta, foiz) raqam satrini
    ehtimoliy float qiymatlariga aylantiradi.
    """
    s = raw.strip().rstrip("%").strip()
    s = s.replace(" ", "").replace("\xa0", "")
    candidates: List[float] = []

    # 1. Ham vergul, ham nuqta qatnashgan holat:
    if "," in s and "." in s:
        if s.rfind(",") < s.rfind("."):
            # 127,857.3 -> 127857.3 (vergul - minglik ajratuvchi, nuqta - o'nlik)
            cleaned = s.replace(",", "")
            try:
                candidates.append(float(cleaned))
            except ValueError:
                pass
        else:
            # 127.857,3 -> 127857.3 (nuqta - minglik ajratuvchi, vergul - o'nlik)
            cleaned = s.replace(".", "").replace(",", ".")
            try:
                candidates.append(float(cleaned))
            except ValueError:
                pass
    elif "," in s:
        # Faqat vergul qatnashgan:
        if s.count(",") > 1:
            # 1,234,567 -> 1234567
            try:
                candidates.append(float(s.replace(",", "")))
            except ValueError:
                pass
        else:
            # Bitta vergul: 127,3 (o'nlik) yoki 127,857 (minglik) bo'lishi mumkin
            try:
                candidates.append(float(s.replace(",", ".")))
            except ValueError:
                pass
            try:
                candidates.append(float(s.replace(",", "")))
            except ValueError:
                pass
    else:
        # Nuqtali yoki butun son
        try:
            candidates.append(float(s))
        except ValueError:
            pass

    return candidates


def extract_numbers_from_text(text: str) -> List[Tuple[str, List[float]]]:
    """
    Matndan barcha raqamlarni (turli formatlardagi: bo'shliqli, vergulli, foizli)
    ajratib olib, (xom_satr, [float_qiymatlar]) ko'rinishida qaytaradi.
    Izoh havolalari (masalan [1], [2]) statistik son hisoblanmaydi va chiqarib tashlanadi.
    """
    if not text:
        return []

    # Manba havolalarini ([1], [2], [1, 2]) olib tashlash
    clean_text = re.sub(r"\[\s*\d+(?:\s*,\s*\d+)*\s*\]", " ", text)

    pattern = re.compile(
        r"""
        (?:
            # Comma thousands with optional dot decimal: 127,857.3 or 127,857
            \b\d{1,3}(?:,\d{3})+(?:\.\d+)?%?
            |
            # Space thousands with optional comma or dot decimal: 127 857,3 or 127 857.3
            \b\d{1,3}(?:[ \xa0]\d{3})+(?:[.,]\d+)?%?
            |
            # Dot thousands with optional comma decimal: 127.857,3 or 127.857
            \b\d{1,3}(?:\.\d{3})+(?:,\d+)?%?
            |
            # Plain number with optional decimal: 127857.3 or 127857,3 or 127857
            \b\d+(?:[.,]\d+)?%?
        )
        """,
        re.VERBOSE
    )

    matches = pattern.findall(clean_text)
    results: List[Tuple[str, List[float]]] = []

    for raw in matches:
        raw_clean = raw.strip()
        if not raw_clean:
            continue
        vals = parse_number_string(raw_clean)
        if vals:
            results.append((raw_clean, vals))

    return results


def collect_dwh_numbers(tool_data: Any) -> Set[float]:
    """
    DWH asboblari qaytargan xom natijalardan (jadval, metadata, timeline)
    barcha ruxsat etilgan haqiqiy raqamlarni to'playdi.
    """
    numbers: Set[float] = set()

    def scan_obj(obj: Any):
        if obj is None:
            return
        elif isinstance(obj, (int, float)):
            numbers.add(float(obj))
        elif isinstance(obj, str):
            # Qatordagi sonlarni ham tekshirish (masalan: '127857.3', '2026-M09')
            # Yil va oylarni ajratish
            for m in re.findall(r"\d+(?:\.\d+)?", obj):
                try:
                    numbers.add(float(m))
                except ValueError:
                    pass
        elif isinstance(obj, dict):
            for v in obj.values():
                scan_obj(v)
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                scan_obj(item)

    scan_obj(tool_data)
    return numbers


def is_number_in_dwh(number: float, dwh_numbers: Set[float], tolerance: float = 0.05) -> bool:
    """
    Berilgan raqam DWH raqamlari to'plamida mavjudligini tekshiradi (kichik xatolik chegarasi bilan).
    """
    for dwh_num in dwh_numbers:
        if abs(number - dwh_num) <= tolerance:
            return True
        if dwh_num != 0 and abs((number - dwh_num) / dwh_num) < 0.001:
            return True
    return False


def split_into_sentences(text: str) -> List[str]:
    """Matnni alohida mantiqiy jumlalarga ajratadi."""
    if not text:
        return []

    raw_sentences = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"(?<=[.!?])\s+", line)
        for p in parts:
            p_clean = p.strip()
            if p_clean:
                raw_sentences.append(p_clean)

    return raw_sentences


def verify_text(llm_text: str, tool_results: Any) -> Dict[str, Any]:
    """
    LLM javobini DWH faktlari bilan verifikatsiya qiladi.

    Qoidalar:
    - Jumlada hech qanday raqam bo'lmasa -> passed: True.
    - Jumlada raqam bo'lsa va ularning HAMMASI DWH da mavjud bo'lsa -> passed: True.
    - Jumlada bitta bo'lsa ham DWH da yo'q to'qilgan raqam bo'lsa -> passed: False, jumla olib tashlanadi.

    Returns:
        Dict: {"all_passed": bool, "sentences": [...], "verified_text": str}
    """
    dwh_numbers = collect_dwh_numbers(tool_results)
    sentences = split_into_sentences(llm_text)

    verified_sentences = []
    all_passed = True

    for s in sentences:
        extracted = extract_numbers_from_text(s)

        if not extracted:
            # Raqamsiz oddiy jumla (izoh yoki kirish so'z)
            verified_sentences.append({
                "text": s,
                "passed": True,
                "reason": None,
                "extracted_numbers": []
            })
            continue

        sentence_passed = True
        failed_number = None

        for raw_num_str, candidate_vals in extracted:
            # Kamida bitta mos keluvchi qiymat bormi?
            matched = any(is_number_in_dwh(v, dwh_numbers) for v in candidate_vals)
            if not matched:
                sentence_passed = False
                failed_number = raw_num_str
                break

        if sentence_passed:
            verified_sentences.append({
                "text": s,
                "passed": True,
                "reason": None,
                "extracted_numbers": [vals[0] for _, vals in extracted]
            })
        else:
            all_passed = False
            verified_sentences.append({
                "text": s,
                "passed": False,
                "reason": f"Raqam bazada topilmadi: '{failed_number}'",
                "extracted_numbers": [vals[0] for _, vals in extracted]
            })

    # Faqat verifikatsiyadan o'tgan jumlalarni qoldirish
    surviving_sentences = [item["text"] for item in verified_sentences if item["passed"]]
    verified_text = " ".join(surviving_sentences).strip()

    if not verified_text and sentences:
        verified_text = "Ushbu so'rov bo'yicha bazada tasdiqlangan ma'lumot topilmadi."

    return {
        "all_passed": all_passed,
        "total_sentences": len(sentences),
        "passed_sentences_count": len(surviving_sentences),
        "failed_sentences_count": len(sentences) - len(surviving_sentences),
        "sentences": verified_sentences,
        "verified_text": verified_text
    }

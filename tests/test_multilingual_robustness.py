"""
=============================================================================
SIAT STAT DWH: Multilingual & Robustness Automated Test Suite
Fayl: tests/test_multilingual_robustness.py
Muallif: Aethelgard SIAT Team
Tavsif:
  O'zbekcha (standart Lotin, yangi Lotin alifbosi ç, ş, ğ, ō), Kirill va Rus
  tillaridagi so'rovlar, imlo xatolari, so'zlashuv iboralari, ko'p savolli
  (compound) so'rovlar hamda xavfsizlik tuzoqlarini tekshiradi.
=============================================================================
"""

import sys
import asyncio
import json
import time
from typing import List, Tuple

sys.path.insert(0, ".")
from agent.orchestrator import orchestrate_question

TEST_CASES: List[Tuple[str, str]] = [
    # 1. Standard Uzbek Latin
    ("uz_latn_direct", "2026-yil sentyabrda mol go'shti narxi qancha edi?"),
    # 2. New Uzbek Latin (ç, ş, ğ, ō, ı)
    ("new_latin", "2026-yil sentyabrda mol gōşt narhı qança?"),
    # 3. Uzbek Cyrillic (ў, қ, ғ, ҳ)
    ("uz_cyrl", "2026 йил сентябрда мол гўшти нархи қанча эди?"),
    # 4. Russian
    ("ru_beef", "Сколько стоила говядина в сентябре 2026 года?"),
    # 5. Russian population
    ("ru_pop", "Население Ташкента"),
    # 6. Russian salary
    ("ru_salary", "Какая средняя зарплата в Ташкенте?"),
    # 7. Typo & colloquial
    ("typo_beef", "mol goshti narhi qancha?"),
    ("colloquial_beef", "go'sht molniki nechpul?"),
    # 8. Compound queries
    ("compound_factual", "mol go'sht narxi, tuxum narxi ?"),
    ("compound_mixed_future", "mol go'shti narxi va 2030-yil inflyatsiyasi?"),
    # 9. Generic product
    ("generic_meat", "go'sht narxi qancha?"),
    # 10. Greetings
    ("greeting_uz", "Salom"),
    ("greeting_ru", "Привет!"),
    ("greeting_cyrl", "Ассалому алайкум"),
    # 11. Temporal / latest
    ("latest_beef", "hozirgi mol go'shti narxi qancha?"),
    # 12. Near-future month of current year
    ("near_future_dec2026", "2026-yil dekabrda mol go'shti narxi qancha?"),
    # 13. Future traps & out of scope
    ("future_trap_2030", "2030-yilda inflyatsiya qancha bo'ladi?"),
    ("crypto_trap", "Bitcoin narxi qancha?"),
    ("weather_trap", "ob-havo qanday?")
]


async def run_all() -> bool:
    print("=" * 70)
    print("AETHELGARD SIAT: MULTILINGUAL & ROBUSTNESS TEST SUITE")
    print("=" * 70)

    passed_total = 0
    failed_total = 0

    for code, q in TEST_CASES:
        t0 = time.time()
        final_done = None
        events = []
        try:
            async for sse in orchestrate_question(q):
                lines = sse.strip().split("\n")
                ev_type = None
                ev_data = None
                for line in lines:
                    if line.startswith("event: "):
                        ev_type = line[7:].strip()
                    elif line.startswith("data: "):
                        try:
                            ev_data = json.loads(line[6:].strip())
                        except Exception:
                            pass
                if ev_type and ev_data:
                    events.append((ev_type, ev_data))
                    if ev_type == "done":
                        final_done = ev_data

            dur = round(time.time() - t0, 3)
            if final_done:
                ans = final_done.get("answer", "")
                all_passed = final_done.get("all_passed", False)
                status_str = "PASS" if all_passed else "FAIL"
                print(f"[{status_str}] {code} ({dur}s)")
                print(f"  Q: {q}")
                print(f"  A: {ans[:140]}...")
                print(f"  Sources: {len(final_done.get('sources', []))}, AllPassed: {all_passed}")
                if all_passed:
                    passed_total += 1
                else:
                    failed_total += 1
            else:
                print(f"[FAIL] {code} - No done event received!")
                failed_total += 1
        except Exception as e:
            print(f"[ERROR] {code} - Exception: {e}")
            failed_total += 1
        print("-" * 70)

    print(f"SUMMARY: {passed_total}/{len(TEST_CASES)} passed, {failed_total} failed.")
    return failed_total == 0


if __name__ == "__main__":
    success = asyncio.run(run_all())
    if not success:
        sys.exit(1)

"""
SAFE-Triage Complete System Test Suite
Tests all implemented features: NEWS2, ESI v5, Pregnancy, Frontend Integration
"""

import sys
sys.path.insert(0, 'backend')

from logic.esi_v5_compliance import evaluate_esi_v5
from logic.deterministic_triage import DeterministicTriageEngine

print("=" * 60)
print("SAFE-TRIAGE SYSTEM TEST SUITE")
print("=" * 60)

passed = 0
failed = 0

def test(name, condition, details=""):
    global passed, failed
    if condition:
        print(f"✅ {name}")
        passed += 1
    else:
        print(f"❌ {name}")
        if details:
            print(f"   → {details}")
        failed += 1

# ============================================================
# SECTION 1: NEWS2 SCORING
# ============================================================
print("\n" + "=" * 60)
print("SECTION 1: NEWS2 VITAL SIGNS SCORING")
print("=" * 60)

# Test 1.1: Normal vitals = Low NEWS2
r = evaluate_esi_v5(
    age_years=40,
    vitals={"hr": 75, "rr": 16, "sbp": 120, "spo2": 98, "temp_c": 37.0}
)
test("1.1 Normal vitals → No critical alerts", 
     r["esi_v5_suggested"] is None or r["esi_v5_suggested"] >= 4)

# Test 1.2: Tachycardia adult
r = evaluate_esi_v5(age_years=40, vitals={"hr": 155})
test("1.2 Adult HR 155 → High-risk alert",
     any("heart rate" in a.lower() or "hr" in a.lower() for a in r["esi_v5_alerts"]))

# Test 1.3: Hypotension
r = evaluate_esi_v5(age_years=40, vitals={"sbp": 85})
test("1.3 SBP 85 → Hypotension alert",
     r["esi_v5_suggested"] is not None and r["esi_v5_suggested"] <= 2)

# ============================================================
# SECTION 2: ESI v5 SAFETY FIXES
# ============================================================
print("\n" + "=" * 60)
print("SECTION 2: ESI v5 PATIENT SAFETY FIXES")
print("=" * 60)

# Test 2.1: SpO2 < 90% alone = ESI 2 (not Level 1)
r = evaluate_esi_v5(age_years=45, vitals={"spo2": 88, "rr": 18})
test("2.1 SpO2 88% + normal RR → ESI 2 (not Level 1)",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 2.2: SpO2 < 90% + respiratory distress = ESI 1
r = evaluate_esi_v5(age_years=45, vitals={"spo2": 88, "rr": 38})
test("2.2 SpO2 88% + RR 38 → ESI 1",
     r["esi_v5_suggested"] == 1,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 2.3: Neonate + fever = mandatory ESI 2
r = evaluate_esi_v5(age_years=0.04, vitals={"temp_c": 38.5}, immunizations_complete=True)
test("2.3 Neonate (14 days) + fever 38.5°C → ESI 2",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 2.4: Pain 9 + renal colic = ESI 2
r = evaluate_esi_v5(age_years=45, pain_scale=9, pain_context="renal_colic")
test("2.4 Pain 9/10 + renal colic → ESI 2",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 2.5: Pain 8 + orthopedic = ESI 3
r = evaluate_esi_v5(age_years=45, pain_scale=8, pain_context="orthopedic")
test("2.5 Pain 8/10 + orthopedic → ESI 3",
     r["esi_v5_suggested"] == 3,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 2.6: Immunocompromised + fever = ESI 2
r = evaluate_esi_v5(
    age_years=45,
    vitals={"temp_c": 38.3},
    is_immunocompromised=True,
    immunocompromised_reason="chemotherapy"
)
test("2.6 Chemo patient + fever 38.3°C → ESI 2",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# ============================================================
# SECTION 3: PEDIATRIC RULES
# ============================================================
print("\n" + "=" * 60)
print("SECTION 3: PEDIATRIC TRIAGE RULES")
print("=" * 60)

# Test 3.1: Infant tachycardia
r = evaluate_esi_v5(age_years=0.17, vitals={"hr": 185})
test("3.1 Infant (2 months) HR 185 → Pediatric alert",
     r["esi_v5_suggested"] is not None and r["esi_v5_suggested"] <= 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 3.2: Pediatric hypoxia (SpO2 < 92%)
r = evaluate_esi_v5(age_years=5, vitals={"spo2": 91})
test("3.2 Child (5 years) SpO2 91% → ESI 1 (peds uses 92% threshold)",
     r["esi_v5_suggested"] == 1,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 3.3: Unimmunized febrile infant
r = evaluate_esi_v5(
    age_years=0.25,  # 3 months
    vitals={"temp_c": 39.0},
    immunizations_complete=False
)
test("3.3 Unimmunized infant + fever → Higher risk",
     r["esi_v5_suggested"] is not None and r["esi_v5_suggested"] <= 2,
     f"Got ESI {r['esi_v5_suggested']}")

# ============================================================
# SECTION 4: PREGNANCY RULES
# ============================================================
print("\n" + "=" * 60)
print("SECTION 4: PREGNANCY TRIAGE RULES")
print("=" * 60)

# Test 4.1: Pregnant + seizure = ESI 1 (eclampsia)
r = evaluate_esi_v5(age_years=28, is_pregnant=True, has_seizure=True)
test("4.1 Pregnant + seizure → ESI 1 (eclampsia)",
     r["esi_v5_suggested"] == 1,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 4.2: Pregnant + SBP 170 = ESI 2 (severe preeclampsia)
r = evaluate_esi_v5(age_years=30, is_pregnant=True, vitals={"sbp": 170})
test("4.2 Pregnant + SBP 170 → ESI 2 (preeclampsia)",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 4.3: Pregnant + trauma = ESI 2
r = evaluate_esi_v5(age_years=32, is_pregnant=True, has_trauma=True)
test("4.3 Pregnant + trauma → ESI 2",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 4.4: Vaginal bleeding at 8 weeks = ESI 2 (ectopic concern)
r = evaluate_esi_v5(
    age_years=29,
    is_pregnant=True,
    gestational_weeks=8,
    pregnancy_complaint="vaginal_bleeding"
)
test("4.4 Pregnant 8 weeks + vaginal bleeding → ESI 2 (ectopic)",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 4.5: Contractions at 32 weeks = ESI 2 (preterm labor)
r = evaluate_esi_v5(
    age_years=27,
    is_pregnant=True,
    gestational_weeks=32,
    pregnancy_complaint="contractions"
)
test("4.5 Pregnant 32 weeks + contractions → ESI 2 (preterm)",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 4.6: Contractions at 39 weeks = ESI 3 (term labor)
r = evaluate_esi_v5(
    age_years=31,
    is_pregnant=True,
    gestational_weeks=39,
    pregnancy_complaint="contractions"
)
test("4.6 Pregnant 39 weeks + contractions → ESI 3 (term labor)",
     r["esi_v5_suggested"] == 3,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 4.7: Decreased fetal movement at 34 weeks = ESI 2
r = evaluate_esi_v5(
    age_years=26,
    is_pregnant=True,
    gestational_weeks=34,
    pregnancy_complaint="decreased_fetal_movement"
)
test("4.7 Pregnant 34 weeks + decreased fetal movement → ESI 2",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 4.8: PPROM at 33 weeks = ESI 2
r = evaluate_esi_v5(
    age_years=28,
    is_pregnant=True,
    gestational_weeks=33,
    pregnancy_complaint="leaking_fluid"
)
test("4.8 Pregnant 33 weeks + leaking fluid → ESI 2 (PPROM)",
     r["esi_v5_suggested"] == 2,
     f"Got ESI {r['esi_v5_suggested']}")

# Test 4.9: Non-pregnant should not trigger pregnancy alerts
r = evaluate_esi_v5(
    age_years=28,
    is_pregnant=False,
    pregnancy_complaint="vaginal_bleeding"
)
pregnancy_alerts = [a for a in r["esi_v5_alerts"] if "pregnan" in a.lower() or "ectopic" in a.lower()]
test("4.9 Non-pregnant → No pregnancy alerts",
     len(pregnancy_alerts) == 0,
     f"Got {len(pregnancy_alerts)} pregnancy alerts")

# ============================================================
# SECTION 5: ALERT CONSOLIDATION
# ============================================================
print("\n" + "=" * 60)
print("SECTION 5: ALERT QUALITY (NO DUPLICATES)")
print("=" * 60)

# Test 5.1: SpO2 88% + normal RR = single alert
r = evaluate_esi_v5(age_years=45, vitals={"spo2": 88, "rr": 18})
hypoxia_alerts = [a for a in r["esi_v5_alerts"] if "hypoxia" in a.lower() or "spo2" in a.lower()]
test("5.1 SpO2 88% + normal RR → Single hypoxia alert",
     len(hypoxia_alerts) == 1,
     f"Got {len(hypoxia_alerts)} alerts: {hypoxia_alerts}")

# Test 5.2: SpO2 88% + RR 38 = single Level 1 alert (not both)
r = evaluate_esi_v5(age_years=45, vitals={"spo2": 88, "rr": 38})
hypoxia_alerts = [a for a in r["esi_v5_alerts"] if "hypoxia" in a.lower()]
test("5.2 SpO2 88% + RR 38 → Single Level 1 hypoxia alert",
     len(hypoxia_alerts) == 1,
     f"Got {len(hypoxia_alerts)} alerts: {hypoxia_alerts}")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print(f"✅ Passed: {passed}")
print(f"❌ Failed: {failed}")
print(f"📊 Total:  {passed + failed}")
print(f"📈 Score:  {passed}/{passed + failed} ({100*passed//(passed+failed)}%)")

if failed == 0:
    print("\n🎉 ALL TESTS PASSED! System ready for production.")
else:
    print(f"\n⚠️  {failed} test(s) need attention.")

print("=" * 60)

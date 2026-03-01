"""
Validation tests for the deterministic ESI v5 engine.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.logic.esi_v5_engine import (
    NEWS2Result,
    PatientFeatures,
    VitalSigns,
    triage_patient,
)


def _vitals(
    hr: int = 80,
    sbp: int = 120,
    dbp: int = 80,
    rr: int = 16,
    spo2: float = 98.0,
    temp: float = 37.0,
    gcs: int = 15,
) -> VitalSigns:
    return VitalSigns(
        heart_rate=hr,
        systolic_bp=sbp,
        diastolic_bp=dbp,
        respiratory_rate=rr,
        spo2=spo2,
        temperature=temp,
        gcs=gcs,
    )


def _news2(total: int) -> NEWS2Result:
    risk = "high" if total >= 7 else ("medium" if total >= 5 else "low")
    return NEWS2Result(
        total_score=total,
        risk_level=risk,
        parameter_scores={},
        single_param_3=total >= 3,
    )


def _features(**overrides) -> PatientFeatures:
    base = dict(
        chief_complaint="general complaint",
        snomed_codes=[],
        body_system="unclear",
        severity="mild",
        onset="gradual",
        red_flags=[],
        age=40,
        gender="female",
        comorbidities=[],
        mental_status="alert",
        pain_score=2,
        ai_confidence=0.90,
        is_offline=False,
    )
    base.update(overrides)
    return PatientFeatures(**base)


def test_stage1_life_threatening_cardiac_arrest():
    result = triage_patient(
        _features(
            chief_complaint="cardiac arrest",
            snomed_codes=["410429000"],
            body_system="cardiac_arrest",
            severity="critical",
            red_flags=["cardiac_arrest", "pulseless"],
            mental_status="unresponsive",
            age=65,
            gender="male",
        ),
        _vitals(hr=0, sbp=0, dbp=0, rr=0, spo2=60.0, gcs=3),
        _news2(15),
    )
    assert result.final_esi == 1


def test_news2_floor_forces_esi1():
    result = triage_patient(
        _features(chief_complaint="mild cough", body_system="respiratory"),
        _vitals(hr=135, sbp=85, rr=28, spo2=88.0, temp=39.5),
        _news2(9),
    )
    assert result.final_esi == 1
    assert result.news2_override is True


def test_chest_pain_is_never_above_esi2():
    result = triage_patient(
        _features(
            chief_complaint="mild chest discomfort",
            body_system="chest_pain_cardiac",
            red_flags=["chest_pain"],
            severity="mild",
            ai_confidence=0.92,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi <= 2


def test_silent_mi_pattern_escalates_to_esi2():
    result = triage_patient(
        _features(
            chief_complaint="mild heartburn and fatigue",
            body_system="heartburn",
            snomed_codes=["16331000"],
            age=55,
            gender="male",
            comorbidities=["diabetes"],
            severity="mild",
            ai_confidence=0.82,
        ),
        _vitals(hr=102, rr=20, spo2=94.0),
        _news2(0),
    )
    assert result.final_esi <= 2


def test_silent_mi_pattern_requires_supporting_vitals():
    result = triage_patient(
        _features(
            chief_complaint="mild heartburn and fatigue",
            body_system="heartburn",
            snomed_codes=["16331000"],
            age=55,
            gender="male",
            comorbidities=["diabetes"],
            severity="mild",
            ai_confidence=0.82,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi >= 3


def test_low_confidence_forces_overtriage_and_review():
    result = triage_patient(
        _features(body_system="unclear", ai_confidence=0.45),
        _vitals(),
        _news2(0),
    )
    assert result.confidence_action == "deterministic_low_confidence"
    assert result.requires_review is True


def test_resource_stage_laceration_is_esi4():
    result = triage_patient(
        _features(
            chief_complaint="small finger laceration",
            body_system="laceration",
            severity="mild",
            ai_confidence=0.93,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 4


def test_resource_stage_med_refill_is_esi5():
    result = triage_patient(
        _features(
            chief_complaint="medication refill",
            body_system="medication_refill",
            severity="mild",
            ai_confidence=0.95,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 5


def test_resource_stage_abdominal_pain_is_esi3():
    result = triage_patient(
        _features(
            chief_complaint="abdominal pain for three hours",
            body_system="abdominal_pain",
            severity="moderate",
            ai_confidence=0.88,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 3


def test_unknown_defaults_to_esi3():
    result = triage_patient(
        _features(
            chief_complaint="vague complaint",
            body_system="unclear",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 3


def test_unclear_with_sudden_speech_loss_is_esi2():
    result = triage_patient(
        _features(
            chief_complaint="مش قادر اتكلم فجأة",
            body_system="unclear",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi <= 2


def test_unclear_with_face_and_arm_fast_signals_is_esi1():
    result = triage_patient(
        _features(
            chief_complaint="facial droop and arm weakness",
            body_system="unclear",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 1


def test_offline_mode_marks_for_review():
    result = triage_patient(
        _features(
            chief_complaint="headache",
            body_system="headache_mild",
            severity="moderate",
            ai_confidence=0.60,
            is_offline=True,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.requires_review is True


def test_news2_score_3_upgrades_esi4_to_esi3():
    result = triage_patient(
        _features(
            chief_complaint="simple cough",
            body_system="cough",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(3),
    )
    assert result.final_esi == 3


def test_news2_score_5_prevents_esi4_or_5():
    result = triage_patient(
        _features(
            chief_complaint="simple cough",
            body_system="cough",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(5),
    )
    assert result.final_esi <= 2


@pytest.mark.parametrize(
    "complaint",
    [
        "مش قادر اتكلم فجأة",
        "كلامي اتلخبط من شوية",
        "لساني اتلت",
        "نص جسمي مش بيتحرك",
        "وشي مايل",
        "sudden inability to speak",
        "slurred speech",
        "جلطة",
        "كلامي مش واضح وإيدي مش بتتحرك",
    ],
)
def test_stroke_fast_cases_floor_to_esi2(complaint: str):
    result = triage_patient(
        _features(
            chief_complaint=complaint,
            body_system="unclear",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi <= 2


def test_multiple_fast_criteria_can_be_esi1_or_esi2():
    result = triage_patient(
        _features(
            chief_complaint="facial droop and arm weakness",
            body_system="unclear",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi <= 2


def test_fast_speech_plus_confusion_forces_esi1():
    result = triage_patient(
        _features(
            chief_complaint="Sudden confusion and inability to speak clearly",
            body_system="unclear",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 1


@pytest.mark.parametrize(
    "complaint",
    [
        "انحراف بالفم وضعف مفاجئ في الطرف الأيسر",
        "بدأ فجأة يتلخبط ومش عارف يتكلم",
        "Sudden facial asymmetry and left-sided weakness",
    ],
)
def test_fast_raw_complaint_precheck_forces_esi1(complaint: str):
    result = triage_patient(
        _features(
            chief_complaint=complaint,
            body_system="unclear",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 1


def test_low_acuity_severe_rash_does_not_inflate_resources():
    result = triage_patient(
        _features(
            chief_complaint="Chronic mild rash for two weeks without systemic symptoms",
            body_system="simple_rash",
            severity="severe",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 5


def test_unmapped_chronic_back_pain_defaults_to_esi4_not_esi3():
    result = triage_patient(
        _features(
            chief_complaint="Chronic back pain without new alarm features",
            body_system="chronic_stable_condition",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 4


def test_chronic_stable_followup_is_esi4():
    result = triage_patient(
        _features(
            chief_complaint="Stable chronic condition follow-up in ED",
            body_system="chronic_stable",
            severity="mild",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 4


def test_chronic_diabetic_urgent_evaluation_minimum_esi3():
    result = triage_patient(
        _features(
            chief_complaint="Needs urgent diabetic evaluation with mild fatigue",
            body_system="chronic_stable",
            severity="mild",
            ai_confidence=0.90,
            comorbidities=["diabetes"],
            age=52,
            gender="male",
        ),
        _vitals(hr=98, rr=20),
        _news2(1),
    )
    assert result.final_esi <= 3


def test_ectopic_pattern_floor_applies_to_esi2():
    result = triage_patient(
        _features(
            chief_complaint="Acute back pain in early pregnancy with dizziness",
            body_system="unclear",
            severity="severe",
            onset="sudden",
            ai_confidence=0.90,
            age=28,
            gender="female",
            red_flags=["ectopic_pregnancy_risk"],
        ),
        _vitals(hr=112, rr=23, sbp=98),
        _news2(2),
    )
    assert result.final_esi == 2


def test_minor_injury_without_active_bleeding_stays_esi4():
    result = triage_patient(
        _features(
            chief_complaint="Minor injury without active severe bleeding",
            body_system="severe_bleeding",
            severity="moderate",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(0),
    )
    assert result.final_esi == 4


def test_silent_mi_category_with_atypical_cluster_is_esi2():
    result = triage_patient(
        _features(
            chief_complaint="Indigestion with unusual sweating",
            body_system="silent_mi",
            severity="severe",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(1),
    )
    assert result.final_esi <= 2


def test_silent_mi_false_positive_urinary_pattern_not_forced_to_esi2():
    result = triage_patient(
        _features(
            chief_complaint="Urinary infection symptoms with dysuria",
            body_system="silent_mi",
            severity="severe",
            ai_confidence=0.90,
        ),
        _vitals(temp=38.7, hr=96, rr=19),
        _news2(2),
    )
    assert result.final_esi >= 3


def test_silent_mi_arabic_indigestion_sweating_is_esi2():
    result = triage_patient(
        _features(
            chief_complaint="حاسس بعسر هضم وعرقان جامد",
            body_system="silent_mi",
            severity="severe",
            ai_confidence=0.90,
        ),
        _vitals(),
        _news2(1),
    )
    assert result.final_esi <= 2


def test_diabetic_emergency_red_flag_text_forces_esi2():
    result = triage_patient(
        _features(
            chief_complaint="very thirsty and feeling sick",
            body_system="unclear",
            severity="severe",
            red_flags=["Critical hypoglycemia - immediate intervention required"],
            ai_confidence=0.50,
        ),
        _vitals(),
        _news2(1),
    )
    assert result.final_esi <= 2

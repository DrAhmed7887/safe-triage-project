"""
ESI v5 Compliance Module for SAFE-Triage
=========================================
Implements 5 critical patient safety fixes from ESI v5 Handbook (AHRQ 2023)

References:
- ESI v5 Handbook, Chapter 3: Decision Points A & B
- ESI v5 Handbook, Chapter 4: Pediatric Considerations
- ESI v5 Handbook, Chapter 6: Special Populations
"""

from typing import Optional, Dict, Tuple, List, Any

# =============================================================================
# PEDIATRIC VITAL SIGN THRESHOLDS (ESI v5, Chapter 4, Page 47)
# =============================================================================
PEDIATRIC_VITALS_ESI_V5 = {
    "neonate_0_28_days": {
        "age_range": (0, 28),  # days
        "hr_high": 205,
        "rr_high": 60,
        "spo2_low": 92,  # ESI v5: <92% is danger zone
        "fever_threshold": 38.0,  # MANDATORY ESI 2 if fever
        "fever_esi": 2,
    },
    "infant_1_3_months": {
        "age_range": (29, 90),
        "hr_high": 180,
        "rr_high": 55,
        "spo2_low": 92,
        "fever_threshold": 38.0,
        "fever_esi": 2,  # Consider ESI 2
    },
    "infant_3_12_months": {
        "age_range": (91, 365),
        "hr_high": 180,
        "rr_high": 50,
        "spo2_low": 92,
        "fever_threshold": 39.0,
        "fever_esi": 3,
    },
    "toddler_1_3_years": {
        "age_range": (366, 1095),
        "hr_high": 160,
        "rr_high": 40,
        "spo2_low": 92,
        "fever_threshold": 39.0,
        "fever_esi": 3,
    },
    "preschool_3_6_years": {
        "age_range": (1096, 2190),
        "hr_high": 140,
        "rr_high": 34,
        "spo2_low": 92,
    },
    "school_6_12_years": {
        "age_range": (2191, 4380),
        "hr_high": 120,
        "rr_high": 30,
        "spo2_low": 92,
    },
    "adolescent_12_18_years": {
        "age_range": (4381, 6570),
        "hr_high": 100,
        "rr_high": 20,
        "spo2_low": 92,
    },
}

# Pain contexts that indicate systemic disruption (ESI v5, Chapter 3)
SYSTEMIC_PAIN_CONTEXTS = [
    "systemic",
    "chest_pain",
    "abdominal_pain",
    "renal_colic",
    "kidney_stone",
    "cancer_pain",
    "sickle_cell",
    "sickle_cell_crisis",
]
ORTHOPEDIC_PAIN_CONTEXTS = [
    "ankle_sprain",
    "orthopedic",
    "musculoskeletal",
    "sprain",
    "strain",
]


def age_years_to_days(age_years: float) -> int:
    """Convert age in years to days."""
    return int(age_years * 365)


def get_age_category(age_days: int) -> Optional[str]:
    """Get the pediatric age category for given age in days."""
    for category, thresholds in PEDIATRIC_VITALS_ESI_V5.items():
        min_days, max_days = thresholds["age_range"]
        if min_days <= age_days <= max_days:
            return category
    return None


def celsius_to_fahrenheit(temp_c: float) -> float:
    return (temp_c * 9 / 5) + 32


def fahrenheit_to_celsius(temp_f: float) -> float:
    return (temp_f - 32) * 5 / 9


def check_pediatric_danger_zone_esi_v5(
    age_days: int,
    hr: Optional[int] = None,
    rr: Optional[int] = None,
    spo2: Optional[float] = None,
) -> Tuple[bool, List[str], int]:
    """
    ESI v5 Decision Point D: Pediatric Danger Zone Vitals
    Reference: ESI v5 Handbook, Chapter 4, Page 47

    Returns: (is_danger_zone, alerts, suggested_esi)
    """
    category = get_age_category(age_days)
    if not category:
        return False, [], 5

    thresholds = PEDIATRIC_VITALS_ESI_V5[category]
    alerts = []
    is_danger = False
    suggested_esi = 5

    # Check HR
    if hr is not None and hr > thresholds["hr_high"]:
        is_danger = True
        alerts.append(
            f"Pediatric tachycardia: HR {hr} > {thresholds['hr_high']} for age"
        )
        suggested_esi = min(suggested_esi, 2)

    # Check RR
    if rr is not None and rr > thresholds["rr_high"]:
        is_danger = True
        alerts.append(
            f"Pediatric tachypnea: RR {rr} > {thresholds['rr_high']} for age"
        )
        suggested_esi = min(suggested_esi, 2)

    # Check SpO2 - ESI v5 uses <92% for pediatrics (not <90%)
    if spo2 is not None and spo2 < thresholds["spo2_low"]:
        is_danger = True
        alerts.append(
            f"Pediatric hypoxia: SpO2 {spo2}% < {thresholds['spo2_low']}%"
        )
        suggested_esi = min(suggested_esi, 1)

    return is_danger, alerts, suggested_esi


def check_level_1_vitals_override(
    spo2: Optional[float] = None,
    rr: Optional[int] = None,
    hr: Optional[int] = None,
    sbp: Optional[int] = None,
    gcs: Optional[int] = None,
    is_pediatric: bool = False,
) -> Tuple[bool, List[str]]:
    """
    ESI v5 Decision Point A: Requires immediate life-saving intervention?
    Reference: ESI v5 Handbook, Chapter 3, Pages 25-27

    CRITICAL: SpO2 < 90% requires OTHER signs of respiratory compromise for Level 1
    """
    alerts = []
    is_level_1 = False

    respiratory_signs = 0

    # Count respiratory compromise signs
    spo2_critical = spo2 is not None and spo2 < 90
    rr_abnormal = rr is not None and (rr < 8 or rr > 35)

    if spo2_critical:
        respiratory_signs += 1

    if rr_abnormal:
        respiratory_signs += 1
        if not spo2_critical:
            alerts.append(f"Abnormal respiratory rate: {rr}/min")

    # SpO2 < 90% WITH other respiratory signs = Level 1
    if spo2_critical and respiratory_signs >= 2:
        is_level_1 = True
        alerts.append(
            f"Critical hypoxia with respiratory distress: SpO2 {spo2}%, RR {rr}/min"
        )

    # Other Level 1 criteria
    if gcs is not None and gcs <= 8:
        is_level_1 = True
        alerts.append(f"Severe altered consciousness: GCS {gcs}")

    if sbp is not None and sbp < 70:
        is_level_1 = True
        alerts.append(f"Severe hypotension: SBP {sbp} mmHg")

    if hr is not None and hr < 40:
        is_level_1 = True
        alerts.append(f"Severe bradycardia: HR {hr}/min")

    return is_level_1, alerts


def check_high_risk_vitals_esi_v5(
    spo2: Optional[float] = None,
    hr: Optional[int] = None,
    sbp: Optional[int] = None,
    rr: Optional[int] = None,
) -> Tuple[int, List[str]]:
    """
    ESI v5 Decision Point B: High-risk situations (ESI 2)
    Reference: ESI v5 Handbook, Chapter 3, Page 28

    Vitals that are dangerous but don't require immediate intervention:
    - SpO2 < 90% alone (without other respiratory signs)
    - SBP 70-90 (hypotension but not shock)
    - HR < 50 or > 150 (but conscious)
    """
    alerts = []
    suggested_esi = 5

    # SpO2 < 90% alone = ESI 2 (high-risk, needs urgent evaluation)
    if spo2 is not None and spo2 < 90:
        has_respiratory_distress = rr is not None and (rr < 10 or rr > 30)
        if not has_respiratory_distress:
            alerts.append(f"High-risk hypoxia: SpO2 {spo2}% < 90% -> ESI 2")
            suggested_esi = min(suggested_esi, 2)

    # Borderline hypotension
    if sbp is not None and 70 <= sbp < 90:
        alerts.append(f"Borderline hypotension: SBP {sbp} mmHg -> ESI 2")
        suggested_esi = min(suggested_esi, 2)

    # Extreme tachycardia/bradycardia (conscious patient)
    if hr is not None and (hr < 50 or hr > 150):
        alerts.append(f"High-risk heart rate: HR {hr}/min -> ESI 2")
        suggested_esi = min(suggested_esi, 2)

    return suggested_esi, alerts


def check_pediatric_fever_esi_v5(
    age_days: int,
    temp_c: Optional[float] = None,
    immunizations_complete: bool = True,
) -> Tuple[int, List[str]]:
    """
    ESI v5 Pediatric Fever Protocol
    Reference: ESI v5 Handbook, Chapter 4, Page 47 (Algorithm)

    CRITICAL: Neonate (1-28 days) + Fever >=38C = MANDATORY ESI 2
    """
    if temp_c is None:
        return 5, []

    alerts = []
    suggested_esi = 5

    category = get_age_category(age_days)
    if not category:
        return 5, []

    thresholds = PEDIATRIC_VITALS_ESI_V5[category]

    if "fever_threshold" in thresholds and temp_c >= thresholds["fever_threshold"]:
        suggested_esi = thresholds.get("fever_esi", 3)

        if category == "neonate_0_28_days":
            alerts.append(
                f"NEONATE FEVER: {temp_c}C - MANDATORY ESI 2 (sepsis risk)"
            )
            suggested_esi = 2
        elif category == "infant_1_3_months":
            alerts.append(f"Young infant fever: {temp_c}C - Consider ESI 2")
            suggested_esi = 2
        else:
            alerts.append(f"Pediatric fever: {temp_c}C")

    # Incomplete immunizations = higher risk
    if immunizations_complete is False and temp_c is not None and temp_c >= 38.0:
        alerts.append("Fever + incomplete immunizations - increased infection risk")
        suggested_esi = min(suggested_esi, 2)

    return suggested_esi, alerts


def check_severe_pain_esi_v5(
    pain_scale: Optional[int] = None,
    pain_context: Optional[str] = None,
) -> Tuple[int, List[str]]:
    """
    ESI v5 Severe Pain Assessment
    Reference: ESI v5 Handbook, Chapter 3, Pages 29-30

    Pain >=7/10 requires CONTEXT evaluation:
    - Systemic (renal colic, cancer, sickle cell) -> ESI 2
    - Orthopedic (ankle sprain) -> Comfort measures, then resource-based (ESI 3-4)
    """
    if pain_scale is None or pain_scale < 7:
        return 5, []

    alerts = []
    context_lower = (pain_context or "").lower()

    # Check for systemic pain contexts
    if any(ctx in context_lower for ctx in SYSTEMIC_PAIN_CONTEXTS):
        alerts.append(
            f"Severe pain {pain_scale}/10 with systemic etiology ({pain_context}) -> ESI 2"
        )
        return 2, alerts

    # Check for orthopedic contexts
    if any(ctx in context_lower for ctx in ORTHOPEDIC_PAIN_CONTEXTS):
        alerts.append(
            f"Severe pain {pain_scale}/10 - orthopedic ({pain_context}) -> comfort measures first"
        )
        return 3, alerts

    # Default severe pain without clear context
    if pain_scale >= 8:
        alerts.append(f"Severe pain {pain_scale}/10 - evaluate for systemic cause")
        return 2, alerts

    return 3, alerts


def check_immunocompromised_fever_esi_v5(
    is_immunocompromised: bool = False,
    immunocompromised_reason: Optional[str] = None,
    temp_c: Optional[float] = None,
) -> Tuple[int, List[str]]:
    """
    ESI v5 Immunocompromised + Fever
    Reference: ESI v5 Handbook, Chapter 3, Page 28 (Decision Point B)

    Immunocompromised patient + fever = ESI 2 (high-risk situation)
    """
    if not is_immunocompromised:
        return 5, []

    alerts = []

    if temp_c is not None and temp_c >= 38.0:
        reason = immunocompromised_reason or "unspecified"
        alerts.append(
            f"Immunocompromised ({reason}) + fever {temp_c}C -> ESI 2"
        )
        return 2, alerts

    # Immunocompromised without fever still needs attention
    alerts.append(
        f"Immunocompromised patient ({immunocompromised_reason or 'unspecified'}) - monitor closely"
    )
    return 3, alerts


def check_pregnancy_esi_v5(
    is_pregnant: bool = False,
    gestational_weeks: Optional[int] = None,
    pregnancy_complaint: Optional[str] = None,
    sbp: Optional[int] = None,
    dbp: Optional[int] = None,
    has_seizure: bool = False,
    has_trauma: bool = False,
    chief_complaint: Optional[str] = None,
) -> Tuple[int, List[str]]:
    """
    ESI v5 Pregnancy Triage Rules
    Reference: ESI Handbook v5, Chapter 4 - Special Populations

    Pregnancy modifies triage acuity for several high-risk conditions.
    """
    alerts = []
    suggested_esi = 5  # Default, will take minimum

    if not is_pregnant:
        return suggested_esi, alerts

    # === ESI 1: LIFE-THREATENING ===

    # Eclampsia: Pregnant + seizure
    if has_seizure:
        alerts.append(
            "ECLAMPSIA CONCERN: Pregnant patient with seizure -> ESI 1 IMMEDIATE"
        )
        return 1, alerts  # Return immediately, highest priority

    # === ESI 2: HIGH-RISK PREGNANCY ===

    # Severe preeclampsia: SBP >=160 or DBP >=110
    if sbp is not None and sbp >= 160:
        alerts.append(
            f"SEVERE PREECLAMPSIA: Pregnant + SBP {sbp} >=160 mmHg -> ESI 2"
        )
        suggested_esi = min(suggested_esi, 2)

    if dbp is not None and dbp >= 110:
        alerts.append(
            f"SEVERE PREECLAMPSIA: Pregnant + DBP {dbp} >=110 mmHg -> ESI 2"
        )
        suggested_esi = min(suggested_esi, 2)

    # Trauma in pregnancy: Always ESI 2
    if has_trauma:
        alerts.append(
            "PREGNANT TRAUMA: Any trauma in pregnancy -> ESI 2 (placental abruption risk)"
        )
        suggested_esi = min(suggested_esi, 2)

    # Pregnancy complaint-based rules
    if pregnancy_complaint:
        # Vaginal bleeding
        if pregnancy_complaint == "vaginal_bleeding":
            if gestational_weeks and gestational_weeks < 20:
                alerts.append(
                    f"THREATENED ABORTION/ECTOPIC: Vaginal bleeding at {gestational_weeks} weeks -> ESI 2"
                )
            else:
                alerts.append(
                    f"ANTEPARTUM HEMORRHAGE: Vaginal bleeding at {gestational_weeks or 'unknown'} weeks -> ESI 2 (placenta previa/abruption)"
                )
            suggested_esi = min(suggested_esi, 2)

        # Preterm contractions
        if pregnancy_complaint == "contractions":
            if gestational_weeks and gestational_weeks < 37:
                alerts.append(
                    f"PRETERM LABOR: Contractions at {gestational_weeks} weeks (<37) -> ESI 2"
                )
                suggested_esi = min(suggested_esi, 2)
            elif gestational_weeks and gestational_weeks >= 37:
                alerts.append(
                    f"TERM LABOR: Contractions at {gestational_weeks} weeks -> ESI 3"
                )
                suggested_esi = min(suggested_esi, 3)

        # Decreased fetal movement (3rd trimester)
        if pregnancy_complaint == "decreased_fetal_movement":
            if gestational_weeks and gestational_weeks >= 28:
                alerts.append(
                    f"FETAL DISTRESS CONCERN: Decreased fetal movement at {gestational_weeks} weeks -> ESI 2"
                )
                suggested_esi = min(suggested_esi, 2)
            else:
                alerts.append(
                    "Decreased fetal movement reported (early pregnancy) -> ESI 3"
                )
                suggested_esi = min(suggested_esi, 3)

        # Leaking fluid (PPROM)
        if pregnancy_complaint == "leaking_fluid":
            if gestational_weeks and gestational_weeks < 37:
                alerts.append(
                    f"PPROM CONCERN: Leaking fluid at {gestational_weeks} weeks (<37) -> ESI 2"
                )
                suggested_esi = min(suggested_esi, 2)
            else:
                alerts.append(
                    f"PROM: Leaking fluid at term ({gestational_weeks} weeks) -> ESI 3"
                )
                suggested_esi = min(suggested_esi, 3)

        # Headache + visual changes (preeclampsia warning)
        if pregnancy_complaint == "headache_visual_changes":
            alerts.append(
                "PREECLAMPSIA WARNING: Headache + visual changes in pregnancy -> ESI 2"
            )
            suggested_esi = min(suggested_esi, 2)

        # Abdominal pain in pregnancy
        if pregnancy_complaint == "abdominal_pain":
            if gestational_weeks and gestational_weeks < 20:
                alerts.append(
                    f"ECTOPIC CONCERN: Abdominal pain at {gestational_weeks} weeks -> ESI 2"
                )
                suggested_esi = min(suggested_esi, 2)
            else:
                alerts.append(
                    f"ABRUPTION/LABOR CONCERN: Abdominal pain at {gestational_weeks or 'unknown'} weeks -> ESI 2"
                )
                suggested_esi = min(suggested_esi, 2)

    return suggested_esi, alerts


def evaluate_esi_v5(
    age_years: float,
    vitals: Optional[Dict] = None,
    pain_scale: Optional[int] = None,
    pain_context: Optional[str] = None,
    is_immunocompromised: bool = False,
    immunocompromised_reason: Optional[str] = None,
    immunizations_complete: bool = True,
    is_pregnant: bool = False,
    gestational_weeks: Optional[int] = None,
    pregnancy_complaint: Optional[str] = None,
    has_seizure: bool = False,
    has_trauma: bool = False,
) -> Dict[str, Any]:
    """
    Main ESI v5 evaluation function.

    Args:
        age_years: Patient age in years
        vitals: Dict with hr, rr, spo2, sbp, temp_c, gcs
        pain_scale: Pain score 0-10
        pain_context: Context string (e.g., "renal_colic", "ankle_sprain")
        is_immunocompromised: Boolean
        immunocompromised_reason: String (e.g., "chemotherapy", "HIV")
        immunizations_complete: Boolean (pediatric)

    Returns:
        Dict with suggested_esi, alerts, and evaluation details
    """
    age_days = age_years_to_days(age_years)
    is_pediatric = age_years < 18

    all_alerts = []
    suggested_levels = []

    vitals = vitals or {}
    hr = vitals.get("hr")
    rr = vitals.get("rr")
    spo2 = vitals.get("spo2")
    sbp = vitals.get("sbp")
    dbp = vitals.get("dbp")
    temp_c = vitals.get("temp_c")
    gcs = vitals.get("gcs")

    # 1. Check Level 1 vitals override
    is_level_1, level1_alerts = check_level_1_vitals_override(
        spo2=spo2, rr=rr, hr=hr, sbp=sbp, gcs=gcs, is_pediatric=is_pediatric
    )
    all_alerts.extend(level1_alerts)
    if is_level_1:
        suggested_levels.append(1)

    # 1b. Check high-risk vitals (ESI 2) - runs even if not Level 1
    high_risk_esi, high_risk_alerts = check_high_risk_vitals_esi_v5(
        spo2=spo2, hr=hr, sbp=sbp, rr=rr
    )
    all_alerts.extend(high_risk_alerts)
    if high_risk_esi < 5:
        suggested_levels.append(high_risk_esi)

    # 2. Pediatric danger zone vitals
    if is_pediatric:
        is_danger, peds_alerts, peds_esi = check_pediatric_danger_zone_esi_v5(
            age_days=age_days, hr=hr, rr=rr, spo2=spo2
        )
        all_alerts.extend(peds_alerts)
        if is_danger:
            suggested_levels.append(peds_esi)

        # 3. Pediatric fever protocol
        fever_esi, fever_alerts = check_pediatric_fever_esi_v5(
            age_days=age_days,
            temp_c=temp_c,
            immunizations_complete=immunizations_complete,
        )
        all_alerts.extend(fever_alerts)
        if fever_esi < 5:
            suggested_levels.append(fever_esi)

    # 4. Severe pain assessment
    pain_esi, pain_alerts = check_severe_pain_esi_v5(
        pain_scale=pain_scale, pain_context=pain_context
    )
    all_alerts.extend(pain_alerts)
    if pain_esi < 5:
        suggested_levels.append(pain_esi)

    # 5. Immunocompromised + fever
    immuno_esi, immuno_alerts = check_immunocompromised_fever_esi_v5(
        is_immunocompromised=is_immunocompromised,
        immunocompromised_reason=immunocompromised_reason,
        temp_c=temp_c,
    )
    all_alerts.extend(immuno_alerts)
    if immuno_esi < 5:
        suggested_levels.append(immuno_esi)

    # 6. Check pregnancy rules
    pregnancy_esi, pregnancy_alerts = check_pregnancy_esi_v5(
        is_pregnant=is_pregnant,
        gestational_weeks=gestational_weeks,
        pregnancy_complaint=pregnancy_complaint,
        sbp=sbp,
        dbp=dbp,
        has_seizure=has_seizure,
        has_trauma=has_trauma,
    )
    all_alerts.extend(pregnancy_alerts)
    if pregnancy_esi < 5:
        suggested_levels.append(pregnancy_esi)

    # Final ESI = minimum (most acute) of all suggested levels
    final_esi = min(suggested_levels) if suggested_levels else None

    return {
        "esi_v5_suggested": final_esi,
        "esi_v5_alerts": all_alerts,
        "is_pediatric": is_pediatric,
        "checks_performed": {
            "level_1_override": is_level_1,
            "pediatric_danger_zone": is_pediatric
            and any("Pediatric" in a for a in all_alerts),
            "pediatric_fever": is_pediatric and any("fever" in a.lower() for a in all_alerts),
            "severe_pain": pain_scale is not None and pain_scale >= 7,
            "immunocompromised": is_immunocompromised,
        },
    }

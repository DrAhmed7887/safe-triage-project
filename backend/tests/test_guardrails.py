#!/usr/bin/env python3
"""Unit tests for narrow AI over-triage safety guardrails."""

import os
import sys
import unittest


sys.path.append(os.path.join(os.getcwd(), "backend"))

from logic.deterministic_triage import (  # noqa: E402
    ESIResourcePredictor,
    apply_safety_guardrails,
    apply_severity_ceiling,
    guardrail_cellulitis_spreading,
    guardrail_dehydration_moderate,
    guardrail_laceration_needs_sutures,
    guardrail_pneumonia_stable,
    guardrail_uti_pyelonephritis,
)


class GuardrailTests(unittest.TestCase):
    def setUp(self):
        self.resource_predictor = ESIResourcePredictor()

    def test_uti_guardrail_caps_without_sepsis_signals(self):
        esi, reason = guardrail_uti_pyelonephritis(
            "Burning with urination, back pain, fever and chills",
            "pyelonephritis",
            2,
        )
        self.assertEqual(esi, 3)
        self.assertIn("GUARDRAIL_UTI", reason)

    def test_uti_guardrail_preserves_explicit_sepsis(self):
        esi, reason = guardrail_uti_pyelonephritis(
            "UTI, septic, confused, HR 118, BP 88/60",
            "urosepsis",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_pneumonia_guardrail_caps_stable_case(self):
        esi, reason = guardrail_pneumonia_stable(
            "Pneumonia with cough and green sputum, fever for 3 days, short of breath with activity",
            "community acquired pneumonia",
            2,
        )
        self.assertEqual(esi, 3)
        self.assertIn("GUARDRAIL_PNEUMONIA", reason)

    def test_pneumonia_guardrail_preserves_hypoxic_case(self):
        esi, reason = guardrail_pneumonia_stable(
            "Pneumonia, SpO2 88%, respiratory distress, fast breathing",
            "pneumonia",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_dehydration_guardrail_caps_without_instability(self):
        esi, reason = guardrail_dehydration_moderate(
            "Vomiting and diarrhea for 3 days, dizzy, not urinating much",
            "dehydration",
            2,
        )
        self.assertEqual(esi, 3)
        self.assertIn("GUARDRAIL_DEHYDRATION", reason)

    def test_dehydration_guardrail_preserves_syncope_or_instability(self):
        esi, reason = guardrail_dehydration_moderate(
            "Dehydration, near syncope, HR 122, BP 86/54",
            "gastroenteritis dehydration",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_cellulitis_guardrail_caps_spreading_without_systemic_signs(self):
        esi, reason = guardrail_cellulitis_spreading(
            "Cellulitis, red swollen leg getting bigger with red streaks",
            "cellulitis",
            2,
        )
        self.assertEqual(esi, 3)
        self.assertIn("GUARDRAIL_CELLULITIS", reason)

    def test_cellulitis_guardrail_preserves_systemic_case(self):
        esi, reason = guardrail_cellulitis_spreading(
            "Cellulitis, red swollen leg getting bigger, red streaks, fever 39, tachycardia",
            "soft tissue infection",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_laceration_guardrail_caps_repair_only_case(self):
        esi, reason = guardrail_laceration_needs_sutures(
            "Cut hand on glass, deep laceration, bleeding controlled with pressure, needs sutures",
            "hand laceration",
            2,
        )
        self.assertEqual(esi, 3)
        self.assertIn("GUARDRAIL_LACERATION", reason)

    def test_laceration_guardrail_preserves_active_hemorrhage(self):
        esi, reason = guardrail_laceration_needs_sutures(
            "Deep laceration with uncontrolled bleeding, spurting arterial blood, BP 82/50",
            "laceration needs sutures",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_uti_guardrail_does_not_fire_on_stroke_family(self):
        esi, reason = guardrail_uti_pyelonephritis(
            "Sudden facial droop arm weakness",
            "acute stroke",
            3,
        )
        self.assertEqual(esi, 3)
        self.assertEqual(reason, "PASS")

    def test_uti_guardrail_does_not_fire_on_tia_family(self):
        esi, reason = guardrail_uti_pyelonephritis(
            "Sudden weakness speech problem resolved",
            "TIA transient ischemic attack",
            3,
        )
        self.assertEqual(esi, 3)
        self.assertEqual(reason, "PASS")

    def test_dehydration_guardrail_does_not_fire_on_dka_family(self):
        esi, reason = guardrail_dehydration_moderate(
            "Type 1 diabetic vomiting fruity breath blood sugar 500",
            "DKA diabetic ketoacidosis",
            3,
        )
        self.assertEqual(esi, 3)
        self.assertEqual(reason, "PASS")

    def test_laceration_guardrail_does_not_fire_on_back_pain_family(self):
        esi, reason = guardrail_laceration_needs_sutures(
            "Lower back pain chronic worse this week",
            "back pain musculoskeletal",
            4,
        )
        self.assertEqual(esi, 4)
        self.assertEqual(reason, "PASS")

    def test_master_guardrails_preserve_chest_pain_acs_case(self):
        esi, reasons = apply_safety_guardrails(
            "Chest pain with diaphoresis and radiation to arm",
            "cardiac chest pain",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reasons, [])

    def test_master_guardrails_preserve_hematemesis_with_instability(self):
        esi, reasons = apply_safety_guardrails(
            "Hematemesis, hypotensive, HR 130, BP 84/50, feeling faint",
            "severe bleeding",
            1,
        )
        self.assertEqual(esi, 1)
        self.assertEqual(reasons, [])

    def test_master_guardrails_preserve_uti_sepsis_case(self):
        esi, reasons = apply_safety_guardrails(
            "UTI, septic, altered, HR 118, BP 88/60",
            "urosepsis",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reasons, [])

    def test_master_guardrails_preserve_hypoxic_pneumonia(self):
        esi, reasons = apply_safety_guardrails(
            "Pneumonia, SpO2 88%, respiratory distress",
            "pneumonia",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reasons, [])

    def test_severity_ceiling_preserves_cardiac_arrest_case(self):
        esi, reason = apply_severity_ceiling("cardiac arrest not breathing", 1)
        self.assertEqual(esi, 1)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_gi_bleed_with_instability(self):
        esi, reason = apply_severity_ceiling("hematemesis hypotension tachycardia", 1)
        self.assertEqual(esi, 1)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_stroke_signals(self):
        esi, reason = apply_severity_ceiling("sudden facial droop arm weakness slurred speech", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_septic_case(self):
        esi, reason = apply_severity_ceiling("fever chills dizzy septic", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_meningeal_signals(self):
        esi, reason = apply_severity_ceiling("headache stiff neck photophobia", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_wake_up_stroke_deficit(self):
        esi, reason = apply_severity_ceiling("woke up with facial droop and wake up deficit right arm", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_tia_resolved_symptoms(self):
        esi, reason = apply_severity_ceiling(
            "had sudden weakness and speech problem tia resolved 20 min ago",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_dka_without_abbreviation(self):
        esi, reason = apply_severity_ceiling("type 1 diabetic vomiting fruity breath blood sugar over 500", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_active_suicidal_ideation_with_plan(self):
        esi, reason = apply_severity_ceiling("active suicidal ideation with plan and means", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_vaginal_bleeding_in_pregnancy(self):
        esi, reason = apply_severity_ceiling("heavy vaginal bleeding in pregnancy 10 weeks", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_testicular_torsion(self):
        esi, reason = apply_severity_ceiling("sudden severe testicular torsion right side onset 1 hour ago", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_gcs3_resuscitation(self):
        esi, reason = apply_severity_ceiling("gcs 3, no response to pain", 1)
        self.assertEqual(esi, 1)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_major_trauma_resuscitation(self):
        esi, reason = apply_severity_ceiling("ejected from vehicle, multiple injuries, bleeding heavily", 1)
        self.assertEqual(esi, 1)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_penetrating_trauma_resuscitation(self):
        esi, reason = apply_severity_ceiling("gunshot wound to chest, difficulty breathing", 1)
        self.assertEqual(esi, 1)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_status_epilepticus_resuscitation(self):
        esi, reason = apply_severity_ceiling("continuous seizure for 10 minutes, not stopping", 1)
        self.assertEqual(esi, 1)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_caps_non_instability_scalp_case_to_esi3(self):
        esi, reason = apply_severity_ceiling("flaky scalp need shampoo recommendation", 2)
        self.assertEqual(esi, 3)
        self.assertIn("CEILING_ESI2", reason)

    def test_severity_ceiling_caps_sports_physical_to_esi4(self):
        esi, reason = apply_severity_ceiling("sports physical healthy teenager", 2)
        self.assertEqual(esi, 4)
        self.assertIn("CEILING_NON_URGENT", reason)

    def test_severity_ceiling_caps_routine_bp_check_to_esi4(self):
        esi, reason = apply_severity_ceiling("routine blood pressure check", 2)
        self.assertEqual(esi, 4)
        self.assertIn("CEILING_NON_URGENT", reason)

    def test_severity_ceiling_caps_work_note_to_esi4(self):
        esi, reason = apply_severity_ceiling("work note needed for employer", 3)
        self.assertEqual(esi, 4)
        self.assertIn("CEILING_NON_URGENT", reason)

    def test_severity_ceiling_caps_insomnia_to_esi4(self):
        esi, reason = apply_severity_ceiling("insomnia can't sleep for three nights", 3)
        self.assertEqual(esi, 4)
        self.assertIn("CEILING_NON_URGENT", reason)

    def test_severity_ceiling_caps_chronic_back_pain_to_esi3(self):
        esi, reason = apply_severity_ceiling("lower back pain chronic worse this week", 2)
        self.assertEqual(esi, 3)
        self.assertIn("CEILING_ESI2", reason)

    def test_severity_ceiling_caps_esi1_without_life_threat_signal(self):
        esi, reason = apply_severity_ceiling("headache stiff neck photophobia", 1)
        self.assertEqual(esi, 2)
        self.assertIn("CEILING_ESI1", reason)

    def test_severity_ceiling_preserves_altered_consciousness_post_fall(self):
        esi, reason = apply_severity_ceiling("fell and hit head, now drowsy and confused", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_possible_ectopic(self):
        esi, reason = apply_severity_ceiling("possible ectopic severe pain", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_woke_up_unable_to_move_right_side(self):
        esi, reason = apply_severity_ceiling(
            "woke up unable to move right side can't speak clearly",
            2,
        )
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_preserves_suicidal_intent_with_plan_language(self):
        esi, reason = apply_severity_ceiling("wants to kill himself has a plan", 2)
        self.assertEqual(esi, 2)
        self.assertEqual(reason, "PASS")

    def test_severity_ceiling_caps_flu_like_illness_to_esi4(self):
        esi, reason = apply_severity_ceiling("flu-like illness body aches mild fever", 3)
        self.assertEqual(esi, 4)
        self.assertTrue(reason.startswith("CEILING_NON_URGENT"))

    def test_resource_predictor_marks_suture_laceration_as_urgent(self):
        result = self.resource_predictor.estimate_resources(
            category="laceration_simple",
            chief_complaint="Hand laceration needs sutures, bleeding controlled",
            age=30,
        )
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["esi_level"], 3)
        self.assertEqual(result["resources"], ["laceration_repair"])

    def test_resource_predictor_marks_facial_laceration_as_urgent(self):
        result = self.resource_predictor.estimate_resources(
            category="laceration_simple",
            chief_complaint="Facial laceration after fall, bleeding controlled",
            age=30,
        )
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["esi_level"], 3)
        self.assertEqual(result["resources"], ["laceration_repair"])

    def test_resource_predictor_counts_heartburn_as_one_resource(self):
        result = self.resource_predictor.estimate_resources(
            category="mild_gi",
            chief_complaint="Heartburn after spicy food, likely acid reflux",
            age=30,
        )
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["esi_level"], 4)
        self.assertEqual(result["resources"], ["ecg"])


if __name__ == "__main__":
    unittest.main()

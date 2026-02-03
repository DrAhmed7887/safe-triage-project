# Gender-specific complaint validation

FEMALE_ONLY_COMPLAINTS = [
    "vaginal bleeding", "vaginal discharge", "menstrual", "pregnant", 
    "pregnancy", "labor", "ovarian", "uterine", "cervical", "miscarriage",
    "نزيف مهبلي", "إفرازات مهبلية", "دورة شهرية", "حامل", "حمل", 
    "ولادة", "طلق", "مبيض", "رحم", "إجهاض"
]

MALE_ONLY_COMPLAINTS = [
    "testicular", "penile", "prostate", "scrotal",
    "خصية", "قضيب", "بروستاتا", "كيس الصفن"
]

def validate_gender_complaint(gender: str, complaint: str) -> dict:
    """Check if complaint is anatomically possible for gender"""
    complaint_lower = complaint.lower()
    
    if gender.lower() == "male":
        for term in FEMALE_ONLY_COMPLAINTS:
            if term in complaint_lower:
                return {
                    "valid": False,
                    "error": f"Anatomical mismatch: '{term}' requires verification for male patient",
                    "error_ar": f"تعارض تشريحي: '{term}' يحتاج تأكيد لمريض ذكر",
                    "suggestion": "Please verify patient gender or re-enter complaint"
                }
    
    elif gender.lower() == "female":
        for term in MALE_ONLY_COMPLAINTS:
            if term in complaint_lower:
                return {
                    "valid": False,
                    "error": f"Anatomical mismatch: '{term}' requires verification for female patient",
                    "error_ar": f"تعارض تشريحي: '{term}' يحتاج تأكيد لمريضة أنثى",
                    "suggestion": "Please verify patient gender or re-enter complaint"
                }
    
    return {"valid": True}

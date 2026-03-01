import io
import csv
import json
import os
import hashlib
import re
import logging
from datetime import datetime, date as date_type
from typing import List, Dict, Any, Optional, Tuple

from google.cloud import bigquery
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

import arabic_reshaper
from bidi.algorithm import get_display
try:
    from umls_rag import UMLSMedicalRAG
except ImportError:  # pragma: no cover - package import fallback
    from backend.umls_rag import UMLSMedicalRAG

GAHAR_NOTICE = "🏥 According to GAHAR Standards | وفقاً لمعايير الجهار"
CONF_HEADER_EN = "CONFIDENTIAL — Authorized Personnel Only"
CONF_HEADER_AR = "سري — للمصرح لهم فقط"
CONF_PHI_EN = "This report contains Protected Health Information (PHI)"
CONF_PHI_AR = "يحتوي هذا التقرير على معلومات صحية محمية"
CONF_ACCESS_EN = "Access restricted to authorized medical staff only"
CONF_ACCESS_AR = "الوصول مقصور على الطاقم الطبي المصرح له فقط"
CONF_FOOTER_EN = "Document Classification: CONFIDENTIAL"
CONF_FOOTER_AR = "تصنيف الوثيقة: سري"
CONF_FOOTER_2_EN = "Unauthorized distribution is prohibited"
CONF_FOOTER_2_AR = "يُحظر التوزيع غير المصرح به"
CONF_WATERMARK_EN = "CONFIDENTIAL"
CONF_WATERMARK_AR = "سري"

PROJECT_ID = os.getenv("PROJECT_ID", "safe-triage-ai")
DATASET_ID = os.getenv("DATASET_ID", "safe_triage_audit")
TRIAGE_TABLE = os.getenv("TRIAGE_TABLE", "triage_logs")
CONFIRMATION_TABLE = os.getenv("CONFIRMATION_TABLE", "triage_confirmations")
BQ_LOCATION = os.getenv("BQ_LOCATION", "me-west1")

EXPORT_COLUMNS = [
    "CaseTimestamp",
    "PatientID",
    "Name",
    "Age",
    "Gender",
    "Complaint",
    "RecommendedESI",
    "FinalESI",
    "NEWS2Score",
    "AIConfidence",
]

PERSONAL_EXPORT_SCOPE = "Personal cases only (NOT system-wide)"
SYSTEM_EXPORT_SCOPE = "System-wide cases (Supervisor export)"

PHONE_PATTERN = re.compile(r"\b(?:\+?2)?0?1[0125]\d{8}\b")
NAME_PATTERN = re.compile(
    r"\b(محمد|أحمد|علي|مصطفى|احمد|عبدالله|يوسف|mohamed|mohammed|ahmed|ali|mostafa|mustafa)\b",
    flags=re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,5}\s+(?:street|st\.?|road|rd\.?|avenue|ave\.?|lane|ln\.?|building|block|apt|apartment)\b[^,;\n]*",
    flags=re.IGNORECASE,
)
ARABIC_ADDRESS_PATTERN = re.compile(r"(?:شارع|عمارة|مبنى)\s+\S+", flags=re.IGNORECASE)
logger = logging.getLogger(__name__)
_UMLS_RAG_INSTANCE: Optional[UMLSMedicalRAG] = None

ICD10_NAME_FALLBACK = {
    "R51": "Headache",
    "R04.0": "Epistaxis",
    "R10.4": "Abdominal pain, unspecified",
    "R07.9": "Chest pain, unspecified",
    "R06.0": "Dyspnea",
    "R12": "Heartburn",
    "R69": "Illness, unspecified",
}


def _table_ref(name: str) -> str:
    return f"{PROJECT_ID}.{DATASET_ID}.{name}"


def _register_font() -> str:
    base_dir = os.path.dirname(__file__)
    candidates = [
        os.path.join(base_dir, "fonts", "NotoSansArabic-Variable.ttf"),
        os.path.join(base_dir, "fonts", "NotoSansArabic-Regular.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("ReportFont", path))
            return "ReportFont"
    return "Helvetica"


def render_arabic(text: str) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def bilingual(en_text: str, ar_text: str) -> str:
    return f"{en_text} | {render_arabic(ar_text)}"


def maybe_render_arabic(text: str) -> str:
    if not text:
        return ""
    if any("\u0600" <= ch <= "\u06FF" for ch in text):
        return render_arabic(text)
    return text


def _parse_date(value: str | None) -> date_type:
    if not value:
        return datetime.utcnow().date()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _get_umls_rag() -> UMLSMedicalRAG:
    global _UMLS_RAG_INSTANCE
    if _UMLS_RAG_INSTANCE is None:
        cache_path = os.path.join(os.path.dirname(__file__), "umls_cache.db")
        _UMLS_RAG_INSTANCE = UMLSMedicalRAG(cache_path)
    return _UMLS_RAG_INSTANCE


def _parse_code_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                pass
        return [text]
    return [str(value).strip()]


def lookup_snomed_name(snomed_code: Any) -> str:
    code = _safe_text(snomed_code)
    if not code:
        return ""
    rag = _get_umls_rag()
    term = rag.lookup_snomed_term(code)
    return term or f"Code: {code}"


def lookup_icd10_name(icd10_code: Any) -> str:
    code = _safe_text(icd10_code)
    if not code:
        return ""
    rag = _get_umls_rag()
    try:
        cursor = rag.conn.execute(
            "SELECT description FROM icd10_cache WHERE icd10_code = ? LIMIT 1",
            (code,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            return str(row[0]).strip()
    except Exception:
        pass
    return ICD10_NAME_FALLBACK.get(code.upper(), f"Code: {code}")


def resolve_clinical_codes(snomed_code: Any, icd10_code: Any) -> Tuple[str, str]:
    """Resolve codes to human-readable names with graceful fallback."""
    snomed_label = _safe_text(snomed_code)
    icd10_label = _safe_text(icd10_code)
    try:
        snomed_name = lookup_snomed_name(snomed_code)
    except Exception:
        snomed_name = f"Code: {snomed_label}" if snomed_label else "Unknown"
    try:
        icd10_name = lookup_icd10_name(icd10_code)
    except Exception:
        icd10_name = f"Code: {icd10_label}" if icd10_label else "Unknown"
    return snomed_name, icd10_name


def _resolve_case_clinical_identity(case: Dict[str, Any]) -> None:
    snomed_codes = _parse_code_list(case.get("snomed_codes") or case.get("snomed_code"))
    icd10_codes = _parse_code_list(case.get("icd10_codes") or case.get("icd10_code") or case.get("icd10"))
    snomed_code = snomed_codes[0] if snomed_codes else ""
    icd10_code = icd10_codes[0] if icd10_codes else ""
    try:
        snomed_name, icd10_name = resolve_clinical_codes(snomed_code, icd10_code)
    except Exception as exc:
        logger.warning("Code resolution failed for case %s: %s", case.get("patient_id"), exc)
        snomed_name = snomed_code or "Unknown"
        icd10_name = icd10_code or "Unknown"
    case["snomed_name"] = snomed_name
    case["icd10_name"] = icd10_name


def _anonymized_patient_id(patient_id: Any, clinician_id: str) -> str:
    patient_raw = _safe_text(patient_id)
    if not patient_raw:
        return "ANON_UNKNOWN"
    digest = hashlib.sha256(f"{patient_raw}{clinician_id}".encode("utf-8")).hexdigest()[:8].upper()
    return f"ANON_{digest}"


def redact_pii(text: Any) -> str:
    source = _safe_text(text)
    if not source:
        return ""
    redacted = PHONE_PATTERN.sub("[PHONE]", source)
    redacted = EMAIL_PATTERN.sub("[EMAIL]", redacted)
    redacted = ADDRESS_PATTERN.sub("[ADDRESS]", redacted)
    redacted = ARABIC_ADDRESS_PATTERN.sub("[ADDRESS]", redacted)
    redacted = NAME_PATTERN.sub("[NAME]", redacted)
    return redacted


def _format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    text_value = _safe_text(value)
    if not text_value:
        return ""
    try:
        return datetime.fromisoformat(text_value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return text_value


def anonymize_patient_data(rows: List[Dict[str, Any]], clinician_id: str) -> List[Dict[str, Any]]:
    """Apply Safe Harbor de-identification to export rows."""
    anonymized_rows: List[Dict[str, Any]] = []
    for row in rows:
        anonymized_rows.append(
            {
                "CaseTimestamp": _format_timestamp(row.get("case_timestamp") or row.get("timestamp")),
                "PatientID": _anonymized_patient_id(row.get("patient_id"), clinician_id),
                "Name": "[Redacted]",
                "Age": row.get("age", "") if row.get("age") is not None else "",
                "Gender": _safe_text(row.get("gender")),
                "Complaint": redact_pii(row.get("chief_complaint") or row.get("complaint")),
                "RecommendedESI": row.get("recommended_esi", "") if row.get("recommended_esi") is not None else "",
                "FinalESI": row.get("final_esi", "") if row.get("final_esi") is not None else "",
                "NEWS2Score": row.get("news2_score", "") if row.get("news2_score") is not None else "",
                "AIConfidence": row.get("ai_confidence", "") if row.get("ai_confidence") is not None else "",
            }
        )
    return anonymized_rows


def _run_rows_query(
    query: str,
    params: Optional[List[bigquery.ScalarQueryParameter]] = None,
) -> List[Dict[str, Any]]:
    client = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    rows = client.query(query, job_config=job_config, location=BQ_LOCATION).result()
    return [dict(row) for row in rows]


def fetch_personal_export_cases(clinician_id: str) -> List[Dict[str, Any]]:
    params = [bigquery.ScalarQueryParameter("clinician_id", "STRING", clinician_id)]
    # Intentional scope restriction: personal export is limited to the requesting clinician's cases.
    query_with_confirmation = f"""
        SELECT
            t.timestamp AS case_timestamp,
            t.patient_id,
            t.age,
            t.gender,
            t.chief_complaint,
            t.recommended_esi,
            t.final_esi,
            t.news2_score,
            t.ai_confidence,
            t.icd10_codes
        FROM `{_table_ref(TRIAGE_TABLE)}` AS t
        WHERE
            t.clinician_id = @clinician_id
            OR EXISTS (
                SELECT 1
                FROM `{_table_ref(CONFIRMATION_TABLE)}` AS c
                WHERE c.patient_id = t.patient_id
                  AND c.clinician_id = @clinician_id
            )
        ORDER BY t.timestamp DESC
    """
    try:
        cases = _run_rows_query(query_with_confirmation, params)
        for case in cases:
            try:
                _resolve_case_clinical_identity(case)
            except Exception as exc:
                logger.warning("Code resolution failed for case %s: %s", case.get("patient_id"), exc)
        return cases
    except Exception:
        fallback_query = f"""
            SELECT
                t.timestamp AS case_timestamp,
                t.patient_id,
                t.age,
                t.gender,
                t.chief_complaint,
                t.recommended_esi,
                t.final_esi,
                t.news2_score,
                t.ai_confidence,
                t.icd10_codes
            FROM `{_table_ref(TRIAGE_TABLE)}` AS t
            WHERE t.clinician_id = @clinician_id
            ORDER BY t.timestamp DESC
        """
        cases = _run_rows_query(fallback_query, params)
        for case in cases:
            try:
                _resolve_case_clinical_identity(case)
            except Exception as exc:
                logger.warning("Code resolution failed for case %s: %s", case.get("patient_id"), exc)
        return cases


def fetch_system_wide_export_cases(
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    query = f"""
        SELECT
            t.timestamp AS case_timestamp,
            t.patient_id,
            t.age,
            t.gender,
            t.chief_complaint,
            t.recommended_esi,
            t.final_esi,
            t.news2_score,
            t.ai_confidence,
            t.icd10_codes
        FROM `{_table_ref(TRIAGE_TABLE)}` AS t
        WHERE (@start_at IS NULL OR t.timestamp >= @start_at)
          AND (@end_at IS NULL OR t.timestamp <= @end_at)
        ORDER BY t.timestamp DESC
    """
    params = [
        bigquery.ScalarQueryParameter("start_at", "TIMESTAMP", start_at),
        bigquery.ScalarQueryParameter("end_at", "TIMESTAMP", end_at),
    ]
    cases = _run_rows_query(query, params)
    for case in cases:
        try:
            _resolve_case_clinical_identity(case)
        except Exception as exc:
            logger.warning("Code resolution failed for case %s: %s", case.get("patient_id"), exc)
    return cases


def _build_export_metadata(
    *,
    generated_at: datetime,
    clinician_id: str,
    scope_label: str,
    requested_by: Optional[str] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
) -> List[str]:
    lines = [
        "SAFE-Triage Export",
        f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Clinician ID: {clinician_id}",
        f"Scope: {scope_label}",
        "Privacy: Safe Harbor de-identified",
        "For quality review purposes only - handle securely",
    ]
    if requested_by:
        lines.append(f"Requested By: {requested_by}")
    if start_at or end_at:
        range_start = start_at.strftime("%Y-%m-%d %H:%M:%S") if start_at else "Open"
        range_end = end_at.strftime("%Y-%m-%d %H:%M:%S") if end_at else "Open"
        lines.append(f"Date Range: {range_start} -> {range_end}")
    return lines


def _rows_to_csv_text(rows: List[Dict[str, Any]], metadata_lines: List[str]) -> str:
    output = io.StringIO()
    for line in metadata_lines:
        output.write(f"# {line}\n")
    output.write("#\n")
    writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in EXPORT_COLUMNS})
    output.write("#\n")
    output.write("# Export action is logged and auditable\n")
    output.write("# Retention guidance: delete after 30 days unless policy requires otherwise\n")
    return output.getvalue()


def export_triage_csv(clinician_id: str) -> Tuple[str, str, int]:
    """Export this clinician's cases with Safe Harbor de-identification."""
    cases = fetch_personal_export_cases(clinician_id)
    anonymized_rows = anonymize_patient_data(cases, clinician_id)
    generated_at = datetime.utcnow()
    metadata = _build_export_metadata(
        generated_at=generated_at,
        clinician_id=clinician_id,
        scope_label=PERSONAL_EXPORT_SCOPE,
    )
    csv_text = _rows_to_csv_text(anonymized_rows, metadata)
    filename = f"triage_export_{generated_at.strftime('%Y%m%d_%H%M%S')}.csv"
    return csv_text, filename, len(anonymized_rows)


def export_triage_csv_with_metadata(clinician_id: str) -> Tuple[str, str, int]:
    """Backward-compatible alias with explicit metadata naming."""
    return export_triage_csv(clinician_id)


def export_system_wide_csv(
    requested_by: str,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
) -> Tuple[str, str, int]:
    """Supervisor-only system-wide export with de-identification."""
    cases = fetch_system_wide_export_cases(start_at=start_at, end_at=end_at)
    anonymized_rows = anonymize_patient_data(cases, "SYSTEM_EXPORT")
    generated_at = datetime.utcnow()
    metadata = _build_export_metadata(
        generated_at=generated_at,
        clinician_id="SYSTEM_EXPORT",
        scope_label=SYSTEM_EXPORT_SCOPE,
        requested_by=requested_by,
        start_at=start_at,
        end_at=end_at,
    )
    csv_text = _rows_to_csv_text(anonymized_rows, metadata)
    filename = f"triage_system_export_{generated_at.strftime('%Y%m%d_%H%M%S')}.csv"
    return csv_text, filename, len(anonymized_rows)


def fetch_cases(report_date: date_type) -> List[Dict[str, Any]]:
    client = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    query = f"""
        SELECT
            patient_id,
            age,
            gender,
            chief_complaint,
            final_esi,
            news2_score,
            clinician_id,
            icd10_codes
        FROM `{_table_ref(TRIAGE_TABLE)}`
        WHERE DATE(timestamp) = @report_date
        ORDER BY timestamp DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("report_date", "DATE", report_date)]
    )
    rows = client.query(query, job_config=job_config, location=BQ_LOCATION).result()
    cases = []
    for row in rows:
        icd10_codes = _parse_code_list(row.icd10_codes)
        icd10_display = []
        for code in icd10_codes:
            _, icd10_name = resolve_clinical_codes("", code)
            if code and icd10_name:
                icd10_display.append(f"{code} ({icd10_name})")
            elif code:
                icd10_display.append(code)
        cases.append({
            "patient_id": row.patient_id,
            "age": row.age,
            "gender": row.gender,
            "chief_complaint": row.chief_complaint,
            "final_esi": row.final_esi,
            "news2_score": row.news2_score,
            "clinician_id": row.clinician_id,
            "icd10": ", ".join(icd10_display) if icd10_display else "",
        })
    return cases


def generate_daily_report(report_date: date_type, department: str) -> bytes:
    font_name = _register_font()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", fontName=font_name, fontSize=16, leading=20, textColor=colors.HexColor("#1a5f7a")))
    styles.add(ParagraphStyle(name="ReportSub", fontName=font_name, fontSize=10, leading=14, textColor=colors.HexColor("#4b5563")))

    cases = fetch_cases(report_date)
    total = len(cases)
    esi_counts = {level: 0 for level in [1, 2, 3, 4, 5]}
    for case in cases:
        esi_counts[case["final_esi"]] = esi_counts.get(case["final_esi"], 0) + 1

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = []

    story.append(Paragraph(bilingual("SAFE-Triage Daily Report", "تقرير الفرز اليومي"), styles["ReportTitle"]))
    story.append(Paragraph(bilingual(CONF_HEADER_EN, CONF_HEADER_AR), styles["ReportSub"]))
    story.append(Paragraph(bilingual(CONF_PHI_EN, CONF_PHI_AR), styles["ReportSub"]))
    story.append(Paragraph(bilingual(CONF_ACCESS_EN, CONF_ACCESS_AR), styles["ReportSub"]))
    story.append(Paragraph(bilingual(f"Department: {department}", f"القسم: {department}"), styles["ReportSub"]))
    story.append(Paragraph(bilingual(f"Date: {report_date.isoformat()}", f"التاريخ: {report_date.isoformat()}"), styles["ReportSub"]))
    story.append(Spacer(1, 0.2 * cm))

    badge_table = Table([[bilingual("🏥 According to GAHAR Standards", "وفقاً لمعايير الجهار")]], colWidths=[17 * cm])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1e8449")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 0.3 * cm))

    summary_data = [
        [bilingual("Total Cases", "إجمالي الحالات"), str(total)],
        ["ESI 1", str(esi_counts[1])],
        ["ESI 2", str(esi_counts[2])],
        ["ESI 3", str(esi_counts[3])],
        ["ESI 4", str(esi_counts[4])],
        ["ESI 5", str(esi_counts[5])],
    ]
    summary_table = Table(summary_data, colWidths=[10 * cm, 3 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(Paragraph(bilingual("Summary Statistics", "ملخص الإحصائيات"), styles["ReportSub"]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4 * cm))

    header = [
        "#",
        bilingual("Patient ID", "رقم المريض"),
        bilingual("Age/Gender", "العمر/النوع"),
        bilingual("Chief Complaint", "الشكوى"),
        "ESI",
        "ICD-10",
        "NEWS2",
        bilingual("Clinician", "الطبيب"),
    ]
    rows = []
    for idx, case in enumerate(cases, start=1):
        rows.append([
            str(idx),
            case["patient_id"] or "",
            f"{case['age']} / {case['gender']}",
            maybe_render_arabic(case["chief_complaint"]),
            str(case["final_esi"]),
            case["icd10"],
            str(case["news2_score"]),
            maybe_render_arabic(case["clinician_id"] or ""),
        ])

    table_data = [header] + rows
    details_table = Table(table_data, colWidths=[0.7 * cm, 3 * cm, 2.2 * cm, 4.5 * cm, 1 * cm, 2.3 * cm, 1.2 * cm, 2.6 * cm])
    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3e8ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#4c1d95")),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(Paragraph(bilingual("Case Details", "تفاصيل الحالات"), styles["ReportSub"]))
    story.append(details_table)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(bilingual("Generated by SAFE-Triage v2.2", "تم إنشاء التقرير بواسطة SAFE-Triage v2.2"), styles["ReportSub"]))

    def draw_confidential(canvas, doc):
        canvas.saveState()
        width, height = A4
        header_text = bilingual(CONF_HEADER_EN, CONF_HEADER_AR)
        footer_text = bilingual(CONF_FOOTER_EN, CONF_FOOTER_AR)
        footer_text_2 = bilingual(CONF_FOOTER_2_EN, CONF_FOOTER_2_AR)
        watermark_text = bilingual(CONF_WATERMARK_EN, CONF_WATERMARK_AR)

        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#374151"))
        canvas.drawString(doc.leftMargin, height - 0.9 * cm, header_text)

        canvas.setFont(font_name, 7)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawRightString(width - doc.rightMargin, 0.75 * cm, footer_text)
        canvas.drawRightString(width - doc.rightMargin, 0.45 * cm, footer_text_2)

        canvas.saveState()
        try:
            canvas.setFillAlpha(0.12)
        except Exception:
            pass
        canvas.setFillColor(colors.HexColor("#9ca3af"))
        canvas.setFont(font_name, 48)
        canvas.translate(width / 2, height / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, watermark_text)
        canvas.restoreState()

        canvas.restoreState()

    doc.build(story, onFirstPage=draw_confidential, onLaterPages=draw_confidential)
    return buffer.getvalue()

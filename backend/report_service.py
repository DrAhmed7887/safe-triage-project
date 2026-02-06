import io
import json
import os
from datetime import datetime, date as date_type
from typing import List, Dict, Any

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
BQ_LOCATION = os.getenv("BQ_LOCATION", "me-west1")


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
        icd10_codes = []
        try:
            if row.icd10_codes:
                icd10_codes = json.loads(row.icd10_codes)
        except Exception:
            icd10_codes = [row.icd10_codes]
        cases.append({
            "patient_id": row.patient_id,
            "age": row.age,
            "gender": row.gender,
            "chief_complaint": row.chief_complaint,
            "final_esi": row.final_esi,
            "news2_score": row.news2_score,
            "clinician_id": row.clinician_id,
            "icd10": ", ".join([code for code in icd10_codes if code]) if icd10_codes else "",
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

import os
import html
import asyncio
from enum import Enum
from datetime import datetime
from threading import Lock
from typing import Dict, Any, Optional

import httpx

GAHAR_NOTICE = "🏥 According to GAHAR Standards | وفقاً لمعايير الجهار"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", ALERT_EMAIL_TO)

ALERT_RECIPIENT_NAME = os.getenv(
    "ALERT_RECIPIENT_NAME",
    "ER Resident on Call | طبيب الطوارئ المناوب",
)

_queue_lock = Lock()
_alert_queue = []


class AlertLevel(str, Enum):
    CODE_RED = "CODE_RED"
    HIGH_ALERT = "HIGH_ALERT"
    ESCALATION = "ESCALATION"
    QA_FLAG = "QA_FLAG"


def _safe_text(value: Optional[str]) -> str:
    return html.escape(value or "")


def _format_recommended(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join([str(v) for v in value if v])
    return str(value) if value else ""


def _alert_banner(level: AlertLevel) -> str:
    if level == AlertLevel.CODE_RED:
        return "🔴🔴🔴"
    if level == AlertLevel.HIGH_ALERT:
        return "🟠🟠🟠"
    if level == AlertLevel.ESCALATION:
        return "🟣🟣🟣"
    return "🟡🟡🟡"


def build_telegram_message(payload: Dict[str, Any]) -> str:
    level = payload.get("alert_level", AlertLevel.HIGH_ALERT)
    line = "━━━━━━━━━━━━━━━━━"
    complaint = _safe_text(payload.get("complaint", ""))
    icd10_code = _safe_text(payload.get("icd10_code", ""))
    icd10_desc = _safe_text(payload.get("icd10_description", ""))
    snomed_code = _safe_text(payload.get("snomed_code", ""))
    snomed_term = _safe_text(payload.get("snomed_term", ""))
    recommended = _safe_text(_format_recommended(payload.get("recommended", "")))
    clinician = _safe_text(payload.get("clinician", "Unassigned | غير محدد"))
    patient_id = _safe_text(payload.get("patient_id", "Unknown"))
    esi_level = _safe_text(str(payload.get("esi_level", "")))
    news2_score = _safe_text(str(payload.get("news2_score", "")))
    timestamp = _safe_text(payload.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    recipient = _safe_text(payload.get("recipient", ALERT_RECIPIENT_NAME))

    header = f"{_alert_banner(level)} <b>SAFE-Triage Alert | تنبيه SAFE-Triage</b>"
    body = [
        header,
        line,
        f"<b>Level | المستوى:</b> {level}",
        f"<b>Patient | المريض:</b> {patient_id}",
        f"<b>ESI:</b> {esi_level} | <b>NEWS2:</b> {news2_score}",
        line,
        f"<b>Complaint | الشكوى:</b> {complaint}",
        f"<b>ICD-10:</b> {icd10_code} ({icd10_desc})",
        f"<b>SNOMED:</b> {snomed_code} ({snomed_term})",
        line,
        f"<b>Recommended | المطلوب:</b> {recommended}",
        f"<b>Clinician | الطبيب:</b> {clinician}",
        f"<b>Time | الوقت:</b> {timestamp}",
        f"📱 <b>Sent to | أُرسل إلى:</b> {recipient}",
        line,
        GAHAR_NOTICE,
    ]
    return "\n".join(body)


def build_email_subject(payload: Dict[str, Any]) -> str:
    level = payload.get("alert_level", AlertLevel.HIGH_ALERT)
    patient_id = payload.get("patient_id", "Unknown")
    esi_level = payload.get("esi_level", "")
    recipient = payload.get("recipient", ALERT_RECIPIENT_NAME)
    recipient_en = recipient.split("|")[0].strip()
    return f"[SAFE-Triage] {level} → {recipient_en}: Patient {patient_id} — ESI {esi_level}"


def build_email_html(payload: Dict[str, Any]) -> str:
    complaint = _safe_text(payload.get("complaint", ""))
    icd10_code = _safe_text(payload.get("icd10_code", ""))
    icd10_desc = _safe_text(payload.get("icd10_description", ""))
    snomed_code = _safe_text(payload.get("snomed_code", ""))
    snomed_term = _safe_text(payload.get("snomed_term", ""))
    recommended = _safe_text(_format_recommended(payload.get("recommended", "")))
    clinician = _safe_text(payload.get("clinician", "Unassigned | غير محدد"))
    patient_id = _safe_text(payload.get("patient_id", "Unknown"))
    esi_level = _safe_text(str(payload.get("esi_level", "")))
    news2_score = _safe_text(str(payload.get("news2_score", "")))
    timestamp = _safe_text(payload.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    recipient = _safe_text(payload.get("recipient", ALERT_RECIPIENT_NAME))
    level = payload.get("alert_level", AlertLevel.HIGH_ALERT)

    return f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>{_alert_banner(level)} SAFE-Triage Alert | تنبيه SAFE-Triage</h2>
      <hr />
      <p><b>Level | المستوى:</b> {level}</p>
      <p><b>Patient | المريض:</b> {patient_id}</p>
      <p><b>ESI:</b> {esi_level} | <b>NEWS2:</b> {news2_score}</p>
      <hr />
      <p><b>Complaint | الشكوى:</b> {complaint}</p>
      <p><b>ICD-10:</b> {icd10_code} ({icd10_desc})</p>
      <p><b>SNOMED:</b> {snomed_code} ({snomed_term})</p>
      <hr />
      <p><b>Recommended | المطلوب:</b> {recommended}</p>
      <p><b>Clinician | الطبيب:</b> {clinician}</p>
      <p><b>Time | الوقت:</b> {timestamp}</p>
      <p>📱 <b>Sent to | أُرسل إلى:</b> {recipient}</p>
      <hr />
      <p><b>{GAHAR_NOTICE}</b></p>
    </div>
    """.strip()


async def _send_telegram(message_html: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ALERT] Telegram not configured")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    async with httpx.AsyncClient(timeout=8) as client:
        resp = await client.post(url, data=payload)
        if resp.status_code >= 200 and resp.status_code < 300:
            return True
        print(f"[ALERT] Telegram failed: {resp.status_code} {resp.text}")
        return False


async def _send_email(subject: str, html_body: str) -> bool:
    if not SENDGRID_API_KEY or not ALERT_EMAIL_TO or not ALERT_EMAIL_FROM:
        print("[ALERT] SendGrid not configured")
        return False
    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": ALERT_EMAIL_TO}]}],
        "from": {"email": ALERT_EMAIL_FROM, "name": "SAFE-Triage"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}],
    }
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 200 and resp.status_code < 300:
            return True
        print(f"[ALERT] Email failed: {resp.status_code} {resp.text}")
        return False


async def _deliver_alert(payload: Dict[str, Any], queue_on_fail: bool = True) -> Dict[str, bool]:
    level = payload.get("alert_level", AlertLevel.HIGH_ALERT)
    message_html = build_telegram_message(payload)
    subject = build_email_subject(payload)
    email_html = build_email_html(payload)

    telegram_ok = False
    email_ok = False

    if level in {AlertLevel.CODE_RED, AlertLevel.HIGH_ALERT, AlertLevel.ESCALATION}:
        telegram_ok = await _send_telegram(message_html)

    if level in {AlertLevel.CODE_RED, AlertLevel.HIGH_ALERT, AlertLevel.ESCALATION, AlertLevel.QA_FLAG}:
        email_ok = await _send_email(subject, email_html)

    queued = False
    if queue_on_fail and not telegram_ok and not email_ok:
        with _queue_lock:
            _alert_queue.append(payload)
        queued = True
        print("[ALERT] Queued alert for retry")

    return {"telegram": telegram_ok, "email": email_ok, "queued": queued}


async def send_alert_async(payload: Dict[str, Any]) -> Dict[str, bool]:
    return await _deliver_alert(payload, queue_on_fail=True)


def send_alert_sync(payload: Dict[str, Any]) -> Dict[str, bool]:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(send_alert_async(payload))
    return loop.create_task(send_alert_async(payload))  # type: ignore[return-value]


async def flush_alert_queue_async() -> Dict[str, Any]:
    with _queue_lock:
        queued = list(_alert_queue)
        _alert_queue.clear()

    if not queued:
        return {"flushed": 0, "remaining": 0}

    failed = []
    for payload in queued:
        result = await _deliver_alert(payload, queue_on_fail=False)
        if not (result.get("telegram") or result.get("email")):
            failed.append(payload)

    if failed:
        with _queue_lock:
            _alert_queue.extend(failed)

    return {"flushed": len(queued) - len(failed), "remaining": len(failed)}


def flush_alert_queue_sync() -> Dict[str, Any]:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(flush_alert_queue_async())
    return loop.create_task(flush_alert_queue_async())  # type: ignore[return-value]


def get_queue_size() -> int:
    with _queue_lock:
        return len(_alert_queue)

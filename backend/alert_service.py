import os
import html
import hashlib
import asyncio
from enum import Enum
from datetime import datetime
from threading import Lock, Thread
from typing import Dict, Any, Optional, Iterable, List

import httpx

try:
    import firebase_admin
    from firebase_admin import messaging
except ImportError:
    firebase_admin = None
    messaging = None

GAHAR_NOTICE = "🏥 According to GAHAR Standards | وفقاً لمعايير الجهار"

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_RECIPIENTS = [
    email.strip()
    for email in os.getenv("ALERT_EMAIL_RECIPIENTS", ALERT_EMAIL_TO).split(",")
    if email.strip()
]
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", ALERT_EMAIL_TO)
ALERT_FRONTEND_URL = os.getenv("ALERT_FRONTEND_URL", "https://safe-triage-ai.web.app")
ALERT_FCM_TOPIC = os.getenv("ALERT_FCM_TOPIC", "critical-alerts")

ALERT_RECIPIENT_NAME = os.getenv(
    "ALERT_RECIPIENT_NAME",
    "ER Resident on Call | طبيب الطوارئ المناوب",
)

_queue_lock = Lock()
_alert_queue = []

_device_lock = Lock()
_fcm_devices: Dict[str, Dict[str, str]] = {}


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


def _alert_title(payload: Dict[str, Any]) -> str:
    """HIPAA-safe push notification title (visible on lock screen)."""
    level = payload.get("alert_level", AlertLevel.HIGH_ALERT)
    esi_level = str(payload.get("esi_level", ""))
    level_label = str(level).replace("_", " ")
    return f"{_alert_banner(level)} SAFE-Triage {level_label} | ESI {esi_level}"


def _alert_body(payload: Dict[str, Any]) -> str:
    """HIPAA-safe push notification body (visible on lock screen).
    No complaint, no vitals, no patient_id — just a prompt to check the dashboard."""
    patient_ref = _phi_safe_patient_ref(str(payload.get("patient_id", "")))
    return f"{patient_ref} requires attention. Tap to review on dashboard. | يتطلب مراجعة. اضغط لفتح لوحة المعلومات."


def _alert_link(payload: Dict[str, Any]) -> str:
    patient_id = str(payload.get("patient_id", "")).strip()
    base_url = ALERT_FRONTEND_URL.rstrip("/")
    if not patient_id:
        return f"{base_url}/dashboard"
    return f"{base_url}/dashboard?case={patient_id}"


def _phi_safe_patient_ref(patient_id: str) -> str:
    """Return a truncated hash of patient_id for HIPAA-safe references outside the secure dashboard."""
    if not patient_id or patient_id == "Unknown":
        return "Case"
    return f"Case #{hashlib.sha256(patient_id.encode()).hexdigest()[:6].upper()}"


def build_email_subject(payload: Dict[str, Any]) -> str:
    level = payload.get("alert_level", AlertLevel.HIGH_ALERT)
    patient_ref = _phi_safe_patient_ref(str(payload.get("patient_id", "")))
    # HIPAA: Do NOT include patient_id, complaint, or clinical details in subject line
    return f"[SAFE-Triage] {level} Alert — {patient_ref} — Action Required"


def build_email_html(payload: Dict[str, Any]) -> str:
    """Build HIPAA-compliant email: NO PHI in email body.
    Clinical details (complaint, ICD-10, SNOMED, vitals) are only
    accessible via the authenticated dashboard link."""
    level = payload.get("alert_level", AlertLevel.HIGH_ALERT)
    patient_ref = _phi_safe_patient_ref(str(payload.get("patient_id", "")))
    esi_level = _safe_text(str(payload.get("esi_level", "")))
    timestamp = _safe_text(payload.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    recipient = _safe_text(payload.get("recipient", ALERT_RECIPIENT_NAME))
    alert_link = _safe_text(_alert_link(payload))

    return f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>{_alert_banner(level)} SAFE-Triage Alert | تنبيه SAFE-Triage</h2>
      <hr />
      <p><b>Alert Level | مستوى التنبيه:</b> {level}</p>
      <p><b>Reference | المرجع:</b> {patient_ref}</p>
      <p><b>Severity | الحدة:</b> ESI {esi_level}</p>
      <p><b>Time | الوقت:</b> {timestamp}</p>
      <p><b>Recipient | المستلم:</b> {recipient}</p>
      <hr />
      <p style="background-color: #FEF3C7; padding: 12px; border-radius: 8px;">
        ⚠️ <b>HIPAA Notice:</b> Clinical details are not included in this email for patient privacy.
        Please review full case details on the secure dashboard.
        <br/>
        ⚠️ <b>تنبيه HIPAA:</b> لم يتم تضمين التفاصيل السريرية في هذا البريد حفاظاً على خصوصية المريض.
        يرجى مراجعة تفاصيل الحالة الكاملة على لوحة المعلومات الآمنة.
      </p>
      <p style="text-align: center; margin: 16px 0;">
        <a href="{alert_link}" style="background-color: #0D9488; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">
          Open SAFE-Triage Dashboard | فتح لوحة المعلومات
        </a>
      </p>
      <hr />
      <p><b>{GAHAR_NOTICE}</b></p>
      <p style="font-size: 11px; color: #6B7280;">
        This message is confidential and intended solely for the recipient.
        If you received this in error, please delete immediately.
      </p>
    </div>
    """.strip()


def _ensure_firebase() -> bool:
    if firebase_admin is None or messaging is None:
        print("[ALERT] firebase-admin not installed")
        return False
    try:
        firebase_admin.get_app()
    except ValueError:
        try:
            firebase_admin.initialize_app()
        except Exception as exc:
            print(f"[ALERT] Firebase init failed: {exc}")
            return False
    except Exception as exc:
        print(f"[ALERT] Firebase unavailable: {exc}")
        return False
    return True


def _normalize_role(role: Optional[str]) -> str:
    return (role or "nurse").strip().lower() or "nurse"


def _registered_push_tokens(roles: Optional[Iterable[str]] = None) -> List[str]:
    allowed = {role.strip().lower() for role in roles or [] if role}
    with _device_lock:
        devices = list(_fcm_devices.values())
    tokens = []
    seen = set()
    for device in devices:
        token = (device.get("token") or "").strip()
        role = _normalize_role(device.get("role"))
        if not token:
            continue
        if allowed and role not in allowed:
            continue
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def register_fcm_device(user_id: str, token: str, role: str) -> Dict[str, Any]:
    registered_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    normalized_role = _normalize_role(role)

    with _device_lock:
        _fcm_devices[user_id] = {
            "token": token,
            "role": normalized_role,
            "registered_at": registered_at,
        }

    subscribed = False
    subscribe_error = None
    if token and _ensure_firebase():
        try:
            messaging.subscribe_to_topic([token], ALERT_FCM_TOPIC)
            subscribed = True
        except Exception as exc:
            subscribe_error = str(exc)
            print(f"[ALERT] Topic subscription failed for {user_id}: {exc}")

    return {
        "status": "registered",
        "user_id": user_id,
        "role": normalized_role,
        "topic": ALERT_FCM_TOPIC,
        "topic_subscribed": subscribed,
        "subscription_error": subscribe_error,
    }


def _push_payload_data(payload: Dict[str, Any]) -> Dict[str, str]:
    """Build FCM data payload. HIPAA: Only include non-PHI fields in the
    notification itself (visible on lock screens). Clinical details go
    in the 'data' envelope which the app reads after authentication."""
    return {
        "alert_level": str(payload.get("alert_level", "")),
        "esi_level": str(payload.get("esi_level", "")),
        # patient_id in data envelope only (not shown on lock screen)
        "case_ref": _phi_safe_patient_ref(str(payload.get("patient_id", ""))),
        "link": _alert_link(payload),
    }


async def _send_push(payload: Dict[str, Any]) -> bool:
    if not _ensure_firebase():
        return False

    title = _alert_title(payload)
    body = _alert_body(payload)
    data = _push_payload_data(payload)
    tokens = _registered_push_tokens({"doctor", "supervisor"})
    icon_url = f"{ALERT_FRONTEND_URL.rstrip('/')}/icons/alert-icon.svg"

    notification = messaging.Notification(title=title, body=body)
    android = messaging.AndroidConfig(priority="high")
    webpush = messaging.WebpushConfig(
        notification=messaging.WebpushNotification(
            title=title,
            body=body,
            icon=icon_url,
            require_interaction=True,
        ),
        fcm_options=messaging.WebpushFCMOptions(link=data["link"]),
    )

    if tokens:
        message = messaging.MulticastMessage(
            notification=notification,
            data=data,
            android=android,
            webpush=webpush,
            tokens=tokens,
        )
        response = await asyncio.to_thread(messaging.send_each_for_multicast, message)
        if response.success_count > 0:
            return True
        print(f"[ALERT] FCM multicast failed for all devices ({response.failure_count} failures)")
        return False

    message = messaging.Message(
        notification=notification,
        data=data,
        android=android,
        webpush=webpush,
        topic=ALERT_FCM_TOPIC,
    )
    try:
        await asyncio.to_thread(messaging.send, message)
        return True
    except Exception as exc:
        print(f"[ALERT] FCM topic send failed: {exc}")
        return False


def get_notification_config_status() -> Dict[str, Any]:
    """Return the current notification configuration status for debugging."""
    return {
        "sendgrid_configured": bool(SENDGRID_API_KEY),
        "email_from_set": bool(ALERT_EMAIL_FROM),
        "email_recipients_set": bool(ALERT_EMAIL_RECIPIENTS),
        "email_recipients_count": len(ALERT_EMAIL_RECIPIENTS),
        "fcm_available": firebase_admin is not None and messaging is not None,
        "fcm_topic": ALERT_FCM_TOPIC,
        "fully_operational": bool(SENDGRID_API_KEY and ALERT_EMAIL_RECIPIENTS and ALERT_EMAIL_FROM),
        "missing_vars": [
            var for var, val in [
                ("SENDGRID_API_KEY", SENDGRID_API_KEY),
                ("ALERT_EMAIL_TO", ALERT_EMAIL_TO),
                ("ALERT_EMAIL_RECIPIENTS", bool(ALERT_EMAIL_RECIPIENTS)),
                ("ALERT_EMAIL_FROM", ALERT_EMAIL_FROM),
            ] if not val
        ],
    }


async def _send_email(subject: str, html_body: str) -> bool:
    if not SENDGRID_API_KEY or not ALERT_EMAIL_RECIPIENTS or not ALERT_EMAIL_FROM:
        missing = []
        if not SENDGRID_API_KEY:
            missing.append("SENDGRID_API_KEY")
        if not ALERT_EMAIL_RECIPIENTS:
            missing.append("ALERT_EMAIL_RECIPIENTS")
        if not ALERT_EMAIL_FROM:
            missing.append("ALERT_EMAIL_FROM")
        print(f"[ALERT] Email disabled — missing env vars: {', '.join(missing)}")
        return False
    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": email} for email in ALERT_EMAIL_RECIPIENTS]}],
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
    subject = build_email_subject(payload)
    email_html = build_email_html(payload)

    push_ok = False
    email_ok = False

    if level in {AlertLevel.CODE_RED, AlertLevel.HIGH_ALERT, AlertLevel.ESCALATION}:
        push_ok = await _send_push(payload)

    if level in {AlertLevel.CODE_RED, AlertLevel.HIGH_ALERT, AlertLevel.ESCALATION, AlertLevel.QA_FLAG}:
        email_ok = await _send_email(subject, email_html)

    queued = False
    if queue_on_fail and not push_ok and not email_ok:
        with _queue_lock:
            _alert_queue.append(payload)
        queued = True
        print("[ALERT] Queued alert for retry")

    return {"push": push_ok, "email": email_ok, "queued": queued}


def _run_coro_sync(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: Dict[str, Any] = {}
    error: Dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:
            error["value"] = exc

    thread = Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


async def send_alert_async(payload: Dict[str, Any]) -> Dict[str, bool]:
    return await _deliver_alert(payload, queue_on_fail=True)


def send_alert_sync(payload: Dict[str, Any]) -> Dict[str, bool]:
    return _run_coro_sync(send_alert_async(payload))


async def flush_alert_queue_async() -> Dict[str, Any]:
    with _queue_lock:
        queued = list(_alert_queue)
        _alert_queue.clear()

    if not queued:
        return {"flushed": 0, "remaining": 0}

    failed = []
    for payload in queued:
        result = await _deliver_alert(payload, queue_on_fail=False)
        if not (result.get("push") or result.get("email")):
            failed.append(payload)

    if failed:
        with _queue_lock:
            _alert_queue.extend(failed)

    return {"flushed": len(queued) - len(failed), "remaining": len(failed)}


def flush_alert_queue_sync() -> Dict[str, Any]:
    return _run_coro_sync(flush_alert_queue_async())


def retry_queued_alerts() -> Dict[str, Any]:
    return flush_alert_queue_sync()


def get_queue_size() -> int:
    with _queue_lock:
        return len(_alert_queue)


def get_queue_status() -> Dict[str, Any]:
    with _queue_lock:
        queued = len(_alert_queue)
        oldest = _alert_queue[0].get("timestamp") if _alert_queue else None
    with _device_lock:
        device_count = len(_fcm_devices)
    return {
        "queued": queued,
        "oldest": oldest,
        "registered_devices": device_count,
        "topic": ALERT_FCM_TOPIC,
    }

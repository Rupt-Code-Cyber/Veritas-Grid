import os
import uuid
import sqlite3
from typing import Optional
from xml.sax.saxutils import escape

import structlog
from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from core.identity_scrubber import CivicIdentityScrubber
from core.logging_config import configure_secure_logging
from core.session_manager import ChatSessionManager


# ============================================================================
# CONFIGURATION
# ============================================================================

configure_secure_logging()
logger = structlog.get_logger()

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "production",
).strip().lower()

GATEWAY_SALT = os.getenv(
    "GATEWAY_SECRET_SALT",
)

DEPLOYMENT_TIER = os.getenv(
    "ACTIVE_DEPLOYMENT_TIER",
    "FREE_PUBLIC",
).strip().upper()

RATE_LIMIT_RULE = os.getenv(
    "SYSTEM_RATE_LIMIT",
    "1000/hour",
).strip()

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "data/civic_gateway.db",
).strip()


# Do not silently use a cryptographic fallback in production.
if not GATEWAY_SALT:
    if ENVIRONMENT == "testing":
        GATEWAY_SALT = (
            "testing-only-fallback-salt"
        )
    else:
        raise RuntimeError(
            "GATEWAY_SECRET_SALT must be configured in production."
        )


# ============================================================================
# TENANT CONFIGURATION
# ============================================================================

TENANT_CONFIG = {
    "NHRC_CIVIC": {
        "tier": "FREE",
    },
    "LEGAL_AID_CIVIC": {
        "tier": "FREE",
    },
    "NESREA_CIVIC": {
        "tier": "FREE",
    },
    "ICPC_CIVIC": {
        "tier": "STARTER",
    },
    "LABOUR_CIVIC": {
        "tier": "FREE",
    },
    "EFCC_CIVIC": {
        "tier": "BUSINESS_ENTERPRISE",
    },
    "DSS_CIVIC": {
        "tier": "FREE",
    },
    "NPF_CIVIC": {
        "tier": "FREE",
    },
    "GLOBAL_CIVIC": {
        "tier": "FREE",
    },
    "STARTER_LAWFIRM_A": {
        "tier": "STARTER",
    },
}


TENANT_TOKENS = {
    "token_efcc_ent": {
        "tenant_id": "EFCC_CIVIC",
        "tier": "BUSINESS_ENTERPRISE",
    },
    "token_npf_free": {
        "tenant_id": "NPF_CIVIC",
        "tier": "FREE",
    },
    "token_icpc_start": {
        "tenant_id": "ICPC_CIVIC",
        "tier": "STARTER",
    },
    "token_lawfirm_start": {
        "tenant_id": "STARTER_LAWFIRM_A",
        "tier": "STARTER",
    },
}


WHATSAPP_TENANT_MAPPING = {
    "1": "NHRC_CIVIC",
    "2": "LEGAL_AID_CIVIC",
    "3": "NESREA_CIVIC",
    "4": "ICPC_CIVIC",
    "5": "LABOUR_CIVIC",
    "6": "EFCC_CIVIC",
    "7": "DSS_CIVIC",
    "8": "NPF_CIVIC",
}


# ============================================================================
# CORE SERVICES
# ============================================================================

scrubber = CivicIdentityScrubber(
    secret_salt=GATEWAY_SALT,
)

redis_host = (
    "localhost"
    if ENVIRONMENT == "testing"
    else "redis_broker"
)

session_manager = ChatSessionManager(
    redis_host=redis_host,
)


# ============================================================================
# RATE LIMITING
# ============================================================================

limiter = Limiter(
    key_func=get_remote_address,
)


# ============================================================================
# FASTAPI
# ============================================================================

app = FastAPI(
    title="Secure Civic Anonymous Intake Gateway",
    version="2.0.0",
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

templates = Jinja2Templates(
    directory="templates",
)


# ============================================================================
# HELPERS
# ============================================================================

def normalize_tenant(tenant_id: str) -> str:
    """
    Normalize and validate a tenant identifier.
    """

    normalized = tenant_id.strip().upper()

    if normalized not in TENANT_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target tenant.",
        )

    return normalized


def xml_response(message: str) -> Response:
    """
    Generate a valid Twilio-compatible XML response.
    """

    safe_message = escape(message)

    body = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Response>"
        f"<Message>{safe_message}</Message>"
        "</Response>"
    )

    return Response(
        content=body,
        media_type="application/xml",
    )


async def enqueue_intake(
    *,
    raw_text: str,
    tracker_token: str,
    tenant_id: str,
    tier_context: str,
) -> None:
    """
    Send an intake record to the worker.

    Testing runs the worker directly.
    Production queues the task asynchronously.
    """

    tenant_id = normalize_tenant(tenant_id)

    if ENVIRONMENT == "testing":
        from worker import process_intake_task_pipeline

        await process_intake_task_pipeline.original_func(
            raw_text=raw_text,
            tracker_token=tracker_token,
            tenant_id=tenant_id,
            tier_context=tier_context,
        )

    else:
        import worker

        worker.process_intake_task_pipeline.kiq(
            raw_text=raw_text,
            tracker_token=tracker_token,
            tenant_id=tenant_id,
            tier_context=tier_context,
        )


# ============================================================================
# TENANT AUTHENTICATION
# ============================================================================

async def verify_tenant_session_token(
    request: Request,
) -> dict:
    """
    Verify the tenant identity associated with the request.

    Production:
        A valid tenant token is mandatory.

    Testing:
        Tenant and tier query parameters may be used.
    """

    authorization = request.headers.get(
        "Authorization"
    )

    query_token = request.query_params.get(
        "token"
    )

    auth_token = authorization or query_token

    if not auth_token:
        if ENVIRONMENT == "testing":
            tenant_id = normalize_tenant(
                request.query_params.get(
                    "tenant",
                    "GLOBAL_CIVIC",
                )
            )

            tier = (
                request.query_params
                .get("tier", "FREE")
                .strip()
                .upper()
            )

            return {
                "tenant_id": tenant_id,
                "tier": tier,
            }

        logger.warning(
            "Unauthenticated tenant access attempt blocked"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Access Denied: Missing tenant credentials."
            ),
        )

    # Support:
    # Authorization: Bearer token_efcc_ent
    if auth_token.lower().startswith("bearer "):
        auth_token = auth_token[7:].strip()

    tenant_profile = TENANT_TOKENS.get(
        auth_token
    )

    if tenant_profile is None:
        logger.warning(
            "Invalid tenant token rejected"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access Denied: Invalid tenant credentials.",
        )

    return tenant_profile


# ============================================================================
# HEALTH
# ============================================================================

@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
async def system_health_check():
    return {
        "status": "ONLINE",
        "ingestion_engine": "ACTIVE",
        "tier_profile": DEPLOYMENT_TIER,
    }


# ============================================================================
# WEB PORTAL
# ============================================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def render_whistleblower_intake_portal(
    request: Request,
):
    return templates.TemplateResponse(
        name="input_form.html",
        context={
            "request": request,
        },
    )


# ============================================================================
# DASHBOARD
# ============================================================================

@app.get(
    "/dashboard",
    response_class=HTMLResponse,
)
async def render_compliance_dashboard_panel(
    request: Request,
    session_profile: dict = Depends(
        verify_tenant_session_token
    ),
):
    normalized_tenant = session_profile[
        "tenant_id"
    ]

    normalized_tier = session_profile[
        "tier"
    ]

    conn = None

    ledger_rows = []
    total_count = 0
    high_risk_count = 0
    avg_density = 0.0

    try:
        conn = sqlite3.connect(
            DATABASE_PATH
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                tracker_token,
                matched_category,
                regulatory_routing_target,
                severity_level,
                anonymized_evidence_body,
                keyword_match_density
            FROM anonymous_ledger_records
            WHERE tenant_id = ?
            ORDER BY id DESC
            """,
            (normalized_tenant,),
        )

        ledger_rows = cursor.fetchall()

        total_count = len(
            ledger_rows
        )

        high_risk_count = sum(
            1
            for row in ledger_rows
            if len(row) > 3
            and str(row[3]).upper()
            in {"HIGH", "CRITICAL"}
        )

        density_values = []

        for row in ledger_rows:
            if len(row) <= 5:
                continue

            value = row[5]

            if value is None:
                continue

            try:
                density_values.append(
                    float(value)
                )
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid keyword density encountered",
                    value=value,
                    tenant_id=normalized_tenant,
                )

        if density_values:
            avg_density = (
                sum(density_values)
                / len(density_values)
            )

    except sqlite3.Error as exc:
        logger.error(
            "Dashboard database read failure",
            error=str(exc),
            tenant_id=normalized_tenant,
        )

    finally:
        if conn is not None:
            conn.close()

    return templates.TemplateResponse(
        name="dashboard.html",
        context={
            "request": request,
            "ledger_rows": ledger_rows,
            "total_count": total_count,
            "high_risk_count": high_risk_count,
            "avg_density": avg_density,
            "tenant_filter": normalized_tenant,
            "current_tier": normalized_tier,
        },
    )


# ============================================================================
# WEB INTAKE WEBHOOK
# ============================================================================

@app.post(
    "/v1/webhooks/web",
)
@limiter.limit(RATE_LIMIT_RULE)
async def process_anonymous_web_submission(
    request: Request,
    report_body: str = Form(...),
    target_tenant: str = Form(...),
):
    if not report_body.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report body cannot be empty.",
        )

    # IMPORTANT:
    # Never trust the tenant value merely because it came from
    # a frontend dropdown.
    sharded_tenant = normalize_tenant(
        target_tenant
    )

    tracker_token = (
        scrubber.generate_anonymous_tracker(
            f"WEB_PORTAL_{uuid.uuid4()}"
        )
    )

    anonymized_text = scrubber.scrub_report_text(
        report_body
    )

    await enqueue_intake(
        raw_text=anonymized_text,
        tracker_token=tracker_token,
        tenant_id=sharded_tenant,
        tier_context=DEPLOYMENT_TIER,
    )

    return {
        "status": "ACCEPTED_FOR_ASYNC_PROCESSING",
        "tracker_receipt_token": tracker_token,
    }


# ============================================================================
# AFRICA'S TALKING SMS WEBHOOK
# ============================================================================

@app.post(
    "/v1/webhooks/africastalking",
)
@app.post(
    "/v1/webhooks/africastalking/",
)
async def handle_incoming_africastalking_sms_webhook(
    request: Request,
    from_: str = Form(..., alias="from"),
    to: str = Form(...),
    text: str = Form(...),
    id: str = Form(...),
):
    clean_sender_phone = from_.strip()

    if not text.strip():
        return Response(
            content="EMPTY_SMS_REJECTED",
            media_type="text/plain",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    tracker_token = (
        scrubber.generate_anonymous_tracker(
            clean_sender_phone
        )
    )

    scrubbed_evidence = (
        scrubber.scrub_report_text(text)
    )

    await enqueue_intake(
        raw_text=scrubbed_evidence,
        tracker_token=tracker_token,
        tenant_id="GLOBAL_CIVIC",
        tier_context=DEPLOYMENT_TIER,
    )

    return Response(
        content="SMS_CAPTURED_SUCCESSFULLY",
        media_type="text/plain",
    )


# ============================================================================
# TWILIO WHATSAPP WEBHOOK
# ============================================================================

@app.post(
    "/v1/webhooks/whatsapp",
)
@app.post(
    "/v1/webhooks/whatsapp/",
)
async def handle_incoming_twilio_whatsapp_webhook(
    request: Request,
    MessageSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    Body: Optional[str] = Form(None),
):
    raw_sender_phone = (
        From
        .replace("whatsapp:", "")
        .strip()
    )

    tracker_token = (
        scrubber.generate_anonymous_tracker(
            raw_sender_phone
        )
    )

    session = (
        session_manager.get_or_create_session(
            tracker_token
        )
    )

    current_state = session.get(
        "current_state"
    )

    target_tenant = session.get(
        "target_tenant_id"
    )

    text_content = (
        Body.strip()
        if Body
        else ""
    )

    # ------------------------------------------------------------------------
    # NEW SESSION
    # ------------------------------------------------------------------------

    if not current_state:

        session_manager.update_session(
            tracker_token,
            {
                "current_state": (
                    "AWAITING_ORG_SELECTION"
                ),
                "target_tenant_id": None,
            },
        )

        return xml_response(
            "🛡️ Secure Anonymous Civic Intake Gateway\n\n"
            "Please select your target routing agency:\n\n"
            "1 - National Human Rights Commission (NHRC)\n"
            "2 - Legal Aid Council of Nigeria\n"
            "3 - NESREA Environmental Monitoring\n"
            "4 - ICPC Anti-Corruption Bureau\n"
            "5 - Ministry of Labour Exploitation Unit\n"
            "6 - Economic and Financial Crimes Commission (EFCC)\n"
            "7 - Department of State Services (DSS)\n"
            "8 - Nigeria Police Force (NPF)"
        )

    # ------------------------------------------------------------------------
    # ORGANIZATION SELECTION
    # ------------------------------------------------------------------------

    if current_state == "AWAITING_ORG_SELECTION":

        selected_tenant = (
            WHATSAPP_TENANT_MAPPING.get(
                text_content
            )
        )

        if not selected_tenant:

            return xml_response(
                "🛡️ Secure Anonymous Civic Intake Gateway\n\n"
                "Invalid selection.\n\n"
                "Please reply with a number from 1 to 8."
            )

        session_manager.update_session(
            tracker_token,
            {
                "current_state": (
                    "AWAITING_REPORT_SUBMISSION"
                ),
                "target_tenant_id": selected_tenant,
            },
        )

        return xml_response(
            "✅ Target Organization Locked.\n\n"
            "Please send your detailed report now. "
            "Your identifying information will be scrubbed "
            "before the report enters the processing pipeline."
        )

    # ------------------------------------------------------------------------
    # REPORT SUBMISSION
    # ------------------------------------------------------------------------

    if current_state == "AWAITING_REPORT_SUBMISSION":

        if not text_content:

            return xml_response(
                "Please send the report details "
                "as a text message."
            )

        if not target_tenant:

            logger.error(
                "WhatsApp session missing target tenant",
                tracker_token=tracker_token,
            )

            session_manager.terminate_session(
                tracker_token
            )

            return xml_response(
                "Your session could not be completed. "
                "Please start a new submission."
            )

        try:
            normalized_tenant = normalize_tenant(
                target_tenant
            )

        except HTTPException:

            logger.error(
                "WhatsApp session contains invalid tenant",
                tracker_token=tracker_token,
                tenant_id=target_tenant,
            )

            session_manager.terminate_session(
                tracker_token
            )

            return xml_response(
                "Your session contains an invalid "
                "organization selection. "
                "Please start a new submission."
            )

        scrubbed_evidence = (
            scrubber.scrub_report_text(
                text_content
            )
        )

        await enqueue_intake(
            raw_text=scrubbed_evidence,
            tracker_token=tracker_token,
            tenant_id=normalized_tenant,
            tier_context=DEPLOYMENT_TIER,
        )

        session_manager.terminate_session(
            tracker_token
        )

        return xml_response(
            "🔒 Secure Submission Captured Successfully!\n\n"
            "Your anonymous tracking token receipt is:\n"
            f"{tracker_token[:16]}...\n\n"
            "Keep this token safe if you need to reference "
            "your submission later."
        )

    # ------------------------------------------------------------------------
    # INVALID SESSION STATE
    # ------------------------------------------------------------------------

    logger.warning(
        "Unknown WhatsApp session state",
        tracker_token=tracker_token,
        current_state=current_state,
    )

    session_manager.terminate_session(
        tracker_token
    )

    return xml_response(
        "Your session has expired or is invalid. "
        "Please send a new message to begin again."
    )
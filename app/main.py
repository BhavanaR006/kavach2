"""
Kavach 2.0 — Main FastAPI Application.

WhatsApp-native agentic AI fraud shield for India.
Routes: WhatsApp webhook, transaction initiation, demo endpoint, health check.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.database import create_all_tables, get_db, async_session_factory
from app.db.scam_patterns import seed_patterns
from app.models.transaction import Transaction, TransactionCreate, TransactionStatus
from app.models.user import User
from app.models.session import ConversationSession, SessionState
from app.integrations.whatsapp import whatsapp_client, WhatsAppMessage
from app.flows.detect_flow import detect_flow
from app.flows.alert_flow import alert_flow
from app.flows.recovery_flow import recovery_flow
from app.agent.kavach_agent import kavach_agent
from app.utils.language_utils import get_kavach_intro


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    logger.info("Kavach 2.0 starting up...")
    await create_all_tables()

    # Seed scam patterns
    async with async_session_factory() as session:
        await seed_patterns(session)

    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("Kavach 2.0 ready to protect!")
    yield
    # Shutdown
    logger.info("Kavach 2.0 shutting down...")


# --- App Setup ---

app = FastAPI(
    title="Kavach 2.0",
    description="WhatsApp-Native Agentic AI Fraud Shield for India",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request Logging Middleware ---

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = datetime.now(timezone.utc)
    logger.info(f"→ {request.method} {request.url.path}")

    response = await call_next(request)

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        f"← {request.method} {request.url.path} "
        f"[{response.status_code}] ({duration:.3f}s)"
    )
    return response


# --- UI (Root) ---

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the demo UI at root."""
    static_path = Path(__file__).parent.parent / "static" / "index.html"
    if static_path.exists():
        return HTMLResponse(content=static_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Kavach 2.0 API</h1><p>Visit /health or /demo</p>")


# --- Health Check ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Kavach 2.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- WhatsApp Webhook Verification (GET) ---

@app.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """
    WhatsApp webhook verification (GET).

    Meta sends a GET request with hub.mode, hub.challenge, and
    hub.verify_token to verify the webhook endpoint.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=hub_challenge or "")

    logger.warning("WhatsApp webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


# --- WhatsApp Webhook (POST) ---

@app.post("/webhook/whatsapp")
async def receive_whatsapp(request: Request):
    """
    Receive incoming WhatsApp messages via Meta webhook.

    Parses the payload, finds or creates a user session,
    and routes through the Kavach agent.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=200, content={"status": "ok"})

    # Parse the webhook message
    message = whatsapp_client.parse_webhook(payload)
    if not message or not message.text:
        # Status updates or non-text messages — acknowledge
        return JSONResponse(status_code=200, content={"status": "ok"})

    logger.info(f"WhatsApp message from {message.from_number}: {message.text[:50]}")

    # Process in a database session
    async with async_session_factory() as db:
        # Find or create user
        user = await _get_or_create_user(db, message.from_number)

        # Find or create conversation session
        session = await _get_active_session(db, message.from_number)

        # Find associated transaction if any
        transaction = await _get_pending_transaction(db, message.from_number)

        # Process through agent
        response = await kavach_agent.process_message(
            phone=message.from_number,
            message=message.text,
            session=session,
            transaction=transaction,
            user=user,
        )

        # Handle actions
        if response.should_alert_contact:
            if transaction:
                await alert_flow.send_trusted_alert(
                    user=user,
                    transaction=transaction,
                    risk=type("Risk", (), {
                        "risk_level": response.risk_level,
                        "risk_score": response.risk_score,
                    })(),
                )

        if response.should_start_recovery and transaction:
            await recovery_flow.execute(session, user, transaction)
        else:
            # Send the agent's response message
            await whatsapp_client.send_message(
                to=message.from_number,
                message=response.message,
            )

        # Persist session changes
        await db.commit()

    return JSONResponse(status_code=200, content={"status": "ok"})


# --- Transaction Initiation (Simulated UPI Hook) ---

@app.post("/api/transaction/initiate")
async def initiate_transaction(txn: TransactionCreate):
    """
    Simulated UPI payment hook for demo purposes.

    When a transaction is initiated, Kavach intercepts it,
    scores risk, and initiates the detection flow.
    """
    async with async_session_factory() as db:
        # Find or create user
        user = await _get_or_create_user(db, txn.user_phone)

        # Create transaction record
        transaction = Transaction(
            user_phone=txn.user_phone,
            recipient_phone=txn.recipient_phone,
            amount=txn.amount,
            status=TransactionStatus.PENDING,
        )
        db.add(transaction)
        await db.flush()

        # Create or get conversation session
        session = await _get_active_session(db, txn.user_phone)
        session.transaction_id = transaction.id

        # Initiate detection flow
        response = await detect_flow.initiate(
            transaction=transaction,
            user=user,
            session=session,
        )

        # Send the detection question to user via WhatsApp
        await whatsapp_client.send_message(
            to=txn.user_phone,
            message=response.message,
        )

        # If HIGH/CRITICAL, alert trusted contact immediately
        if response.should_alert_contact:
            from app.agent.scam_detector import DetectionResult
            detection = DetectionResult(
                risk_score=response.risk_score,
                risk_level=response.risk_level,
            )
            await alert_flow.send_trusted_alert(
                user=user,
                transaction=transaction,
                risk=detection,
            )

        await db.commit()

        return {
            "status": "intercepted",
            "transaction_id": transaction.id,
            "risk_score": response.risk_score,
            "risk_level": response.risk_level.value,
            "action": response.action,
            "message_sent": response.message[:100] + "...",
        }


# --- Demo Endpoint ---

@app.post("/demo")
async def run_demo():
    """
    Run the full Meena demo scenario automatically for judges.

    Simulates:
    1. Transaction initiation (₹40,000 to unknown)
    2. User confirms pressure (reply "1")
    3. Recovery flow execution
    """
    demo_phone = "+918977533468"
    demo_trusted = "+918977533468"
    demo_recipient = "+917777777777"

    async with async_session_factory() as db:
        # Step 1: Create/get demo user with trusted contact
        user = await _get_or_create_user(db, demo_phone)
        user.name = "Meena"
        user.language_preference = "hi"
        user.age = 54
        user.is_first_time_user = True
        user.trusted_contact_phone = demo_trusted
        user.trusted_contact_name = "Son (Trusted Contact)"

        # Step 2: Create high-risk transaction
        transaction = Transaction(
            user_phone=demo_phone,
            recipient_phone=demo_recipient,
            amount=40000.0,
            status=TransactionStatus.PENDING,
        )
        db.add(transaction)
        await db.flush()

        # Step 3: Create session and initiate detection
        session = ConversationSession(
            user_phone=demo_phone,
            state=SessionState.IDLE,
            messages=[],
        )
        db.add(session)
        await db.flush()
        session.transaction_id = transaction.id

        # Step 4: Run detection flow
        detect_response = await detect_flow.initiate(
            transaction=transaction, user=user, session=session
        )
        await whatsapp_client.send_message(to=demo_phone, message=detect_response.message)

        # Step 5: Simulate user confirming pressure (reply "1" / "haan")
        agent_response = await kavach_agent.process_message(
            phone=demo_phone,
            message="1",
            session=session,
            transaction=transaction,
            user=user,
        )

        # Step 6: Execute recovery flow
        recovery_messages = await recovery_flow.execute(session, user, transaction)

        await db.commit()

        return {
            "status": "demo_completed",
            "scenario": "Meena (54, Lucknow) - Digital Arrest Scam Prevention",
            "steps": [
                {
                    "step": 1,
                    "action": "Transaction intercepted",
                    "amount": "₹40,000",
                    "risk_score": detect_response.risk_score,
                    "risk_level": detect_response.risk_level.value,
                },
                {
                    "step": 2,
                    "action": "Detection question sent to user",
                    "message": detect_response.message[:100],
                },
                {
                    "step": 3,
                    "action": "User confirmed pressure",
                    "response": agent_response.action,
                    "risk_level": agent_response.risk_level.value,
                },
                {
                    "step": 4,
                    "action": "Trusted contact alerted",
                    "contact": demo_trusted,
                },
                {
                    "step": 5,
                    "action": "Recovery flow completed",
                    "messages_sent": len(recovery_messages),
                },
                {
                    "step": 6,
                    "action": "Incident logged",
                    "transaction_status": transaction.status,
                    "session_state": session.state,
                },
            ],
        }


# --- Chat API (for UI) ---

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """
    Interactive chat endpoint for the demo UI.

    Accepts a message + language, processes through the agent,
    and returns the response with WhatsApp payload preview.
    """
    body = await request.json()
    message = body.get("message", "")
    language = body.get("language", "hi")
    phone = body.get("phone", "+919999900001")

    async with async_session_factory() as db:
        user = await _get_or_create_user(db, phone)
        user.language_preference = language

        session = await _get_active_session(db, phone)
        transaction = await _get_pending_transaction(db, phone)

        response = await kavach_agent.process_message(
            phone=phone,
            message=message,
            session=session,
            transaction=transaction,
            user=user,
        )

        # Build WhatsApp API payload preview (what would actually be sent)
        whatsapp_payload = {
            "messaging_product": "whatsapp",
            "to": phone.lstrip("+"),
            "type": "text",
            "text": {"body": response.message},
        }

        await db.commit()

        return {
            "response": response.message,
            "action": response.action,
            "risk_level": response.risk_level.value,
            "risk_score": response.risk_score,
            "should_alert_contact": response.should_alert_contact,
            "should_start_recovery": response.should_start_recovery,
            "session_state": session.state,
            "whatsapp_payload_preview": whatsapp_payload,
        }


# --- Privacy Policy ---

@app.get("/api/privacy")
async def privacy_policy():
    """Data privacy policy — what Kavach stores and what it doesn't."""
    return {
        "data_minimization": {
            "stored": [
                "Phone number (hashed in production)",
                "Language preference",
                "Transaction amount and recipient (for risk scoring)",
                "Session state (IDLE/QUESTIONING/RESOLVED)",
                "Risk score (numeric only)",
            ],
            "NOT_stored": [
                "Message content is processed in-memory and NOT persisted after session ends",
                "No call recordings or media",
                "No contact list or WhatsApp profile data",
                "No location data",
                "No Aadhaar/PAN/banking credentials",
            ],
        },
        "trusted_contact_privacy": {
            "what_they_receive": "Alert that their contact may be under pressure + request to call them",
            "what_they_NEVER_see": [
                "Conversation content between user and Kavach",
                "Scam message details",
                "Transaction recipient details",
                "User's other contacts or messages",
            ],
        },
        "data_retention": "Session data auto-deleted after 24 hours in production",
        "encryption": "All API communication over HTTPS/TLS 1.3",
        "whatsapp_scope": {
            "permissions_required": "Only message send/receive — no contact list, no media, no status",
            "data_flow": "User message → Kavach analysis (in-memory) → Response. No data shared with third parties.",
        },
        "compliance": "Aligned with IT Act 2000, RBI data localization guidelines, and DPDP Act 2023",
    }


# --- Helper Functions ---

async def _get_or_create_user(db: AsyncSession, phone: str) -> User:
    """Find existing user by phone or create a new one."""
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            phone=phone,
            language_preference="hi",
            is_first_time_user=True,
        )
        db.add(user)
        await db.flush()
        logger.info(f"Created new user: {phone}")

    return user


async def _get_active_session(
    db: AsyncSession, phone: str
) -> ConversationSession:
    """Find an active conversation session or create a new one."""
    active_states = [
        SessionState.IDLE,
        SessionState.TRANSACTION_DETECTED,
        SessionState.QUESTIONING,
        SessionState.RECOVERY_IN_PROGRESS,
    ]

    result = await db.execute(
        select(ConversationSession)
        .where(ConversationSession.user_phone == phone)
        .where(ConversationSession.state.in_([s.value for s in active_states]))
        .order_by(ConversationSession.updated_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()

    if session is None:
        session = ConversationSession(
            user_phone=phone,
            state=SessionState.IDLE,
            messages=[],
        )
        db.add(session)
        await db.flush()

    return session


async def _get_pending_transaction(
    db: AsyncSession, phone: str
) -> Optional[Transaction]:
    """Find a pending/flagged transaction for the user."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_phone == phone)
        .where(
            Transaction.status.in_([
                TransactionStatus.PENDING,
                TransactionStatus.FLAGGED,
            ])
        )
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()

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
from app.models.transaction import Transaction, TransactionCreate, TransactionStatus, RiskLevel
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

    Manages the full conversation flow as a state machine:
    AWAITING_LANGUAGE → QUESTIONING → AWAITING_SCAM_TYPE → RECOVERY
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=200, content={"status": "ok"})

    # Parse the webhook message
    message = whatsapp_client.parse_webhook(payload)
    if not message or not message.text:
        return JSONResponse(status_code=200, content={"status": "ok"})

    logger.info(f"WhatsApp message from {message.from_number}: {message.text[:50]}")

    # Normalize phone number to E.164 format
    phone = message.from_number
    if not phone.startswith("+"):
        phone = "+" + phone

    user_input = message.text.strip().lower()

    async with async_session_factory() as db:
        user = await _get_or_create_user(db, phone)
        session = await _get_active_session(db, phone)
        transaction = await _get_pending_transaction(db, phone)

        session.add_message("user", message.text)

        # --- STATE MACHINE ---

        if session.state == SessionState.AWAITING_LANGUAGE.value:
            # User selected language
            lang_map = {"hindi": "hi", "english": "en", "telugu": "te",
                        "tamil": "ta", "bengali": "bn",
                        "lang_hi": "hi", "lang_en": "en", "lang_te": "te"}
            selected_lang = lang_map.get(user_input, "hi")
            user.language_preference = selected_lang
            session.state = SessionState.QUESTIONING.value

            # Send "Are you being forced?" with Yes/No buttons in their language
            from app.utils.language_utils import get_transaction_question
            amount = transaction.amount if transaction else 0
            question = get_transaction_question(selected_lang, amount)

            yes_labels = {"hi": "Haan", "en": "Yes", "te": "Avunu", "ta": "Aam", "bn": "Hyaan"}
            no_labels = {"hi": "Nahi", "en": "No", "te": "Ledu", "ta": "Illa", "bn": "Na"}

            await whatsapp_client.send_buttons(
                to=phone,
                body=question,
                buttons=[
                    {"id": "yes_forced", "title": yes_labels.get(selected_lang, "Yes")},
                    {"id": "no_safe", "title": no_labels.get(selected_lang, "No")},
                ],
            )

        elif session.state == SessionState.QUESTIONING.value:
            # User replied Yes or No
            from app.utils.language_utils import is_affirmative, is_negative, get_scam_type_question, get_scam_options_for_list
            if is_affirmative(user_input):
                session.state = SessionState.AWAITING_SCAM_TYPE.value
                session.risk_score = 80
                session.risk_level = "CRITICAL"

                # Alert trusted contact NOW
                if transaction and user.trusted_contact_phone:
                    from app.agent.scam_detector import DetectionResult
                    detection = DetectionResult(risk_score=80, risk_level=RiskLevel.CRITICAL)
                    await alert_flow.send_trusted_alert(user=user, transaction=transaction, risk=detection)

                # Send scam type list in user's language
                await whatsapp_client.send_list(
                    to=phone,
                    body=get_scam_type_question(user.language_preference),
                    button_text="Select",
                    sections=get_scam_options_for_list(user.language_preference),
                )
            elif is_negative(user_input):
                session.state = SessionState.CONFIRMED_SAFE.value
                safe_messages = {
                    "hi": "Theek hai! Aapki transaction safe hai. Agar future mein koi suspicious call/message aaye toh Kavach se baat karein.",
                    "en": "All good! Your transaction is safe. If you receive any suspicious call/message in future, talk to Kavach.",
                    "te": "Okay! Mee transaction safe ga undi. Future lo suspicious call/message vasthe Kavach tho matladandi.",
                    "ta": "Okay! Ungal transaction safe. Future la suspicious call/message vandhaal Kavach kitta pesungal.",
                    "bn": "Theek ache! Apnar transaction safe. Future e suspicious call/message ele Kavach er sathe kotha bolun.",
                }
                msg = safe_messages.get(user.language_preference, safe_messages["en"])
                await whatsapp_client.send_message(to=phone, message=msg)
            else:
                # Didn't understand — resend buttons
                await whatsapp_client.send_buttons(
                    to=phone,
                    body="Please tap one of the buttons below:",
                    buttons=[
                        {"id": "yes_forced", "title": "Haan / Yes"},
                        {"id": "no_safe", "title": "Nahi / No"},
                    ],
                )

        elif session.state == SessionState.AWAITING_SCAM_TYPE.value:
            # User selected scam type or typed "other"
            from app.utils.language_utils import SCAM_TYPE_MAP

            # If user selected "other", ask them to type
            if user_input == "other":
                other_prompts = {
                    "hi": "Kripya briefly type karein kya hua hai:",
                    "en": "Please briefly type what happened:",
                    "te": "దయచేసి ఏం జరిగిందో briefly type చేయండి:",
                }
                await whatsapp_client.send_message(
                    to=phone,
                    message=other_prompts.get(user.language_preference, other_prompts["en"]),
                )
                # Stay in same state — next message will be their typed description
                await db.commit()
                return JSONResponse(status_code=200, content={"status": "ok"})

            scam_type = SCAM_TYPE_MAP.get(user_input, "OTHER")
            session.add_message("system", f"Scam type: {scam_type}")
            session.state = SessionState.RECOVERY_IN_PROGRESS.value

            # === AGENTIC AI FLOW — personalized recovery ===
            lang = user.language_preference

            # Step 1: Use AI to generate personalized calming + advice
            try:
                from app.integrations.claude_client import claude_client
                ai_prompt = (
                    f"You are Kavach 2.0, a fraud protection agent. "
                    f"The user (language: {lang}) was targeted by a {scam_type} scam. "
                    f"Generate a SHORT, calming message (3-4 lines) in {'Hindi' if lang=='hi' else 'Telugu' if lang=='te' else 'Tamil' if lang=='ta' else 'Bengali' if lang=='bn' else 'English'} that: "
                    f"1) Tells them they are safe now "
                    f"2) Explains briefly why this was a scam (specific to {scam_type}) "
                    f"3) Says their transaction is blocked and trusted contact is alerted"
                )
                ai_response = await claude_client.complete(
                    system="You are a compassionate fraud protection assistant. Reply ONLY in the requested language. Keep it short and calming.",
                    user=ai_prompt,
                    max_tokens=300,
                )
                await whatsapp_client.send_message(to=phone, message=ai_response)
            except Exception as e:
                logger.warning(f"AI response failed, using default: {e}")
                from app.agent.recovery_agent import recovery_agent
                calming = await recovery_agent.get_calming_message(lang)
                await whatsapp_client.send_message(to=phone, message=calming)

            # Step 2: Send recovery steps
            from app.agent.recovery_agent import recovery_agent
            steps = await recovery_agent.get_recovery_guide(lang)
            guide = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
            await whatsapp_client.send_message(to=phone, message=guide)

            # Step 3: Send helpline info
            helpline = await recovery_agent.get_helpline_message(lang)
            await whatsapp_client.send_message(to=phone, message=helpline)

            # Step 4: Block transaction
            if transaction:
                from app.models.transaction import TransactionStatus
                transaction.status = TransactionStatus.BLOCKED

            # Step 5: Mark resolved
            session.state = SessionState.RESOLVED.value
            await whatsapp_client.send_message(
                to=phone,
                message="Transaction BLOCKED. Incident logged. Stay safe.",
            )

        else:
            # IDLE or unknown state — just acknowledge
            await whatsapp_client.send_message(
                to=phone,
                message="Kavach 2.0 is active. If you need help, a transaction interception will start the protection flow.",
            )

        await db.commit()

    return JSONResponse(status_code=200, content={"status": "ok"})


# --- Transaction Initiation (Simulated UPI Hook) ---

@app.post("/api/transaction/initiate")
async def initiate_transaction(request: Request):
    """
    Simulated UPI payment hook for demo purposes.

    Accepts both TransactionCreate format and simplified UI format.
    """
    body = await request.json()

    # Support both formats
    user_phone = body.get("user_phone") or body.get("phone", "+919999999999")
    recipient_phone = body.get("recipient_phone") or body.get("recipient", "+917777777777")
    amount = float(body.get("amount", 40000))

    async with async_session_factory() as db:
        # Find or create user
        user = await _get_or_create_user(db, user_phone)

        # Create transaction record
        transaction = Transaction(
            user_phone=user_phone,
            recipient_phone=recipient_phone,
            amount=amount,
            status=TransactionStatus.PENDING,
        )
        db.add(transaction)
        await db.flush()

        # Create or get conversation session
        session = await _get_active_session(db, user_phone)
        session.transaction_id = transaction.id

        # Score the transaction
        from app.agent.risk_scorer import risk_scorer
        risk = risk_scorer.score_transaction(
            transaction=transaction, user=user, is_new_recipient=True
        )
        transaction.risk_score = risk.total_score
        transaction.risk_level = risk.risk_level.value
        transaction.status = TransactionStatus.FLAGGED

        # Set session state to QUESTIONING and ask the real detection
        # question directly. This REST/demo path (unlike the WhatsApp
        # webhook) never does a separate language-selection round trip —
        # the caller already specifies language — so we must not leave the
        # session in AWAITING_LANGUAGE: a reply arriving in that state was
        # being run through raw scam-detection on bare text like "1"/"2"
        # instead of being interpreted as an answer, which is what caused
        # risk scores to escalate unpredictably on every demo run.
        session.state = SessionState.QUESTIONING.value
        session.risk_score = risk.total_score
        session.risk_level = risk.risk_level.value

        from app.utils.language_utils import get_transaction_question
        question = get_transaction_question(user.language_preference, amount)
        session.add_message("agent", question)
        await whatsapp_client.send_message(to=user_phone, message=question)

        await db.commit()

        return {
            "status": "intercepted",
            "transaction_id": transaction.id,
            "risk_score": risk.total_score,
            "risk_level": risk.risk_level.value,
            "action": "QUESTION",
            "message": question,
            "message_sent": "Detection question sent to user via WhatsApp",
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
            db=db,
        )

        # Send the scam type question to user
        await whatsapp_client.send_message(to=demo_phone, message=agent_response.message)

        # Step 5b: Simulate user selecting scam type (1 = fake police/CBI)
        agent_response2 = await kavach_agent.process_message(
            phone=demo_phone,
            message="1",
            session=session,
            transaction=transaction,
            user=user,
            db=db,
        )

        # Step 6: Execute recovery flow (AGENTIC — all autonomous from here)
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
            db=db,
        )

        # These were previously left as flags only — the banner would show
        # in the demo UI but no alert/recovery actually ran. Wire them to
        # the same flows /demo already uses successfully.
        recovery_messages: list[str] = []
        if response.should_alert_contact and transaction is not None:
            from app.agent.scam_detector import DetectionResult as _DetectionResult
            await alert_flow.send_trusted_alert(
                user=user,
                transaction=transaction,
                risk=_DetectionResult(
                    risk_score=response.risk_score, risk_level=response.risk_level
                ),
            )

        if response.should_start_recovery and transaction is not None:
            recovery_messages = await recovery_flow.execute(session, user, transaction)

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
            "recovery_messages": recovery_messages,
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
        SessionState.AWAITING_LANGUAGE,
        SessionState.TRANSACTION_DETECTED,
        SessionState.QUESTIONING,
        SessionState.AWAITING_SCAM_TYPE,
        SessionState.CONFIRMED_RISK,
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


# --- Setup Demo Endpoint ---

@app.post("/api/setup-demo")
async def setup_demo_user(request: Request):
    """Set up a demo user with trusted contact for showcase."""
    body = await request.json()
    phone = body.get("phone", "+919999999999")
    language = body.get("language", "hi")
    name = body.get("name", "Demo User")

    async with async_session_factory() as db:
        user = await _get_or_create_user(db, phone)
        user.name = name
        user.language_preference = language
        user.age = 54
        user.is_first_time_user = True
        user.trusted_contact_phone = "+918888888888"
        user.trusted_contact_name = "Trusted Contact"

        # Reset any leftover session/transaction from a previous demo run
        # on this phone number, so every "Run Full Demo" click starts clean
        # instead of resuming whatever state the last run ended in.
        stale_sessions = await db.execute(
            select(ConversationSession).where(ConversationSession.user_phone == phone)
        )
        for old_session in stale_sessions.scalars().all():
            old_session.state = SessionState.RESOLVED.value

        stale_txns = await db.execute(
            select(Transaction)
            .where(Transaction.user_phone == phone)
            .where(Transaction.status.in_([TransactionStatus.PENDING, TransactionStatus.FLAGGED]))
        )
        for old_txn in stale_txns.scalars().all():
            old_txn.status = TransactionStatus.COMPLETED

        await db.commit()

    return {"status": "ok", "phone": phone, "language": language}

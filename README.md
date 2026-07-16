# Kavach 2.0 — Trusted Circle Agent

> WhatsApp-Native Agentic AI Fraud Shield for India

**Team Bloom** | Bhavana R — Solo Developer (Full Stack + AI/ML)

**Live URL:** https://kavach2-theta.vercel.app  
**GitHub:** https://github.com/BhavanaR006/kavach2

---

## Quick Start (Run on Your System)

### Step 1: Clone the repository

```bash
git clone https://github.com/BhavanaR006/kavach2.git
cd kavach2
```

### Step 2: Create virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
# OR
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### Step 3: Set up environment (optional — works without any keys)

```bash
cp .env.example .env
# The prototype runs fully without any API keys.
# All external services degrade gracefully to mock/log mode.
```

### Step 4: Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Kavach 2.0 starting up...
INFO:     Database tables created successfully
INFO:     Seeded 27 scam patterns into database
INFO:     Kavach 2.0 ready to protect!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Run tests

```bash
pytest tests/ -v
```

Expected output: **34 tests passed**

---

## Test Cases for Judges

Once the server is running at `http://localhost:8000`, try these:

### Test Case 1: Health Check

```bash
curl http://localhost:8000/health
```

**Expected Output:**
```json
{
  "status": "healthy",
  "service": "Kavach 2.0",
  "environment": "development",
  "timestamp": "2026-07-14T..."
}
```

---

### Test Case 2: Full Demo (Runs Complete Fraud Prevention Scenario)

```bash
curl -X POST http://localhost:8000/demo
```

**What happens internally:**
1. Creates user "Meena" (age 54, first-time digital user, Hindi-speaking)
2. Creates a ₹40,000 transaction to an unknown recipient
3. Risk scorer flags it as CRITICAL (score: 85/100) due to: new recipient +30, amount >₹10K +20, first-time user +20, age >50 +15
4. Sends detection question in Hindi to Meena
5. Simulates Meena confirming she is under pressure (reply "1")
6. Alerts trusted contact (her son) via WhatsApp/SMS
7. Executes full recovery flow: calming message → 6 recovery steps → complaint template → 1930 helpline info
8. Logs incident, marks transaction as BLOCKED

**Expected Output:**
```json
{
  "status": "demo_completed",
  "scenario": "Meena (54, Lucknow) - Digital Arrest Scam Prevention",
  "steps": [
    {"step": 1, "action": "Transaction intercepted", "amount": "₹40,000", "risk_score": 85, "risk_level": "CRITICAL"},
    {"step": 2, "action": "Detection question sent to user", "message": "⚠️ Kavach ने देखा..."},
    {"step": 3, "action": "User confirmed pressure", "response": "QUESTION", "risk_level": "LOW"},
    {"step": 4, "action": "Trusted contact alerted", "contact": "+918888888888"},
    {"step": 5, "action": "Recovery flow completed", "messages_sent": 4},
    {"step": 6, "action": "Incident logged", "transaction_status": "BLOCKED", "session_state": "RESOLVED"}
  ]
}
```

---

### Test Case 3: Intercept a High-Risk Transaction

```bash
curl -X POST http://localhost:8000/api/transaction/initiate \
  -H "Content-Type: application/json" \
  -d '{"user_phone": "+919876543210", "recipient_phone": "+917777777777", "amount": 50000}'
```

**Expected Output:**
```json
{
  "status": "intercepted",
  "transaction_id": 1,
  "risk_score": 70,
  "risk_level": "HIGH",
  "action": "QUESTION",
  "message_sent": "⚠️ Kavach ने देखा आप ₹50,000 transfer करने वाले हैं..."
}
```

**What the risk score means:**
- New recipient: +30
- Amount > ₹50,000: +40
- Total: 70 → HIGH risk
- Action: Send clarifying question to user

---

### Test Case 4: Low-Risk Transaction

```bash
curl -X POST http://localhost:8000/api/transaction/initiate \
  -H "Content-Type: application/json" \
  -d '{"user_phone": "+919876543210", "recipient_phone": "+917777777777", "amount": 500}'
```

**Expected Output:**
```json
{
  "status": "intercepted",
  "risk_score": 30,
  "risk_level": "MEDIUM",
  "action": "QUESTION"
}
```

Score is lower (30) because amount is small. Only "new recipient" (+30) applies.

---

### Test Case 5: Simulate a Scam Message via WhatsApp Webhook

```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "919876543210",
            "id": "msg_test_001",
            "timestamp": "1720000000",
            "type": "text",
            "text": {"body": "CBI se bol rahe hain. Aapke khilaf case file hua hai. Turant 50000 transfer karo nahi toh arrest ho jaoge. Kisi ko mat batana."}
          }]
        }
      }]
    }]
  }'
```

**Expected Output:**
```json
{"status": "ok"}
```

**What happens in server logs (check terminal):**
- Scam detector identifies: AUTHORITY_IMPERSONATION (CBI), URGENCY (turant), FINANCIAL_DEMAND (transfer), ISOLATION (mat batana)
- Risk score: 70+ (HIGH)
- Session state moves to QUESTIONING
- Follow-up question sent to user (logged to console since WhatsApp is in mock mode)

---

### Test Case 6: Simulate Safe Message

```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "919999900000",
            "id": "msg_test_002",
            "timestamp": "1720000000",
            "type": "text",
            "text": {"body": "Hi, kaise ho? Kal dinner pe chalein?"}
          }]
        }
      }]
    }]
  }'
```

**Expected:** Normal message, risk score 0, no alerts triggered.

---

### Test Case 7: WhatsApp Webhook Verification

```bash
curl "http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.challenge=test_challenge_123&hub.verify_token=kavach_verify_2024"
```

**Expected Output:**
```
test_challenge_123
```

This is how Meta verifies the webhook endpoint is valid.

---

### Test Case 8: Run Automated Test Suite

```bash
pytest tests/ -v
```

**Expected Output:**
```
tests/test_detector.py::TestKeywordDetection::test_authority_impersonation_english PASSED
tests/test_detector.py::TestKeywordDetection::test_digital_arrest_hindi PASSED
tests/test_detector.py::TestKeywordDetection::test_multiple_signals_compound PASSED
tests/test_detector.py::TestKeywordDetection::test_safe_message_low_score PASSED
tests/test_agent.py::TestAgentCriticalRisk::test_critical_risk_triggers_recovery PASSED
tests/test_agent.py::TestAgentQuestioningState::test_affirmative_response_triggers_recovery PASSED
tests/test_flows.py::TestDetectFlowInitiation::test_initiate_high_risk_alerts_contact PASSED
...
======================== 34 passed ========================
```

---

## Overview

Kavach 2.0 intercepts UPI payment intent, runs a conversational coercion check with the user in their language, silently alerts a trusted contact if fraud is detected, and autonomously guides recovery.

**Key Differentiators:**
- Lives inside WhatsApp — no app download required
- Works in Hindi, Telugu, Tamil, Bengali, and English
- Agentic AI loop: PERCEIVE → REASON → ACT → LEARN
- 27+ scam patterns covering digital arrest, KYC fraud, authority impersonation
- Trusted Circle — silently alerts family/friends when fraud is detected
- Auto-generates cybercrime.gov.in complaint templates
- Graceful degradation — runs fully without any API keys

**The Problem:** ₹22,500 Cr lost to cyber fraud in 2025 alone. 28 Lakh+ fraud cases filed (+24% YoY). 1 in 5 UPI users have been scammed. The primary weapon is isolation — victims are kept on calls for hours, forbidden to contact anyone.

**Our Solution:** Protection where the people already are — inside WhatsApp.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    USER (WhatsApp)                    │
└──────────────────────┬──────────────────────────────┘
                       │ webhook
┌──────────────────────▼──────────────────────────────┐
│              FastAPI Backend (main.py)                │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  WhatsApp   │  │  Transaction │  │   Demo    │  │
│  │  Webhook    │  │  Initiation  │  │  Endpoint │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘  │
└─────────┼────────────────┼─────────────────┼────────┘
          │                │                 │
┌─────────▼────────────────▼─────────────────▼────────┐
│              AGENT LAYER (Agentic Loop)               │
│                                                       │
│  PERCEIVE ──→ REASON ──→ ACT ──→ LEARN               │
│      │            │          │        │               │
│  [Context]  [ScamDetector] [Flows] [Patterns DB]     │
│             [RiskScorer]                              │
└───────────────────────────────────────────────────────┘
          │                │                 │
┌─────────▼────────────────▼─────────────────▼────────┐
│              INTEGRATION LAYER                        │
│  ┌─────────┐ ┌────────┐ ┌─────────┐ ┌───────────┐  │
│  │ Gemini/ │ │WhatsApp│ │ Twilio  │ │ BHASHINI  │  │
│  │ Claude  │ │  API   │ │  SMS    │ │Translation│  │
│  └─────────┘ └────────┘ └─────────┘ └───────────┘  │
└───────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────┐
│              DATA LAYER                              │
│  ┌──────────────┐  ┌──────────────────────────────┐ │
│  │   SQLite /   │  │  Scam Patterns (27+ seeds)  │ │
│  │  PostgreSQL  │  │  Users, Sessions, Txns       │ │
│  └──────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## How the Agentic Loop Works

```
User sends message
        │
        ▼
┌─── PERCEIVE ────┐
│ Read message     │
│ Load session     │
│ Check transaction│
└────────┬─────────┘
         │
         ▼
┌──── REASON ─────┐
│ ScamDetector:    │
│  • Gemini AI     │
│  • Keyword match │
│ RiskScorer:      │
│  • 6 factors     │
└────────┬─────────┘
         │
         ▼
┌───── ACT ───────┐
│ LOW → Allow      │
│ MED → Ask ques   │
│ HIGH → Alert     │
│ CRIT → Recovery  │
└────────┬─────────┘
         │
         ▼
┌──── LEARN ──────┐
│ Log pattern      │
│ Update DB        │
└──────────────────┘
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check — returns service status |
| GET | `/webhook/whatsapp` | WhatsApp webhook verification (hub.challenge) |
| POST | `/webhook/whatsapp` | Receive incoming WhatsApp messages |
| POST | `/api/transaction/initiate` | Simulated UPI payment hook (triggers detection) |
| POST | `/demo` | Run full Meena demo scenario automatically |

---

## Risk Scoring Factors

| Factor | Points | Example |
|--------|--------|---------|
| New recipient (never transacted) | +30 | First time sending to this UPI ID |
| Amount > ₹10,000 | +20 | ₹15,000 transfer |
| Amount > ₹50,000 | +40 | ₹60,000 transfer |
| Within 30 min of incoming call | +25 | Scammer just called |
| Late night (11 PM - 6 AM) | +10 | 2 AM transaction |
| User age > 50 | +15 | Elderly user |
| First-time digital user | +20 | New to UPI |

**Risk Levels:**
- 0-25: LOW → Allow transaction
- 26-50: MEDIUM → Ask clarifying questions
- 51-75: HIGH → Alert trusted contact
- 76-100: CRITICAL → Immediate recovery flow

---

## Scam Patterns Detected (27+ patterns)

| Category | Example | Languages |
|----------|---------|-----------|
| Digital Arrest | "You are under digital arrest, stay on video call" | en, hi |
| Authority Impersonation | Fake CBI/Police/RBI/Court officers | en, hi, te, ta |
| KYC Fraud | "Your KYC expired, account will be frozen" | en, hi |
| Financial Demand | OTP requests, processing fees, fine payments | en, hi |
| Isolation | "Don't tell anyone, confidential investigation" | en, hi |
| Urgency | "Only 10 minutes or arrest warrant issued" | en, hi |
| Lottery/Prize | "You won ₹25 lakh, pay ₹5000 processing fee" | en, hi |
| Fake Job | "Work from home, invest ₹10,000 first" | en, hi |

---

## Environment Variables

| Variable | Description | Required? |
|----------|-------------|-----------|
| `GEMINI_API_KEY` | Google Gemini API key (FREE) | No — keyword fallback works |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (paid) | No — Gemini or fallback used |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp token | No — logs to console |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp sender ID | No — logs to console |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification | No — defaults to kavach_verify_2024 |
| `TWILIO_ACCOUNT_SID` | Twilio SID | No — logs to console |
| `TWILIO_AUTH_TOKEN` | Twilio auth | No — logs to console |
| `TWILIO_PHONE_NUMBER` | Twilio sender | No — logs to console |
| `BHASHINI_API_KEY` | BHASHINI key | No — uses pre-translated strings |
| `BHASHINI_USER_ID` | BHASHINI user | No — uses pre-translated strings |
| `DATABASE_URL` | DB connection | No — defaults to SQLite |

**Important: The entire prototype runs without ANY API keys.** All external services degrade gracefully — messages are logged to console, scam detection uses keyword matching, translations use pre-built strings in 5 languages.

---

## Note for Judges: WhatsApp API Token

The WhatsApp Business Cloud API uses a **temporary access token** that expires every 24 hours. If you're testing live WhatsApp delivery and the token has expired:

1. Go to https://developers.facebook.com/apps → Select "Kavach2" app
2. Navigate to: Use cases → Customize → API Setup
3. Click **"Generate access token"** to get a fresh token
4. Update the `WHATSAPP_ACCESS_TOKEN` environment variable

**If you don't want to set up WhatsApp credentials:**
- The prototype works fully without them
- Messages are logged to the server console instead of being sent
- All detection, risk scoring, alerting logic, and recovery flows execute normally
- The web UI at the root URL (/) demonstrates the full flow visually

**Why a temporary token?** Meta's WhatsApp Cloud API issues 24-hour tokens for test mode. In production, a permanent System User token would be configured. This is standard Meta developer workflow, not a limitation of our code.

---

## API & Technology Stack (as per original design)

| Technology | Status | Notes |
|-----------|--------|-------|
| WhatsApp Business API | LIVE | Meta Cloud API v18.0, test credentials active |
| Google Gemini / Claude AI | LIVE | Gemini free tier for scam detection |
| BHASHINI API | IMPLEMENTED (fallback mode) | Code complete, uses pre-translated strings for 5 languages when key not set |
| Twilio SMS | IMPLEMENTED (fallback mode) | Code complete, logs to console when credentials not set |
| UPI Intent Hook | SIMULATED | `/api/transaction/initiate` simulates real UPI interception |
| I4C Scam Patterns | LIVE | 27 patterns seeded from public domain data |

All 6 technologies from the original design are implemented. WhatsApp and Gemini are live with real credentials. BHASHINI and Twilio gracefully fall back to mock mode — zero code changes needed to activate them with real keys.

---

## Running with Docker

```bash
docker-compose up --build
# Server available at http://localhost:8000
# Then run any test case above
```

---

## Note on WhatsApp Integration

WhatsApp Business Cloud API is **fully integrated and live** with real message delivery. The system sends interactive buttons and list messages — users just tap, no typing needed.

**WhatsApp token expires every 24 hours** (Meta's standard for test mode). To regenerate:
1. Go to developers.facebook.com → Kavach2 app → API Setup
2. Click "Generate access token"
3. Update `WHATSAPP_ACCESS_TOKEN` in Vercel environment variables
4. Redeploy

In production, a permanent System User token would be used (no daily regeneration).

---

## Open-Source Attribution

| Library | Version | License | Role in Build | Source Link |
|---------|---------|---------|---------------|-------------|
| FastAPI | 0.111.0 | MIT | Web framework and API routing | https://github.com/tiangolo/fastapi |
| Anthropic Python SDK | 0.28.0 | MIT | Claude LLM integration for scam detection | https://github.com/anthropic-ai/anthropic-sdk-python |
| Google Gemini API | N/A | Google ToS (free tier) | Primary LLM for scam detection | https://aistudio.google.com |
| SQLAlchemy | 2.0.30 | MIT | ORM for database models | https://github.com/sqlalchemy/sqlalchemy |
| Twilio Python SDK | 9.2.3 | MIT | SMS fallback notifications | https://github.com/twilio/twilio-python |
| Pydantic | 2.7.4 | MIT | Data validation and settings | https://github.com/pydantic/pydantic |
| httpx | 0.27.0 | BSD | Async HTTP client for API calls | https://github.com/encode/httpx |
| loguru | 0.7.2 | MIT | Structured logging | https://github.com/Delgan/loguru |
| pytest | 8.2.2 | MIT | Testing framework | https://github.com/pytest-dev/pytest |
| aiosqlite | 0.20.0 | MIT | Async SQLite driver | https://github.com/omnilib/aiosqlite |
| uvicorn | 0.30.1 | BSD | ASGI server | https://github.com/encode/uvicorn |
| BHASHINI ULCA API | N/A | Govt of India (open access) | Multilingual translation | https://bhashini.gov.in |
| WhatsApp Business Cloud API | N/A | Meta Platform ToS | Primary user interface | https://developers.facebook.com/docs/whatsapp |
| I4C Scam Pattern Data | N/A | Public Domain | Scam pattern seeding | https://www.cybercrime.gov.in |

---

## Project Structure

```
kavach2/
├── app/
│   ├── main.py                  # FastAPI app with all routes
│   ├── config.py                # Pydantic BaseSettings
│   ├── agent/
│   │   ├── kavach_agent.py      # Main orchestrator (PERCEIVE→REASON→ACT→LEARN)
│   │   ├── scam_detector.py     # Gemini/Claude AI + keyword fallback detection
│   │   ├── risk_scorer.py       # Multi-factor transaction risk scoring
│   │   └── recovery_agent.py    # Post-fraud recovery guidance
│   ├── flows/
│   │   ├── detect_flow.py       # Multi-turn detection state machine
│   │   ├── alert_flow.py        # Trusted contact alert (WhatsApp + SMS)
│   │   └── recovery_flow.py     # 6-step recovery orchestration
│   ├── integrations/
│   │   ├── whatsapp.py          # Meta WhatsApp Cloud API v18.0
│   │   ├── twilio_sms.py        # Twilio SMS fallback
│   │   ├── bhashini.py          # BHASHINI ULCA translation
│   │   └── claude_client.py     # Gemini (free) + Claude (paid) with retry
│   ├── models/
│   │   ├── transaction.py       # Transaction ORM + Pydantic schemas
│   │   ├── user.py              # User profile model
│   │   └── session.py           # Conversation session with state machine
│   ├── db/
│   │   ├── database.py          # Async SQLAlchemy engine setup
│   │   └── scam_patterns.py     # Pattern storage and seeding
│   └── utils/
│       ├── language_utils.py    # Multilingual helpers (5 languages)
│       └── complaint_template.py # Cybercrime.gov.in complaint generator
├── tests/
│   ├── test_agent.py            # Agent behavior tests (7 tests)
│   ├── test_detector.py         # Scam detection tests (16 tests)
│   └── test_flows.py            # State machine tests (11 tests)
├── data/
│   └── scam_patterns.json       # 27 seed patterns across 6 categories
├── api/
│   └── index.py                 # Vercel serverless entry point
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── vercel.json
└── README.md
```

---

## License

Built for ScriptedBy{Her} 2.0 (Meesho) by Bhavana R (Team Bloom).

---

*Kavach 2.0 — Because Protection Should Be Where the People Are* 🛡️

# Kavach 2.0 — Trusted Circle Agent

> WhatsApp-Native Agentic AI Fraud Shield for India

**Team Bloom** | Bhavana (Backend & AI/ML) · Tanay (Frontend & Product) · Garvit (Data & Security)

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

**The Problem:** ₹4.8B lost annually to digital fraud in India. 82% of fraud is reported via messaging platforms. 71% of financial fraud starts from a WhatsApp message or call.

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
│  │ Claude  │ │WhatsApp│ │ Twilio  │ │ BHASHINI  │  │
│  │  API    │ │  API   │ │  SMS    │ │Translation│  │
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

## Setup & Installation

### Prerequisites
- Python 3.11+
- pip or conda
- Docker & docker-compose (optional, for containerized deployment)

### Local Setup

```bash
# Clone and enter directory
cd kavach2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | Yes (for AI detection) |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp Business token | For WhatsApp delivery |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp sender phone ID | For WhatsApp delivery |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification token | For webhook setup |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | For SMS fallback |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | For SMS fallback |
| `TWILIO_PHONE_NUMBER` | Twilio sender number (E.164) | For SMS fallback |
| `BHASHINI_API_KEY` | BHASHINI ULCA API key | For translations |
| `BHASHINI_USER_ID` | BHASHINI user ID | For translations |
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `ENVIRONMENT` | Runtime environment | No (defaults to development) |
| `LOG_LEVEL` | Logging level | No (defaults to INFO) |

> **Note:** The system degrades gracefully — if API keys are missing, it logs messages instead of failing.

---

## Running Locally

```bash
# Start the server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v

# Health check
curl http://localhost:8000/health
```

---

## Running with Docker

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build

# View logs
docker-compose logs -f kavach-app

# Stop
docker-compose down
```

For production with PostgreSQL, update `.env`:
```
DATABASE_URL=postgresql+asyncpg://kavach:kavach_secure_pass@postgres:5432/kavach2
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

### Transaction Initiation Payload

```json
{
  "user_phone": "+919999999999",
  "recipient_phone": "+917777777777",
  "amount": 40000.0
}
```

### Demo Response

```json
{
  "status": "demo_completed",
  "scenario": "Meena Sharma - Digital Arrest Scam Prevention",
  "steps": [
    {"step": 1, "action": "Transaction intercepted", "risk_score": 85},
    {"step": 2, "action": "Detection question sent to user"},
    {"step": 3, "action": "User confirmed pressure"},
    {"step": 4, "action": "Trusted contact alerted"},
    {"step": 5, "action": "Recovery flow completed"},
    {"step": 6, "action": "Incident logged"}
  ]
}
```

---

## Demo Flow (Step-by-Step)

This scenario demonstrates Kavach protecting "Meena" (age 55, first-time digital user) from a digital arrest scam:

**Step 1:** Initiate a high-risk transaction
```bash
curl -X POST http://localhost:8000/api/transaction/initiate \
  -H "Content-Type: application/json" \
  -d '{"user_phone": "+919999999999", "recipient_phone": "+917777777777", "amount": 40000}'
```

**Step 2:** System detects high-risk (new recipient + high amount + elderly + first-time user) and sends WhatsApp message in Hindi:
> "⚠️ Kavach ने देखा आप ₹40,000 transfer करने वाले हैं एक नये account में। क्या आपको किसी ने force किया है? (1-हाँ / 2-नहीं)"

**Step 3:** User replies "1" (yes/haan) — confirming they are under pressure

**Step 4:** Kavach immediately alerts trusted contact (Rahul Sharma):
> "🚨 Meena Sharma is about to transfer ₹40,000 to an unknown account and may be under pressure from a scammer. Please call them immediately."

**Step 5:** Kavach sends recovery guide to user in Hindi (6 steps including 1930 helpline)

**Step 6:** Full incident logged with complaint template generated

**Or run the entire flow automatically:**
```bash
curl -X POST http://localhost:8000/demo
```

---

## Open-Source Attribution

| Library | Version | License | Role in Build | Source Link |
|---------|---------|---------|---------------|-------------|
| FastAPI | 0.111.0 | MIT | Web framework and API routing | https://github.com/tiangolo/fastapi |
| Anthropic Python SDK | 0.28.0 | MIT | Claude LLM integration for scam detection | https://github.com/anthropic-ai/anthropic-sdk-python |
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

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_detector.py -v

# Run with coverage (install pytest-cov first)
pytest tests/ --cov=app --cov-report=term-missing
```

**Test Coverage:**
- `test_agent.py` — KavachAgent with mock LLM for LOW/HIGH/CRITICAL risk scenarios
- `test_detector.py` — ScamDetector keyword fallback with Hindi & English messages
- `test_flows.py` — DetectFlow state machine transitions

---

## Project Structure

```
kavach2/
├── app/
│   ├── main.py                  # FastAPI app with all routes
│   ├── config.py                # Pydantic BaseSettings
│   ├── agent/
│   │   ├── kavach_agent.py      # Main orchestrator (PERCEIVE→REASON→ACT→LEARN)
│   │   ├── scam_detector.py     # Claude AI + keyword fallback detection
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
│   │   └── claude_client.py     # Anthropic Claude with retry logic
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
│   ├── test_agent.py
│   ├── test_detector.py
│   └── test_flows.py
├── data/
│   └── scam_patterns.json       # 27+ seed patterns across categories
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Note on WhatsApp Integration

This prototype is **architecturally designed** for WhatsApp Business Cloud API integration. The full webhook handler, message parsing, and response delivery logic is implemented in `app/integrations/whatsapp.py`.

However, for this hackathon demo, **WhatsApp Business API access was not available** (requires Meta business verification which takes several days). The system therefore operates in **graceful degradation mode**:

- All messages that would be sent via WhatsApp are **logged to console** instead
- The `/demo` endpoint proves the complete end-to-end flow works
- When WhatsApp credentials are configured, the system switches to live delivery **with zero code changes**

In production deployment:
1. Register at [Meta Business Suite](https://business.facebook.com)
2. Apply for WhatsApp Business API access
3. Configure webhook URL to `/webhook/whatsapp`
4. Add access token to environment variables
5. All existing code immediately works with real WhatsApp delivery

---

## Live Deployment

**Production URL:** https://kavach2-theta.vercel.app

| Endpoint | Try it |
|----------|--------|
| Health check | `curl https://kavach2-theta.vercel.app/health` |
| Full demo | `curl -X POST https://kavach2-theta.vercel.app/demo` |
| Transaction intercept | `curl -X POST https://kavach2-theta.vercel.app/api/transaction/initiate -H "Content-Type: application/json" -d '{"user_phone":"+919999999999","recipient_phone":"+917777777777","amount":40000}'` |

---

## License

Built for Kavach Hackathon 2.0 by Team Bloom.

---

*Kavach 2.0 — Because Protection Should Be Where the People Are* 🛡️

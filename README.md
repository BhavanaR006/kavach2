# Kavach 2.0 — Trusted Circle Agent 🛡️

> WhatsApp-Native Agentic AI Fraud Shield for India

**Team Bloom** · Bhavana R · IIT Gandhinagar · ScriptedBy{Her} 2.0 — Meesho

| | |
|---|---|
| 🌐 **Live Demo** | https://kavach2-theta.vercel.app |
| 💻 **GitHub** | https://github.com/BhavanaR006/kavach2 |
| 📱 **Interface** | WhatsApp (+ Web UI for demo) |
| 🤖 **AI Backend** | Groq → Gemini → Claude (cascading fallback) |

---

## What is Kavach 2.0?

Kavach 2.0 intercepts a UPI payment **before** it is made, asks the user a simple question in their own language, and — if they confirm they are under pressure — **silently alerts a pre-set trusted contact** (family member) to call them immediately. That is the moment the scam breaks.

It then guides the user through full recovery: calming message → 6 recovery steps → pre-filled cybercrime.gov.in complaint → 1930 helpline instructions. All in Hindi, Telugu, Tamil, Bengali, or English.

**The core insight:** Scams don't succeed because victims are careless. They succeed because victims are deliberately isolated. Kavach breaks that isolation before the money moves.

---

## Quick Start — Run Locally in 2 Minutes

### Step 1: Clone the repo
```bash
git clone https://github.com/BhavanaR006/kavach2.git
cd kavach2
```

### Step 2: Create virtual environment
```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
venv\Scripts\activate          # Windows
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set up environment variables
```bash
cp .env.example .env
```
Open `.env` and fill in your keys (see [Environment Variables](#environment-variables) section below).

> ✅ **The app works with ZERO API keys.** All services degrade gracefully — scam detection uses keyword fallback, messages are logged to console instead of sent. You can run the full demo without any keys.

### Step 5: Start the server
```bash
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO  — Kavach 2.0 starting up...
INFO  — LLM Backend: Groq (free tier, fast)      ← if GROQ_API_KEY is set
INFO  — Database tables created/verified
INFO  — Seeded 27 scam patterns into database
INFO  — Kavach 2.0 ready to protect!
INFO  — Uvicorn running on http://0.0.0.0:8000
```

### Step 6: Open the demo UI
Go to → **http://localhost:8000**

Click any scenario in the left sidebar to see Kavach in action.

---

## Environment Variables

Create a `.env` file in the project root with the following:

```env
# ── AI / LLM (pick at least one — Groq is recommended, it's free) ──────────
GROQ_API_KEY=            # FREE → https://console.groq.com/keys
GEMINI_API_KEY=          # FREE → https://aistudio.google.com/apikey
ANTHROPIC_API_KEY=       # Paid → https://console.anthropic.com (optional)

# ── WhatsApp Business Cloud API (Meta) ──────────────────────────────────────
WHATSAPP_ACCESS_TOKEN=       # developers.facebook.com → Your App → WhatsApp → API Setup
WHATSAPP_PHONE_NUMBER_ID=    # Same page — long numeric ID below the token
WHATSAPP_VERIFY_TOKEN=kavach_verify_2024   # Keep this exactly as shown

# ── Twilio SMS (fallback if WhatsApp fails) ──────────────────────────────────
TWILIO_ACCOUNT_SID=      # https://console.twilio.com
TWILIO_AUTH_TOKEN=       # https://console.twilio.com
TWILIO_PHONE_NUMBER=     # Format: +1xxxxxxxxxx

# ── BHASHINI (Govt of India multilingual API) ────────────────────────────────
BHASHINI_API_KEY=        # https://bhashini.gov.in/ulca (free, takes 1-2 days to approve)
BHASHINI_USER_ID=        # Same portal

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///./kavach.db   # SQLite for local dev (default)

# ── App Config ───────────────────────────────────────────────────────────────
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Key descriptions

| Variable | Required? | Where to get it | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | Recommended | console.groq.com/keys | Free, fast, 30 req/min |
| `GEMINI_API_KEY` | Optional | aistudio.google.com/apikey | Free fallback if Groq not set |
| `ANTHROPIC_API_KEY` | Optional | console.anthropic.com | Paid, used as last resort |
| `WHATSAPP_ACCESS_TOKEN` | Optional | Meta Developer Console | See ⚠️ note below |
| `WHATSAPP_PHONE_NUMBER_ID` | Optional | Meta Developer Console | Found on same page as token |
| `WHATSAPP_VERIFY_TOKEN` | Optional | Set yourself | Must match Meta webhook config |
| `TWILIO_ACCOUNT_SID` | Optional | console.twilio.com | SMS fallback only |
| `TWILIO_AUTH_TOKEN` | Optional | console.twilio.com | SMS fallback only |
| `BHASHINI_API_KEY` | Optional | bhashini.gov.in/ulca | Pre-translated strings used as fallback |
| `DATABASE_URL` | Optional | — | Defaults to local SQLite |

### ⚠️ Important: WhatsApp Token Expires Every 24 Hours

Meta's WhatsApp Business Cloud API issues a **temporary access token** that expires every 24 hours in test/development mode. You must regenerate it daily before testing live WhatsApp delivery.

**How to regenerate:**
1. Go to → https://developers.facebook.com/apps
2. Select your app (Kavach2) → WhatsApp → API Setup
3. Click **"Generate access token"** → copy it
4. Update `WHATSAPP_ACCESS_TOKEN` in your `.env` file (local) and in Vercel environment variables (deployed)
5. Redeploy on Vercel after updating

> In production deployment, a permanent System User token would be configured — no daily regeneration needed. The 24-hour expiry is standard Meta developer/test mode behaviour.

---

## AI Priority Order (Cascading Fallback)

Kavach tries AI providers in this order automatically:

```
1. Groq (FREE, fastest — llama3-8b-8192, ~0.5s response)
        ↓ if not configured or fails
2. Google Gemini (FREE — gemini-2.0-flash-lite)
        ↓ if not configured or fails
3. Anthropic Claude (Paid — claude-sonnet-4-6)
        ↓ if not configured or fails
4. Keyword-based detection (always works, no API needed)
```

**Recommendation:** Set `GROQ_API_KEY` — it is free, extremely fast, and has generous rate limits (30 req/min on free tier).

---

## Deploying to Vercel

### Step 1: Push to GitHub
```bash
git add .
git commit -m "your message"
git push origin main
```
Vercel auto-deploys on every push (takes ~2 minutes).

### Step 2: Add environment variables in Vercel
- vercel.com → Your project → **Settings** → **Environment Variables**
- Add each key from the table above
- Click **Save** → then go to **Deployments** → **Redeploy**

> ⚠️ Vercel does NOT show saved keys again — store them somewhere safe (e.g. a private Notes doc) before pasting into Vercel.

---

## Running Tests
```bash
pytest tests/ -v
```

Expected: **34 tests passed** covering agent behaviour, scam detection, and flow state machine.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Demo web UI |
| GET | `/health` | Health check |
| GET | `/webhook/whatsapp` | WhatsApp webhook verification |
| POST | `/webhook/whatsapp` | Receive incoming WhatsApp messages |
| POST | `/api/transaction/initiate` | Simulate UPI payment interception |
| POST | `/api/chat` | Chat endpoint for demo UI |
| POST | `/api/setup-demo` | Set up a demo user with trusted contact |
| POST | `/demo` | Run full Meena scenario end-to-end |
| GET | `/api/privacy` | Data privacy policy |

---

## Architecture

```
USER (WhatsApp / Web UI)
         │
         ▼
FastAPI Backend (main.py)
         │
    ┌────┴─────────────────────┐
    │      AGENT LAYER         │
    │  PERCEIVE → REASON       │
    │     → ACT → LEARN        │
    │                          │
    │  ScamDetector            │
    │  RiskScorer              │
    │  KavachAgent             │
    └────┬─────────────────────┘
         │
    ┌────┴─────────────────────┐
    │   INTEGRATION LAYER      │
    │  Groq / Gemini / Claude  │
    │  WhatsApp Business API   │
    │  Twilio SMS (fallback)   │
    │  BHASHINI (translation)  │
    └────┬─────────────────────┘
         │
    ┌────┴─────────────────────┐
    │      DATA LAYER          │
    │  SQLite / PostgreSQL     │
    │  27+ Scam Patterns       │
    └──────────────────────────┘
```

---

## How the 3-Step Flow Works

```
Step 1 — DETECT
UPI payment initiated → Kavach intercepts
→ Risk scorer evaluates (amount, recipient, user age, timing)
→ Sends question in user's language:
  "Kya aapko kisi ne is payment ke liye force kiya hai?"

Step 2 — BREAK ISOLATION
User replies "Haan" / "Yes"
→ Kavach silently alerts trusted contact via WhatsApp:
  "Your mother is about to transfer ₹40,000 under pressure. Call NOW."
→ Trusted contact calls → scam breaks

Step 3 — RECOVER
→ Calming message to user in their language
→ 6-step recovery guide
→ Pre-filled cybercrime.gov.in complaint template
→ 1930 helpline instructions
→ Transaction marked BLOCKED
```

---

## Risk Scoring

| Factor | Score |
|---|---|
| New / unknown recipient | +30 |
| Amount > ₹10,000 | +20 |
| Amount > ₹50,000 | +40 |
| Transaction within 30 min of call | +25 |
| Late night (11 PM – 6 AM) | +10 |
| User age > 50 | +15 |
| First-time digital user | +20 |

| Score | Risk Level | Action |
|---|---|---|
| 0–25 | LOW | Allow |
| 26–50 | MEDIUM | Ask clarifying question |
| 51–75 | HIGH | Alert trusted contact |
| 76–100 | CRITICAL | Immediate recovery flow |

---

## Running with Docker

```bash
docker-compose up --build
# App available at http://localhost:8000
```

---

## Project Structure

```
kavach2/
├── app/
│   ├── main.py                   # FastAPI app, all routes
│   ├── config.py                 # Pydantic settings (reads .env)
│   ├── agent/
│   │   ├── kavach_agent.py       # Main agentic loop (PERCEIVE→REASON→ACT→LEARN)
│   │   ├── scam_detector.py      # AI + keyword-based scam detection
│   │   ├── risk_scorer.py        # Multi-factor risk scoring
│   │   └── recovery_agent.py     # Recovery guidance generation
│   ├── flows/
│   │   ├── detect_flow.py        # Multi-turn detection state machine
│   │   ├── alert_flow.py         # Trusted contact alert (WhatsApp + SMS)
│   │   └── recovery_flow.py      # 6-step recovery orchestration
│   ├── integrations/
│   │   ├── whatsapp.py           # Meta WhatsApp Cloud API v18.0
│   │   ├── twilio_sms.py         # Twilio SMS fallback
│   │   ├── bhashini.py           # BHASHINI multilingual translation
│   │   └── claude_client.py      # Groq → Gemini → Claude cascading client
│   ├── models/
│   │   ├── transaction.py        # Transaction model + Pydantic schemas
│   │   ├── user.py               # User profile model
│   │   └── session.py            # Conversation session + state machine
│   ├── db/
│   │   ├── database.py           # Async SQLAlchemy setup
│   │   └── scam_patterns.py      # Pattern seeding (27 patterns)
│   └── utils/
│       ├── language_utils.py     # Multilingual helpers (5 languages)
│       └── complaint_template.py # Complaint generator
├── tests/
│   ├── test_agent.py             # 7 agent behaviour tests
│   ├── test_detector.py          # 16 scam detection tests
│   └── test_flows.py             # 11 state machine tests
├── data/
│   └── scam_patterns.json        # 27 seed scam patterns
├── api/
│   └── index.py                  # Vercel serverless entry point
├── static/
│   └── index.html                # Demo web UI
├── .env.example                  # Template — copy to .env and fill in keys
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── vercel.json
└── README.md
```

---

## Open-Source Attribution

| Library | Version | License | Role in Build | Source |
|---|---|---|---|---|
| FastAPI | ≥0.100.0 | MIT | Web framework and API routing | [github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi) |
| Anthropic Python SDK | ≥0.20.0 | MIT | Claude LLM integration | [github.com/anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) |
| Google Generative AI SDK | ≥0.5.0 | Apache 2.0 | Gemini LLM integration | [github.com/google-gemini/generative-ai-python](https://github.com/google-gemini/generative-ai-python) |
| Groq Python SDK | latest | MIT | Groq LLM integration (primary AI) | [github.com/groq/groq-python](https://github.com/groq/groq-python) |
| SQLAlchemy | ≥2.0.0 | MIT | ORM for all database models | [github.com/sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) |
| aiosqlite | ≥0.19.0 | MIT | Async SQLite driver | [github.com/omnilib/aiosqlite](https://github.com/omnilib/aiosqlite) |
| Twilio Python SDK | ≥8.0.0 | MIT | SMS fallback notifications | [github.com/twilio/twilio-python](https://github.com/twilio/twilio-python) |
| Pydantic | ≥2.0.0 | MIT | Data validation and settings | [github.com/pydantic/pydantic](https://github.com/pydantic/pydantic) |
| pydantic-settings | ≥2.0.0 | MIT | Environment variable management | [github.com/pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) |
| httpx | ≥0.24.0 | BSD | Async HTTP client for API calls | [github.com/encode/httpx](https://github.com/encode/httpx) |
| loguru | ≥0.7.0 | MIT | Structured logging throughout | [github.com/Delgan/loguru](https://github.com/Delgan/loguru) |
| uvicorn | ≥0.22.0 | BSD | ASGI server | [github.com/encode/uvicorn](https://github.com/encode/uvicorn) |
| pytest | ≥7.0.0 | MIT | Testing framework | [github.com/pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| pytest-asyncio | ≥0.21.0 | Apache 2.0 | Async test support | [github.com/pytest-dev/pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) |
| WhatsApp Business Cloud API | v18.0 | Meta Platform ToS | Primary user interface | [developers.facebook.com/docs/whatsapp](https://developers.facebook.com/docs/whatsapp) |
| BHASHINI ULCA API | — | Govt of India (open access) | Multilingual translation | [bhashini.gov.in](https://bhashini.gov.in) |
| I4C Scam Pattern Data | — | Public Domain | Scam pattern library seed data | [cybercrime.gov.in](https://www.cybercrime.gov.in) |

---

## Built For

ScriptedBy{Her} 2.0 — Meesho Women-Only Hackathon
Theme: Building for Bharat with Agentic AI

*Team Bloom · Bhavana R · IIT Gandhinagar*

---

*Kavach 2.0 — Because protection should be where the people are* 🛡️

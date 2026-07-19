# Kavach 2.0 — Trusted Circle Agent 🛡️

> WhatsApp-Native Agentic AI Fraud Shield for India

**Team Bloom** | Bhavana R — IIT Gandhinagar (AI) | ScriptedBy{Her} 2.0 — Meesho

| | |
|---|---|
| 🌐 **Live Demo** | https://kavach2-theta.vercel.app |
| 💻 **GitHub** | https://github.com/BhavanaR006/kavach2 |
| 📱 **Interface** | WhatsApp + Web Demo UI |
| 🤖 **AI Backend** | Groq → Gemini → Claude (cascading fallback) |

---

## What is Kavach 2.0?

Kavach 2.0 intercepts a UPI payment **before** it is made, asks the user a simple question in their own language, and — if they confirm they are under pressure — **silently alerts a pre-set trusted contact** to call them immediately. That is the moment the scam breaks.

It then guides the user through full recovery: calming message → 6-step recovery guide → pre-filled cybercrime.gov.in complaint → bank notification template → 1930 helpline. All in Hindi, Telugu, Tamil, Bengali, or English.

**The core insight:** Scams don't succeed because victims are careless. They succeed because victims are **deliberately isolated**. Kavach breaks that isolation before the money moves.

---

## Quick Start (2 minutes)

```bash
git clone https://github.com/BhavanaR006/kavach2.git
cd kavach2
python -m venv venv
source venv/bin/activate        # macOS/Linux
# OR: venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env            # fill in your keys (see API Keys section below)
uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** — you will see a 4-step guided flow:
1. Enter your details and trusted contact number
2. Select your UPI app (PhonePe / GPay / Paytm / BHIM)
3. Enter payment details
4. Watch Kavach protect you in real time

**Works with ZERO API keys** — uses keyword-based detection as fallback. Add keys only for live AI + WhatsApp delivery.

> **Note on AI backend:** We originally planned to use Google Gemini but switched to Groq (LLaMA 3.1) as the primary backend due to Gemini's aggressive free-tier rate limiting (15 req/min, frequent 429 errors). Groq provides 30 req/min with sub-second responses at no cost.

---

## Demo Limitations & Design Decisions

Kavach 2.0 is a hackathon prototype. Some real-world integrations are simulated in the demo UI due to platform API restrictions:

| Feature | Production Vision | Demo Implementation | Why Simulated |
|---|---|---|---|
| UPI Integration | Native deep-link into PhonePe/GPay via UPI intent API | Simulated UPI payment screen in demo UI | UPI apps do not expose public payment APIs to third parties |
| Cybercrime Portal | Auto-fill complaint on cybercrime.gov.in | Opens portal in new tab + pre-filled complaint letter to copy-paste | Portal has no public form submission API |
| WhatsApp Delivery | Real-time WhatsApp messages to user's phone | WhatsApp Business API fully integrated — token regenerated daily in test mode | Meta issues 24-hr temp tokens in test/dev mode |
| Bank Freeze | Direct API call to user's bank to freeze transfer | Pre-formatted bank notification letter for user to send manually | Indian banks have no public fraud-freeze API for third parties |
| BHASHINI Translation | Live API translation for all 5 languages | Pre-translated strings used as fallback | BHASHINI API approval from Govt takes 1-2 days; key pending |
| API Rate Limits | Unlimited AI inference | Cascading fallback: Groq → Gemini → Claude → keywords | Free tier limits on Groq (30 req/min) and Gemini (15 req/min) |

These reflect real-world platform restrictions — not concept limitations. In a production deployment with proper partnerships, all of these would be live integrations.

---

## API Keys — Complete Setup Guide

All keys are **optional**. The app runs fully without any of them. Add keys to unlock live AI detection and real WhatsApp delivery.

### 1. Groq API Key (FREE — Recommended, Primary AI)
> Fastest LLM, free, 30 req/min. This is the primary AI backend.

1. Go to → https://console.groq.com/keys
2. Sign up (free) → Create API Key → Copy it
3. Add to `.env`: `GROQ_API_KEY=gsk_xxxxxxxxxxxx`

---

### 2. Gemini API Key (FREE — Fallback AI)
> Used automatically if Groq is not configured or fails.

1. Go to → https://aistudio.google.com/apikey
2. Click "Create API Key" → Copy it
3. Add to `.env`: `GEMINI_API_KEY=AIzaSyxxxxxxxxxx`

---

### 3. Anthropic Claude API Key (Paid — Last Resort AI)
> Only used if both Groq and Gemini fail. Completely optional.

1. Go to → https://console.anthropic.com
2. API Keys → Create Key → Copy it
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxx`

---

### 4. WhatsApp Business API (Meta) — For Live WhatsApp Messages

> ⚠️ **The WhatsApp access token expires every 24 hours in test/dev mode. You MUST regenerate it daily before testing live delivery.**

**Step 1 — Get your token and Phone Number ID:**
1. Go to → https://developers.facebook.com/apps
2. Select your app (or create one: Business type → WhatsApp product)
3. Navigate to: **WhatsApp → API Setup**
4. You will see:
   - **Temporary access token** — copy this (valid 24 hours only)
   - **Phone Number ID** — copy this (permanent, never changes)
5. Add to `.env`:
```
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=fill_it_with_yours
WHATSAPP_VERIFY_TOKEN=kavach_verify_2024
```

**Step 2 — Add your phone as a test recipient:**
1. Same API Setup page → "Send and receive messages" → "To" → "Manage phone number list"
2. Add your personal number (+91XXXXXXXXXX)
3. Verify with WhatsApp OTP

**Step 3 — Set webhook (so user replies reach Kavach):**
1. WhatsApp → Configuration → Webhook
2. Callback URL: `https://kavach2-theta.vercel.app/webhook/whatsapp`
3. Verify token: `kavach_verify_2024`
4. Subscribe to: `messages`

**How to regenerate the token every day:**
1. Go to developers.facebook.com → Your App → WhatsApp → API Setup
2. Click **"Generate access token"**
3. Copy the new token
4. Update `WHATSAPP_ACCESS_TOKEN` in your `.env` (local) AND in Vercel → Settings → Environment Variables (deployed)
5. Push to GitHub → Vercel auto-redeploys

> **Why does it expire?** Meta issues 24-hour tokens in test/dev mode. In production, a permanent System User token is configured — no daily regeneration needed. This is standard Meta developer workflow.

---

### 5. Twilio SMS (Optional — SMS Fallback)
> Only activated if WhatsApp delivery fails. Completely optional.

1. Go to → https://console.twilio.com (free trial available)
2. Copy Account SID, Auth Token, and your Twilio phone number
3. Add to `.env`:
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
```

---

### 6. BHASHINI API (Optional — Live Multilingual Translation)
> Pre-translated strings are used as fallback if this key is not set.

1. Go to → https://bhashini.gov.in/ulca
2. Register → Apply for API access (Government of India — free, takes 1-2 days approval)
3. Add to `.env`:
```
BHASHINI_API_KEY=xxxxxxxxxxxxxxxx
BHASHINI_USER_ID=xxxxxxxxxxxxxxxx
```

---

### Your complete `.env` file

```env
# AI / LLM (Groq is recommended — free and fastest)
GROQ_API_KEY=gsk_xxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxx       # optional, paid

# WhatsApp — ⚠️ EXPIRES EVERY 24 HOURS — regenerate daily before testing
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=fill_it_with_yours
WHATSAPP_VERIFY_TOKEN=kavach_verify_2024

# Twilio SMS (optional fallback if WhatsApp fails)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# BHASHINI (optional — pre-translated strings used if not set)
BHASHINI_API_KEY=xxxxxxxxxxxxxxxx
BHASHINI_USER_ID=xxxxxxxxxxxxxxxx

# Database (SQLite for local dev, PostgreSQL for production)
DATABASE_URL=sqlite+aiosqlite:///./kavach.db

# App config
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### AI Priority Order (automatic cascading fallback)

```
1. Groq       — FREE, fastest (~0.5s, llama3-8b, 30 req/min)
      ↓ if not set or fails
2. Gemini     — FREE fallback (gemini-2.0-flash, 15 req/min)
      ↓ if not set or fails
3. Claude     — Paid fallback (claude-sonnet-4-6)
      ↓ if not set or fails
4. Keywords   — Always works, zero API key needed
```

### For Vercel Deployment

Add all keys in: **vercel.com → Your project → Settings → Environment Variables**

> ⚠️ Vercel does NOT show saved keys again after saving. Store them somewhere safe (e.g. a private Notes doc) before pasting into Vercel. After updating any key → Deployments → Redeploy.

---

## User Flow (4 Steps)

1. **User Onboarding** — Enter name, phone, age, language, trusted contact → saved to database
2. **UPI App Selection** — Choose PhonePe / GPay / Paytm / BHIM (simulates real UPI intent)
3. **Payment Screen** — Enter recipient and amount → Kavach AI intercepts and risk-scores instantly
4. **WhatsApp AI Chat** — Full conversation: detection question → scam type → recovery → complaint letter

---

## Running Tests

```bash
pytest tests/ -v
```

Expected: **34 tests passed**

---

## Test Suite — What the 34 Tests Cover

The test suite covers three modules across 34 tests to verify correctness of the core agentic logic.

### test_agent.py — 7 tests (Agent behaviour)

Tests how `KavachAgent` responds at each risk level using mocked LLM responses:

| Test | What it checks |
|---|---|
| `test_low_risk_continues_normally` | Safe message like "Hi how are you?" → action=CONTINUE, no alert |
| `test_high_risk_asks_followup` | Hindi scam message "CBI ne call kiya" → action=QUESTION, session moves to QUESTIONING |
| `test_critical_risk_triggers_recovery` | Full digital arrest message → action=RECOVERY, trusted contact alerted |
| `test_affirmative_response_triggers_recovery` | User says "1" (yes, I'm pressured) → action=ASK_SCAM_TYPE, alert fired |
| `test_negative_response_marks_safe` | User says "2" (no pressure) → action=SAFE, session=CONFIRMED_SAFE |
| `test_messages_recorded_in_session` | Conversation history saved correctly — 2 messages after one exchange |
| No-transaction state | Typing "hi" with no active transaction → welcome message, NOT "transaction safe" |

### test_detector.py — 16 tests (Scam detection accuracy)

Tests the keyword-based fallback detector with real scam message samples:

| Test | What it checks |
|---|---|
| `test_authority_impersonation_english` | "CBI calling. Case filed against you." → AUTHORITY_IMPERSONATION signal |
| `test_authority_impersonation_hindi` | "Police se bol rahe hain. Warrant jari hua." → same signal in Hindi |
| `test_digital_arrest_english` | "You are under digital arrest." → DIGITAL_ARREST, score ≥ 40 |
| `test_digital_arrest_hindi` | "Digital arrest mein hain. Video call mat karo." → same in Hindi |
| `test_kyc_fraud_english` | "Your KYC expired. Account suspended." → KYC_FRAUD signal |
| `test_financial_demand_english` | "Send OTP. Transfer processing fee." → FINANCIAL_DEMAND signal |
| `test_isolation_hindi` | "Kisi ko mat batana." → ISOLATION signal |
| `test_urgency_english` | "Act immediately. Last chance." → URGENCY signal |
| `test_multiple_signals_compound` | CBI + digital arrest + transfer + don't tell → CRITICAL, 3+ signals |
| `test_safe_message_low_score` | "Hi, meet for lunch?" → score=0, LOW, no signals |
| `test_safe_transaction_message` | "Send money for dinner." → LOW risk, normal money talk |
| `test_score_capped_at_100` | Message with all keywords → score never exceeds 100 |
| `test_low_score` | Score 0–25 → RiskLevel.LOW |
| `test_medium_score` | Score 26–50 → RiskLevel.MEDIUM |
| `test_high_score` | Score 51–75 → RiskLevel.HIGH |
| `test_critical_score` | Score 76–100 → RiskLevel.CRITICAL |

### test_flows.py — 11 tests (State machine transitions)

Tests the `DetectFlow` state machine end-to-end:

| Test | What it checks |
|---|---|
| `test_initiate_sets_transaction_detected` | Flow initiation → session moves to TRANSACTION_DETECTED, action=QUESTION |
| `test_initiate_flags_transaction` | Transaction status changes to FLAGGED on initiation |
| `test_initiate_sends_hindi_question` | Question contains the correct amount in Hindi |
| `test_initiate_high_risk_alerts_contact` | ₹60,000 + elderly user → HIGH/CRITICAL, should_alert_contact=True |
| `test_initiate_low_amount_lower_risk` | ₹500 + young user → risk score < 76 |
| `test_process_response_affirmative` | "haan" during QUESTIONING → CONFIRMED_RISK, alert contact, action=ASK_SCAM_TYPE |
| `test_process_response_negative` | "nahi" during QUESTIONING → CONFIRMED_SAFE, action=SAFE, no recovery |
| `test_is_active_questioning` | Session in QUESTIONING → is_active() returns True |
| `test_is_active_transaction_detected` | Session in TRANSACTION_DETECTED → is_active() returns True |
| `test_is_not_active_idle` | Session in IDLE → is_active() returns False |
| `test_is_not_active_resolved` | Session in RESOLVED → is_active() returns False |

**In one line:** The tests verify that the agent responds correctly at every risk level, the scam detector catches real patterns in both Hindi and English, and the state machine transitions work correctly end to end.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Serves the demo web UI |
| GET | `/health` | Health check — returns service status |
| GET | `/webhook/whatsapp` | WhatsApp webhook verification (hub.challenge) |
| POST | `/webhook/whatsapp` | Receive incoming WhatsApp messages |
| POST | `/api/transaction/initiate` | Simulated UPI payment hook (triggers detection) |
| POST | `/api/chat` | Chat endpoint for demo UI |
| POST | `/api/setup-demo` | Set up demo user with trusted contact |
| POST | `/demo` | Run full Meena scenario end-to-end automatically |
| GET | `/api/privacy` | Data privacy policy |

---

## Risk Scoring

| Factor | Points | Example |
|---|---|---|
| New / unknown recipient | +30 | First time sending to this UPI ID |
| Amount > ₹10,000 | +20 | ₹15,000 transfer |
| Amount > ₹50,000 | +40 | ₹60,000 transfer |
| Transaction within 30 min of call | +25 | Scammer just called |
| Late night (11 PM – 6 AM) | +10 | 2 AM transaction |
| User age > 50 | +15 | Elderly user |
| First-time digital user | +20 | New to UPI |

| Score | Risk Level | Action |
|---|---|---|
| 0–25 | LOW | Allow transaction |
| 26–50 | MEDIUM | Ask clarifying question |
| 51–75 | HIGH | Alert trusted contact |
| 76–100 | CRITICAL | Immediate full recovery flow |

---

## Scam Patterns Detected (27+ patterns)

| Category | Example | Languages |
|---|---|---|
| Digital Arrest | "You are under digital arrest, stay on video call" | en, hi |
| Authority Impersonation | Fake CBI / Police / RBI / Court officers | en, hi, te, ta |
| KYC Fraud | "Your KYC expired, account will be frozen" | en, hi |
| Financial Demand | OTP requests, processing fees, fine payments | en, hi |
| Isolation | "Don't tell anyone, confidential investigation" | en, hi |
| Urgency | "Only 10 minutes or arrest warrant issued" | en, hi |
| Lottery / Prize | "You won ₹25 lakh, pay ₹5000 processing fee" | en, hi |
| Fake Job | "Work from home, invest ₹10,000 first" | en, hi |

---

## Test Cases for Judges

### Test Case 1: Health Check

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "healthy", "service": "Kavach 2.0", "environment": "development"}
```

---

### Test Case 2: Full Demo (Meena Scenario)

```bash
curl -X POST http://localhost:8000/demo
```

Simulates Meena (54, Lucknow) — digital arrest scam intercepted, trusted contact alerted, recovery completed, transaction BLOCKED.

**Expected:**
```json
{
  "status": "demo_completed",
  "scenario": "Meena (54, Lucknow) - Digital Arrest Scam Prevention",
  "steps": [
    {"step": 1, "action": "Transaction intercepted", "amount": "₹40,000", "risk_score": 85, "risk_level": "CRITICAL"},
    {"step": 2, "action": "Detection question sent to user"},
    {"step": 3, "action": "User confirmed pressure"},
    {"step": 4, "action": "Trusted contact alerted"},
    {"step": 5, "action": "Recovery flow completed", "messages_sent": 4},
    {"step": 6, "action": "Incident logged", "transaction_status": "BLOCKED"}
  ]
}
```

---

### Test Case 3: High-Risk Transaction

```bash
curl -X POST http://localhost:8000/api/transaction/initiate \
  -H "Content-Type: application/json" \
  -d '{"user_phone": "+919876543210", "recipient_phone": "+917777777777", "amount": 50000}'
```

**Expected:** `risk_score: 70, risk_level: HIGH, action: QUESTION`
(New recipient +30, amount >₹50K +40 = 70)

---

### Test Case 4: Low-Risk Transaction

```bash
curl -X POST http://localhost:8000/api/transaction/initiate \
  -H "Content-Type: application/json" \
  -d '{"user_phone": "+919876543210", "recipient_phone": "+917777777777", "amount": 500}'
```

**Expected:** `risk_score: 30, risk_level: MEDIUM` (only new recipient +30)

---

### Test Case 5: Scam Message Detection

```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{"changes": [{"value": {"messages": [{
      "from": "919876543210",
      "id": "msg_test_001",
      "timestamp": "1720000000",
      "type": "text",
      "text": {"body": "CBI se bol rahe hain. Aapke khilaf case file hua hai. Turant 50000 transfer karo. Kisi ko mat batana."}
    }]}}]}]
  }'
```

**Expected:** `{"status": "ok"}` — server logs show AUTHORITY_IMPERSONATION + URGENCY + ISOLATION detected, risk=HIGH.

---

### Test Case 6: WhatsApp Webhook Verification

```bash
curl "http://localhost:8000/webhook/whatsapp?hub.mode=subscribe&hub.challenge=test_123&hub.verify_token=kavach_verify_2024"
```

**Expected:** `test_123`

---

### Test Case 7: Run Full Test Suite

```bash
pytest tests/ -v
```

**Expected:** `34 passed`

---

## Overview

**Key differentiators:**
- Lives inside WhatsApp — no app download required for end users
- Works in Hindi, Telugu, Tamil, Bengali, and English (BHASHINI)
- Truly agentic — PERCEIVE → REASON → ACT → LEARN loop
- 27+ scam patterns: digital arrest, KYC fraud, authority impersonation, lottery, fake jobs
- Trusted Circle — silently alerts family when fraud detected
- Auto-generates cybercrime.gov.in complaint + bank notification template
- Graceful degradation — runs fully without any API keys

**The problem:** ₹22,500 Cr lost to cyber fraud in 2025. 28 Lakh+ cases filed (+24% YoY). 1 in 5 UPI users scammed. Primary weapon: isolation — victims kept on calls for hours, forbidden to contact anyone.

**Our solution:** Break that isolation before the money moves.

---

## Architecture

```
USER (WhatsApp / Web UI)
         │
         ▼
FastAPI Backend (main.py)
         │
    ┌────┴──────────────────────┐
    │       AGENT LAYER          │
    │  PERCEIVE → REASON         │
    │     → ACT → LEARN          │
    │                            │
    │  KavachAgent               │
    │  ScamDetector              │
    │  RiskScorer                │
    └────┬──────────────────────┘
         │
    ┌────┴──────────────────────┐
    │   INTEGRATION LAYER        │
    │  Groq / Gemini / Claude    │
    │  WhatsApp Business API     │
    │  Twilio SMS (fallback)     │
    │  BHASHINI (translation)    │
    └────┬──────────────────────┘
         │
    ┌────┴──────────────────────┐
    │      DATA LAYER            │
    │  SQLite / PostgreSQL       │
    │  27+ Scam Patterns         │
    │  Users, Sessions, Txns     │
    └───────────────────────────┘
```

---

## How the 3-Step Flow Works

```
Step 1 — DETECT
UPI payment initiated → Kavach intercepts
→ Risk scorer evaluates (amount, recipient, age, time)
→ Sends question in user's language:
  "Kya aapko kisi ne force kiya hai?"

Step 2 — BREAK ISOLATION
User replies "Haan" / "Yes"
→ Silently alerts trusted contact via WhatsApp:
  "Your mother is about to transfer ₹40,000 under pressure. Call NOW."
→ Trusted contact calls → scam breaks

Step 3 — RECOVER
→ Calming message in user's language
→ 6-step recovery guide
→ Pre-filled cybercrime.gov.in complaint letter
→ Bank notification template
→ 1930 helpline instructions
→ Transaction marked BLOCKED
```

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
│   │   ├── risk_scorer.py        # Multi-factor risk scoring (6 factors)
│   │   └── recovery_agent.py     # Recovery guidance + complaint generation
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
│   │   └── scam_patterns.py      # Pattern seeding (27+ patterns)
│   └── utils/
│       ├── language_utils.py     # Multilingual helpers (5 languages)
│       └── complaint_template.py # Complaint + bank notice generator
├── tests/
│   ├── test_agent.py             # 7 agent behaviour tests
│   ├── test_detector.py          # 16 scam detection tests
│   └── test_flows.py             # 11 state machine tests
├── data/
│   └── scam_patterns.json        # 27+ seed scam patterns
├── api/
│   └── index.py                  # Vercel serverless entry point
├── static/
│   └── index.html                # 4-step demo web UI
├── .env.example                  # Template — copy to .env and fill keys
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── vercel.json
└── README.md
```

---

## Environment Variables Reference

| Variable | Required? | Description |
|---|---|---|
| `GROQ_API_KEY` | Recommended | Primary LLM — free, fast (console.groq.com) |
| `GEMINI_API_KEY` | Optional | Fallback LLM — free (aistudio.google.com) |
| `ANTHROPIC_API_KEY` | Optional | Last resort LLM — paid (console.anthropic.com) |
| `WHATSAPP_ACCESS_TOKEN` | Optional | Meta WhatsApp token — **expires every 24 hours** |
| `WHATSAPP_PHONE_NUMBER_ID` | Optional | Meta phone number ID (permanent) |
| `WHATSAPP_VERIFY_TOKEN` | Optional | Webhook verify token (default: kavach_verify_2024) |
| `TWILIO_ACCOUNT_SID` | Optional | Twilio SMS fallback |
| `TWILIO_AUTH_TOKEN` | Optional | Twilio SMS fallback |
| `TWILIO_PHONE_NUMBER` | Optional | Twilio sender number |
| `BHASHINI_API_KEY` | Optional | Live translation — pre-translated strings used as fallback |
| `BHASHINI_USER_ID` | Optional | BHASHINI user ID |
| `DATABASE_URL` | Optional | Defaults to SQLite locally, use PostgreSQL for prod |

---

## Open-Source Attribution

| Library | Version | License | Role in Build | Source |
|---|---|---|---|---|
| FastAPI | ≥0.100.0 | MIT | Web framework and API routing | [github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi) |
| Groq Python SDK | latest | MIT | Primary LLM — llama3-8b-8192 | [github.com/groq/groq-python](https://github.com/groq/groq-python) |
| Anthropic Python SDK | ≥0.20.0 | MIT | Claude LLM fallback | [github.com/anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) |
| Google Generative AI SDK | ≥0.5.0 | Apache 2.0 | Gemini LLM fallback | [github.com/google-gemini/generative-ai-python](https://github.com/google-gemini/generative-ai-python) |
| SQLAlchemy | ≥2.0.0 | MIT | ORM for all database models | [github.com/sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) |
| aiosqlite | ≥0.19.0 | MIT | Async SQLite driver | [github.com/omnilib/aiosqlite](https://github.com/omnilib/aiosqlite) |
| Twilio Python SDK | ≥8.0.0 | MIT | SMS fallback notifications | [github.com/twilio/twilio-python](https://github.com/twilio/twilio-python) |
| Pydantic | ≥2.0.0 | MIT | Data validation and settings | [github.com/pydantic/pydantic](https://github.com/pydantic/pydantic) |
| pydantic-settings | ≥2.0.0 | MIT | Environment variable management | [github.com/pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) |
| httpx | ≥0.24.0 | BSD | Async HTTP client for API calls | [github.com/encode/httpx](https://github.com/encode/httpx) |
| loguru | ≥0.7.0 | MIT | Structured logging throughout | [github.com/Delgan/loguru](https://github.com/Delgan/loguru) |
| uvicorn | ≥0.22.0 | BSD | ASGI server | [github.com/encode/uvicorn](https://github.com/encode/uvicorn) |
| pytest | ≥7.0.0 | MIT | Testing framework (34 tests) | [github.com/pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| pytest-asyncio | ≥0.21.0 | Apache 2.0 | Async test support | [github.com/pytest-dev/pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) |
| WhatsApp Business Cloud API | v18.0 | Meta Platform ToS | Primary user interface + alerts | [developers.facebook.com/docs/whatsapp](https://developers.facebook.com/docs/whatsapp) |
| BHASHINI ULCA API | — | Govt of India (open access) | Multilingual translation | [bhashini.gov.in](https://bhashini.gov.in) |
| I4C Scam Pattern Data | — | Public Domain | Scam pattern library seed data | [cybercrime.gov.in](https://www.cybercrime.gov.in) |

---

## License

Built for ScriptedBy{Her} 2.0 — Meesho Women-Only Hackathon
Theme: Building for Bharat with Agentic AI

*Team Bloom · Bhavana R · IIT Gandhinagar*

---

*Kavach 2.0 — Because protection should be where the people are* 🛡️

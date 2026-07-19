"""
Recovery agent for Kavach 2.0.

Handles post-fraud-detection recovery: generates complaint templates,
bank notifications, recovery guides, and helpline information.
"""

from datetime import datetime
from typing import Optional

from loguru import logger

from app.models.session import ConversationSession
from app.models.user import User
from app.models.transaction import Transaction
from app.integrations.bhashini import bhashini_client
from app.utils.complaint_template import (
    generate_recovery_guide,
    generate_helpline_message,
)


class RecoveryAgent:
    """
    Guides users through post-fraud recovery steps.

    Generates complaint templates, bank notifications, delivers
    multilingual recovery guides, and provides helpline information.
    """

    async def generate_complaint_text(
        self,
        session: ConversationSession,
        user: User,
        transaction: Transaction,
    ) -> str:
        """
        Generate a pre-filled cybercrime.gov.in complaint letter.

        Args:
            session: Conversation session with context.
            user: User profile.
            transaction: The flagged transaction.

        Returns:
            Formatted complaint letter ready for submission.
        """
        date_str = datetime.now().strftime("%d %B %Y")
        datetime_str = datetime.now().strftime("%d %B %Y, %I:%M %p")

        # Determine scam type from session messages
        scam_type = "government officials"
        if session.messages:
            for msg in session.messages:
                content = msg.get("content", "").lower()
                if "digital_arrest" in content:
                    scam_type = "Digital Arrest (fake video call arrest)"
                elif "authority_impersonation" in content or "fake_police" in content:
                    scam_type = "Police/CBI/Government Officers"
                elif "kyc_fraud" in content or "kyc" in content:
                    scam_type = "Bank KYC/Aadhaar Update Officers"
                elif "financial_demand" in content or "otp" in content:
                    scam_type = "Financial Service Agents demanding OTP/money"
                elif "lottery" in content:
                    scam_type = "Lottery/Prize Scam Operators"
                    break

        complaint = f"""
CYBERCRIME COMPLAINT LETTER
============================

TO,
The Station House Officer / Cyber Crime Cell
National Cyber Crime Reporting Portal (cybercrime.gov.in)
Helpline: 1930

DATE: {date_str}

SUBJECT: Complaint Regarding Online Financial Fraud

------------------------------------------------------------
1. COMPLAINANT DETAILS
------------------------------------------------------------
Name         : {user.name or 'Not Provided'}
Phone Number : {user.phone}

------------------------------------------------------------
2. INCIDENT DESCRIPTION
------------------------------------------------------------
I wish to report that I was contacted by fraudsters who
impersonated {scam_type} and coerced me into initiating
a UPI payment under false pretenses. I was deliberately
isolated and threatened, leaving me unable to seek help
from family members during the incident.

------------------------------------------------------------
3. TRANSACTION DETAILS
------------------------------------------------------------
Amount Attempted  : Rs.{transaction.amount:,.0f}
Recipient Account : {transaction.recipient_phone}
Date & Time       : {datetime_str}
Transaction ID    : TXN-{transaction.id}
Status            : BLOCKED by Kavach 2.0

------------------------------------------------------------
4. ACTION REQUESTED
------------------------------------------------------------
I respectfully request the authorities to:
  a) Investigate the fraudulent account mentioned above
  b) Freeze any transactions to/from the recipient account
  c) Take legal action against the perpetrators
  d) Provide acknowledgement of this complaint

------------------------------------------------------------
5. DECLARATION
------------------------------------------------------------
I hereby declare that all information provided above is
true and correct to the best of my knowledge.

Complainant Signature : ___________________________
Full Name             : {user.name or 'Not Provided'}
Date                  : {date_str}
Place                 : ___________________________

------------------------------------------------------------
For assistance: Call 1930 | Visit cybercrime.gov.in
------------------------------------------------------------
""".strip()

        logger.info(f"Generated complaint for user {user.phone}")
        return complaint

    async def generate_bank_notification(
        self,
        session: ConversationSession,
        user: User,
        transaction: Transaction,
    ) -> str:
        """
        Generate a bank fraud notification letter.

        Args:
            session: Conversation session with context.
            user: User profile.
            transaction: The flagged transaction.

        Returns:
            Formatted bank notification letter.
        """
        date_str = datetime.now().strftime("%d %B %Y")

        # Determine scam type
        scam_type = "government officials"
        if session.messages:
            for msg in session.messages:
                content = msg.get("content", "").lower()
                if "digital_arrest" in content:
                    scam_type = "Digital Arrest scammers"
                elif "authority" in content or "police" in content:
                    scam_type = "fake Police/CBI officers"
                elif "kyc" in content:
                    scam_type = "fake KYC update agents"
                elif "otp" in content or "financial" in content:
                    scam_type = "OTP/money demand fraudsters"
                    break

        bank_notice = f"""
BANK FRAUD NOTIFICATION
========================

TO,
The Branch Manager / Customer Care
(Your Bank Name)

DATE: {date_str}

SUBJECT: Urgent Request - Suspected Fraud - Please Freeze Transaction

Dear Sir/Madam,

I, {user.name or 'Account Holder'}, with mobile number {user.phone},
wish to report a suspected fraudulent transaction and request immediate action.

------------------------------------------------------------
TRANSACTION DETAILS
------------------------------------------------------------
Amount        : Rs.{transaction.amount:,.0f}
Transferred To: {transaction.recipient_phone}
Date & Time   : {transaction.initiated_at}
Reference ID  : TXN-{transaction.id}

------------------------------------------------------------
REQUEST
------------------------------------------------------------
I was coerced by fraudsters impersonating {scam_type}.
I request you to:
  1. Immediately freeze / reverse the above transaction
  2. Block further transactions to the recipient account
  3. Provide written acknowledgement of this complaint

I have also:
  - Filed complaint at cybercrime.gov.in
  - Called the 1930 Cyber Crime Helpline

Yours sincerely,
{user.name or 'Account Holder'}
{user.phone}
{date_str}

------------------------------------------------------------
""".strip()

        logger.info(f"Generated bank notification for user {user.phone}")
        return bank_notice

    async def get_recovery_guide(self, language: str) -> list[str]:
        """Get step-by-step recovery guide in user's language."""
        steps = generate_recovery_guide(language)

        if language not in {"hi", "te", "ta", "bn", "en"}:
            english_steps = generate_recovery_guide("en")
            translated_steps = []
            for step in english_steps:
                translated = await bhashini_client.translate(step, "en", language)
                translated_steps.append(translated)
            return translated_steps

        logger.info(f"Recovery guide retrieved in language: {language}")
        return steps

    async def get_helpline_message(self, language: str) -> str:
        """Get 1930 helpline instructions in user's language."""
        message = generate_helpline_message(language)

        if language not in {"hi", "te", "ta", "bn", "en"}:
            message = await bhashini_client.translate(
                generate_helpline_message("en"), "en", language
            )

        logger.info(f"Helpline message retrieved in language: {language}")
        return message

    async def get_calming_message(self, language: str) -> str:
        """Get an immediate calming message for the user after fraud detection."""
        calming_messages = {
            "hi": (
                "🙏 शांत रहिए। आप सुरक्षित हैं।\n\n"
                "Kavach ने आपकी सुरक्षा के लिए यह transaction रोक दिया है। "
                "चिंता न करें — हम आपकी मदद करेंगे। "
                "नीचे recovery steps दिए गए हैं।"
            ),
            "te": (
                "🙏 ప్రశాంతంగా ఉండండి. మీరు సురక్షితంగా ఉన్నారు.\n\n"
                "Kavach మీ భద్రత కోసం ఈ లావాదేవీని ఆపింది. "
                "ఆందోళన చెందకండి — మేము మీకు సహాయం చేస్తాము. "
                "క్రింద recovery steps ఉన్నాయి."
            ),
            "ta": (
                "🙏 அமைதியாக இருங்கள். நீங்கள் பாதுகாப்பாக உள்ளீர்கள்.\n\n"
                "Kavach உங்கள் பாதுகாப்பிற்காக இந்த பரிவர்த்தனையை நிறுத்தியது. "
                "கவலைப்படாதீர்கள் — நாங்கள் உங்களுக்கு உதவுவோம். "
                "கீழே recovery steps உள்ளன."
            ),
            "bn": (
                "🙏 শান্ত থাকুন। আপনি নিরাপদ আছেন।\n\n"
                "Kavach আপনার সুরক্ষার জন্য এই লেনদেন বন্ধ করেছে। "
                "চিন্তা করবেন না — আমরা আপনাকে সাহায্য করব। "
                "নিচে recovery steps দেওয়া আছে।"
            ),
            "en": (
                "🙏 Stay calm. You are safe.\n\n"
                "Kavach has stopped this transaction for your protection. "
                "Don't worry — we will help you through this. "
                "Recovery steps are provided below."
            ),
        }

        message = calming_messages.get(language, calming_messages["en"])
        logger.info(f"Calming message delivered in language: {language}")
        return message


# Singleton instance
recovery_agent = RecoveryAgent()

"""
Recovery agent for Kavach 2.0.

Handles post-fraud-detection recovery: generates complaint templates,
provides recovery guides, and delivers helpline information in the
user's preferred language.
"""

from typing import Optional

from loguru import logger

from app.models.session import ConversationSession
from app.models.user import User
from app.models.transaction import Transaction
from app.integrations.bhashini import bhashini_client
from app.utils.complaint_template import (
    generate_complaint,
    generate_recovery_guide,
    generate_helpline_message,
)


class RecoveryAgent:
    """
    Guides users through post-fraud recovery steps.

    Generates complaint templates, delivers multilingual recovery guides,
    and provides helpline information via BHASHINI translation.
    """

    async def generate_complaint_text(
        self,
        session: ConversationSession,
        user: User,
        transaction: Transaction,
    ) -> str:
        """
        Generate a pre-filled cybercrime.gov.in complaint.

        Args:
            session: Conversation session with context.
            user: User profile.
            transaction: The flagged transaction.

        Returns:
            Formatted complaint text ready for submission.
        """
        complaint = generate_complaint(session, user, transaction)
        logger.info(f"Generated complaint for user {user.phone}")
        return complaint

    async def get_recovery_guide(self, language: str) -> list[str]:
        """
        Get step-by-step recovery guide in user's language.

        Steps are pre-translated. If the language is not directly supported,
        falls back to English and attempts BHASHINI translation.

        Args:
            language: User's preferred language code.

        Returns:
            List of recovery step strings in the specified language.
        """
        # Get pre-translated guide
        steps = generate_recovery_guide(language)

        # If language not in our pre-built set, translate from English
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
        """
        Get 1930 helpline instructions in user's language.

        Args:
            language: User's preferred language code.

        Returns:
            Helpline instruction message in the specified language.
        """
        message = generate_helpline_message(language)

        # Translate if language not directly supported
        if language not in {"hi", "te", "ta", "bn", "en"}:
            message = await bhashini_client.translate(
                generate_helpline_message("en"), "en", language
            )

        logger.info(f"Helpline message retrieved in language: {language}")
        return message

    async def get_calming_message(self, language: str) -> str:
        """
        Get an immediate calming message for the user after fraud detection.

        Args:
            language: User's preferred language code.

        Returns:
            Calming message in the specified language.
        """
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

import httpx
from typing import List, Dict
from app.config import get_settings
from app.models.schemas import Language, InteractionMode
import structlog

logger = structlog.get_logger()
settings = get_settings()

class MenuService:
    """Handle interactive menu creation for WhatsApp"""
    def __init__(self):
        self.api_url = f"{settings.WABA_API_URL}/{settings.WABA_PHONE_NUMBER_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.WABA_ACCESS_TOKEN}",
            "Content-type": "application/json"
        }
    
    def get_welcome_message(self) -> Dict[str, str]:
        """get Billingual weloe message"""
        return {
             "urdu": """السلام علیکم! 🏥

میں آپ کی صحت کی دیکھ بھال میں مدد کے لیے حاضر ہوں۔

براہ کرم اپنی پسندیدہ زبان منتخب کریں:
اردو کے لیے "1" یا "اردو" لکھیں
English کے لیے "2" یا "English" لکھیں

آپ کسی بھی وقت زبان تبدیل کر سکتے ہیں۔""",
            "english": """Hello!
I'm here to help you with medical assistance.

Please select your preferred language
Type "1" or "Urdu" for Urdu
Type "2" or "English" for English

You can change language at any time."""
        }

    def get_mode_selection_message(self, language: Language) -> str:
        """Get interaction mode selection messsage"""
        messages = {
            Language.URDU: """شکریہ! 🙏

اب براہ کرم بات چیت کا طریقہ منتخب کریں:

*آڈیو/آواز* - مجھ سے بات کریں
   (وائس میسج بھیجیں یا "voice" لکھیں)

*ٹیکسٹ/متن* - مجھے پیغام بھیجیں  
   (ٹائپ کریں یا "text" لکھیں)

آپ کسی بھی وقت طریقہ تبدیل کر سکتے ہیں۔""",
            Language.ENGLISH: """Thank You!

Now please select your interaction language:

*Voice/Audio - Talk to me
(Send voice message or type voice)

*Text/Message - Type to me 
(Type your message or type "voice")

You can change mode anytime"""
        }
        return messages.get(language, messages[Language.ENGLISH])

    def get_confirmation_message(
        self,
        language: Language,
        mode: InteractionMode
    ) -> str:
        """Get confirmation msg after setup"""

        mode_text= {
            InteractionMode.VOICE: {
                Language.URDU: "آواز/آڈیو",
                Language.ENGLISH: "Voice/Audio"
            },
            InteractionMode.TEXT:{
                Language.URDU:  "متن/ٹیکسٹ",
                Language.ENGLISH: "Text/Message"
            }
        }

        messages = {
            Language.URDU:  f"""بہترین!
آپ کی ترتیبات:
• زبان: اردو
• طریقہ: {mode_text[mode][Language.URDU]}

اب آپ مجھ سے کچھ بھی پوچھ سکتے ہیں:
• ڈاکٹر تلاش کریں
• اپائنٹمنٹ کے اوقات دریافت کریں
• علاج کے بارے میں معلومات حاصل کریں

زبان یا طریقہ تبدیل کرنے کے لیے "settings" لکھیں۔

آپ کی کیا مدد کر سکتا ہوں؟""",
            Language.ENGLISH: f"""Perfect!
Your settings:
Language: English
Mode: {mode_text[mode][Language.ENGLISH]}

You can now ask me anything:
Find a doctor
Get appointment timings
Get treatment information

Type "settings" to change language or mode.

How can i help you?"""
        }
        return messages.get(language, messages[Language.ENGLISH])
    
    def get_help_message(self, language: Language) -> str:
        """Get help message"""
        messages = {
            Language.URDU:  """میں آپ کی کیسے مدد کر سکتا ہوں؟ 🏥

آپ مجھ سے یہ پوچھ سکتے ہیں:

👨‍⚕️ **ڈاکٹر تلاش کریں**
• "دل کے ڈاکٹر دکھائیں"
• "ڈاکٹر احمد کے اوقات کیا ہیں؟"

📅 **اپائنٹمنٹ**
• "پیر کو کون سے ڈاکٹر دستیاب ہیں؟"
• "کارڈیالوجی کی اپائنٹمنٹ"

💊 **علاج کی معلومات**
• "دل کی بیماری کا علاج"
• "ذیابیطس کی دیکھ بھال"

⚙️ **ترتیبات تبدیل کریں**
• "settings" - زبان یا طریقہ تبدیل کریں
• "help" - یہ مینو دوبارہ دیکھیں""",
            Language.ENGLISH: """How can I help you? 
You can ask me:

👨‍⚕️ **Find Doctors**
• "Show me cardiologists"
• "What are Dr. Ahmed's timings?"

📅 **Appointments**
• "Which doctors are available on Monday?"
• "Cardiology appointment"

💊 **Treatment Information**
• "Heart disease treatment"
• "Diabetes care"

⚙️ **Change Settings**
• "settings" - Change language or mode
• "help" - Show this menu again"""
        }
        return messages.get(language, messages[Language.ENGLISH])
    def get_settings_menu(self, current_language: Language, current_mode: InteractionMode) -> str:
        """Get settings menu"""
        messages = {
            Language.URDU: f"""**موجودہ ترتیبات**

زبان: {"اردو" if current_language == Language.URDU else "English"}
طریقہ: {"آواز" if current_mode == InteractionMode.VOICE else "متن"}

**تبدیل کرنے کے لیے:**
• "language" - زبان تبدیل کریں
• "mode" - طریقہ تبدیل کریں
• "back" - واپس جائیں""",
            Language.ENGLISH: f"""**Current Settings**
Language: {"Urdu" if current_language == Language.URDU else "English"}
Mode: {"Voice" if current_mode == InteractionMode.VOICE else "Text"}

**To Change:**
"language" - Change Language
"mode" - Change Mode
"back" - Go back"""
        }
        return messages.get(current_language, messages[Language.ENGLISH])

    async def send_interactive_buttons(
        self,
        to: str, 
        body_text: str, 
        buttons: List[Dict[str, str]]
    ) -> bool:
        """Send interactive button message (if available in WABA tier)"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": body_text
                    },
                    "action": {
                        "buttons": buttons
                    }
                }
            }

            async with httpx.AsyncClient as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

            logger.info("interactive_buttons_sent", to=to)
            return True

        except Exception as e:
            logger.error("interactive_buttons_failed", to=to, error=str(e))
            return False

menu_service = MenuService()

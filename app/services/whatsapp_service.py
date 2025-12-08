import httpx
from typing import Optional
from app.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

class WhatsAppService:
    """handles whatsapp business api integration"""
    def __init__(self):
        self.api_url = f"{settings.WABA_API_URL}/{settings.WABA_PHONE_NUMBER_ID}/messages"
        self.headers = {
            "Authorization": f"Bearer {settings.WABA_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

    async def send_text_message(self, to: str, text: str) -> bool:
        """send a text message via whatsapp"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": text,
                "text": {
                    "preview_url": False,
                    "body": text
                }   
            }

            async with httpx.AsyncClient as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
            
            logger.info("text_message_sent", to=to, length=len(text))
            return True

        except Exception as e:
            logger.error("text_message_failed", to=to, error=str(e))
            return False

    async def send_audio_message(self, to: str, audio_url: str) -> bool:
        """send an audio message via whatsapp"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "audio",
                "audio": {
                    "link": audio_url
                }
            }

            async with httpx.AsyncClient as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()


            logger.info("audio_message_sent", to=to, audio_url=audio_url)
            return True

        except Exception as e:
            logger.warning("audio_message_failed", to=to, error=str(e))
            return False

    async def upload_media(self, audio_content : bytes) -> Optional[str]:
        """
        Upload audio file to WhatsApp and get media ID
        Note: This returns a media ID, not a public URL
        You'll need to host the audio file on your server for direct URL access
        """

        try:
            upload_url = f"{settings.WABA_API_URL}/{settings.WABA_PHONE_NUMBER_ID}/media"
            files = {
                "file": {"audio.ogg", audio_content, "audio/ogg"},
                "messaging_product": {None, "whatsapp"},
                "type": {None, "audio/ogg"}
            }

            headers = {"Authorization": f"Bearer {settings.WABA_ACCESS_TOKEN}"}

            async with httpx.AsyncClient as client:
                response = await client.post(
                    upload_url,
                    headers=headers,
                    files=files,
                    timeout=60.0
                )

                response.raise_for_status()

            media_id = response.json().get("id")
            logger.info("media_uploaded", media_id=media_id)
            return media_id

        except Exception as e:
            logger.error("media_uploaded_failed", error=str(e))
            return None

    async def send_audio_by_id(self, to: str, media_id: str) -> bool:
        """Send audio via whatsapp media id"""

        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "audio",
                "audio": {
                    "id": media_id
                }
            }

            async with httpx.AsyncClient as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

            logger.info("audio_message_sent_by_id", to=to, media_id=media_id)
            return True

        except Exception as e:
            logger.error("audio_message_by_id_failed", to=to, error=str(e))
            return False


    async def mark_message_read(self, message_id: str) -> bool:
        """Mark a message as read"""

        try:
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }

            async with httpx.AsyncClient as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()

            logger.info("message_marked_read", message_id=message_id)
            return True

        except Exception as e:
            logger.error("marked_read_failed", message_id=message_id, error=str(e))
            return False
    
    async def send_reaction(self, to: str, message_id: str, emoji: str) -> bool:
        """Send a reaction to a message"""

        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "reaction",
                "reaction": {
                    "message_id": message_id,
                    "emoji": emoji
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

            logger.info("reaction_sent", to=to, emoji=emoji)
            return True

        except Exception as e:
            logger.error("reaction_failed", to=to, error=str(e))
            return False

whatsapp_service = WhatsAppService()


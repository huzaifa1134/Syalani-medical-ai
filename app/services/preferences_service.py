import redis.asyncio as redis   
import json
from typing import Optional
from datetime import datetime
from app.config import get_settings
from app.models.schemas import UserPreferences, Language, InteractionMode
import structlog

logger = structlog.get_logger()
settings = get_settings()

class PreferencesService:
    """Manages user language and interaction preferences"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize redis connection"""
        try:
            import ssl as ssl_module

            # Create SSL context that doesn't verify certificates
            ssl_context = ssl_module.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl_module.CERT_NONE

            # Connect to Redis with SSL
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=int(settings.REDIS_PORT),
                db=int(settings.REDIS_DB),
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                ssl=True,
                ssl_cert_reqs=None,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True
            )

            await self.redis_client.ping()
            logger.info("preferences_redis_connected")
        except Exception as e:
            logger.error("preferences_redis_connection_failed", error=str(e), host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            raise 
    async def disconnect(self):
        """Close redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("preferences_redis_disconnected")
    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences"""
        try:
            key = f"preferences:{user_id}"
            data = await self.redis_client.get(key)

            if data:
                prefs_dict = json.loads(data)
                preferences = UserPreferences(**prefs_dict)
                logger.info(
                    "preferences_retrieved",
                    user_id=user_id,
                    language=preferences.language,
                    mode=preferences.interaction_mode
                )
                return preferences
            else:
                logger.info("preferences_default", user_id=user_id)
                return UserPreferences(
                    user_id=user_id,
                    language=Language.AUTO,
                    interaction_mode=InteractionMode.NOT_SET
                )
        except Exception as e:
            logger.error("preferences_retrieval_failed", user_id=user_id, error=str(e))
            return UserPreferences(user_id=user_id)

    async def save_preferences(self, preferences: UserPreferences) -> bool:
        """Save user preferences"""
        try:
            key = f"preferences:{preferences.user_id}"
            preferences.last_updated = datetime.utcnow()

            data = preferences.model_dump_json()
            await self.redis_client.set(key, data)

            logger.info(
                "preferences_saved",
                user_id=preferences.user_id,
                language=preferences.language,
                mode=preferences.interaction_mode
            )
            return True
        except Exception as e:
            logger.error("preferences_save_failed", user_id=preferences.user_id, error=str(e))
            return False

    async def set_language(self, user_id: str, language: Language) -> bool:
        """Set user prefered language"""
        try:
            preferences = await self.get_preferences(user_id)
            preferences.language = language
            return await self.save_preferences(preferences)
        except Exception as e:
            logger.error("language_set_failed", user_id=user_id, error=str(e))
            return False

    async def set_interaction_mode(self, user_id: str, mode: InteractionMode) -> bool:
        """Set user's prefered interaction mode"""
        try:
            preferences = await self.get_preferences(user_id)
            preferences.interaction_mode = mode
            return await self.save_preferences(preferences)
        except Exception as e:
            logger.error("mode_set_failed", user_id=user_id, error=str(e))
            return False
    
    async def needs_onboarding(self, user_id: str) -> bool:
        """Check if user needs onboarding (first time user)"""
        preferences = await self.get_preferences(user_id)
        return preferences.interaction_mode == InteractionMode.NOT_SET

    def get_language_config(self, language: Language) -> dict:
        """Get language-specific configuration"""
        configs = {
            Language.URDU: {
                "stt_code": "ur-PK",
                "tts_code": "ur-PK",
                "tts_voice": "ur-PK-Standard-A",
                "name": "Urdu"
            },
            Language.ENGLISH: {
                "stt_code": "en-US",
                "tts_code": "en-US",
                "tts_voice": "en-US-Neural2-A",
                "name": "English"
            },
            Language.AUTO: {
                "stt_code": "ur-PK",
                "tts_code": "ur-PK",
                "tts_voice": "ur-PK-Standard-A",
                "name": "Auto"
            }
        }
        return configs.get(language, configs[Language.AUTO])

preferences_service = PreferencesService()
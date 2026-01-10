from logging import error
import redis.asyncio as redis
import json
from typing import Optional, Dict, List
from datetime import datetime
from app.models.schemas import UserContext
from app.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

class ContextService:
    """Manages user conversation context using Redis"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.max_history = 6

    async def connect(self):
        """Initialize Redis connection"""
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
            logger.info("redis_connected", host=settings.REDIS_HOST)
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e), host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("redis_disconnected")
    
    async def get_context(self, user_id: str) -> UserContext:
        """Retrieve user context from redis"""
        try:
            key = f"context:{user_id}"
            data = await self.redis_client.get(key)

            if data:
                context_dict = json.loads(data)
                context = UserContext(**context_dict)
                logger.info("context_retrieved", user_id=user_id, messages=len(context.chat_history))
                return context
            else:
                logger.info("context_empty", user_id=user_id)
                return UserContext(user_id=user_id, chat_history=[])

        except Exception as e:
            logger.error("context_retrieval_failed", user_id=user_id, error=str(e))
            return UserContext(user_id=user_id, chat_history=[])

    async def save_context(self, context: UserContext) -> bool:
        """Save user Context to Redis with TTL"""
        try:
            key = f"context:{context.user_id}"

            if len(context.chat_history) > self.max_history:
                context.chat_history = context.chat_history[-self.max_history:]
            
            context.last_updated = datetime.utcnow()

            data = context.model_dump_json()
            await self.redis_client.setex(
                key,
                settings.CONTEXT_TTL,
                data
            )
            logger.info(
                "context_saved",
                user_id=context.user_id,
                messages=len(context.chat_history),
                ttl=settings.CONTEXT_TTL
            )
            return True
        except Exception as e:
            logger.error("context_save_failed", user_id=context.user_id, error=str(e))
            return False

    async def add_message(self, user_id: str, role: str, content: str) -> bool:
        """Add a message to user's context"""
        try:
            context = await self.get_context(user_id)
            context.chat_history.append({
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            })
            return await self.save_context(context)
        except Exception as e:
            logger.error("message_add_failed", user_id=user_id, error=str(e))
            return False

    async def clear_context(self, user_id: str) -> bool:
        """Clear user's context"""
        try:
            key = f"context:{user_id}"
            await self.redis_client.delete(key)
            logger.info("context_cleared", user_id=user_id)
            return True
        except Exception as e:
            logger.error("context_clear_failed", user_id=user_id, error=str(e))
            return False

    def format_context_for_llm(self, chat_history: List[Dict[str, str]]) -> str:
        """Format chat history for LLM"""
        if not chat_history:
            return ""

        formatted = "پچھلی بات چیت:\n"
        for msg in chat_history[-4:]:
            role = "صارف" if msg["role"] == "user" else "معاون"
            formatted += f"{role}: {msg['context']}\n"

        return formatted

context_service = ContextService()
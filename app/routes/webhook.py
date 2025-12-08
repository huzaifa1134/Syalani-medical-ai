from typing import Dict
from fastapi import APIRouter, Request, Response, HTTPException
from app.config import get_settings
from app.models.schemas import (
    STTRequest, TTSRequest, Language, InteractionMode, LLMRequest, RAGQuery
)
from app.services.speech_service import speech_service
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.context_service import context_service
from app.services.menu_service import menu_service
from app.services.whatsapp_service import whatsapp_service
from app.services.preferences_service import preferences_service
from app.utils.language_detector import language_detector
import structlog

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = structlog.get_logger()
settings = get_settings()


@router.get("")
async def verify_webhook(request: Request):
    """Webhook verification endpoint for WhatsApp Business API"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WABA_VERIFY_TOKEN:
        logger.info("webhook_verified", challenge=challenge)
        return Response(content=challenge, media_type="text/plain")

    logger.warning("webhook_verification_failed", mode=mode)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def handle_webhook(payload: dict):
    """Main webhook endpoint to receive WhatsApp messages"""
    try:
        logger.info("webhook_received", payload_keys=list(payload.keys()))

        if payload.get("object") != "whatsapp_business_account":
            logger.warning("invalid_webhook_object", object=payload.get("object"))
            return {"status": "ok"}

        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            logger.info("no_messages_in_webhook")
            return {"status": "ok"}

        message = messages[0]
        message_id = message.get("id")
        from_number = message.get("from")
        message_type = message.get("type")

        logger.info(
            "processing_message",
            message_id=message_id,
            from_number=from_number,
            type=message_type
        )

        await whatsapp_service.mark_message_read(message_id)

        if await preferences_service.needs_onboarding(from_number):
            await send_welcome_message(from_number)
            return {"status": "ok"}

        prefs = await preferences_service.get_preferences(from_number)

        if message_type == "text":
            text = message.get("text", {}).get("body", "").lower().strip()

            if await handle_command(text, from_number, prefs):
                return {"status": "ok"}

        await whatsapp_service.send_reaction(from_number, message_id, "👍")

        if message_type == "audio":
            if prefs.interaction_mode == InteractionMode.TEXT:
                msg = "متن موڈ فعال ہے۔ براہ کرم ٹائپ کریں۔" if prefs.language == Language.URDU else "Text mode is active. Please type your message."
                await whatsapp_service.send_text_message(from_number, msg)
            else:
                await process_audio_message(message, from_number, prefs.language)

        elif message_type == "text":
            if prefs.interaction_mode == InteractionMode.VOICE:
                msg = "معاف کیجیے، میں صرف آڈیو اور ٹیکسٹ پیغامات کو سمجھ سکتا ہوں۔" if prefs.language == Language.URDU else "Sorry, I only understand audio and text messages."
                await whatsapp_service.send_text_message(from_number, msg)
            else:
                await process_text_message(message, from_number, prefs.language)

        else:
            logger.warning("unsupported_message_type", type=message_type)
            msg = "معاف کیجیے، میں صرف آڈیو اور ٹیکسٹ پیغامات کو سمجھ سکتا ہوں۔" if prefs.language == Language.URDU else "Sorry, I only understand audio and text messages."
            await whatsapp_service.send_text_message(from_number, msg)

        return {"status": "ok"}
    except Exception as e:
        logger.error("webhook_processing_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Processing failed")


async def send_welcome_message(from_number: str):
    """Send welcome message with language selection"""
    welcome = menu_service.get_welcome_message()
    combined_message = f"{welcome['urdu']}\n\n---\n\n{welcome['english']}"
    await whatsapp_service.send_text_message(from_number, combined_message)


async def handle_command(text: str, from_number: str, prefs) -> bool:
    """Handle special commands like settings, help, language selection"""

    if text in ["1", "urdu", "اردو"]:
        await preferences_service.set_language(from_number, Language.URDU)
        msg = menu_service.get_mode_selection_message(Language.URDU)
        await whatsapp_service.send_text_message(from_number, msg)
        return True

    if text in ["2", "english", "انگلش"]:
        await preferences_service.set_language(from_number, Language.ENGLISH)
        msg = menu_service.get_mode_selection_message(Language.ENGLISH)
        await whatsapp_service.send_text_message(from_number, msg)
        return True

    if text in ["voice", "آواز", "audio", "آڈیو"]:
        await preferences_service.set_interaction_mode(from_number, InteractionMode.VOICE)
        prefs = await preferences_service.get_preferences(from_number)
        msg = menu_service.get_confirmation_message(prefs.language, InteractionMode.VOICE)
        await whatsapp_service.send_text_message(from_number, msg)
        return True

    if text in ["text", "متن", "ٹیکسٹ"]:
        await preferences_service.set_interaction_mode(from_number, InteractionMode.TEXT)
        prefs = await preferences_service.get_preferences(from_number)
        msg = menu_service.get_confirmation_message(prefs.language, InteractionMode.TEXT)
        await whatsapp_service.send_text_message(from_number, msg)
        return True

    if text in ["settings", "ترتیبات", "setting"]:
        msg = menu_service.get_settings_menu(prefs.language, prefs.interaction_mode)
        await whatsapp_service.send_text_message(from_number, msg)
        return True

    if text in ["help", "مدد", "menu", "مینو"]:
        msg = menu_service.get_help_message(prefs.language)
        await whatsapp_service.send_text_message(from_number, msg)
        return True

    if text == "language":
        welcome = menu_service.get_welcome_message()
        combined = f"{welcome['urdu']}\n\n---\n\n{welcome['english']}"
        await whatsapp_service.send_text_message(from_number, combined)
        return True

    if text == "mode":
        msg = menu_service.get_mode_selection_message(prefs.language)
        await whatsapp_service.send_text_message(from_number, msg)
        return True

    return False


async def process_audio_message(message: dict, from_number: str, user_language: Language):
    """Process audio message through complete pipeline"""
    try:
        audio_data = message.get("audio", {})
        audio_id = audio_data.get("id")
        audio_url = await get_media_url(audio_id)

        if not audio_url:
            logger.error("audio_url_not_found", audio_id=audio_id)
            msg = "معاف کیجیے، آڈیو پیغام پڑھنے میں مسئلہ ہے۔" if user_language == Language.URDU else "Sorry, there was a problem reading the audio message."
            await whatsapp_service.send_text_message(from_number, msg)
            return

        lang_config = preferences_service.get_language_config(user_language)

        logger.info("step_1_stt_start", from_number=from_number)
        stt_request = STTRequest(audio_url=audio_url, language=lang_config["stt_code"])
        stt_response = await speech_service.speech_to_text(stt_request)

        if not stt_response.transcript:
            logger.warning("empty_transcript", from_number=from_number)
            msg = "معاف کیجیے، میں آپ کی آواز نہیں سمجھ سکا۔ براہ کرم دوبارہ کوشش کریں۔" if user_language == Language.URDU else "Sorry, I couldn't understand your voice. Please try again."
            await whatsapp_service.send_text_message(from_number, msg)
            return

        user_query = stt_response.transcript
        logger.info("stt_complete", transcript=user_query)

        await process_query(user_query, from_number, user_language, respond_with_voice=True)
    except Exception as e:
        logger.error("audio_processing_failed", error=str(e), from_number=from_number)
        msg = "معاف کیجیے، ایک تکنیکی مسئلہ ہے۔ براہ کرم بعد میں کوشش کریں۔" if user_language == Language.URDU else "Sorry, there was a technical issue. Please try again later."
        await whatsapp_service.send_text_message(from_number, msg)


async def process_text_message(message: dict, from_number: str, user_language: Language):
    """Process text message"""
    try:
        text_body = message.get("text", {}).get("body", "")

        if not text_body:
            return

        logger.info("text_message_received", text=text_body, from_number=from_number)

        await process_query(text_body, from_number, user_language, respond_with_voice=False)

    except Exception as e:
        logger.error("text_processing_failed", error=str(e), from_number=from_number)


async def process_query(user_query: str, from_number: str, user_language: Language, respond_with_voice: bool = False):
    """Main processing pipeline with language support"""
    try:
        logger.info("step_2_context_retrieval", from_number=from_number)
        user_context = await context_service.get_context(from_number)

        detected_language = user_language
        if user_language == Language.AUTO:
            detected_language = language_detector.detect(user_query)
            logger.info("language_detected", language=detected_language)

        logger.info("step_3_rag_search", query=user_query)
        rag_query = RAGQuery(
            query=user_query,
            language=detected_language,
            user_context=user_context.chat_history,
            search_type="hybrid"
        )
        rag_result = await rag_service.search(rag_query)

        logger.info("step_4_llm_generation")
        llm_request = LLMRequest(
            user_query=user_query,
            language=detected_language,
            context=user_context.chat_history,
            rag_results=rag_result.results
        )
        llm_response = await llm_service.generate_response(llm_request)

        await context_service.add_message(from_number, "user", user_query)
        await context_service.add_message(from_number, "assistant", llm_response.response)

        if respond_with_voice:
            logger.info("step_5_tts", response_length=len(llm_response.response))
            lang_config = preferences_service.get_language_config(detected_language)

            tts_request = TTSRequest(
                text=llm_response.response,
                language=lang_config["tts_code"],
                voice_name=lang_config["tts_voice"]
            )
            tts_response = await speech_service.text_to_speech(tts_request)

            media_id = await whatsapp_service.upload_media(tts_response.audio_content)

            if media_id:
                await whatsapp_service.send_audio_by_id(from_number, media_id)
            else:
                await whatsapp_service.send_text_message(from_number, llm_response.response)
        else:
            await whatsapp_service.send_text_message(from_number, llm_response.response)

        logger.info("pipeline_complete", from_number=from_number, language=detected_language)
    except Exception as e:
        logger.error("query_processing_failed", error=str(e), from_number=from_number)
        msg = "معاف کیجیے، میں ابھی آپ کی مدد نہیں کر سکتا۔ براہ کرم بعد میں کوشش کریں۔" if user_language == Language.URDU else "I'm sorry, I cannot assist you right now. Please try again later."
        await whatsapp_service.send_text_message(from_number, msg)


async def get_media_url(media_id: str) -> str:
    """Get media URL from WhatsApp media ID"""
    try:
        url = f"{settings.WABA_API_URL}/{media_id}"
        headers = {"Authorization": f"Bearer {settings.WABA_ACCESS_TOKEN}"}

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()

            media_url = response.json().get("url")
            logger.info("media_url_retrieved", media_id=media_id)
            return media_url

    except Exception as e:
        logger.error("media_url_retrieval_failed", media_id=media_id, error=str(e))
        return ""
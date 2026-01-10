import google.generativeai as genai
from typing import List, Dict, Optional, Any
from app.config import get_settings
from app.models.schemas import LLMRequest, LLMResponse, Language
from app.utils.language_detector import language_detector
import structlog

logger = structlog.get_logger()
settings = get_settings()

class LLMService:
    """Handles AI response generation using Gemini - Bilingual Support"""
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

        self.system_prompts = {
            Language.URDU: """آپ ایک صحت کی دیکھ بھال کرنے والے معاون ہیں جو اردو میں بات کرتے ہیں۔

آپ کے کام:
1. مریضوں کو ڈاکٹروں کی تلاش میں مدد کریں
2. ڈاکٹروں کے اوقات اور مقامات کی معلومات فراہم کریں
3. علاج کے طریقوں کے بارے میں رہنمائی دیں
4. ہمیشہ شائستہ اور پیشہ ورانہ انداز میں جواب دیں

اہم ہدایات:
- صرف دی گئی معلومات استعمال کریں، اپنی طرف سے کچھ نہ بنائیں
- اگر معلومات دستیاب نہیں ہے تو صاف کہیں کہ "معاف کیجیے، یہ معلومات ابھی دستیاب نہیں ہے"
- طبی مشورہ نہ دیں، صرف معلومات فراہم کریں
- جوابات مختصر اور واضح رکھیں
- ہمیشہ اردو میں جواب دیں""",

            Language.ENGLISH: """You are a healthcare assistant who communicates in english

Your responsibilities:
1. Help patients find doctors
2. Provide information about doctor timings and location
3. Guide about treatment procedures
4. ALways respond politely and professionally

Important guidelines:
- Only use the provided information, dont make things up
- If information is not available, clearly states "I'm sorry, This information is not currently available"
- Don't give medical advoce, only provide information
- Keep responses concise and clear
- Always respond in English"""
        }

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate AI response based on user query, context, and RAG results"""
        # Initialize detected_language before try block
        detected_language = request.language

        try:
            #detect language if AUTO
            if request.language == Language.AUTO:
                detected_language = language_detector.detect(request.user_query)
                logger.info("language_auto_detected", detected=detected_language)

            prompt = self._build_prompt(
                query=request.user_query,
                language=detected_language,
                context=request.context,
                rag_results=request.rag_results
            )

            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=500
                )
            )

            response_text = response.text.strip()
            tokens_used = len(prompt.split()) + len(response_text.split())

            logger.info(
                "llm_response_generated",
                language=detected_language,
                query_length=len(request.user_query),
                tokens_used=tokens_used
            )

            return LLMResponse(
                response=response_text,
                detected_language=detected_language,
                model=settings.GEMINI_MODEL,
                tokens_used=tokens_used
            )

        except Exception as e:
            logger.error("llm_generation_failed", error=str(e), query=request.user_query[:50])

            fallback_messages = {
                Language.URDU: "معاف کیجیے، میں ابھی آپ کی مدد نہیں کر سکتا۔ براہ کرم دوبارہ کوشش کریں",
                Language.ENGLISH: "I'm Sorry, I cant assist you right now. Please try again in a bit"
            }

            return LLMResponse(
                response=fallback_messages.get(detected_language, fallback_messages[Language.URDU]),
                detected_language=detected_language,
                model=settings.GEMINI_MODEL,
                tokens_used=0
            )

    def _build_prompt(
        self,
        query: str,
        language: Language,
        context: Optional[List[Dict[str, str]]] = None,
        rag_results: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build comprehensive prompt for LLM in selected language"""

        system_prompt = self.system_prompts.get(language, self.system_prompts[Language.ENGLISH]) 
        prompt_parts = [system_prompt, "\n---\n"]

        #add context if available

        if context and len(context) > 0:
            if language == Language.URDU:
                prompt_parts.append("پچھلی بات چیت:\n")
                for msg in context[-4:]:
                    role = "صارف" if msg["role"] == "user" else "معاون"
                    prompt_parts.append(f"{role}: {msg['content']}\n")
            else:
                prompt_parts.append("Previous conversations:\n")
                for msg in context[-4:]:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    prompt_parts.append(f"{role}: {msg['content']}\n")
            prompt_parts.append("\n")

        if rag_results and len(rag_results) > 0:
            if language == Language.URDU:
                prompt_parts.append("متعلقہ معلومات:\n")
            else:
                prompt_parts.append("Relevant Information:\n")
            
            for i, result in enumerate(rag_results, 1):
                if 'name' in result:
                    if language == Language.URDU:
                        prompt_parts.append(f"\n{i}. ڈاکٹر کا نام: {result.get("name", "N/A")}\n")
                        prompt_parts.append(f" خصوصیت : {result.get('speciality', "N/A")}\n")

                    if "timings" in result and isinstance(result["timing"], list):
                        prompt_parts.append(" اوقات:\n")
                        for timing in result["timings"]:
                            day = timing.get('day', 'N/A')
                            time = timing.get('time', 'N/A')
                            prompt_parts.append(f"      {day}: {time}\n")

                    prompt_parts.append(f"      مقام: {result.get('location', 'N/A' )}")
                    if 'phone' in result:
                        prompt_parts.append(f"  فون: {result.get('phone', 'N/A')}\n")
                    else:
                        prompt_parts.append(f"\n{i}. Doctor Name: {result.get('name', 'N/A')}\n")
                        prompt_parts.append(f"  Speciality: {result.get('speciality', 'N/A')}\n")

                        if 'timings' in result and isinstance(result['timing'], list):
                            prompt_parts.append(" Timings:\n")
                            for timing in result["timings"]:
                                day = timing.get('day', 'N/A')
                                time = timing.get('time', 'N/A')
                                prompt_parts.append(f"      {day}: {time}\n")

                        prompt_parts.append(f"      Location: {result.get('location', 'N/A')}")
                        if 'phone' in result:
                            prompt_parts.append(f"  Phone: {result.get('phone', 'N/A')}\n")
                elif 'title' in result:
                    content = result.get('content', '')
                    if language == Language.URDU:
                        prompt_parts.append(f"\n{i}. {result.get('title', 'N/A')}\n") 
                        prompt_parts.append(f"      {content[:300]}...\n")
                    else:
                        prompt_parts.append(f"\n{i}. {result.get('title', 'N/A')}\n")
                        prompt_parts.append(f"      {content[:300]}...\n")
            prompt_parts.append("\n")

        #add current query

        if language == Language.URDU:
            prompt_parts.append(f"صارف کا سوال: {query}\n\n")
            prompt_parts.append("براہ کرم اوپر دی گئی معلومات کی بنیاد پر مختصر اور واضح جواب دیں۔ اگر معلومات دستیاب نہیں ہے تو صاف طور پر بتائیں۔\n\nجواب:")

        else:
            prompt_parts.append(f"User's question: {query}\n\n")
            prompt_parts.append("Please provide a concise and clear answer based on the information above. If information is not available, clearly state so.\n\nAnswer:")
        return "".join(prompt_parts)
    
    async def generate_simple_response(self, query: str, language: Language = Language.AUTO) -> str:
        """Generate a simple response without RAG and context"""

        try:
            request = LLMRequest(
                user_query=query,
                language=language,
                context=None,
                rag_results=None
            )
            response = await self.generate_response(request)
            return response.response
        except Exception as e:
            logger.error("simple_response_failed", error=str(e))
            fallback = {
                Language.URDU: "معاف کیجیے، میں ابھی آپ کی مدد نہیں کر سکتا۔",
                Language.ENGLISH: "I'm sorry, I cant assist you right now."
            }
            return fallback.get(language, fallback[Language.ENGLISH])

llm_service = LLMService()
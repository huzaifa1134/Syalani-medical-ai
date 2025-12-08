from typing import Dict, List, Optional
from datetime import datetime
from app.models.schemas import (
    UserContext, SymptomData, ConversationState, Language, LLMRequest
)
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
import structlog
import json

logger = structlog.get_logger()

class ConversationHandler:
    """Handle multi-step medical conversation - Information only (No appointment booking)"""
    def __init__(self):
        self.emergency_keywords_urdu = [
            "saans nahi", "behosh", "khoon beh", "dil ka dora", "stroke", "bohot tez dard", "dil ka dabav"
        ]
        self.emergency_keywords_english = [
            "can't breath", "unconcious", "severe bleeding", "heart attack", "stroke", "crushing pain", "chest pressure"
        ]
    async def process_message(
        self,
        user_query: str,
        user_context: UserContext,
        language: Language
    ) -> str:
        """Main conversation router"""
        state = user_context.conversation_state

        if state == ConversationState.INITIAL_COMPLAINT:
            return await self.handle_initial_complaint(user_query, user_context, language)
        elif state == ConversationState.GATHERING_SYMPTOMS:
            return await self.gather_symptoms(user_query, user_context, language)
        elif state == ConversationState.RISK_ASSESSMENT:
            return await self.assess_risk(user_context, language)
        elif state == ConversationState.DOCTOR_RECOMMENDATION:
            return await self.recommend_doctor(user_context, language)

        else:
            return await self.handle_initial_complaint(user_query, user_context, language)

    async def handle_initial_complaint(
        self,
        user_query: str,
        user_context: UserContext,
        language: Language
    ) -> str:
        """First message - extract complaint and ask questins"""
        chief_complaint = await self.extract_complaint(user_query)

        user_context.symptom_data = SymptomData(
            chief_complaint=chief_complaint
        )

        if await self.is_obvious_emergency(user_query):
            user_context.risk_level = "emergency"
            user_context.conversation_state = ConversationState.RISK_ASSESSMENT
            return await self.handle_emergency(language)

        user_context.conversation_state = ConversationState.GATHERING_SYMPTOMS
        return await self.generate_followup_questions(chief_complaint, language)
    
    async def extract_complaint(self, user_query: str) -> str:
        """Extract amin complain form user message"""
        query_lower = user_query.lower()

        complaints = {
            "chest": "chest pain",
            "seene": "chest pain",
            "dard": "pain",
            "headache": "headache",
            "sar": "headache",
            "fever": "fever",
            "bukhar": "fever",
            "cough": "cough",
            "khansi": "cough"
        }
        
        for key, value in complaints.items():
            if key in query_lower:
                return value

        return 'general complaint'

    async def is_obvious_emergency(self, text: str) -> bool:
        """Check for emergency keywords"""
        text_lower = text.lower()

        all_keywords = self.emergency_keywords_urdu + self.emergency_keywords_english   
        return any(keyword in text_lower for keyword in all_keywords)

    async def handle_emergency(self, text: str) -> str:
        """Emergency response"""

        messages = {
            Language.URDU: """**یہ ایمرجنسی ہو سکتی ہے!**
فوری اقدامات:
ابھی 1122 کال کریں (ایمبولینس)
یا فوری قریبی ہسپتال کی ایمرجنسی جائیں

قریب ترین سیلانی ایمرجنسی:
• سیلانی ویلفیئر - 24/7 ایمرجنسی
• فون: 021-111-729-526

**انتظار نہ کریں! فوری جائیں!**""",
           Language.ENGLISH: """**This could be an emergency**
Immediate actions:
Call 1122 NOW (Ambulance)
Or go to nearest hospital emergency

Nearest Saylani Emergency:
Saylani welfare 24/7 emergency
Phone: 021-111-729-526

**Don't wait! Go immediately!**""" 
        }
        return messages.get(language, messages[Language.ENGLISH])

    async def generate_followup_questions(
        self,
        complaint: str,
        language: Language
    ) -> str:
        """Generate relevant followup questions"""
        questions_templates= {
            Language.URDU: {
                "chest pain": """میں آپ کی مدد کرنا چاہتا ہوں، لیکن پہلے کچھ اہم سوالات:

1 **یہ درد کب شروع ہوا?**
   • ابھی / آج / کچھ دن سے

2 **درد کیسا ہے?**
   • تیز چبھن
   • دبانے والا
   • جلن والا

3 **کوئی اور علامت?**
   • سانس میں تکلیف
   • پسینے آنا
   • چکر آنا
   • الٹی

4 **شدت کتنی ہے؟** (1 سے 10 میں)

براہ کرم تفصیل سے بتائیں۔""",
                
                "headache": """سر درد کے بارے میں مزید بتائیں:

1 کب سے ہے؟
2 سر کے کس حصے میں؟
3 کتنا شدید؟ (1-10)
4 الٹی/چکر/نظر کی کمزوری؟
5 بخار ہے؟""",
                
                "default": """آپ کی تکلیف کے بارے میں مزید بتائیں:

1 کب سے ہے؟
2 کتنی شدید ہے؟ (1-10)
3 کوئی اور علامت؟
4 پہلے کبھی ایسا ہوا؟"""
            },

            Language.ENGLISH: {
                "chest pain": """I want to help you, but first some important questions:
1**When did this pain start?**
Just now / Today / Few days ago

2**What type of pain**
Sharp/stabbing
Pressure/squeezing
Burning

3**Any other symptoms?**
Difficulty breathing
Sweating
Dizziness
Nausea

**How severe** (1 to 10)

Please provide details""",

                "default": """Tell me more about your problem:
1 When did it start?
2 How severe is it? (1-10)
3 Any other symptom?
4 Has this happened before?"""
            }
        }

        templates = questions_templates.get(language, questions_templates[Language.ENGLISH])
        
        for key, template in templates.items():
            if key in complaint.lower():
                return template

        return templates.get("default", templates[list(templates.keys())[0]])

    async def gather_symptoms(
        self,
        user_query: str,
        user_context: UserContext,
        language: Language
    ) -> str:
        """Process user's symptom answers"""

        parsed_data = await self.parse_symptom_answers(user_query)

        symptom_data = user_context.symptom_data
        if parsed_data.get("duration"):
            symptom_data.duration = parsed_data["duration"]
        if parsed_data.get("severity"):
            symptom_data.severity = parsed_data["severity"]
        if parsed_data.get("additional_symptoms"):
            symptom_data.additional_symptoms.extend(parsed_data["additional_symptoms"])
        
        if self.has_enough_info(symptom_data):
            user_context.conversation_state= ConversationState.RISK_ASSESSMENT
            return await self.assess_risk(user_context, language)
        else:
            return await self.ask_missing_info(symptom_data,language)

    async def parse_symptom_answers(self, user_query: str) -> Dict:
        """Parse user's symptomdescription using llm"""

        prompt = f"""
Extract medical information from this user message: "{user_query}"

Return JSON with:
- duration: when did it start (e.g., "2 hours", "today", "3 days")   
- severity: how bad (eg. mild, moderate, severe)   
- additional_symptoms: list of other symptoms mentioned

example:
Input: "2 ghnate se bht tez dard saans bhi lena mushkil"
Output: {{"duration": "2 ghante", "severity": "severe", "additional_symptoms": ["breathing_difficulty"]}}
"""

        try:
            response = await llm_service.generate_simple_response(prompt, Language.ENGLISH)
            response_clean = response.strip()
            if "```json" in response_clean:
                response_clean = response_clean.split("```json")[1].split("```")[0]
            elif "```" in response_clean:
                response_clean = response_clean.split("```")[1].split("```")[0]

            parsed = json.loads(response_clean)
            return parsed

        except Exception as e:
            logger.error("parse_symptoms_failed", error=str(e))
            return {}

    def has_enough_info(self, symptom_data: SymptomData) -> bool:
        """Check if we have enough information to proceed"""
        return bool(
            symptom_data.chief_complaint and
            symptom_data.duration and 
            symptom_data.severity
        )

    async def ask_missing_info(self, symptom_data: SymptomData, language: Language) -> str:
        """Ask for missing information"""
        
        messages = {
            Language.URDU: "شکریہ۔ کچھ مزید تفصیل چاہیے:\n\n",
            Language.ENGLISH: "Thank you. Need a bit more detail:\n\n"
        }
        
        msg = messages.get(language, messages[Language.ENGLISH])
        
        if not symptom_data.duration:
            msg += "• یہ کب سے ہے؟\n" if language == Language.URDU else "• When did this start?\n"
        
        if not symptom_data.severity:
            msg += "• کتنا شدید ہے؟ (1-10)\n" if language == Language.URDU else "• How severe is it? (1-10)\n"
        
        return msg
    async def assess_risk(self, user_context: UserContext, language: Language) -> str:
        """Assess emergency level and move to recommendation"""

        symptom_data = user_context.symptom_data

        if symptom_data.severity in ["severe", "شدید"] or symptom_data.severity_scale and symptom_data.severity_scale >= 8:
            user_context.risk_level = "urgent"
        else:
            user_context.risk_level = "routine"

        user_context.conversation_state = ConversationState.DOCTOR_RECOMMENDATION
        return await self.recommend_doctor(user_context, language)

    async def recommend_doctor(self, user_context: UserContext, language: Language) -> str:
        """Final doctor recommendation with nearest branches - INFORMATION ONLY"""

        symptom_data = user_context.symptom_data
        user_location = user_context.user_location
        
        if not user_location:
            return await self.ask_for_location(language)
        
        symptoms = [symptom_data.chief_complaint] + symptom_data.additional_symptoms
        
        doctors = await rag_service.smart_symptom_search(
            user_query=symptom_data.chief_complaint,
            user_location=user_location,
            extracted_symptoms=symptoms
        )
        
        if not doctors:
            return await self.no_doctors_available(language)
        
        return await self.format_doctor_recommendation(
            doctors=doctors,
            symptom_data=symptom_data,
            risk_level=user_context.risk_level,
            language=language
        )
    
    async def format_doctor_recommendation(
        self,
        doctors: List[Dict],
        symptom_data: SymptomData,
        risk_level: str,
        language: Language
    ) -> str:
        """Format doctor recommendations - NO FEES, INFO ONLY"""
        
        if language == Language.URDU:
            response = f"آپ کی علامات کی بنیاد پر:\n\n"
            response += f"**قریب ترین ڈاکٹرز (سیلانی ویلفیئر - مفت علاج):**\n\n"
            
            for i, doctor in enumerate(doctors[:3], 1):
                response += f"{i}. **{doctor['name']}**\n"
                response += f"   {doctor.get('qualification', 'N/A')}\n"
                response += f"   تجربہ: {doctor.get('experience_years', 'N/A')} سال\n\n"
                
                response += f"   **دستیاب برانچز:**\n"
                nearby = doctor.get("nearby_branches", [])[:2]
                
                for branch in nearby:
                    branch_info = branch.get("branch_full_info", {})
                    response += f"\n   • {branch_info.get('branch_name', 'N/A')}\n"
                    response += f"     فاصلہ: {branch.get('branch_distance', 'N/A')} کلومیٹر\n"
                    response += f"     علاقہ: {branch_info.get('area', 'N/A')}\n"
                    
                    today = datetime.now().strftime("%A")
                    schedule = next(
                        (s for s in branch.get("schedule", []) if s["day"] == today),
                        None
                    )
                    if schedule:
                        times = ", ".join(schedule["time_slots"])
                        response += f"     آج کے اوقات: {times}\n"
                    else:
                        response += f"     آج دستیاب نہیں\n"
                    
                    response += f"     فون: {branch_info.get('contact', {}).get('phone', 'N/A')}\n"
                
                response += "\n"
            
            response += "\n**سیلانی ویلفیئر کی سہولیات:**\n"
            response += "• مکمل طبی علاج (مفت)\n"
            response += "• لیبارٹری ٹیسٹنگ (مفت)\n"
            response += "• 24/7 ایمرجنسی سروس\n"
            response += "• ایمبولینس دستیاب\n\n"
            
            if risk_level == "urgent":
                response += "**نوٹ:** جلد از جلد ڈاکٹر سے رابطہ کریں!\n\n"
            
            response += "**معلومات کے لیے:**\n"
            response += "مندرجہ بالا نمبرز پر رابطہ کریں یا 021-111-729-526 پر کال کریں۔"
            
        else:  # English
            response = f"Based on your symptoms:\n\n"
            response += f"**Nearest Doctors (Saylani Welfare - Free Treatment):**\n\n"
            
            for i, doctor in enumerate(doctors[:3], 1):
                response += f"{i}. **{doctor['name']}**\n"
                response += f"   {doctor.get('qualification', 'N/A')}\n"
                response += f"   Experience: {doctor.get('experience_years', 'N/A')} years\n\n"
                
                response += f"   **Available Branches:**\n"
                nearby = doctor.get("nearby_branches", [])[:2]
                
                for branch in nearby:
                    branch_info = branch.get("branch_full_info", {})
                    response += f"\n   • {branch_info.get('branch_name', 'N/A')}\n"
                    response += f"     Distance: {branch.get('branch_distance', 'N/A')} km\n"
                    response += f"     Area: {branch_info.get('area', 'N/A')}\n"
                    
                    today = datetime.now().strftime("%A")
                    schedule = next(
                        (s for s in branch.get("schedule", []) if s["day"] == today),
                        None
                    )
                    if schedule:
                        times = ", ".join(schedule["time_slots"])
                        response += f"     Today: {times}\n"
                    else:
                        response += f"     Not available today\n"
                    
                    response += f"     Phone: {branch_info.get('contact', {}).get('phone', 'N/A')}\n"
                
                response += "\n"
            
            response += "\n**Saylani Welfare Facilities:**\n"
            response += "• Complete medical treatment (Free)\n"
            response += "• Laboratory testing (Free)\n"
            response += "• 24/7 Emergency service\n"
            response += "• Ambulance available\n\n"
            
            if risk_level == "urgent":
                response += "**Note:** Please contact doctor urgently!\n\n"
            
            response += "**For Information:**\n"
            response += "Contact above numbers or call 021-111-729-526"
        
        return response
    
    async def ask_for_location(self, language: Language) -> str:
        """Ask user for their location"""
        messages = {
            Language.URDU: "براہ کرم اپنا علاقہ بتائیں (مثال: کلفٹن، کراچی)",
            Language.ENGLISH: "Please share your area/location (e.g., Clifton, Karachi)"
        }
        return messages.get(language, messages[Language.ENGLISH])
    
    async def no_doctors_available(self, language: Language) -> str:
        """No doctors found response"""
        messages = {
            Language.URDU: "معاف کیجیے، ابھی ڈاکٹر دستیاب نہیں ہیں۔ براہ کرم ہمارے ہیلپ لائن 021-111-729-526 پر کال کریں۔",
            Language.ENGLISH: "Sorry, no doctors available right now. Please call our helpline 021-111-729-526"
        }
        return messages.get(language, messages[Language.ENGLISH])


# Global instance
conversation_handler = ConversationHandler()




        


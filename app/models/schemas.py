from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class Language(str, Enum):
    URDU = "ur"
    ENGLISH = "en"
    AUTO = "auto"

class InteractionMode(str, Enum):
    VOICE = "voice"
    TEXT = "text"
    NOT_SET = "not_set"

class UserPreferences(BaseModel):
    """User's language and interaction preferences"""
    user_id: str
    language: Language = Language.AUTO
    interaction_mode: InteractionMode = InteractionMode.NOT_SET
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class ConversationState(str, Enum):
    """Current conversation state"""
    INITIAL_COMPLAINT = "initial_complaint"
    GATHERING_SYMPTOMS = "gathering_symptoms"
    RISK_ASSESSMENT = "risk_assessment"
    DOCTOR_RECOMMENDATION = "doctor_recommendation"
    APPOINTMENT_BOOKING = "appointment_booking"

class SymptomData(BaseModel):
    """Collected symptom information"""
    chief_complaint: str
    duration: Optional[str] = None
    severity: Optional[str] = None
    pain_type: Optional[str] = None
    additional_symptoms: List[str] = Field(default_factory=list)
    medical_history: Optional[str] = None
    current_medications: List[str] = Field(default_factory=list)
    severity_scale: Optional[int] = None

class WhatsAppMessage(BaseModel):
    """WhatsApp message schema"""
    from_number: str
    message_id: str
    timestamp: str
    type: str
    audio_url: Optional[str] = None
    text: Optional[str] = None

class UserContext(BaseModel):
    """User Conversation Context"""
    user_id: str
    conversation_state: ConversationState = ConversationState.INITIAL_COMPLAINT
    symptom_data: Optional[SymptomData] = None
    chat_history: List[Dict[str, str]] = Field(default_factory=list)
    risk_level: Optional[str] = None
    preferences: Optional[UserPreferences] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class STTRequest(BaseModel):
    audio_url: str
    language: str = "ur-PK"

class STTResponse(BaseModel):
    transcript: str
    confidence: float
    detected_language: str

class TTSRequest(BaseModel):
    text: str
    language: str = "ur-PK"
    voice_name: str = "ur-PK-Standard-A"

class TTSResponse(BaseModel):
    audio_content: bytes
    duration: float

class RAGQuery(BaseModel):
    query: str
    language: Language = Language.AUTO
    user_context: Optional[List[Dict[str, str]]] = None
    search_type: str = "smart_symptom"

class RAGResult(BaseModel):
    results: List[Dict[str, Any]]
    search_type: str
    relevant_score: Optional[float] = None

class LLMRequest(BaseModel):
    user_query: str
    language: Language = Language.AUTO
    conversation_state: Optional[ConversationState] = None
    symptom_data: Optional[SymptomData] = None
    context: Optional[List[Dict[str, str]]] = None
    rag_results:Optional[List[Dict[str, Any]]] = None

class LLMResponse(BaseModel):
    response: str
    detected_language: Language
    model: str
    tokens_used: Optional[int] = None

class WhatsAppWebhook(BaseModel):
    object: str
    entry: List[Dict[str, Any]]

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]
    version: str

class MenuOption(BaseModel):
    id: str
    title: str
    description: Optional[str] = None

class BranchInfo(BaseModel):
    """Hospital branch information"""
    branch_id: str
    branch_name: str
    city: str
    area: str
    full_address: str
    location: Dict[str, Any]  # GeoJSON
    contact: Dict[str, str]
    distance_km: Optional[float] = None
    distance_display: Optional[str] = None


class DoctorInfo(BaseModel):
    """Doctor information with branch details"""
    doctor_id: str
    name: str
    qualification: str
    specialty: str
    experience_years: int
    languages: List[str]
    branches: List[Dict[str, Any]]
    rating: Optional[float] = None
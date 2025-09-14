from datetime import datetime
from typing import List, Optional, TypeVar, Generic, Tuple, Dict, Any
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr

# --- Generic Response Model (Unchanged) ---
T = TypeVar('T')
class StandardResponse(BaseModel, Generic[T]):
    status: bool = True
    data: Optional[T] = None
    message: Optional[str] = None

# --- Helper for MongoDB ObjectId (Unchanged) ---
class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, v, *args, **kwargs):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

# --- Source Citation Schema (Unchanged) ---
class SourceCitation(BaseModel):
    url: str
    title: str
    index: int


class LocationRequest(BaseModel):
    latitude: float
    longitude: float

class Hospital(BaseModel):
    name: str
    type: str
    latitude: float
    longitude: float
    phone: Optional[str] = None
    address: Optional[str] = None
    google_maps_url: str

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
class UserCreate(UserBase):
    password: str
class UserProfileUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = None
    weight_kg: Optional[float] = Field(None, ge=0)
    height_cm: Optional[float] = Field(None, ge=0)
    allergies: Optional[List[str]] = None
    previous_issues: Optional[List[str]] = None
    current_medications: Optional[List[str]] = None
class UserProfile(UserBase, UserProfileUpdate):
    pass
class UserInDB(UserBase, UserProfileUpdate):
    id: PyObjectId = Field(alias="_id")
    hashed_password: str
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    username: Optional[str] = None


# --- Chat Schemas (UPDATED) ---
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    turn_number: Optional[int] = None
    citations: Optional[List[SourceCitation]] = None

class ChatSession(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    # --- NEW FIELDS ---
    chat_name: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    # ---
    created_at: datetime = Field(default_factory=datetime.now)
    history: List[ChatMessage] = []
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ChatRequest(BaseModel):
    prompt: str
    chat_id: Optional[str] = None

class ChatTurnResponse(BaseModel):
    chat_id: str
    ai_response: str
    turn_number: int
    citations: Optional[List[SourceCitation]] = None

# --- NEW: Schemas for Rename and Delete ---
class RenameChatRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100)

class SimpleMessageResponse(BaseModel):
    message: str

class AppointmentBase(BaseModel):
    doctor_name: Optional[str] = Field(None, min_length=1)
    specialization: Optional[str] = None
    reason: Optional[str] = Field(None, max_length=500)
    appointment_time: datetime

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    doctor_name: Optional[str] = Field(None, min_length=1)
    specialization: Optional[str] = None
    reason: Optional[str] = Field(None, max_length=500)
    appointment_time: Optional[datetime] = None

class AppointmentRecord(BaseModel):
    transcript: Optional[str] = None
    summary: Optional[str] = None
    structured_summary: Optional[Dict[str, Any]] = None # <-- MODIFIED: Use Dict for JSON object
    audio_path: Optional[str] = None
    processed_at: Optional[datetime] = None

class AppointmentInDB(AppointmentBase, AppointmentRecord):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class TranscriptionResponse(BaseModel):
    appointment_id: str
    transcript: str
    summary: str
    structured_summary: Dict[str, Any]
from pydantic import BaseModel
from typing import Optional, Dict, Any


class ChatMessageInput(BaseModel):
    user_id: str  # To identify the user session
    message: str
    session_state: Optional[Dict[str, Any]] = {}  # To maintain conversation state
    image_base64: Optional[str] = None  # Base64 encoded image data
    image_mime_type: Optional[str] = None  # e.g., "image/png", "image/jpeg"
    audio_base64: Optional[str] = None  # Base64 encoded audio data
    audio_mime_type: Optional[str] = None  # e.g., "audio/wav", "audio/mp3"


class ChatMessageOutput(BaseModel):
    bot_response: str
    session_state: Dict[str, Any] = {}


class ChangeBookingTimePayload(BaseModel):
    booking_id: str
    new_time: str  # Expected format: "YYYY-MM-DD HH:MM:SS"


class MockVexereApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

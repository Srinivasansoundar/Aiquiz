from pydantic import BaseModel
from typing import Optional
class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer."""
    answer: str


class QuizResponse(BaseModel):
    """Response containing quiz data or completion status."""
    question: Optional[str] = None
    options: Optional[list] = None
    hint: Optional[str] = None
    hint_attempt: Optional[int] = None
    status: Optional[str] = None


class PDFIngestionResponse(BaseModel):
    """Response containing PDF ingestion status."""
    success: bool
    message: Optional[str] = None
    collection_name: Optional[str] = None
"""Quiz routes for handling HTTP requests."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.core.services.quiz_service import QuizService


# Request/Response models
# class StartSessionRequest(BaseModel):
#     """Request to start a new quiz session."""
#     pass


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




# Create router
router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.get("/start", response_model=QuizResponse)
async def start_quiz_session() -> QuizResponse:
    """Start a new quiz session.
    
    Returns the first question.
    """
    try:
        result = QuizService.start_session()
        
        return QuizResponse(
            question=result.get("question"),
            options=result.get("options"),
            hint=result.get("hint"),
            hint_attempt=result.get("hint_attempt"),
            status=result.get("status"),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting quiz: {str(e)}")


@router.post("/answer", response_model=QuizResponse)
async def submit_answer(request: SubmitAnswerRequest) -> QuizResponse:
    """Submit an answer and get the next question or completion status.
    
    Returns next question, hint (if wrong), or completion message.
    """
    try:
        result = QuizService.submit_answer(request.answer)
        
        return QuizResponse(
            question=result.get("question"),
            options=result.get("options"),
            hint=result.get("hint"),
            hint_attempt=result.get("hint_attempt"),
            status=result.get("status"),
            # message=result.get("message"),
            # total_chunks_processed=result.get("total_chunks_processed"),
            # total_questions=result.get("total_questions"),
        )
        
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")



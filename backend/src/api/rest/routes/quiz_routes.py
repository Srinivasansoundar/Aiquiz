"""Quiz routes for handling HTTP requests."""

from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Optional
from src.core.services.quiz_service import QuizService
from src.core.services.pdf_ingestion_service import PDFUploadService
from src.schemas.quiz_schema import SubmitAnswerRequest,QuizResponse,PDFIngestionResponse


   




# Create router
router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.get("/start", response_model=QuizResponse)
async def start_quiz_session(collection_name: Optional[str] = None) -> QuizResponse:
    """Start a new quiz session.
    
    Args:
        collection_name: Optional name of ChromaDB collection to use for questions
    
    Returns the first question.
    """
    try:
        result = QuizService.start_session(collection_name=collection_name)
        
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


@router.post("/upload-pdf", response_model=PDFIngestionResponse)
async def upload_pdf(file: UploadFile = File(...), 
                     collection_name: Optional[str] = None,
                     chunk_size: int = 1000,
                     chunk_overlap: int = 200) -> PDFIngestionResponse:
    """Upload a PDF file and ingest it into ChromaDB.
    
    Args:
        file: PDF file to upload
        collection_name: Optional name for ChromaDB collection (auto-generated if not provided)
        chunk_size: Size of text chunks (default: 1000)
        chunk_overlap: Overlap between chunks (default: 200)
    
    Returns:
        Ingestion status and metadata
    """
    try:
        # Validate file
        is_valid, message = PDFUploadService.validate_pdf(file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Read file content
        content = await file.read()
        
        # Process PDF
        result = PDFUploadService.upload_and_ingest(
            file_content=content,
            filename=file.filename,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        if result.get("success"):
            return PDFIngestionResponse(
                success=True,
                message=result.get("message"),
                collection_name=result.get("collection_name"),
               
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading PDF: {str(e)}")



"""Quiz routes for handling HTTP requests."""

from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Optional
from src.core.services.quiz_service import QuizService
from src.core.services.topic_based_pdf_upload_service import TopicBasedPDFUploadService
from src.core.services.traditional_pdf_upload_service import TraditionalPDFUploadService
from src.core.services.topic_quiz_service import TopicQuizService
from src.schemas.quiz_schema import (
    SubmitAnswerRequest, QuizResponse, PDFIngestionResponse,
    TopicRequest, TopicContentResponse, TopicSearchRequest, TopicSearchResponse,
    QuizReport, QuizReportResponse
)


   




# Create router
router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.get("/start", response_model=QuizResponse)
async def start_quiz_session(collection_name: Optional[str] = None, 
                             topic: Optional[str] = None,
                             num_chunks: int = 5) -> QuizResponse:
    """Start a new quiz session.
    
    Args:
        collection_name: Name of ChromaDB collection to use for questions
        topic: Optional topic to generate questions from (if not provided, generates from all content)
        num_chunks: Number of chunks to retrieve for topic (default: 5)
    
    Returns the first question with difficulty level.
    """
    try:
        result = QuizService.start_session(
            collection_name=collection_name,
            topic=topic,
            num_chunks=num_chunks
        )
        
        return QuizResponse(
            question=result.get("question"),
            options=result.get("options"),
            hint=result.get("hint"),
            hint_attempt=result.get("hint_attempt"),
            status=result.get("status"),
            difficulty=result.get("difficulty"),
            topic=result.get("topic"),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting quiz: {str(e)}")


@router.post("/answer", response_model=QuizResponse)
async def submit_answer(request: SubmitAnswerRequest) -> QuizResponse:
    """Submit an answer and get the next question or completion status.
    
    Returns next question with difficulty level, hint (if wrong), or completion message.
    """
    try:
        result = QuizService.submit_answer(request.answer)
        
        return QuizResponse(
            question=result.get("question"),
            options=result.get("options"),
            hint=result.get("hint"),
            hint_attempt=result.get("hint_attempt"),
            status=result.get("status"),
            difficulty=result.get("difficulty"),
            topic=result.get("topic"),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")


@router.post("/upload-pdf", response_model=PDFIngestionResponse)
async def upload_pdf(file: UploadFile = File(...), 
                     collection_name: Optional[str] = None,
                     chunk_size: int = 500,
                     chunk_overlap: int = 100) -> PDFIngestionResponse:
    """Upload a PDF file and ingest it into ChromaDB with topic-based organization.
    
    This endpoint uses unstructured.partition_pdf to extract content organized by topics,
    then splits using RecursiveCharacterTextSplitter within each topic.
    
    Args:
        file: PDF file to upload
        collection_name: Optional name for ChromaDB collection (auto-generated if not provided)
        chunk_size: Size of text chunks within each topic (default: 500)
        chunk_overlap: Overlap between chunks (default: 100)
    
    Returns:
        Ingestion status with collection metadata and topics found
    """
    try:
        # Validate file
        is_valid, message = TopicBasedPDFUploadService.validate_pdf(file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Read file content
        content = await file.read()
        
        # Process PDF with topic-based ingestion
        result = TopicBasedPDFUploadService.upload_and_ingest(
            file_content=content,
            filename=file.filename,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        if result.get("success"):
            return PDFIngestionResponse(
                success=True,
                message=f"Successfully ingested PDF into {result.get('total_topics')} topics. Total documents: {result.get('total_documents')}",
                collection_name=result.get("collection_name"),
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading PDF: {str(e)}")


@router.post("/upload-pdf-traditional", response_model=PDFIngestionResponse)
async def upload_pdf_traditional(file: UploadFile = File(...), 
                                 collection_name: Optional[str] = None,
                                 chunk_size: int = 1000,
                                 chunk_overlap: int = 200) -> PDFIngestionResponse:
    """Upload a PDF file and ingest it into ChromaDB using traditional method.
    
    This endpoint uses PyPDFLoader to extract content and RecursiveCharacterTextSplitter
    for chunking without topic organization (simpler, faster approach).
    
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
        is_valid, message = TraditionalPDFUploadService.validate_pdf(file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Read file content
        content = await file.read()
        
        # Process PDF with traditional ingestion
        result = TraditionalPDFUploadService.upload_and_ingest(
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
    
# @router.post("/get-topics", response_model=TopicSearchResponse)
# async def get_topic_content(request: TopicRequest) -> TopicContentResponse:
#     """Retrieve content chunks for a specific topic using semantic search.
    
#     This endpoint takes a user-selected topic and retrieves relevant content chunks
#     from a ChromaDB collection using semantic similarity search.
    
#     Args:
#         request: TopicRequest containing:
#             - topic: The topic name or query string
#             - collection_name: ChromaDB collection to search
#             - num_chunks: Number of chunks to retrieve (default: 5)
    
#     Returns:
#         TopicContentResponse with matching chunks and metadata
#     """
#     try:
#         topic_service = TopicQuizService()
#         result = topic_service.get_topic_content(
#             collection_name=request.collection_name,
#             topic=request.topic,
#             num_chunks=request.num_chunks or 5
#         )
        
#         if result.get("success"):
#             # Convert chunks to ChunkData objects
#             chunk_data = result.get("chunks", [])
#             return TopicContentResponse(
#                 success=True,
#                 topic=result.get("topic"),
#                 collection_name=result.get("collection_name"),
#                 num_chunks=result.get("num_chunks"),
#                 chunks=chunk_data,
#             )
#         else:
#             return TopicContentResponse(
#                 success=False,
#                 error=result.get("error"),
#                 topic=request.topic,
#                 collection_name=request.collection_name,
#             )
            
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, 
#             detail=f"Error retrieving topic content: {str(e)}"
#         )


@router.post("/search-topics", response_model=TopicSearchResponse)
async def search_topics(request: TopicSearchRequest) -> TopicSearchResponse:
    """Search for topics in a collection using semantic search.
    
    This endpoint searches for topics or keywords in a ChromaDB collection
    and returns matching results with their topics and content previews.
    
    Args:
        request: TopicSearchRequest containing:
            - query: Search query string
            - collection_name: ChromaDB collection to search
            - num_results: Number of results to return (default: 10)
    
    Returns:
        TopicSearchResponse with search results and unique topics
    """
    try:
        topic_service = TopicQuizService()
        result = topic_service.search_topics(
            collection_name=request.collection_name,
            query=request.query,
            num_results=request.num_results or 10
        )
        
        if result.get("success"):
            return TopicSearchResponse(
                success=True,
                query=result.get("query"),
                collection_name=result.get("collection_name"),
                num_results=result.get("num_results"),
                unique_topics=result.get("unique_topics"),
                results=result.get("results"),
            )
        else:
            return TopicSearchResponse(
                success=False,
                error=result.get("error"),
                query=request.query,
                collection_name=request.collection_name,
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error searching topics: {str(e)}"
        )


@router.delete("/delete-collection/{collection_name}")
async def delete_collection(collection_name: str) -> dict:
    """Delete a collection from ChromaDB.
    
    Args:
        collection_name: Name of the collection to delete
    
    Returns:
        Success message
    """
    try:
        import chromadb
        from pathlib import Path
        
        # Get ChromaDB directory
        chroma_dir = Path(__file__).resolve().parents[4] / "chroma_db"
        
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path=str(chroma_dir))
        
        # Delete collection
        client.delete_collection(name=collection_name)
        
        return {
            "success": True,
            "message": f"Collection '{collection_name}' deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error deleting collection: {str(e)}"
        )


@router.get("/report", response_model=QuizReportResponse)
async def get_quiz_report() -> QuizReportResponse:
    """Get the report for the current completed quiz session.
    
    Returns a comprehensive report including:
    - Total score and percentage
    - Number of questions answered incorrectly on first try
    - All questions with user answers and correct answers
    - For topic-based quiz: Shows the selected topic
    - For general quiz: Shows strong topics (≥70%) and weak topics (<50%)
    
    Strong Topics: Topics where user scored 70% or higher
    Weak Topics: Topics where user scored below 50%
    
    Returns:
        QuizReportResponse with full report data
    """
    try:
        result = QuizService.get_quiz_report()
        
        if result.get("success"):
            report = result.get("report", {})
            return QuizReportResponse(
                success=True,
                report=report
            )
        else:
            return QuizReportResponse(
                success=False,
                error=result.get("error", "Unknown error")
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving report: {str(e)}"
        )

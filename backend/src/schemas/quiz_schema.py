from pydantic import BaseModel
from typing import Optional, List, Dict, Any


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
    difficulty: Optional[str] = None  # "easy", "medium", or "hard"
    topic: Optional[str] = None  # Topic from chunk metadata


class PDFIngestionResponse(BaseModel):
    """Response containing PDF ingestion status."""
    success: bool
    message: Optional[str] = None
    collection_name: Optional[str] = None


class TopicRequest(BaseModel):
    """Request to get content for a specific topic."""
    topic: str
    collection_name: str
    num_chunks: Optional[int] = 5


class ChunkData(BaseModel):
    """Data for a single text chunk."""
    chunk_id: int
    content: str
    metadata: Dict[str, Any]


class TopicContentResponse(BaseModel):
    """Response containing topic-specific content chunks."""
    success: bool
    topic: Optional[str] = None
    collection_name: Optional[str] = None
    num_chunks: Optional[int] = None
    chunks: Optional[List[ChunkData]] = None
    error: Optional[str] = None


class TopicSearchRequest(BaseModel):
    """Request to search for topics."""
    query: str
    collection_name: str
    num_results: Optional[int] = 10


class SearchResultItem(BaseModel):
    """Single search result item."""
    content: str
    topic: str
    filename: Optional[str] = None


class TopicSearchResponse(BaseModel):
    """Response containing topic search results."""
    success: bool
    query: Optional[str] = None
    collection_name: Optional[str] = None
    num_results: Optional[int] = None
    unique_topics: Optional[List[str]] = None
    results: Optional[List[SearchResultItem]] = None
    error: Optional[str] = None


class QuestionRecord(BaseModel):
    """Record of a question asked in the quiz."""
    question_num: int
    question: str
    options: List[str]
    correct_answer: str
    user_answer: str
    is_correct: bool
    wrong_on_first_try: bool
    difficulty: str
    topic: str


class TopicScore(BaseModel):
    """Score information for a single topic."""
    topic: str
    total_questions: int
    correct_answers: int
    score_percentage: float


class QuizReport(BaseModel):
    """Comprehensive report for a completed quiz session."""
    total_questions: int
    correct_answers: int
    wrong_answers: int
    score_percentage: float
    # wrong_on_first_try_count: int
    # wrong_on_first_try_percentage: float  # Percentage of wrong answers that were on first try
    is_topic_based: bool
    selected_topic: Optional[str] = None
    strong_topics: Optional[List[TopicScore]] = None  # Only for general quiz
    weak_topics: Optional[List[TopicScore]] = None  # Only for general quiz
    # wrong_on_first_try_questions: Optional[List[QuestionRecord]] = None  # Questions answered wrong on first try
    questions: List[QuestionRecord]


class QuizReportResponse(BaseModel):
    """Response containing quiz report."""
    success: bool
    report: Optional[QuizReport] = None
    error: Optional[str] = None
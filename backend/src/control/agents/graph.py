import os
from dotenv import load_dotenv
from typing import TypedDict, List, Dict
from langchain_groq import ChatGroq
from pathlib import Path
import chromadb
from pydantic import BaseModel
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver
# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
# llama-3.3-70b-versatile
# llama-3.1-70b-versatile
# llama3-70b-8192
# llama-3.1-8b-instant
llm=ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=api_key,
    # max_tokens=800
)
class QuizState(TypedDict):
    current_chunks: List[str]   
    chunk_cursor: int            
    current_question: Dict       
    user_answer: str
    is_correct: bool
    hint_attempt: int           
    status: str
    collection_name: str
    topic: str  # NEW: Topic name if user selected one
    topic_chunks: List[str]  # NEW: Pre-fetched chunks for topic
    topic_from_chunk: str  # Topic extracted from chunk metadata
    # retrieved_context: List[str]
    hint: str
    current_difficulty: str  # "easy", "medium", or "hard"
    correct_count_at_difficulty: int  # Track consecutive correct answers at current difficulty
    # NEW: Quiz tracking for report generation
    quiz_history: List[Dict]  # List of all questions, answers, and results
    question_count: int  # Total number of questions asked
    wrong_on_first_try_count: int  # Number of questions answered incorrectly on first attempt
    wrong_on_first_try_for_current_question: bool  # Tracks if current question was wrong on first attempt

class QuestionResponse(BaseModel):
    question:str
    options:list[str]
    correct_answer:str
    difficulty:str  # "easy", "medium", or "hard"

def start_session_node(state:QuizState) -> QuizState:
    """Create and return a fresh QuizState for a new session.

    This initializes the state and resets all counters (cursor, hint attempts,
    correctness flag, and user answer).
    Preserves topic and topic_chunks if provided (topic-based mode).
    Starts with EASY difficulty level.
    """

    return {
        "current_chunks": [],
        "chunk_cursor": 0,
        "current_question": {},
        "user_answer": "",
        "is_correct": False,
        "hint_attempt": 0,
        "status": "started",
        "hint": "",
        "collection_name": state.get("collection_name", ""),
        "topic": state.get("topic", ""),  # NEW: Preserve topic if provided
        "topic_chunks": state.get("topic_chunks", []),  # NEW: Preserve pre-fetched chunks
        "topic_from_chunk": "",  # Topic extracted from chunk metadata
        "current_difficulty": "easy",  # Start with easy questions
        "correct_count_at_difficulty": 0,  # Track correct answers at current difficulty
        # NEW: Initialize quiz tracking
        "quiz_history": [],  # Will accumulate all questions and answers
        "question_count": 0,  # Total questions asked
        "wrong_on_first_try_count": 0,  # Questions answered incorrectly on first try
        "wrong_on_first_try_for_current_question": False,  # Tracks if current question was wrong on first attempt
    }

     


CHROMA_DIR = Path(__file__).resolve().parents[3] / "chroma_db"
print(CHROMA_DIR)

def load_next_chunk_node(state: QuizState) -> QuizState: 
    """Load next chunk for question generation.
    
    Supports two modes:
    1. Topic-based: Uses pre-fetched topic_chunks passed from quiz_service
    2. Normal: Fetches chunks from ChromaDB using cursor pagination
    """
    
    # Check if we're in topic-based mode
    topic_chunks = state.get("topic_chunks", [])
    
    if topic_chunks and len(topic_chunks) > 0:
        # Topic-based flow: Use pre-fetched topic chunks
        cursor = state.get("chunk_cursor", 0)
        
        # Get next chunk from topic_chunks
        if cursor < len(topic_chunks):
            next_chunk = topic_chunks[cursor]
            docs = [next_chunk]
            new_cursor = cursor + 1
        else:
            # No more chunks available
            docs = []
            new_cursor = cursor
    else:
        # Normal flow: Fetch from ChromaDB using cursor pagination
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        
        # Get collection by name or use the first available
        collection_name = state.get("collection_name")
        
        if collection_name:
            # Use specified collection
            collection = client.get_collection(name=collection_name)
        else:
            # Fallback to first available collection
            collections = client.list_collections()
            if not collections:
                raise ValueError("No collections found in ChromaDB. Please ensure data has been ingested.")
            collection = collections[0]
        
        cursor = state.get("chunk_cursor", 0)
        result = collection.get(offset=cursor, limit=2, include=["documents","metadatas"])
        docs = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        new_cursor = cursor + len(docs)
        
        # Extract topic from metadata if available
        topic_from_chunk = ""
        if metadatas and len(metadatas) > 0:
            chunk1_topic = metadatas[0].get("topic", "").strip()
            chunk2_topic = metadatas[1].get("topic", "").strip() if len(metadatas) > 1 else ""
            
            # If first chunk has valid topic (not "General"), use it
            if chunk1_topic and chunk1_topic != "General":
                # Combine with second chunk topic if different and not "General"
                if chunk2_topic and chunk2_topic != chunk1_topic and chunk2_topic != "General":
                    topic_from_chunk = f"{chunk1_topic}&{chunk2_topic}"
                else:
                    topic_from_chunk = chunk1_topic
            # If first chunk is "General" or empty, use second chunk topic
            elif chunk2_topic and chunk2_topic != "General":
                topic_from_chunk = chunk2_topic
    if state.get("hint_attempt")==3:
        if state.get("current_difficulty")=="medium":
            state["current_difficulty"]="easy"
        elif state.get("current_difficulty")=="hard":
            state["current_difficulty"]="medium"
        else:
            state["current_difficulty"]="easy"   
    
    return {
        **state,
        "current_chunks": docs,
        "chunk_cursor": new_cursor,
        "hint_attempt": 0,
        "hint": "",
        "collection_name": state.get("collection_name", ""),
        "topic_from_chunk": topic_from_chunk if not topic_chunks else state.get("topic_from_chunk", ""),
    }
# {
#   "ids": [...],
#   "documents": [...],
#   "metadatas": [...],      # only if requested
#   "embeddings": [...]      # only if requested
# }

def generate_question_node(state: QuizState) -> QuizState:
    """Generate a multiple-choice question from the current chunks using the LLM
    with structured output based on current difficulty level.
    
    Difficulty Levels:
    - easy: Basic recall of facts, definitions, or simple concepts
    - medium: Understanding relationships, applications, or deeper analysis
    - hard: Critical thinking, synthesis, complex problem-solving
    """
    
    llm_structured_output = llm.with_structured_output(QuestionResponse)
    chunks = state.get("current_chunks", [])
    if not chunks:
        raise ValueError("No chunks available to generate a question from")
    
    # Join chunks into context
    context = "\n".join(chunks)
    current_difficulty = state.get("current_difficulty", "easy")
    
    # Create difficulty-specific prompts
    difficulty_prompts = {
        "easy": """Based on the following text content, generate a SIMPLE multiple-choice question that tests BASIC RECALL of facts, definitions, or key concepts. The question should be straightforward and directly answerable from the text.

Content:
{context}

Generate an EASY question with 4 options and identify the correct answer.""",
        
        "medium": """Based on the following text content, generate a MODERATE multiple-choice question that tests UNDERSTANDING and APPLICATION of concepts. The question should require understanding relationships, drawing simple conclusions, or applying concepts.

Content:
{context}

Generate a MEDIUM difficulty question with 4 options and identify the correct answer.""",
        
        "hard": """Based on the following text content, generate a CHALLENGING multiple-choice question that tests CRITICAL THINKING, SYNTHESIS, and DEEPER ANALYSIS. The question should require connecting ideas, analyzing implications, or solving complex problems.

Content:
{context}

Generate a HARD difficulty question with 4 options and identify the correct answer."""
    }
    
    prompt = difficulty_prompts.get(current_difficulty, difficulty_prompts["easy"]).format(context=context)
    
    # Invoke the LLM with structured output
    response = llm_structured_output.invoke(prompt)
    
    # Update state with the generated question including difficulty
    state["current_question"] = {
        "question": response.question,
        "options": response.options,
        "correct_answer": response.correct_answer,
        "difficulty": response.difficulty,
    }
    state["user_answer"] = ""
    state["is_correct"] = False
    
    return state

def await_user_answer(state: QuizState) -> QuizState:
    """Pause the graph execution and wait for user input (answer) via an interrupt.
    
    LangGraph will pause at this node and wait for external input before resuming.
    The user's answer is provided through the POST /answer endpoint.
    Sends question, options, hint (if any), attempt info, difficulty, and topic from metadata to frontend.
    """
    question_data = state.get("current_question", {})
    hint = state.get("hint", "")
    hint_attempt = state.get("hint_attempt", 0)
    current_difficulty = state.get("current_difficulty", "easy")
    topic_from_chunk = state.get("topic_from_chunk", "")
    
    # Prepare data to send to the client
    interrupt_data = {
        "question": question_data.get("question", ""),
        "options": question_data.get("options", []),
        "hint": hint,
        "hint_attempt": hint_attempt,
        "difficulty": current_difficulty,
        "topic": topic_from_chunk,
    }
    
    # Call interrupt() to pause the graph and wait for user input
    user_input = interrupt(interrupt_data)
    
    # Resume here with user's answer
    state["user_answer"] = user_input
    
    return state


def evaluator_answer_node(state: QuizState) -> QuizState:
    """Evaluate whether the user's answer is correct.
    
    Compares user_answer with the correct_answer from current_question.
    Sets is_correct flag in state.
    Tracks if answer was wrong on first try (when hint_attempt == 0).
    Once marked as wrong on first try, this flag persists even if user gets hints and answers correctly later.
    """
   
    
    user_answer = state.get("user_answer", "").strip().lower()
    correct_answer = state.get("current_question", {}).get("correct_answer", "").strip().lower()
    
    # Check if answer is correct
    is_correct = user_answer == correct_answer
    
    # Track if this is wrong on first try (before any hints)
    # Only set this flag on the FIRST wrong attempt (hint_attempt == 0)
    hint_attempt = state.get("hint_attempt", 0)
    if not is_correct and hint_attempt == 0:
        # Mark this question as answered wrong on first try
        state["wrong_on_first_try_for_current_question"] = True
        state["wrong_on_first_try_count"] = state.get("wrong_on_first_try_count", 0) + 1
    
    state["is_correct"] = is_correct
    
    return state


def route_based_answer(state: QuizState) -> str:
    """Route to next node based on whether answer is correct and attempt count.
    
    Handles difficulty progression:
    - Correct answer: Increment consecutive correct count
      - If 2+ consecutive correct at current level → advance to next difficulty
      - Otherwise → move to next question at same difficulty
    - Wrong answer: Reset consecutive count, show hints (max 3 attempts)
    
    Difficulty progression: easy → medium → hard
    
    Returns:
        "record_answer_to_history" to record the answer before moving on
        "generate_hint_node" if answer is incorrect (on attempts 1-3)
    """
    
    is_correct = state.get("is_correct", False)
    hint_attempt = state.get("hint_attempt", 0)
    
    if is_correct:
        # Answer is correct - record it and check for difficulty progression
        return "record_answer_to_history"
    else:
        # Answer is incorrect, increment attempt and generate hint
        if hint_attempt < 3:
            return "generate_hint_node"
        else:
            # After 3 wrong attempts, record as wrong and move to next question
            return "record_answer_to_history"


# def retrieve_context_node(state: QuizState) -> QuizState:
#     """Perform similarity search in ChromaDB using the question text.
    
#     Retrieves relevant context documents from ChromaDB that are semantically
#     similar to the user's incorrect answer or the question itself.
#     Stores results in state["retrieved_context"].
#     """
#     client = chromadb.PersistentClient(path=str(CHROMA_DIR))
#     collection = client.list_collections()[0]
    
#     # Get the question text to use as search query
#     question_text = state.get("current_question", {}).get("question", "")
    
#     if not question_text:
#         # Fallback: use user answer if question is not available
#         question_text = state.get("user_answer", "")
    
#     if not question_text:
#         # If no search text, return empty context
#         state["retrieved_context"] = []
#         return state
    
#     # Perform similarity search with query
#     # query() returns documents similar to the query text
#     try:
#         search_results = collection.query(
#             query_texts=[question_text],
#             n_results=3,  # Get top 3 similar documents
#             include=["documents"]
#         )
        
#         # Extract documents from results
#         retrieved_docs = search_results.get("documents", [[]])[0]
#         state["retrieved_context"] = retrieved_docs
        
#     except Exception as e:
#         print(f"Error during similarity search: {e}")
#         state["retrieved_context"] = []
    
#     return state


def generate_hint_node(state: QuizState) -> QuizState:
    """Generate hints based on attempt number.
    
    - Attempt 1: General hint based on chunks
    - Attempt 2: More specific hint related to the question
    - Attempt 3: Direct answer
    
    Retrieves context from ChromaDB first, then generates hint based on attempt level.
    After generating hint, the state is ready for await_user_answer.
    """
  
    # First retrieve relevant context using similarity search
    # client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # collection = client.list_collections()[0]
    
    # question_text = state.get("current_question", {}).get("question", "")
    # if not question_text:
    #     question_text = state.get("user_answer", "")
    
    # if question_text:
    #     try:
    #         search_results = collection.query(
    #             query_texts=[question_text],
    #             n_results=3,
    #             include=["documents"]
    #         )
    #         retrieved_docs = search_results.get("documents", [[]])[0]
    #         state["retrieved_context"] = retrieved_docs
    #     except Exception as e:
    #         print(f"Error during context retrieval: {e}")
    #         state["retrieved_context"] = []
    
    hint_attempt = state.get("hint_attempt", 0) + 1  # increment here
    state["hint_attempt"] = hint_attempt
    chunks = state.get("current_chunks", [])
    question_data = state.get("current_question", {})
    question = question_data.get("question", "")
    correct_answer = question_data.get("correct_answer", "")
    user_answer = state.get("user_answer", "")
    
    if hint_attempt == 1:
        # First wrong attempt: Generate general hint from chunks
        context = "\n".join(chunks)
        prompt = f"""Based on the following content, provide a GENERAL HINT (not the answer) to help understand the topic for this question:

Question: {question}

Content:
{context}

Provide a helpful hint that guides the user without giving away the answer."""
        
    elif hint_attempt == 2:
        # Second wrong attempt: Generate specific hint
        context = "\n".join(chunks)
        prompt = f"""Based on the following content, provide a MORE SPECIFIC HINT to help answer this question:

Question: {question}
User's answer was: {user_answer}

Content:
{context}

Provide a specific hint that points to the right direction without revealing the answer."""
        
    else:  # hint_attempt >= 3
        # Third wrong attempt: Give the direct answer
        state["hint"] = f"The correct answer is: {correct_answer}"
        state["correct_count_at_difficulty"] = -1
        # state["current_difficulty"]="easy"
        return state
    
    # Invoke LLM for hint generation
    try:
        response = llm.invoke(prompt)
        hint_text = response.content if hasattr(response, 'content') else str(response)
        state["hint"] = hint_text
    except Exception as e:
        state["hint"] = f"Unable to generate hint. The correct answer is: {correct_answer}"
    
    return state


def end_session_node(state: QuizState) -> QuizState:
    """Send completion message when all chunks and questions have been processed.
    
    Updates status and completes the quiz session without waiting for user input.
    The frontend will receive the completion status through the final state.
    """
    state["status"] = "completed"
    state["hint"] = "All questions completed! Quiz session finished."
    
    return state


def record_answer_to_history(state: QuizState) -> QuizState:
    """Record the current question and answer to the quiz history.
    
    Adds a complete record of the question, user's answer, and result to quiz_history.
    Increments question_count.
    """
    
    question_record = {
        "question_num": state.get("question_count", 0) + 1,
        "question": state.get("current_question", {}).get("question", ""),
        "options": state.get("current_question", {}).get("options", []),
        "correct_answer": state.get("current_question", {}).get("correct_answer", ""),
        "user_answer": state.get("user_answer", ""),
        "is_correct": state.get("is_correct", False) and state.get("hint_attempt")==0,
        "wrong_on_first_try": state.get("wrong_on_first_try_for_current_question", False),
        "difficulty": state.get("current_difficulty", "easy"),
        "topic": state.get("topic_from_chunk", ""),
    }
    
    # Add to quiz history
    quiz_history = state.get("quiz_history", [])
    quiz_history.append(question_record)
    
    state["quiz_history"] = quiz_history
    state["question_count"] = state.get("question_count", 0) + 1
    
    # Reset flags for next question
    if not state.get("is_correct", False):
        state["hint_attempt"] = 0
    state["wrong_on_first_try_for_current_question"] = False
    
    return state


def check_difficulty_progression(state: QuizState) -> QuizState:
    """Check and handle difficulty progression after correct answer.
    
    Progression rules:
    - Increment consecutive correct count
    - If 2+ consecutive correct:
      - Advance to next difficulty (easy→medium→hard)
      - Reset counter for new difficulty
    - Stay at current difficulty if < 2 consecutive correct
    """
    current_difficulty = state.get("current_difficulty", "easy")
    correct_count = state.get("correct_count_at_difficulty", 0) + 1
    
    difficulty_levels = ["easy", "medium", "hard"]
    current_index = difficulty_levels.index(current_difficulty)
    
    # Advance to next difficulty after 2 consecutive correct answers
    if correct_count >= 2 and current_index < len(difficulty_levels) - 1:
        state["current_difficulty"] = difficulty_levels[current_index + 1]
        state["correct_count_at_difficulty"] = 0
        print(f"✅ Advancing to {state['current_difficulty']} difficulty!")
    else:
        state["correct_count_at_difficulty"] = correct_count
    
    return state


def check_chunks_available(state: QuizState) -> str:
    """Check if more chunks are available to process.
    
    Returns:
        "generate_question" if chunks available
        "end_session" if no more chunks
    """
   
    
    chunks = state.get("current_chunks", [])
    
    if chunks and len(chunks) > 0:
        return "generate_question"
    else:
        return "end_session"
    
def route_after_recording(state: QuizState) -> str:
        if state.get("is_correct", False):
            return "check_difficulty_progression"
        else:
            return "load_next_chunk"
from langgraph.graph import StateGraph, END

def create_quiz_graph():
    """Create and return the compiled LangGraph workflow for the quiz agent with difficulty progression."""
    
    # Initialize StateGraph with QuizState
    graph = StateGraph(QuizState)
    
    # Add nodes
    graph.add_node("start_session", start_session_node)
    graph.add_node("load_next_chunk", load_next_chunk_node)
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("await_user_answer", await_user_answer)
    graph.add_node("evaluator_answer", evaluator_answer_node)
    graph.add_node("generate_hint", generate_hint_node)
    graph.add_node("record_answer_to_history", record_answer_to_history)
    graph.add_node("check_difficulty_progression", check_difficulty_progression)
    graph.add_node("end_session", end_session_node)
    
    # Add edges
    # Entry point
    graph.set_entry_point("start_session")
    
    # After starting, load the first chunk
    graph.add_edge("start_session", "load_next_chunk")
    
    # After loading chunk, check if chunks are available
    graph.add_conditional_edges(
        "load_next_chunk",
        check_chunks_available,
        {
            "generate_question": "generate_question",
            "end_session": "end_session",
        }
    )
    
    # Generate question → await answer
    graph.add_edge("generate_question", "await_user_answer")
    
    # After user answers, evaluate
    graph.add_edge("await_user_answer", "evaluator_answer")
    
    # Conditional routing based on correctness and attempts
    graph.add_conditional_edges(
        "evaluator_answer",
        route_based_answer,
        {
            "record_answer_to_history": "record_answer_to_history",
            "generate_hint_node": "generate_hint",
            "load_next_chunk_node": "record_answer_to_history",
        }
    )
    
    # After recording, check if answer was correct
    # def route_after_recording(state: QuizState) -> str:
    #     if state.get("is_correct", False):
    #         return "check_difficulty_progression"
    #     else:
    #         return "load_next_chunk"
    
    graph.add_conditional_edges(
        "record_answer_to_history",
        route_after_recording,
        {
            "check_difficulty_progression": "check_difficulty_progression",
            "load_next_chunk": "load_next_chunk",
        }
    )
    
    # After checking difficulty progression, load next question
    graph.add_edge("check_difficulty_progression", "load_next_chunk")
    
    # After generating hint, ask user again
    graph.add_edge("generate_hint", "await_user_answer")
    
    # End session → END
    graph.add_edge("end_session", END)
    
    # Compile the graph
    checkpointer = MemorySaver()
    compiled_graph = graph.compile(checkpointer=checkpointer)
    
    return compiled_graph


# Optionally, create a module-level graph instance
# quiz_graph = create_quiz_graph()




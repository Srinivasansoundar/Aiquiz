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
    # retrieved_context: List[str]
    hint: str 

class QuestionResponse(BaseModel):
    question:str
    options:list[str]
    correct_answer:str

def start_session_node(state:QuizState) -> QuizState:
    """Create and return a fresh QuizState for a new session.

    This initializes the state and resets all counters (cursor, hint attempts,
    correctness flag, and user answer).
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
    }

     


CHROMA_DIR = Path(__file__).resolve().parents[2] / "core" / "services" / "chroma_db"

def load_next_chunk_node(state: QuizState) -> QuizState: 
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    
    # Get available collections
    collections = client.list_collections()
    if not collections:
        raise ValueError("No collections found in ChromaDB. Please ensure data has been ingested.")
    
    collection = collections[0]
    
    cursor = state.get("chunk_cursor", 0)
    result = collection.get(offset=cursor, limit=2, include=["documents"])
    docs = result.get("documents", [])
    
    # if not docs:
    #     # No more documents available
    #     return {
    #         **state,
    #         "current_chunks": [],
    #         "chunk_cursor": cursor
    #     }

    return {
        **state,
        "current_chunks": docs,
        "chunk_cursor": cursor + len(docs),
        "hint_attempt":0,
        "hint":""
    }
# {
#   "ids": [...],
#   "documents": [...],
#   "metadatas": [...],      # only if requested
#   "embeddings": [...]      # only if requested
# }

def generate_question_node(state: QuizState) -> QuizState:
    """Generate a multiple-choice question from the current chunks using the LLM
    with structured output, and update the state with the generated question.
    """
    
    
    llm_structured_output = llm.with_structured_output(QuestionResponse)
    chunks = state.get("current_chunks", [])
    if not chunks:
        raise ValueError("No chunks available to generate a question from")
    
    # Join chunks into context
    context = "\n".join(chunks)
    
    # Create a prompt that instructs the LLM to generate a question
    prompt = f"""Based on the following text content, generate a multiple-choice question with 4 options and identify the correct answer.

Content:
{context}

Generate a question that tests understanding of the content. Return the question, 4 options, and the correct answer."""

    # Invoke the LLM with structured output
    response = llm_structured_output.invoke(prompt)
    
    # Update state with the generated question
    state["current_question"] = {
        "question": response.question,
        "options": response.options,
        "correct_answer": response.correct_answer,
    }
    state["user_answer"] = ""
    state["is_correct"] = False
    
    return state

def await_user_answer(state: QuizState) -> QuizState:
    """Pause the graph execution and wait for user input (answer) via an interrupt.
    
    LangGraph will pause at this node and wait for external input before resuming.
    The user's answer is provided through the POST /answer endpoint.
    Sends question, options, hint (if any), and attempt info to frontend.
    """
    question_data = state.get("current_question", {})
    hint = state.get("hint", "")
    hint_attempt = state.get("hint_attempt", 0)
    
    # Prepare data to send to the client
    interrupt_data = {
        "question": question_data.get("question", ""),
        "options": question_data.get("options", []),
        "hint": hint,
        "hint_attempt": hint_attempt,
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
    """
   
    
    user_answer = state.get("user_answer", "").strip().lower()
    correct_answer = state.get("current_question", {}).get("correct_answer", "").strip().lower()
    
    # Check if answer is correct
    is_correct = user_answer == correct_answer
    
    state["is_correct"] = is_correct
    
    return state


def route_based_answer(state: QuizState) -> str:
    """Route to next node based on whether answer is correct and attempt count.
    
    Tracks wrong attempts:
    - 1st attempt (hint_attempt=0): Generate general hint → show hint → await answer
    - 2nd attempt (hint_attempt=1): Generate specific hint → show hint → await answer
    - 3rd attempt (hint_attempt=2): Show correct answer → move to next chunk
    
    Returns:
        "load_next_chunk_node" if answer is correct
        "generate_hint_node" if answer is incorrect (on attempts 1-3)
    """
    
    
    is_correct = state.get("is_correct", False)
    hint_attempt = state.get("hint_attempt", 0)
    
    if is_correct:
        # Reset hint attempt for next question
        # state["hint_attempt"] = 0
        return "load_next_chunk_node"
    else:
        # Answer is incorrect, increment attempt and generate hint
        if hint_attempt < 3:
            # state["hint_attempt"] = hint_attempt + 1
            return "generate_hint_node"
        else:
            # After 3 wrong attempts, move to next chunk
            # state["hint_attempt"] = 0
            return "load_next_chunk_node"


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
from langgraph.graph import StateGraph, END

def create_quiz_graph():
    """Create and return the compiled LangGraph workflow for the quiz agent."""
    
    # Initialize StateGraph with QuizState
    graph = StateGraph(QuizState)
    
    # Add nodes
    graph.add_node("start_session", start_session_node)
    graph.add_node("load_next_chunk", load_next_chunk_node)
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("await_user_answer", await_user_answer)
    graph.add_node("evaluator_answer", evaluator_answer_node)
    graph.add_node("generate_hint", generate_hint_node)
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
            "load_next_chunk_node": "load_next_chunk",
            "generate_hint_node": "generate_hint",
        }
    )
    
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




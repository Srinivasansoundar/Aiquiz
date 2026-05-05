# """Quiz service containing business logic for quiz operations."""

# from typing import Dict, Any
# from src.control.agents.graph import create_quiz_graph


# # Single user quiz state and graph
# quiz_state: Dict[str, Any] = {}
# quiz_graph: Any = None


# class QuizService:
#     """Service for managing a single-user quiz session."""
    
#     @staticmethod
#     def start_session() -> Dict[str, Any]:
#         """Start a new quiz session.
        
#         Returns:
#             Dictionary with first question data
#         """
#         global quiz_state, quiz_graph
        
#         # Create and initialize the quiz graph
#         quiz_graph = create_quiz_graph()
        
#         # Initialize empty state (the graph will populate it)
#         initial_state = {}
        
#         # Invoke graph - it will pause at first interrupt (await_user_answer)
#         try:
#             result = quiz_graph.invoke(initial_state)
#             quiz_state = result
#              #Starts from entry node
#              # Executes nodes step-by-step
#              #Updates state
#              # Stops when:
#              # flow ends OR
#              # interrupt happens

#              # 👉 Then returns the current state

#              # Return first question
#             # return {
#             #     "question": result.get("current_question", {}).get("question", ""),
#             #     "options": result.get("current_question", {}).get("options", []),
#             #     "hint": result.get("hint", ""),
#             #     "hint_attempt": result.get("hint_attempt", 0),
#             #     "status": result.get("status", "active"),
#             # }
#         except Exception as graph_error:
#             # Handle interrupt - graph paused waiting for answer
#             if "Interrupt" in str(type(graph_error)):
#                 # Extract interrupt data
#                 interrupt_data = graph_error.args[0] if graph_error.args else {}
#                 # Keep the initial_state which has been updated by nodes before interrupt
#                 # The state was modified during graph execution before hitting the interrupt
#                 quiz_state = initial_state
                
#                 return {
#                     "question": interrupt_data.get("question", ""),
#                     "options": interrupt_data.get("options", []),
#                     "hint": interrupt_data.get("hint", ""),
#                     "hint_attempt": interrupt_data.get("hint_attempt", 0),
#                     "status": "awaiting_answer",
#                 }
#             else:
#                 raise
    
#     @staticmethod
#     def submit_answer(answer: str) -> Dict[str, Any]:
#         """Submit an answer and get the next question or completion status.
        
#         Args:
#             answer: The user's answer
            
#         Returns:
#             Dictionary with next question or completion status
            
#         Raises:
#             RuntimeError: If no active quiz session
#         """
#         global quiz_state, quiz_graph
        
#         if not quiz_graph or not quiz_state:
#             raise RuntimeError("No active quiz session. Start a new session first.")
        
#         # Update state with user's answer
#         quiz_state["user_answer"] = answer
        
#         # Resume graph execution
#         try:
#             result = quiz_graph.invoke(quiz_state)
#             # graph modifies it in-place:
#             quiz_state = result
            
#             # Check if quiz is completed
#             if result.get("status") == "completed":
#                 return {
#                     "status": "completed",
#                     "message": result.get("hint", "Quiz completed!"),
#                 }
            
#             # Return next question
#             # return {
#             #     "question": result.get("current_question", {}).get("question", ""),
#             #     "options": result.get("current_question", {}).get("options", []),
#             #     "hint": result.get("hint", ""),
#             #     "hint_attempt": result.get("hint_attempt", 0),
#             #     "status": result.get("status", "active"),
#             # }
            
#         except Exception as graph_error:
#             # Handle interrupt - graph paused again
#             if "Interrupt" in str(type(graph_error)):
#                 interrupt_data = graph_error.args[0] if graph_error.args else {}
                
#                 return {
#                     "question": interrupt_data.get("question", ""),
#                     "options": interrupt_data.get("options", []),
#                     "hint": interrupt_data.get("hint", ""),
#                     "hint_attempt": interrupt_data.get("hint_attempt", 0),
#                     "status": "awaiting_answer",
#                 }
#             else:
#                 raise
    
from langgraph.types import Command
from src.control.agents.graph import create_quiz_graph
from src.core.services.topic_quiz_service import TopicQuizService
from typing import Dict, List, Any, Optional
from langsmith import traceable
# ✅ Created ONCE — MemorySaver persists across start/submit calls
quiz_graph = create_quiz_graph()

THREAD_CONFIG = {"configurable": {"thread_id": "single-user-session"}}

class QuizService:

    @staticmethod
    @traceable(name="start_quiz_session", description="Initialize a new quiz session")
    def start_session(collection_name: str = None, topic: Optional[str] = None, 
                     num_chunks: int = 5) -> Dict[str, Any]:
        try:
            initial_state = {
                "chunk_cursor": 0, 
                "status": "started",
                "collection_name": collection_name or "",
                "topic": topic,
                "topic_chunks": [],
            }
            
            # If topic is provided, fetch relevant chunks
            if topic and collection_name:
                topic_service = TopicQuizService()
                result = topic_service.search_topics(
                    collection_name=collection_name,
                    query=topic,
                    num_results=num_chunks
                )
                
                if result.get("success"):
                    # Extract chunk content for the graph to use
                    chunks = result.get("results", [])
                    initial_state["topic_chunks"] = [chunk["content"] for chunk in chunks]
                    print(f"📚 Loaded {len(chunks)} chunks for topic: {topic}")
                else:
                    print(f"⚠️ Warning: Could not fetch topic chunks: {result.get('error')}")
            
            quiz_graph.invoke(
                initial_state,
                config=THREAD_CONFIG
            )

            current_state = quiz_graph.get_state(THREAD_CONFIG)
            # current_state = {
            #     "values": {...},        # your state data
            #     "tasks": [...],         # execution steps
            #     "next": [...],          # next nodes to run
            #     "config": {...},        # thread/session config
            # }
            # print(current_state)

            if not current_state or not current_state.tasks:
                return {"status": "completed", "message": "No questions found."}

            if not current_state.tasks[0].interrupts:
                return {"status": "completed", "message": "No interrupt found."}

            interrupt_data = current_state.tasks[0].interrupts[0].value

            return {
                "question": interrupt_data.get("question", ""),
                "options": interrupt_data.get("options", []),
                "hint": interrupt_data.get("hint", ""),
                "hint_attempt": interrupt_data.get("hint_attempt", 0),
                "status": "awaiting_answer",
            }
        except Exception as e:
            raise RuntimeError(f"Error starting quiz: {e}")

    @staticmethod
    @traceable(name="submit_quiz_answer", description="Submit user answer and get next question")
    def submit_answer(answer: str) -> Dict[str, Any]:
        try:
            quiz_graph.invoke(
                Command(resume=answer),
                config=THREAD_CONFIG
            )
#             "Resume the graph from where it stopped,
# and pass this value as the result of the interrupt"

            current_state = quiz_graph.get_state(THREAD_CONFIG)

            if not current_state or not current_state.tasks:
                return {"status": "completed", "message": "Quiz session finished!"}

            if not current_state.tasks[0].interrupts:
                return {"status": "completed", "message": "Quiz completed."}

            interrupt_data = current_state.tasks[0].interrupts[0].value

            return {
                "question": interrupt_data.get("question", ""),
                "options": interrupt_data.get("options", []),
                "hint": interrupt_data.get("hint", ""),
                "hint_attempt": interrupt_data.get("hint_attempt", 0),
                "status": "awaiting_answer",
            }
        except Exception as e:
            raise RuntimeError(f"Error submitting answer: {e}")
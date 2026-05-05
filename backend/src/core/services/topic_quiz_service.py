"""Service for generating quiz questions from specific topics."""
# this is not used when there is frontend and backend

from typing import Dict, Any, List, Optional
from src.core.services.topic_based_ingestion import TopicBasedPDFIngestionService
from langchain_core.documents import Document


class TopicQuizService:
    """Service for retrieving topic-specific content and generating questions."""
    
    def __init__(self):
        """Initialize the topic quiz service."""
        self.ingestion_service = TopicBasedPDFIngestionService()
    
    def search_topics(self, collection_name: str, query: str, 
                     num_results: int = 10) -> Dict[str, Any]:
        """Search for topics in a collection using semantic search.
        
        Args:
            collection_name: ChromaDB collection to search
            query: Search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        try:
            results = self.ingestion_service.retrieve_by_topic(
                collection_name=collection_name,
                topic=query,
                k=num_results
            )
            
            # Extract unique topics from results
            unique_topics = set()
            search_results = []
            
            for result in results:
                topic = result.metadata.get("topic", "Unknown")
                unique_topics.add(topic)
                search_results.append({
                    "content": result.page_content,  # Full content for quiz generation
                    "topic": topic,
                    "filename": result.metadata.get("filename"),
                })
            
            return {
                "success": True,
                "query": query,
                "collection_name": collection_name,
                "num_results": len(search_results),
                "unique_topics": list(unique_topics),
                "results": search_results,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to search topics: {str(e)}",
                "query": query,
                "collection_name": collection_name,
            }

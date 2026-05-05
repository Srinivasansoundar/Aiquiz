"""Topic-based PDF ingestion service using unstructured library."""

import os
from typing import List, Dict, Any
from pathlib import Path
import tempfile

from unstructured.partition.pdf import partition_pdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class TopicBasedPDFIngestionService:
    """Service for ingesting PDFs, organizing by topics, and storing in ChromaDB."""
    
    def __init__(self, chroma_db_path: str = "./chroma_db"):
        """Initialize the ingestion service.
        
        Args:
            chroma_db_path: Path to ChromaDB persistence directory
        """
        self.chroma_db_path = chroma_db_path
        self._setup_embeddings()
    
    def _setup_embeddings(self):
        """Setup OpenAI embeddings."""
        api_key = os.getenv('OPEN_API_KEY')
        if not api_key:
            raise ValueError("OPEN_API_KEY environment variable not set")
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def load_pdf_with_unstructured(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and partition PDF using unstructured library.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of elements with metadata including titles
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid PDF
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        print(f"📄 Loading PDF with unstructured: {file_path}")
        
        try:
            # Partition PDF - extracts text with element metadata
            elements = partition_pdf(
                filename=file_path,
                # strategy="fast",
                extract_images_in_pdf=False,  # Set to True if you need images
                infer_table_structure=True,   # Extract table structures
            )
            
            print(f"✅ Partitioned PDF into {len(elements)} elements")
            return elements
            
        except Exception as e:
            raise ValueError(f"Failed to partition PDF: {str(e)}")
    
    def organize_by_topics(self, elements: List[Any]) -> Dict[str, List[str]]:
        """Organize elements by their titles/topics.
        
        Args:
            elements: List of elements from unstructured.partition_pdf
            
        Returns:
            Dictionary with topics as keys and content as values
        """
        print("📚 Organizing content by topics...")
        
        topics_dict: Dict[str, List[str]] = {}
        current_topic = "General"
        
        for element in elements:
            # Get element type and text
            element_text = str(element)
            element_type = element.__class__.__name__
            
            # Detect if this is a title/heading
            # Title elements typically have higher font size
            if element_type in ['Title', 'NarrativeText']:
                if hasattr(element, 'text'):
                    text = element.text.strip()
                    # If it looks like a heading (short, all caps, or specific patterns)
                    if len(text) < 100 and (text.isupper() or text.startswith('Chapter') or 
                                            text.startswith('Section') or '.' not in text):
                        current_topic = text
                        topics_dict[current_topic] = []
                        print(f"  📖 Found topic: {current_topic}")
                        continue
            
            # Add content to current topic
            if element_text.strip():
                if current_topic not in topics_dict:
                    topics_dict[current_topic] = []
                topics_dict[current_topic].append(element_text)
        
        print(f"✅ Organized into {len(topics_dict)} topics")
        return topics_dict
    
    def split_topic_content(self, topic_content: str, 
                          chunk_size: int = 500, 
                          chunk_overlap: int = 100) -> List[str]:
        """Split topic content using RecursiveCharacterTextSplitter.
        
        Args:
            topic_content: Combined text for a single topic
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks for this topic
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""],  # More granular separators
        )
        
        chunks = splitter.split_text(topic_content)
        return chunks
    
    def create_topic_documents(self, topics_dict: Dict[str, List[str]], 
                              filename: str,
                              chunk_size: int = 500,
                              chunk_overlap: int = 100) -> List[Document]:
        """Convert organized topics into Document objects with metadata.
        
        Args:
            topics_dict: Dictionary of topics and their content
            filename: Source filename for metadata
            chunk_size: Size of chunks within each topic
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of Document objects with topic metadata
        """
        documents = []
        
        for topic, content_list in topics_dict.items():
            # Combine all content for this topic
            combined_content = "\n\n".join(content_list)
            
            if not combined_content.strip():
                continue
            
            # Split content within this topic
            chunks = self.split_topic_content(
                combined_content, 
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            print(f"  ✅ Split topic '{topic}' into {len(chunks)} chunks")
            
            # Create documents with topic metadata
            for idx, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "filename": filename,
                        "topic": topic,  # Key metadata for semantic search
                        "chunk_id": idx,
                    }
                )
                documents.append(doc)
        
        return documents
    
    def store_in_chromadb(self, documents: List[Document], 
                         collection_name: str) -> Chroma:
        """Store documents in ChromaDB with a new collection.
        
        Args:
            documents: List of Document objects to store
            collection_name: Name of the collection to create
            
        Returns:
            Chroma vector store instance
        """
        print(f"💾 Storing {len(documents)} documents in ChromaDB...")
        print(f"📚 Collection name: {collection_name}")
        
        # Ensure chroma_db directory exists
        os.makedirs(self.chroma_db_path, exist_ok=True)
        
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=self.chroma_db_path,
        )
        
        print(f"✅ Successfully stored in ChromaDB collection: {collection_name}")
        return vector_store
    
    def retrieve_by_topic(self, collection_name: str, topic: str, 
                         k: int = 5) -> List[Document]:
        """Retrieve chunks for a specific topic using semantic search.
        
        Args:
            collection_name: Name of the ChromaDB collection
            topic: Topic to search for
            k: Number of top results to retrieve
            
        Returns:
            List of relevant Document chunks
        """
        print(f"🔍 Searching for topic: {topic}")
        
        # Load the existing vector store
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.chroma_db_path,
        )
        
        # Create a filter for the specific topic
        # Then do similarity search with the topic as query
        results = vector_store.similarity_search(topic, k=k)
        
        print(f"✅ Retrieved {len(results)} relevant chunks for topic: {topic}")
        return results
    
    def ingest_pdf_from_upload(self, file_content: bytes, filename: str,
                              collection_name: str,
                              chunk_size: int = 500,
                              chunk_overlap: int = 100) -> Dict[str, Any]:
        """Complete pipeline: load, organize by topics, chunk, and store.
        
        Args:
            file_content: Binary content of PDF file
            filename: Original filename
            collection_name: Name for ChromaDB collection
            chunk_size: Size of chunks within topics
            chunk_overlap: Overlap between chunks
            
        Returns:
            Dictionary with ingestion results
        """
        try:
            # Save file temporarily
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                # Step 1: Load and partition PDF
                elements = self.load_pdf_with_unstructured(tmp_path)
                
                # Step 2: Organize by topics
                topics_dict = self.organize_by_topics(elements)
                
                # Step 3: Create documents with topic metadata
                documents = self.create_topic_documents(
                    topics_dict,
                    filename,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                
                # Step 4: Store in ChromaDB
                self.store_in_chromadb(documents, collection_name)
                
                return {
                    "success": True,
                    "filename": filename,
                    "collection_name": collection_name,
                    "total_documents": len(documents),
                    "topics": list(topics_dict.keys()),
                    "total_topics": len(topics_dict),
                }
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to ingest PDF: {str(e)}",
                "filename": filename,
                "collection_name": collection_name,
            }

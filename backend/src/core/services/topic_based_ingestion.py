"""Topic-based PDF ingestion service using unstructured library."""

import os
from typing import List, Dict, Any
from pathlib import Path
import tempfile

from unstructured.partition.pdf import partition_pdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class TopicBasedPDFIngestionService:
    """Service for ingesting PDFs, organizing by topics, and storing in ChromaDB."""
    
    # Threshold for determining if content is "large" (in characters)
    LARGE_CONTENT_THRESHOLD = 2000  # ~400-500 words
    
    def __init__(self, chroma_db_path: str = "./chroma_db"):
        """Initialize the ingestion service.
        
        Args:
            chroma_db_path: Path to ChromaDB persistence directory
        """
        self.chroma_db_path = chroma_db_path
        self._setup_embeddings()
        self.semantic_chunker = None  # Lazy initialized
    
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
    
    def _get_semantic_chunker(self):
        """Get or create semantic chunker (lazy initialization)."""
        if self.semantic_chunker is None:
            self.semantic_chunker = SemanticChunker(self.embeddings)
        return self.semantic_chunker
    
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
    # [
    # Title(text="Introduction"),
    # NarrativeText(text="AI is..."),
    # Table(text="..."),
    # ]
    # Each object has text,metadata,category
    
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
        title_hierarchy = []  # Track title hierarchy to detect subtitles
        
        for i, element in enumerate(elements):
            # Get element type and text
            element_text = str(element)
            element_type = element.__class__.__name__
            
            # Detect if this is a title/heading
            if element_type == 'Title':
                if hasattr(element, 'text'):
                    text = element.text.strip()
                    if not text:
                        continue
                    
                    # Check element metadata for font size (indicates hierarchy)
                    # font_size = None
                    # if hasattr(element, 'metadata'):
                    #     # Try to extract font size from metadata
                    #     if hasattr(element.metadata, 'get'):
                    #         font_size = element.metadata.get('font_size')
                    #     elif hasattr(element.metadata, 'font_size'):
                    #         font_size = element.metadata.font_size
                    
                    # Detect true heading vs subtitle:
                    # - True headings: short, < 100 chars, no period at end
                    # - Subtitles: often similar in length but come after main title
                    is_heading = (
                        len(text) < 100 and 
                        not text.endswith('.') and
                        (text.isupper() or 
                         text.startswith('Chapter') or 
                         text.startswith('Section') or
                         text.startswith('Part ') or
                         text.istitle())  # Proper case title detection
                    )
                    
                    # If previous element was also a title, this is likely a subtitle
                    prev_was_title = i > 0 and elements[i-1].__class__.__name__ == 'Title'
                    
                    # Assign content to current title if:
                    # 1. It's clearly a heading (looks like one)
                    # 2. It's NOT right after another title (to avoid subtitle problem)
                    if is_heading and not prev_was_title:
                        current_topic = text
                        if current_topic not in topics_dict:
                            topics_dict[current_topic] = []
                        title_hierarchy.append(current_topic)
                        print(f"  📖 Found topic: {current_topic}")
                        continue
                    elif prev_was_title:
                        # This is likely a subtitle - skip it or add to current topic as header
                        print(f"  📝 Skipping subtitle: {text}")
                        continue
            
            # Handle NarrativeText and other content types
            elif element_type in ['NarrativeText']:
                if element_text.strip():
                    if current_topic not in topics_dict:
                        topics_dict[current_topic] = []
                    topics_dict[current_topic].append(element_text)
            
            # Add other content to current topic
            elif element_text.strip():
                if current_topic not in topics_dict:
                    topics_dict[current_topic] = []
                topics_dict[current_topic].append(element_text)
        
        # Clean up empty topics
        topics_dict = {k: v for k, v in topics_dict.items() if v}
        
        print(f"✅ Organized into {len(topics_dict)} topics")
        # print(topics_dict)
        return topics_dict
    
    def split_topic_content(self, topic_content: str, 
                          chunk_size: int = 500, 
                          chunk_overlap: int = 100) -> List[str]:
        """Split topic content using semantic chunking for large content, regex splitting for small.
        
        Args:
            topic_content: Combined text for a single topic
            chunk_size: Maximum size of each chunk (for regular splitter)
            chunk_overlap: Overlap between chunks (for regular splitter)
            
        Returns:
            List of text chunks for this topic
        """
        content_length = len(topic_content)
        
        # Use semantic chunking for large content
        if content_length > self.LARGE_CONTENT_THRESHOLD:
            print(f"  🧠 Using semantic chunking ({content_length} chars > {self.LARGE_CONTENT_THRESHOLD} threshold)")
            try:
                semantic_chunker = self._get_semantic_chunker()
                chunks = semantic_chunker.split_text(topic_content)
                return chunks
            except Exception as e:
                print(f"  ⚠️ Semantic chunking failed: {str(e)}. Falling back to recursive splitter.")
                # Fall back to recursive splitting if semantic chunking fails
        else:
            print(f"  ✂️ Using recursive text splitting ({content_length} chars ≤ {self.LARGE_CONTENT_THRESHOLD} threshold)")
        
        # Use recursive character splitting for small content or as fallback
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
        print(documents[:5])
        
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
            collection_metadata={"hnsw:space": "cosine"}
        )
        
        print(f"✅ Successfully stored in ChromaDB collection: {collection_name}")
        return vector_store
    
    def retrieve_by_topic(self, collection_name: str, topic: str, 
                         k: int = 5) -> List[Document]:
        print(f"🔍 Searching for topic: {topic}")
        
        # Load the existing vector store
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.chroma_db_path,
        )
        
        try:
            # Get all documents to extract unique topics from metadata
            all_docs = vector_store.get(include=["metadatas"])
            metadatas = all_docs.get("metadatas", [])
            
            # Extract unique topics from metadata
            unique_topics = set()
            for metadata in metadatas:
                if metadata and "topic" in metadata:
                    unique_topics.add(metadata["topic"])
            
            if not unique_topics:
                print("⚠️ No topics found in metadata. Cannot proceed.")
                return []
            
            print(f"📚 Found {len(unique_topics)} unique topics in collection")
            
            # Embed query once
            query_embedding = self.embeddings.embed_query(topic)
            
            # Compute similarity with each stored topic
            topic_similarities = []
            for stored_topic in unique_topics:
                topic_embedding = self.embeddings.embed_query(stored_topic)
                similarity = self._cosine_similarity(query_embedding, topic_embedding)
                topic_similarities.append((stored_topic, similarity))
            
            # Filter by similarity threshold only
            SIMILARITY_THRESHOLD = 0.7
            top_topics = [
                t for t, s in topic_similarities if s >= SIMILARITY_THRESHOLD
            ]
            
            print(f"✅ {len(top_topics)} topics matched (threshold={SIMILARITY_THRESHOLD}):")
            for t, s in sorted(topic_similarities, key=lambda x: x[1], reverse=True):
                if s >= SIMILARITY_THRESHOLD:
                    print(f"  - '{t}' (similarity={s:.2f})")
            
            # Directly fetch all chunks for matched topics
            if top_topics:
                where_filter = (
                    {"topic": {"$eq": top_topics[0]}}
                    if len(top_topics) == 1
                    else {"$or": [{"topic": {"$eq": t}} for t in top_topics]}
                )
                
                raw = vector_store.get(where=where_filter, include=["documents", "metadatas"])
                
                from langchain_core.documents import Document
                results = [
                    Document(page_content=doc, metadata=meta)
                    for doc, meta in zip(raw["documents"], raw["metadatas"])
                ]
                print(f"✅ Fetched {len(results)} chunks from matched topics")
            else:
                results = []

            # Fall back to global search only if topic fetch didn't return enough chunks
            if len(results) < k:
                print(f"⚠️ Only {len(results)}/{k} chunks from topics, falling back to global search...")
                global_results_with_scores = vector_store.similarity_search_with_score(topic, k=k*2)
                
                # Filter by similarity threshold
                # ChromaDB returns distance, convert to similarity: similarity = 1 - distance
                GLOBAL_SIMILARITY_THRESHOLD = 0.5  # Only keep results with similarity >= 0.7
                global_results = []
                for doc, distance in global_results_with_scores:
                    similarity = 1 - distance  # Convert distance to similarity
                    if similarity >= GLOBAL_SIMILARITY_THRESHOLD:
                        global_results.append(doc)
                        print(f"  ✅ Global result: similarity={similarity:.2f}")
                    else:
                        print(f"  ⚠️ Skipped: similarity={similarity:.2f} < {GLOBAL_SIMILARITY_THRESHOLD} threshold")
                
                # Merge and deduplicate
                seen = {doc.page_content for doc in results}
                for doc in global_results:
                    if doc.page_content not in seen:
                        seen.add(doc.page_content)
                        results.append(doc)

            final_results = results[:k]
            print(f"✅ Returning {len(final_results)} results")
            return final_results

        except Exception as e:
            print(f"⚠️ Error during retrieval: {str(e)}")
            return []
# cosine similarity = 1 - cosine distance

# cosine distance range:  0 (identical) → 2 (opposite)
# cosine similarity range: 1 (identical) → -1 (opposite)


    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    
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

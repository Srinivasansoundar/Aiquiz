"""PDF ingestion service for loading, chunking, and storing documents in ChromaDB."""

import os
from typing import List
from pathlib import Path
import tempfile

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class PDFIngestionService:
    """Service for ingesting PDFs and storing them in ChromaDB."""
    
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
    
    def load_pdf(self, file_path: str) -> str:
        """Load and extract text from PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text from the PDF
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid PDF
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        print(f"📄 Loading PDF: {file_path}")
        
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            text = ""
            for doc in documents:
                text += f"\n{doc.page_content}\n"
            
            print(f"✅ Extracted text from {len(documents)} pages")
            return text
            
        except Exception as e:
            raise ValueError(f"Failed to read PDF: {str(e)}")
    
    def split_documents(self, text: str, chunk_size: int = 1000, 
                       chunk_overlap: int = 200) -> List[Document]:
        """Split text into chunks using RecursiveCharacterSplitter.
        
        Args:
            text: Text to split
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of Document objects with chunks
        """
        print("🔨 Splitting documents into chunks...")
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )
        
        chunks = splitter.split_text(text)
        print(f"✅ Created {len(chunks)} chunks")
        
        return chunks
    
    def create_documents(self, chunks: List[str], filename: str, 
                        metadata: dict = None) -> List[Document]:
        """Convert chunks into LangChain Document objects with metadata.
        
        Args:
            chunks: List of text chunks
            filename: Source filename for metadata
            metadata: Additional metadata to attach to documents
            
        Returns:
            List of Document objects
        """
        documents = []
        base_metadata = {"filename": filename}
        
        if metadata:
            base_metadata.update(metadata)
        
        for idx, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    **base_metadata,
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
        
        print(f"✅ Successfully stored documents in collection: {collection_name}")
        return vector_store
    
    def ingest_pdf(self, file_path: str, collection_name: str, 
                  chunk_size: int = 1000, chunk_overlap: int = 200,
                  metadata: dict = None) -> dict:
        """Complete ingestion pipeline: load, split, and store PDF.
        
        Args:
            file_path: Path to PDF file
            collection_name: Name for the ChromaDB collection
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            metadata: Additional metadata to attach
            
        Returns:
            Dictionary with ingestion results
        """
        print(f"\n🚀 Starting PDF ingestion pipeline...")
        print(f"📝 File: {file_path}")
        print(f"📚 Collection: {collection_name}\n")
        
        try:
            # Step 1: Load PDF
            text = self.load_pdf(file_path)
            
            # Step 2: Split into chunks
            chunks = self.split_documents(text, chunk_size, chunk_overlap)
            
            # Step 3: Create documents with metadata
            filename = Path(file_path).name
            documents = self.create_documents(chunks, filename, metadata)
            
            # Step 4: Store in ChromaDB
            vector_store = self.store_in_chromadb(documents, collection_name)
            
            result = {
                "success": True,
                "message": f"Successfully ingested PDF: {filename}",
                "collection_name": collection_name,
                
            }
            
            print(f"\n✨ PDF Ingestion Complete!")
            print(f"📊 Summary: {len(chunks)} chunks created from {filename}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error during ingestion: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path,
                "collection_name": collection_name,
            }


def ingest_pdf_from_upload(file_content: bytes, original_filename: str, 
                          collection_name: str, chunk_size: int = 1000,
                          chunk_overlap: int = 200) -> dict:
    """Convenient function to ingest PDF from file upload.
    
    Args:
        file_content: Bytes content of the PDF file
        original_filename: Original filename
        collection_name: ChromaDB collection name
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        Dictionary with ingestion results
    """
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name
    
    try:
        service = PDFIngestionService()
        result = service.ingest_pdf(
            file_path=tmp_path,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata={"original_filename": original_filename}
        )
        return result
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

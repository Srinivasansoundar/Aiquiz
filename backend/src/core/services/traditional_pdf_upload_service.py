"""Service for handling PDF uploads using traditional PDF ingestion."""

from typing import Optional
from src.core.services.ingestion import ingest_pdf_from_upload
import uuid


class TraditionalPDFUploadService:
    """Service for managing PDF uploads using traditional ingestion (PyPDFLoader + RecursiveCharacterTextSplitter)."""
    
    @staticmethod
    def upload_and_ingest(file_content: bytes, filename: str,
                         collection_name: Optional[str] = None,
                         chunk_size: int = 1000,
                         chunk_overlap: int = 200) -> dict:
        """Process uploaded PDF and ingest into ChromaDB using traditional method.
        
        Uses PyPDFLoader for PDF extraction and RecursiveCharacterTextSplitter
        for chunking without topic organization.
        
        Args:
            file_content: Binary content of the PDF file
            filename: Original filename of the PDF
            collection_name: Name for ChromaDB collection (auto-generated if None)
            chunk_size: Size of text chunks (default: 1000)
            chunk_overlap: Overlap between chunks (default: 200)
            
        Returns:
            Dictionary with ingestion results
        """
        # Auto-generate collection name if not provided
        if not collection_name:
            # Use filename without extension as collection name
            base_name = filename.rsplit('.', 1)[0]
            safe_name = base_name.replace(" ", "_").replace("-", "_").lower()
            # Replace spaces and special characters
            collection_name = f"{safe_name}_{uuid.uuid4().hex[:8]}"
        
        print(f"\n🎯 Processing PDF upload with traditional ingestion: {filename}")
        print(f"📚 Collection name: {collection_name}")
        
        try:
            result = ingest_pdf_from_upload(
                file_content=file_content,
                original_filename=filename,
                collection_name=collection_name,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to process PDF: {str(e)}",
                "filename": filename,
                "collection_name": collection_name,
            }
    
    @staticmethod
    def validate_pdf(filename: str) -> tuple[bool, str]:
        """Validate if file is a PDF.
        
        Args:
            filename: Name of the file to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not filename.lower().endswith('.pdf'):
            return False, "File must be a PDF"
        
        if len(filename) == 0:
            return False, "Filename cannot be empty"
        
        return True, "File is valid"

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from loguru import logger
from app.core.config import settings
from app.services.pdf_parser import pdf_parser


class RAGService:
    """
    Retrieval-Augmented Generation (RAG) Service
    Handles document ingestion and retrieval using ChromaDB
    """
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=settings.chroma_collection_name
            )
            logger.info(f"Loaded existing collection: {settings.chroma_collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "CV Evaluator reference documents"}
            )
            logger.info(f"Created new collection: {settings.chroma_collection_name}")
    
    def ingest_document(
        self,
        document_path: str,
        document_type: str,
        document_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> bool:
        """
        Ingest a document into the vector database
        
        Args:
            document_path: Path to the PDF document
            document_type: Type of document (job_description, case_study, cv_rubric, project_rubric)
            document_id: Unique identifier for the document
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract text from PDF
            text = pdf_parser.extract_text(document_path)
            
            # Split into chunks
            chunks = self._chunk_text(text, chunk_size, chunk_overlap)
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(chunks).tolist()
            
            # Prepare metadata
            metadatas = [
                {
                    "document_type": document_type,
                    "document_id": document_id,
                    "chunk_index": i,
                    "source": document_path
                }
                for i in range(len(chunks))
            ]
            
            # Generate IDs
            ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(
                f"Successfully ingested {len(chunks)} chunks from {document_path} "
                f"(type: {document_type})"
            )
            return True
        
        except Exception as e:
            logger.error(f"Error ingesting document {document_path}: {e}")
            return False
    
    def retrieve_context(
        self,
        query: str,
        document_types: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query
        
        Args:
            query: Search query
            document_types: List of document types to search in
            top_k: Number of top results to return
            
        Returns:
            List of relevant document chunks with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"document_type": {"$in": document_types}}
            )
            
            # Format results
            contexts = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    contexts.append({
                        "text": doc,
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })
            
            logger.info(
                f"Retrieved {len(contexts)} contexts for query: '{query[:50]}...' "
                f"from document types: {document_types}"
            )
            return contexts
        
        except Exception as e:
            logger.error(f"Error retrieving context for query '{query}': {e}")
            return []
    
    def retrieve_for_cv_evaluation(self, cv_text: str, job_title: str) -> str:
        """
        Retrieve relevant context for CV evaluation
        
        Args:
            cv_text: Extracted CV text
            job_title: Job title being evaluated for
            
        Returns:
            Formatted context string for LLM prompt
        """
        # Retrieve from job description and CV rubric
        query = f"{job_title} requirements and qualifications"
        contexts = self.retrieve_context(
            query=query,
            document_types=["job_description", "cv_rubric"],
            top_k=5
        )
        
        # Format context
        formatted_context = "# Reference Context for CV Evaluation\n\n"
        formatted_context += "## Job Requirements and Qualifications:\n"
        
        for ctx in contexts:
            if ctx['metadata']['document_type'] == 'job_description':
                formatted_context += f"{ctx['text']}\n\n"
        
        formatted_context += "\n## CV Evaluation Rubric:\n"
        for ctx in contexts:
            if ctx['metadata']['document_type'] == 'cv_rubric':
                formatted_context += f"{ctx['text']}\n\n"
        
        return formatted_context
    
    def retrieve_for_project_evaluation(self, project_text: str) -> str:
        """
        Retrieve relevant context for project evaluation
        
        Args:
            project_text: Extracted project report text
            
        Returns:
            Formatted context string for LLM prompt
        """
        # Retrieve from case study brief and project rubric
        query = "project requirements evaluation criteria"
        contexts = self.retrieve_context(
            query=query,
            document_types=["case_study", "project_rubric"],
            top_k=5
        )
        
        # Format context
        formatted_context = "# Reference Context for Project Evaluation\n\n"
        formatted_context += "## Case Study Requirements:\n"
        
        for ctx in contexts:
            if ctx['metadata']['document_type'] == 'case_study':
                formatted_context += f"{ctx['text']}\n\n"
        
        formatted_context += "\n## Project Evaluation Rubric:\n"
        for ctx in contexts:
            if ctx['metadata']['document_type'] == 'project_rubric':
                formatted_context += f"{ctx['text']}\n\n"
        
        return formatted_context
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between consecutive chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - chunk_overlap)
        
        return chunks
    
    def reset_collection(self):
        """Reset the collection (useful for re-ingestion)"""
        try:
            self.client.delete_collection(name=settings.chroma_collection_name)
            self.collection = self.client.create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "CV Evaluator reference documents"}
            )
            logger.info("Collection reset successfully")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")


# Global instance
rag_service = RAGService()
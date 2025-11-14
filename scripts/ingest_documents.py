#!/usr/bin/env python3
"""
Document Ingestion Script

This script ingests reference documents into the vector database for RAG:
- Job Description
- Case Study Brief
- CV Scoring Rubric
- Project Scoring Rubric
"""

import os
import sys
from pathlib import Path
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import rag_service
from app.core.config import settings


def ingest_documents():
    """Ingest all reference documents into the vector database"""
    
    logger.info("Starting document ingestion...")
    
    # Define documents to ingest
    documents = [
        {
            "path": "./data/reference_docs/job_description.pdf",
            "type": "job_description",
            "id": "job_desc_backend_engineer",
            "description": "Job Description for Backend Engineer"
        },
        {
            "path": "./data/reference_docs/case_study_brief.pdf",
            "type": "case_study",
            "id": "case_study_brief",
            "description": "Case Study Brief"
        },
        {
            "path": "./data/reference_docs/cv_rubric.pdf",
            "type": "cv_rubric",
            "id": "cv_scoring_rubric",
            "description": "CV Evaluation Rubric"
        },
        {
            "path": "./data/reference_docs/project_rubric.pdf",
            "type": "project_rubric",
            "id": "project_scoring_rubric",
            "description": "Project Evaluation Rubric"
        }
    ]
    
    # Track results
    successful = []
    failed = []
    
    for doc in documents:
        logger.info(f"Ingesting: {doc['description']} ({doc['path']})")
        
        # Check if file exists
        if not os.path.exists(doc['path']):
            logger.warning(f"File not found: {doc['path']} - Skipping")
            failed.append(doc)
            continue
        
        # Ingest document
        try:
            success = rag_service.ingest_document(
                document_path=doc['path'],
                document_type=doc['type'],
                document_id=doc['id']
            )
            
            if success:
                logger.info(f"✓ Successfully ingested: {doc['description']}")
                successful.append(doc)
            else:
                logger.error(f"✗ Failed to ingest: {doc['description']}")
                failed.append(doc)
        
        except Exception as e:
            logger.error(f"✗ Error ingesting {doc['description']}: {e}")
            failed.append(doc)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("INGESTION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total documents: {len(documents)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    
    if successful:
        logger.info("\nSuccessfully ingested:")
        for doc in successful:
            logger.info(f"  ✓ {doc['description']}")
    
    if failed:
        logger.warning("\nFailed to ingest:")
        for doc in failed:
            logger.warning(f"  ✗ {doc['description']}")
    
    logger.info("="*60)
    
    return len(failed) == 0


def reset_and_reingest():
    """Reset the vector database and reingest all documents"""
    logger.warning("Resetting vector database...")
    rag_service.reset_collection()
    logger.info("Vector database reset complete")
    
    return ingest_documents()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest reference documents into vector database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the vector database before ingesting"
    )
    
    args = parser.parse_args()
    
    try:
        if args.reset:
            success = reset_and_reingest()
        else:
            success = ingest_documents()
        
        if success:
            logger.info("✓ All documents ingested successfully")
            sys.exit(0)
        else:
            logger.error("✗ Some documents failed to ingest")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Fatal error during ingestion: {e}", exc_info=True)
        sys.exit(1)
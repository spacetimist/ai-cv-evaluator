from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid
import os
from datetime import datetime
from loguru import logger

from app.core.database import get_db, UploadedDocument, DocumentType
from app.core.config import settings
from app.models.schemas import UploadResponse, ErrorResponse

router = APIRouter()


def validate_file(file: UploadFile) -> bool:
    """
    Validate uploaded file
    
    Args:
        file: Uploaded file
        
    Returns:
        True if valid, raises HTTPException otherwise
    """
    # Check file extension
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )
    
    return True


async def save_upload_file(
    file: UploadFile,
    document_type: DocumentType
) -> tuple[str, str, int]:
    """
    Save uploaded file to disk
    
    Args:
        file: Uploaded file
        document_type: Type of document (CV or project_report)
        
    Returns:
        Tuple of (file_id, file_path, file_size)
    """
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    
    # Create filename with document type prefix
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{document_type.value}_{file_id}{file_extension}"
    file_path = os.path.join(settings.upload_dir, filename)
    
    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # Save file
    file_size = 0
    with open(file_path, "wb") as buffer:
        content = await file.read()
        file_size = len(content)
        
        # Check file size
        if file_size > settings.max_file_size:
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )
        
        buffer.write(content)
    
    logger.info(f"Saved {document_type.value} file: {file_path} ({file_size} bytes)")
    
    return file_id, file_path, file_size


@router.post(
    "/upload",
    response_model=dict,
    summary="Upload CV and Project Report",
    description="Upload candidate CV and project report (both PDF files)",
    responses={
        200: {"description": "Files uploaded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid file format or size"}
    }
)
async def upload_documents(
    cv: UploadFile = File(..., description="Candidate CV (PDF)"),
    project_report: UploadFile = File(..., description="Project Report (PDF)"),
    db: Session = Depends(get_db)
):
    """
    Upload CV and project report documents
    
    Args:
        cv: CV file upload
        project_report: Project report file upload
        db: Database session
        
    Returns:
        Dictionary with IDs and metadata for both uploaded files
    """
    try:
        # Validate files
        validate_file(cv)
        validate_file(project_report)
        
        # Save CV
        cv_id, cv_path, cv_size = await save_upload_file(cv, DocumentType.CV)
        cv_doc = UploadedDocument(
            id=cv_id,
            filename=cv.filename,
            file_path=cv_path,
            document_type=DocumentType.CV,
            uploaded_at=datetime.utcnow(),
            file_size=cv_size
        )
        db.add(cv_doc)
        
        # Save Project Report
        project_id, project_path, project_size = await save_upload_file(
            project_report,
            DocumentType.PROJECT_REPORT
        )
        project_doc = UploadedDocument(
            id=project_id,
            filename=project_report.filename,
            file_path=project_path,
            document_type=DocumentType.PROJECT_REPORT,
            uploaded_at=datetime.utcnow(),
            file_size=project_size
        )
        db.add(project_doc)
        
        # Commit to database
        db.commit()
        db.refresh(cv_doc)
        db.refresh(project_doc)
        
        logger.info(f"Successfully uploaded CV ({cv_id}) and project report ({project_id})")
        
        return {
            "cv": {
                "id": cv_doc.id,
                "filename": cv_doc.filename,
                "document_type": cv_doc.document_type.value,
                "uploaded_at": cv_doc.uploaded_at.isoformat(),
                "file_size": cv_doc.file_size
            },
            "project_report": {
                "id": project_doc.id,
                "filename": project_doc.filename,
                "document_type": project_doc.document_type.value,
                "uploaded_at": project_doc.uploaded_at.isoformat(),
                "file_size": project_doc.file_size
            }
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error uploading documents: {e}", exc_info=True)
        
        # Clean up files if error occurred
        if 'cv_path' in locals() and os.path.exists(cv_path):
            os.remove(cv_path)
        if 'project_path' in locals() and os.path.exists(project_path):
            os.remove(project_path)
        
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading documents: {str(e)}"
        )


@router.get(
    "/uploads/{document_id}",
    response_model=UploadResponse,
    summary="Get document information",
    description="Retrieve information about an uploaded document"
)
async def get_document_info(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Get information about an uploaded document
    
    Args:
        document_id: Document ID
        db: Database session
        
    Returns:
        Document information
    """
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == document_id
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID {document_id} not found"
        )
    
    return UploadResponse(
        id=doc.id,
        filename=doc.filename,
        document_type=doc.document_type.value,
        uploaded_at=doc.uploaded_at,
        file_size=doc.file_size
    )
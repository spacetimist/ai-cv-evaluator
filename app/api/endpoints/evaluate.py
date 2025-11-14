from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
from loguru import logger

from app.core.database import get_db, EvaluationJob, UploadedDocument, JobStatus
from app.models.schemas import EvaluationRequest, EvaluationQueuedResponse, ErrorResponse
from app.workers.celery_worker import evaluate_candidate_task

router = APIRouter()


@router.post(
    "/evaluate",
    response_model=EvaluationQueuedResponse,
    summary="Start evaluation",
    description="Trigger asynchronous evaluation of CV and project report",
    responses={
        200: {"description": "Evaluation queued successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Document not found"}
    }
)
async def start_evaluation(
    request: EvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    Start asynchronous evaluation of candidate CV and project report
    
    Args:
        request: Evaluation request with document IDs and job title
        db: Database session
        
    Returns:
        Job ID and status for tracking the evaluation
    """
    try:
        # Validate that documents exist
        cv_doc = db.query(UploadedDocument).filter(
            UploadedDocument.id == request.cv_id
        ).first()
        
        if not cv_doc:
            raise HTTPException(
                status_code=404,
                detail=f"CV document with ID {request.cv_id} not found"
            )
        
        project_doc = db.query(UploadedDocument).filter(
            UploadedDocument.id == request.project_report_id
        ).first()
        
        if not project_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Project report with ID {request.project_report_id} not found"
            )
        
        # Create evaluation job
        job_id = str(uuid.uuid4())
        
        job = EvaluationJob(
            id=job_id,
            cv_id=request.cv_id,
            project_report_id=request.project_report_id,
            job_title=request.job_title,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(
            f"Created evaluation job {job_id} for CV {request.cv_id} "
            f"and project {request.project_report_id}"
        )
        
        # Queue the evaluation task
        evaluate_candidate_task.apply_async(args=[job_id], task_id=job_id)
        
        logger.info(f"Queued evaluation task for job {job_id}")
        
        return EvaluationQueuedResponse(
            id=job_id,
            status=JobStatus.QUEUED,
            message="Evaluation queued successfully"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error starting evaluation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error starting evaluation: {str(e)}"
        )


@router.post(
    "/evaluate-sync",
    summary="Start evaluation (synchronous - for testing)",
    description="⚠️ For testing only: Synchronous evaluation that blocks until complete",
    deprecated=True
)
async def start_evaluation_sync(
    request: EvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    Synchronous version of evaluation (for testing purposes only)
    
    WARNING: This endpoint blocks until evaluation is complete.
    Use /evaluate for production.
    """
    try:
        # Create job
        job_id = str(uuid.uuid4())
        
        job = EvaluationJob(
            id=job_id,
            cv_id=request.cv_id,
            project_report_id=request.project_report_id,
            job_title=request.job_title,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        
        db.add(job)
        db.commit()
        
        logger.warning(f"Running SYNCHRONOUS evaluation for job {job_id} (testing only)")
        
        # Run task synchronously (blocking)
        result = evaluate_candidate_task(job_id)
        
        # Refresh job from database
        db.refresh(job)
        
        return {
            "id": job_id,
            "status": job.status.value,
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Error in synchronous evaluation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error in synchronous evaluation: {str(e)}"
        )


@router.delete(
    "/evaluate/{job_id}",
    summary="Cancel evaluation",
    description="Cancel a queued or processing evaluation job"
)
async def cancel_evaluation(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Cancel an evaluation job (if still queued)
    
    Args:
        job_id: Evaluation job ID
        db: Database session
        
    Returns:
        Cancellation confirmation
    """
    job = db.query(EvaluationJob).filter(EvaluationJob.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job with ID {job_id} not found"
        )
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status.value}"
        )
    
    # Update job status
    job.status = JobStatus.FAILED
    job.error_message = "Cancelled by user"
    job.completed_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Cancelled evaluation job {job_id}")
    
    return {
        "message": f"Job {job_id} cancelled successfully",
        "job_id": job_id,
        "status": "cancelled"
    }
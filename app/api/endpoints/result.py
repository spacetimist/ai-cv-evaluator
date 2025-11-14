from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json
from loguru import logger

from app.core.database import get_db, EvaluationJob, JobStatus
from app.models.schemas import (
    EvaluationResponse,
    EvaluationResult,
    CVDetailedScores,
    ProjectDetailedScores,
    ErrorResponse
)

router = APIRouter()


@router.get(
    "/result/{job_id}",
    response_model=EvaluationResponse,
    summary="Get evaluation result",
    description="Retrieve the status and result of an evaluation job",
    responses={
        200: {"description": "Evaluation status and result"},
        404: {"model": ErrorResponse, "description": "Job not found"}
    }
)
async def get_evaluation_result(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get evaluation job status and results
    
    Args:
        job_id: Evaluation job ID
        db: Database session
        
    Returns:
        Job status and evaluation results (if completed)
    """
    try:
        # Query job from database
        job = db.query(EvaluationJob).filter(EvaluationJob.id == job_id).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation job with ID {job_id} not found"
            )
        
        # Build response based on job status
        if job.status == JobStatus.QUEUED:
            return EvaluationResponse(
                id=job.id,
                status=JobStatus.QUEUED,
                result=None,
                created_at=job.created_at,
                completed_at=None
            )
        
        elif job.status == JobStatus.PROCESSING:
            return EvaluationResponse(
                id=job.id,
                status=JobStatus.PROCESSING,
                result=None,
                created_at=job.created_at,
                completed_at=None
            )
        
        elif job.status == JobStatus.FAILED:
            return EvaluationResponse(
                id=job.id,
                status=JobStatus.FAILED,
                result=None,
                error_message=job.error_message,
                created_at=job.created_at,
                completed_at=job.completed_at
            )
        
        elif job.status == JobStatus.COMPLETED:
            # Parse detailed scores if available
            cv_detailed = None
            if job.cv_detailed_scores:
                try:
                    cv_scores_dict = json.loads(job.cv_detailed_scores)
                    cv_detailed = CVDetailedScores(**cv_scores_dict)
                except Exception as e:
                    logger.warning(f"Could not parse CV detailed scores: {e}")
            
            project_detailed = None
            if job.project_detailed_scores:
                try:
                    project_scores_dict = json.loads(job.project_detailed_scores)
                    project_detailed = ProjectDetailedScores(**project_scores_dict)
                except Exception as e:
                    logger.warning(f"Could not parse project detailed scores: {e}")
            
            # Build result object
            result = EvaluationResult(
                cv_match_rate=job.cv_match_rate,
                cv_feedback=job.cv_feedback,
                project_score=job.project_score,
                project_feedback=job.project_feedback,
                overall_summary=job.overall_summary,
                cv_detailed_scores=cv_detailed,
                project_detailed_scores=project_detailed
            )
            
            return EvaluationResponse(
                id=job.id,
                status=JobStatus.COMPLETED,
                result=result,
                created_at=job.created_at,
                completed_at=job.completed_at
            )
        
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unknown job status: {job.status}"
            )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error retrieving evaluation result: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving evaluation result: {str(e)}"
        )


@router.get(
    "/results",
    summary="List all evaluation jobs",
    description="Get a list of all evaluation jobs with their current status"
)
async def list_evaluation_jobs(
    limit: int = 50,
    offset: int = 0,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    List all evaluation jobs
    
    Args:
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip
        status: Optional filter by status
        db: Database session
        
    Returns:
        List of evaluation jobs
    """
    try:
        query = db.query(EvaluationJob)
        
        # Filter by status if provided
        if status:
            try:
                status_enum = JobStatus(status.lower())
                query = query.filter(EvaluationJob.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: queued, processing, completed, failed"
                )
        
        # Order by created_at descending (newest first)
        query = query.order_by(EvaluationJob.created_at.desc())
        
        # Apply pagination
        total = query.count()
        jobs = query.offset(offset).limit(limit).all()
        
        # Format response
        job_list = []
        for job in jobs:
            job_info = {
                "id": job.id,
                "job_title": job.job_title,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            
            # Add results if completed
            if job.status == JobStatus.COMPLETED:
                job_info["cv_match_rate"] = job.cv_match_rate
                job_info["project_score"] = job.project_score
            
            job_list.append(job_info)
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "jobs": job_list
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error listing evaluation jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing evaluation jobs: {str(e)}"
        )


@router.get(
    "/stats",
    summary="Get evaluation statistics",
    description="Get statistics about evaluation jobs"
)
async def get_evaluation_stats(db: Session = Depends(get_db)):
    """
    Get statistics about evaluation jobs
    
    Args:
        db: Database session
        
    Returns:
        Statistics about jobs
    """
    try:
        total_jobs = db.query(EvaluationJob).count()
        queued_jobs = db.query(EvaluationJob).filter(
            EvaluationJob.status == JobStatus.QUEUED
        ).count()
        processing_jobs = db.query(EvaluationJob).filter(
            EvaluationJob.status == JobStatus.PROCESSING
        ).count()
        completed_jobs = db.query(EvaluationJob).filter(
            EvaluationJob.status == JobStatus.COMPLETED
        ).count()
        failed_jobs = db.query(EvaluationJob).filter(
            EvaluationJob.status == JobStatus.FAILED
        ).count()
        
        # Calculate average scores from completed jobs
        completed = db.query(EvaluationJob).filter(
            EvaluationJob.status == JobStatus.COMPLETED
        ).all()
        
        avg_cv_match = 0.0
        avg_project_score = 0.0
        
        if completed:
            avg_cv_match = sum(j.cv_match_rate for j in completed) / len(completed)
            avg_project_score = sum(j.project_score for j in completed) / len(completed)
        
        return {
            "total_jobs": total_jobs,
            "queued": queued_jobs,
            "processing": processing_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs,
            "average_cv_match_rate": round(avg_cv_match, 3),
            "average_project_score": round(avg_project_score, 2)
        }
    
    except Exception as e:
        logger.error(f"Error getting evaluation stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting evaluation stats: {str(e)}"
        )
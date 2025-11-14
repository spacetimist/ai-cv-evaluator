from celery import Celery
from loguru import logger
from datetime import datetime
import asyncio
import json

from app.core.config import settings
from app.core.database import SessionLocal, EvaluationJob, JobStatus, UploadedDocument
from app.services.evaluation_service import evaluation_service

# Initialize Celery
celery_app = Celery(
    'cv_evaluator',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.evaluation_timeout,
    task_soft_time_limit=settings.evaluation_timeout - 30,
)


@celery_app.task(bind=True, name='evaluate_candidate', max_retries=3)
def evaluate_candidate_task(self, job_id: str):
    """
    Celery task to evaluate candidate CV and project report
    
    Args:
        job_id: ID of the evaluation job
    """
    db = SessionLocal()
    
    try:
        # Get job from database
        job = db.query(EvaluationJob).filter(EvaluationJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Update status to processing
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Starting evaluation for job {job_id}")
        
        # Get uploaded documents
        cv_doc = db.query(UploadedDocument).filter(
            UploadedDocument.id == job.cv_id
        ).first()
        project_doc = db.query(UploadedDocument).filter(
            UploadedDocument.id == job.project_report_id
        ).first()
        
        if not cv_doc or not project_doc:
            raise ValueError("CV or project report document not found")
        
        # Run evaluation (async functions need event loop)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Step 1: Evaluate CV
            logger.info(f"Evaluating CV: {cv_doc.file_path}")
            cv_result = loop.run_until_complete(
                evaluation_service.evaluate_cv(
                    cv_path=cv_doc.file_path,
                    job_title=job.job_title
                )
            )
            
            # Step 2: Evaluate Project
            logger.info(f"Evaluating project: {project_doc.file_path}")
            project_result = loop.run_until_complete(
                evaluation_service.evaluate_project(
                    project_path=project_doc.file_path
                )
            )
            
            # Step 3: Generate overall summary
            logger.info("Generating overall summary")
            overall_summary = loop.run_until_complete(
                evaluation_service.synthesize_overall_summary(
                    cv_result=cv_result,
                    project_result=project_result,
                    job_title=job.job_title
                )
            )
            
        finally:
            loop.close()
        
        # Update job with results
        job.cv_match_rate = cv_result.match_rate
        job.cv_feedback = cv_result.feedback
        job.cv_detailed_scores = json.dumps(cv_result.detailed_scores.model_dump())
        
        job.project_score = project_result.score
        job.project_feedback = project_result.feedback
        job.project_detailed_scores = json.dumps(project_result.detailed_scores.model_dump())
        
        job.overall_summary = overall_summary
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.error_message = None
        
        db.commit()
        
        logger.info(f"Evaluation completed successfully for job {job_id}")
        return {
            "status": "completed",
            "job_id": job_id,
            "cv_match_rate": cv_result.match_rate,
            "project_score": project_result.score
        }
    
    except Exception as e:
        logger.error(f"Error evaluating job {job_id}: {e}", exc_info=True)
        
        # Update job with error
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.retry_count += 1
        db.commit()
        
        # Retry if under max attempts
        if job.retry_count < settings.retry_max_attempts:
            logger.info(f"Retrying job {job_id} (attempt {job.retry_count + 1})")
            raise self.retry(exc=e, countdown=2 ** job.retry_count)
        else:
            logger.error(f"Job {job_id} failed after {job.retry_count} retries")
            return {"status": "failed", "error": str(e)}
    
    finally:
        db.close()


@celery_app.task(name='health_check')
def health_check_task():
    """Simple health check task for Celery"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
import json
from typing import Dict, Any
from loguru import logger
from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.pdf_parser import pdf_parser
from app.models.schemas import (
    CVDetailedScores,
    ProjectDetailedScores,
    CVEvaluationResult,
    ProjectEvaluationResult
)


class EvaluationService:
    """
    Service for evaluating CVs and project reports using LLM chaining
    """
    
    def __init__(self):
        self.llm = llm_service
        self.rag = rag_service
        self.parser = pdf_parser
    
    async def evaluate_cv(
        self,
        cv_path: str,
        job_title: str
    ) -> CVEvaluationResult:
        """
        Evaluate CV against job requirements
        
        Args:
            cv_path: Path to CV PDF
            job_title: Job title to evaluate against
            
        Returns:
            CVEvaluationResult with scores and feedback
        """
        logger.info(f"Starting CV evaluation for job title: {job_title}")
        
        try:
            # Step 1: Parse CV
            parsed_cv = self.parser.parse_cv(cv_path)
            cv_text = parsed_cv['raw_text']
            
            # Step 2: Retrieve relevant context from RAG
            context = self.rag.retrieve_for_cv_evaluation(cv_text, job_title)
            
            # Step 3: Construct prompt for LLM
            prompt = self._build_cv_evaluation_prompt(cv_text, job_title, context)
            
            system_prompt = """You are an expert technical recruiter specializing in backend engineering and AI/ML roles. 
Your task is to evaluate candidate CVs objectively and provide structured feedback.
You must respond ONLY with valid JSON format, no additional text or markdown."""
            
            # Step 4: Generate evaluation
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # Step 5: Parse response
            result = self._parse_cv_evaluation_response(response)
            
            logger.info(f"CV evaluation completed. Match rate: {result.match_rate}")
            return result
        
        except Exception as e:
            logger.error(f"Error evaluating CV: {e}")
            raise
    
    async def evaluate_project(
        self,
        project_path: str
    ) -> ProjectEvaluationResult:
        """
        Evaluate project report against case study requirements
        
        Args:
            project_path: Path to project report PDF
            
        Returns:
            ProjectEvaluationResult with scores and feedback
        """
        logger.info("Starting project evaluation")
        
        try:
            # Step 1: Parse project report
            parsed_project = self.parser.parse_project_report(project_path)
            project_text = parsed_project['raw_text']
            
            # Step 2: Retrieve relevant context from RAG
            context = self.rag.retrieve_for_project_evaluation(project_text)
            
            # Step 3: Construct prompt for LLM
            prompt = self._build_project_evaluation_prompt(project_text, context)
            
            system_prompt = """You are an expert technical evaluator specializing in backend systems, AI/LLM integration, and RAG implementations.
Your task is to evaluate project implementations objectively against requirements and best practices.
You must respond ONLY with valid JSON format, no additional text or markdown."""
            
            # Step 4: Generate evaluation
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # Step 5: Parse response
            result = self._parse_project_evaluation_response(response)
            
            logger.info(f"Project evaluation completed. Score: {result.score}")
            return result
        
        except Exception as e:
            logger.error(f"Error evaluating project: {e}")
            raise
    
    async def synthesize_overall_summary(
        self,
        cv_result: CVEvaluationResult,
        project_result: ProjectEvaluationResult,
        job_title: str
    ) -> str:
        """
        Synthesize final overall summary from CV and project evaluations
        
        Args:
            cv_result: CV evaluation result
            project_result: Project evaluation result
            job_title: Job title
            
        Returns:
            Overall summary string (3-5 sentences)
        """
        logger.info("Synthesizing overall summary")
        
        try:
            prompt = f"""Based on the following evaluation results, provide a concise overall summary (3-5 sentences) about the candidate's fit for the {job_title} position.

CV Evaluation:
- Match Rate: {cv_result.match_rate}
- Feedback: {cv_result.feedback}

Project Evaluation:
- Score: {project_result.score}/5
- Feedback: {project_result.feedback}

Provide a balanced summary that:
1. Highlights the candidate's key strengths
2. Identifies any gaps or areas for improvement
3. Provides a clear recommendation

Respond with ONLY the summary text, no JSON or additional formatting."""
            
            system_prompt = """You are an expert hiring manager providing final recommendations on candidates.
Be concise, balanced, and actionable in your summary."""
            
            summary = await self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4
            )
            
            logger.info("Overall summary generated successfully")
            return summary.strip()
        
        except Exception as e:
            logger.error(f"Error synthesizing summary: {e}")
            raise
    
    def _build_cv_evaluation_prompt(
        self,
        cv_text: str,
        job_title: str,
        context: str
    ) -> str:
        """Build prompt for CV evaluation"""
        return f"""{context}

# CANDIDATE CV TO EVALUATE:
{cv_text}

# EVALUATION TASK:
Evaluate this CV for the position of "{job_title}" based on the job requirements and rubric provided above.

Score each parameter on a scale of 1-5:
1. Technical Skills Match (Weight: 40%)
2. Experience Level (Weight: 25%)
3. Relevant Achievements (Weight: 20%)
4. Cultural/Collaboration Fit (Weight: 15%)

Calculate the weighted average and convert to a match_rate (0-1 scale by multiplying by 0.2).

Respond with ONLY valid JSON in this exact format:
{{
    "technical_skills_match": <score 1-5>,
    "experience_level": <score 1-5>,
    "relevant_achievements": <score 1-5>,
    "cultural_fit": <score 1-5>,
    "match_rate": <decimal 0-1>,
    "feedback": "<2-3 sentences explaining strengths and gaps>"
}}

DO NOT include any text outside the JSON object."""
    
    def _build_project_evaluation_prompt(
        self,
        project_text: str,
        context: str
    ) -> str:
        """Build prompt for project evaluation"""
        return f"""{context}

# PROJECT REPORT TO EVALUATE:
{project_text}

# EVALUATION TASK:
Evaluate this project report based on the case study requirements and rubric provided above.

Score each parameter on a scale of 1-5:
1. Correctness (Prompt & Chaining) (Weight: 30%)
2. Code Quality & Structure (Weight: 25%)
3. Resilience & Error Handling (Weight: 20%)
4. Documentation & Explanation (Weight: 15%)
5. Creativity / Bonus (Weight: 10%)

Calculate the weighted average for the overall score (1-5 scale).

Respond with ONLY valid JSON in this exact format:
{{
    "correctness": <score 1-5>,
    "code_quality": <score 1-5>,
    "resilience": <score 1-5>,
    "documentation": <score 1-5>,
    "creativity": <score 1-5>,
    "overall_score": <decimal 1-5>,
    "feedback": "<2-3 sentences explaining what was done well and what needs improvement>"
}}

DO NOT include any text outside the JSON object."""
    
    def _parse_cv_evaluation_response(self, response: str) -> CVEvaluationResult:
        """Parse LLM response for CV evaluation"""
        try:
            # Extract JSON from response
            json_str = self.llm.extract_json_from_response(response)
            data = json.loads(json_str)
            
            detailed_scores = CVDetailedScores(
                technical_skills_match=float(data['technical_skills_match']),
                experience_level=float(data['experience_level']),
                relevant_achievements=float(data['relevant_achievements']),
                cultural_fit=float(data['cultural_fit'])
            )
            
            return CVEvaluationResult(
                match_rate=float(data['match_rate']),
                feedback=data['feedback'],
                detailed_scores=detailed_scores
            )
        
        except Exception as e:
            logger.error(f"Error parsing CV evaluation response: {e}")
            logger.error(f"Response was: {response}")
            raise ValueError(f"Failed to parse CV evaluation response: {e}")
    
    def _parse_project_evaluation_response(self, response: str) -> ProjectEvaluationResult:
        """Parse LLM response for project evaluation"""
        try:
            # Extract JSON from response
            json_str = self.llm.extract_json_from_response(response)
            data = json.loads(json_str)
            
            detailed_scores = ProjectDetailedScores(
                correctness=float(data['correctness']),
                code_quality=float(data['code_quality']),
                resilience=float(data['resilience']),
                documentation=float(data['documentation']),
                creativity=float(data['creativity'])
            )
            
            return ProjectEvaluationResult(
                score=float(data['overall_score']),
                feedback=data['feedback'],
                detailed_scores=detailed_scores
            )
        
        except Exception as e:
            logger.error(f"Error parsing project evaluation response: {e}")
            logger.error(f"Response was: {response}")
            raise ValueError(f"Failed to parse project evaluation response: {e}")


# Global instance
evaluation_service = EvaluationService()
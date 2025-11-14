import pdfplumber
from typing import Dict, Any
from loguru import logger
import re


class PDFParser:
    """Service for parsing PDF documents"""
    
    def __init__(self):
        pass
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extract raw text from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text as string
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            
            logger.info(f"Successfully extracted {len(text)} characters from {pdf_path}")
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            raise
    
    def parse_cv(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse CV PDF and extract structured information
        
        Args:
            pdf_path: Path to CV PDF file
            
        Returns:
            Dictionary containing raw text and structured data
        """
        try:
            raw_text = self.extract_text(pdf_path)
            
            # Basic section detection
            sections = self._detect_sections(raw_text)
            
            # Extract key information
            structured_data = {
                "has_experience_section": "experience" in raw_text.lower() or "work history" in raw_text.lower(),
                "has_education_section": "education" in raw_text.lower(),
                "has_skills_section": "skill" in raw_text.lower() or "technical" in raw_text.lower(),
                "has_projects_section": "project" in raw_text.lower(),
                "word_count": len(raw_text.split()),
                "sections_detected": list(sections.keys())
            }
            
            return {
                "raw_text": raw_text,
                "structured_data": structured_data,
                "sections": sections
            }
        
        except Exception as e:
            logger.error(f"Error parsing CV from {pdf_path}: {e}")
            raise
    
    def parse_project_report(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse project report PDF and extract structured information
        
        Args:
            pdf_path: Path to project report PDF file
            
        Returns:
            Dictionary containing raw text and structured data
        """
        try:
            raw_text = self.extract_text(pdf_path)
            
            # Basic section detection
            sections = self._detect_sections(raw_text)
            
            # Extract key information specific to project reports
            structured_data = {
                "has_approach_section": "approach" in raw_text.lower() or "design" in raw_text.lower(),
                "has_implementation_section": "implementation" in raw_text.lower() or "code" in raw_text.lower(),
                "has_results_section": "result" in raw_text.lower() or "outcome" in raw_text.lower(),
                "has_api_endpoints": "endpoint" in raw_text.lower() or "api" in raw_text.lower(),
                "has_llm_mention": "llm" in raw_text.lower() or "language model" in raw_text.lower(),
                "has_rag_mention": "rag" in raw_text.lower() or "retrieval" in raw_text.lower(),
                "word_count": len(raw_text.split()),
                "sections_detected": list(sections.keys())
            }
            
            return {
                "raw_text": raw_text,
                "structured_data": structured_data,
                "sections": sections
            }
        
        except Exception as e:
            logger.error(f"Error parsing project report from {pdf_path}: {e}")
            raise
    
    def _detect_sections(self, text: str) -> Dict[str, str]:
        """
        Detect common sections in a document
        
        Args:
            text: Document text
            
        Returns:
            Dictionary mapping section names to their content
        """
        sections = {}
        
        # Common section headers (case-insensitive)
        section_patterns = [
            r"(?i)(experience|work experience|work history)",
            r"(?i)(education|academic background)",
            r"(?i)(skills|technical skills|competencies)",
            r"(?i)(projects|project experience)",
            r"(?i)(achievements|accomplishments)",
            r"(?i)(summary|profile|objective)",
            r"(?i)(approach|design|methodology)",
            r"(?i)(implementation|development)",
            r"(?i)(results|outcomes|findings)",
            r"(?i)(api|endpoints|interface)",
        ]
        
        # Simple section detection (can be improved)
        lines = text.split('\n')
        current_section = "introduction"
        sections[current_section] = ""
        
        for line in lines:
            # Check if line is a section header
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip()) and len(line.strip()) < 50:
                    current_section = line.strip().lower()
                    sections[current_section] = ""
                    is_header = True
                    break
            
            if not is_header:
                sections[current_section] += line + "\n"
        
        return sections


# Global instance
pdf_parser = PDFParser()
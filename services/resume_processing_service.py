# services/resume_processing_service.py
import os
import json
import threading
import logging
from typing import Dict, Any, Optional, Tuple
from config.firebase_config import firebase_config
from models.resume_model import ResumeModel
from utils.file_utils import get_file_size, calculate_file_hash
import time

logger = logging.getLogger(__name__)

class ResumeProcessingService:
    """Service for handling resume processing operations"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        self.resume_model = ResumeModel(self.db)
        self._processing_threads = {}
    
    def start_resume_processing(self, user_id: str, file_path: str, filename: str, job_description: str = "") -> Tuple[str, bool]:
        """
        Start asynchronous resume processing
        
        Returns:
            Tuple of (resume_id, success)
        """
        try:
            # Create initial resume record with processing status
            resume_data = {
                'filename': filename,
                'file_path': file_path,
                'file_size': get_file_size(file_path),
                'file_hash': calculate_file_hash(file_path),
                'job_description': job_description
            }
            
            resume_id = self.resume_model.create_resume_record_processing(user_id, resume_data)
            
            # Start processing in background thread
            processing_thread = threading.Thread(
                target=self._process_resume_async,
                args=(resume_id, file_path, job_description),
                daemon=True
            )
            processing_thread.start()
            
            # Track the thread
            self._processing_threads[resume_id] = processing_thread
            
            logger.info(f"Started resume processing for resume_id: {resume_id}")
            return resume_id, True
            
        except Exception as e:
            logger.error(f"Error starting resume processing: {e}")
            return "", False
    
    def _process_resume_async(self, resume_id: str, file_path: str, job_description: str):
        """Process resume asynchronously"""
        try:
            logger.info(f"Starting async processing for resume: {resume_id}")
            
            # Update status to processing
            self.resume_model.update_resume_status(resume_id, 'processing')
            
            # Import and use the actual resume processing functions
            from services.resume_extractor_cl import process_resume_file
            
            # Process the resume using the actual implementation
            extracted_data, questions, analysis = process_resume_file(file_path, job_description)
            
            # Check if processing was successful
            if isinstance(extracted_data, dict) and 'error' in extracted_data:
                # Handle processing error
                error_message = extracted_data.get('error', 'Unknown processing error')
                self.resume_model.update_resume_status(resume_id, 'failed', error_message)
                logger.error(f"Resume processing failed for {resume_id}: {error_message}")
                return
            
            # Check if it's not a resume
            if isinstance(extracted_data, dict) and not extracted_data.get('is_resume', True):
                error_message = f"Document verification failed: {extracted_data.get('reason', 'Not a resume')}"
                self.resume_model.update_resume_status(resume_id, 'failed', error_message)
                logger.warning(f"Document is not a resume for {resume_id}: {error_message}")
                return
            
            # Prepare complete resume data for Firebase
            complete_data = {}
            
            # Update with extracted data
            if extracted_data:
                complete_data['extracted_data'] = extracted_data
            
            # Update with interview questions
            if questions:
                complete_data['interview_questions'] = questions
            
            # Update with job match analysis
            if analysis:
                complete_data['job_match_analysis'] = analysis
            
            # Update Firebase with all processed data
            self.resume_model.update_resume_with_processed_data(resume_id, complete_data)
            
            # Mark as completed
            self.resume_model.update_resume_status(resume_id, 'completed')
            
            logger.info(f"Resume processing completed successfully for: {resume_id}")
            
        except Exception as e:
            logger.error(f"Error in async resume processing: {e}")
            self.resume_model.update_resume_status(resume_id, 'failed', str(e))
        
        finally:
            # Clean up thread tracking
            if resume_id in self._processing_threads:
                del self._processing_threads[resume_id]
    
    def get_processing_status(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Get processing status of a resume"""
        try:
            resume_data = self.resume_model.get_resume_by_id(resume_id)
            if not resume_data:
                return None
            
            return {
                'resume_id': resume_id,
                'status': resume_data.get('processing_status', 'unknown'),
                'created_at': resume_data.get('created_at'),
                'processed_at': resume_data.get('processed_at'),
                'error_message': resume_data.get('error_message'),
                'filename': resume_data.get('filename', '')
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            return None
    
    def get_resume_results(self, resume_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete resume processing results"""
        try:
            resume_data = self.resume_model.get_resume_by_id(resume_id)
            if not resume_data or resume_data.get('user_id') != user_id:
                return None
            
            if resume_data.get('processing_status') != 'completed':
                return {
                    'status': resume_data.get('processing_status', 'unknown'),
                    'message': 'Resume processing not completed yet'
                }
            
            return {
                'status': 'completed',
                'extracted_data': resume_data.get('extracted_data'),
                'interview_questions': resume_data.get('interview_questions'),
                'job_match_analysis': resume_data.get('job_match_analysis'),
                'filename': resume_data.get('filename', ''),
                'processed_at': resume_data.get('processed_at')
            }
            
        except Exception as e:
            logger.error(f"Error getting resume results: {e}")
            return None

# Global service instance
resume_service = ResumeProcessingService()
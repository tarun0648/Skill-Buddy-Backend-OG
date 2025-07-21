# services/resume_processing_service.py
import os
import json
import threading
import logging
from typing import Dict, Any, Optional, Tuple
from config.firebase_config import firebase_config
from models.resume_model import ResumeModel
from utils.file_utils import get_file_size, calculate_file_hash
from services.task_manager import task_manager
import time

logger = logging.getLogger(__name__)

class ResumeProcessingService:
    """Service for handling resume processing operations with enhanced parallel processing"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        self.resume_model = ResumeModel(self.db)
    
    def update_user_resume_status(self, user_id: str, has_resume: bool):
        """Update user's resume status and recalculate profile completion"""
        try:
            from models.user_model import UserModel
            user_model = UserModel(self.db)
            user_model.update_resume_status(user_id, has_resume)
            logger.info(f"Updated resume status for user {user_id}: {has_resume}")
        except Exception as e:
            logger.error(f"Error updating user resume status: {e}")
    
    def start_resume_processing(self, user_id: str, file_path: str, filename: str, job_description: str = "") -> Tuple[str, bool]:
        """
        Start asynchronous resume processing using task manager
        
        Returns:
            Tuple of (task_id, success)
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
            
            # Create resume record in database
            resume_id = self.resume_model.create_resume_record_processing(user_id, resume_data)
            
            # Prepare task data
            task_data = {
                'resume_id': resume_id,
                'filename': filename,
                'file_path': file_path,
                'job_description': job_description,
                'file_size': resume_data['file_size']
            }
            
            # Start task using task manager
            task_id = task_manager.start_task(
                task_type='resume',
                user_id=user_id,
                task_data=task_data,
                processing_func=self._process_resume_task,
                resume_id=resume_id,
                file_path=file_path,
                job_description=job_description
            )
            
            if not task_id:
                # Clean up resume record if task failed to start
                self.resume_model.delete_resume(resume_id)
                return "", False
            
            logger.info(f"Started resume processing for user {user_id}, task_id: {task_id}, resume_id: {resume_id}")
            return task_id, True
            
        except Exception as e:
            logger.error(f"Error starting resume processing: {e}")
            return "", False
    
    def _process_resume_task(self, task_id: str, user_id: str, resume_id: str, file_path: str, job_description: str) -> Dict[str, Any]:
        """Process resume asynchronously - called by task manager"""
        try:
            logger.info(f"Starting resume processing task {task_id} for resume {resume_id}")
            
            # Update resume status to processing
            self.resume_model.update_resume_status(resume_id, 'processing')
            
            # Check if file exists
            if not os.path.exists(file_path):
                error_message = f"Resume file not found: {file_path}"
                self.resume_model.update_resume_status(resume_id, 'failed', error_message)
                logger.error(f"Resume file not found: {file_path}")
                self._update_user_resume_status_after_processing(user_id)
                return {'status': 'failed', 'error': error_message}
            
            # Import and use the actual resume processing functions
            from services.resume_extractor_cl import process_resume_file
            
            # Process the resume using the actual implementation
            extracted_data, questions, analysis = process_resume_file(file_path, job_description)
            
            # Check if processing was successful
            if isinstance(extracted_data, dict) and 'error' in extracted_data:
                # Handle processing error
                error_message = extracted_data.get('error', 'Unknown processing error')
                
                # Provide more specific error messages for common issues
                if "No text could be extracted" in error_message:
                    error_message = "Unable to extract text from the PDF. This could be due to:\n" \
                                  "• The PDF is password-protected\n" \
                                  "• The PDF contains only images (scanned document)\n" \
                                  "• The PDF is corrupted\n" \
                                  "• The PDF uses non-standard text encoding\n\n" \
                                  "Please try uploading a different PDF or ensure the document contains selectable text."
                elif "PDF extraction failed" in error_message:
                    error_message = "PDF processing failed. Please ensure the file is a valid PDF and try again."
                elif "Claude API call failed" in error_message:
                    error_message = "AI processing service temporarily unavailable. Please try again later."
                
                self.resume_model.update_resume_status(resume_id, 'failed', error_message)
                logger.error(f"Resume processing failed for {resume_id}: {error_message}")
                
                # Update user's resume status - check if they have other completed resumes
                self._update_user_resume_status_after_processing(user_id)
                return {'status': 'failed', 'error': error_message}
            
            # Check if it's not a resume
            if isinstance(extracted_data, dict) and not extracted_data.get('is_resume', True):
                confidence = extracted_data.get('confidence', 0)
                reason = extracted_data.get('reason', 'Document verification failed')
                
                if confidence > 70:
                    error_message = f"Document verification failed: {reason}. Please upload a valid resume/CV."
                else:
                    error_message = f"Document may not be a resume: {reason}. Please ensure you're uploading a resume or CV."
                
                self.resume_model.update_resume_status(resume_id, 'failed', error_message)
                logger.warning(f"Document is not a resume for {resume_id}: {error_message}")
                
                # Update user's resume status - check if they have other completed resumes
                self._update_user_resume_status_after_processing(user_id)
                return {'status': 'failed', 'error': error_message}
            
            # Validate extracted data
            if not extracted_data or not isinstance(extracted_data, dict):
                error_message = "Failed to extract resume data. Please try uploading a different resume."
                self.resume_model.update_resume_status(resume_id, 'failed', error_message)
                logger.error(f"Invalid extracted data for {resume_id}")
                self._update_user_resume_status_after_processing(user_id)
                return {'status': 'failed', 'error': error_message}
            
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
            
            # Update user's resume status to true since we have a completed resume
            self.update_user_resume_status(user_id, True)
            
            logger.info(f"Resume processing completed successfully for: {resume_id}")
            
            return {
                'status': 'completed',
                'resume_id': resume_id,
                'extracted_data': extracted_data,
                'questions': questions,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error in resume processing task: {e}")
            error_message = f"Unexpected error during processing: {str(e)}"
            self.resume_model.update_resume_status(resume_id, 'failed', error_message)
            
            # Update user's resume status - check if they have other completed resumes
            self._update_user_resume_status_after_processing(user_id)
            
            return {'status': 'failed', 'error': error_message}
    
    def _update_user_resume_status_after_processing(self, user_id: str):
        """Update user's resume status by checking if they have any completed resumes"""
        try:
            user_resumes = self.resume_model.get_user_resumes(user_id)
            has_completed_resumes = any(r.get('processing_status') == 'completed' for r in user_resumes)
            self.update_user_resume_status(user_id, has_completed_resumes)
        except Exception as e:
            logger.error(f"Error updating user resume status after processing: {e}")
    
    def get_processing_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get processing status of user's latest resume task"""
        try:
            # Get latest resume task for user
            latest_task = task_manager.get_latest_task(user_id, 'resume')
            
            if not latest_task:
                return None
            
            task_id = latest_task['id']
            status_data = task_manager.get_task_status(task_id)
            
            if not status_data:
                return None
            
            # Get resume details
            resume_id = latest_task.get('task_data', {}).get('resume_id')
            resume_data = None
            if resume_id:
                resume_data = self.resume_model.get_resume_by_id(resume_id)
            
            return {
                'task_id': task_id,
                'resume_id': resume_id,
                'status': status_data.get('status'),
                'progress': status_data.get('progress', 0),
                'created_at': status_data.get('created_at'),
                'started_at': status_data.get('started_at'),
                'completed_at': status_data.get('completed_at'),
                'error_message': status_data.get('error_message'),
                'filename': latest_task.get('task_data', {}).get('filename', ''),
                'is_active': status_data.get('is_active', False)
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            return None
    
    def get_resume_results(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete resume processing results for user's latest resume"""
        try:
            # Get latest resume task for user
            latest_task = task_manager.get_latest_task(user_id, 'resume')
            
            if not latest_task:
                return None
            
            task_id = latest_task['id']
            resume_id = latest_task.get('task_data', {}).get('resume_id')
            
            if not resume_id:
                return None
            
            # Check if task is completed
            if latest_task.get('status') != 'completed':
                return {
                    'status': latest_task.get('status', 'unknown'),
                    'progress': latest_task.get('progress', 0),
                    'message': 'Resume processing not completed yet'
                }
            
            # Get resume data
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
                'task_id': task_id,
                'resume_id': resume_id,
                'extracted_data': resume_data.get('extracted_data'),
                'interview_questions': resume_data.get('interview_questions'),
                'job_match_analysis': resume_data.get('job_match_analysis'),
                'filename': resume_data.get('filename', ''),
                'processed_at': resume_data.get('processed_at')
            }
            
        except Exception as e:
            logger.error(f"Error getting resume results: {e}")
            return None
    
    def get_user_resumes(self, user_id: str) -> list:
        """Get all resumes for a user with task status"""
        try:
            # Get resume records
            resumes = self.resume_model.get_user_resumes(user_id)
            
            # Get task information for each resume
            tasks = task_manager.get_user_tasks(user_id, 'resume')
            task_map = {task.get('task_data', {}).get('resume_id'): task for task in tasks}
            
            # Combine resume data with task status
            for resume in resumes:
                resume_id = resume.get('id')
                if resume_id in task_map:
                    task = task_map[resume_id]
                    resume['task_id'] = task.get('id')
                    resume['task_status'] = task.get('status')
                    resume['task_progress'] = task.get('progress', 0)
                    resume['task_created_at'] = task.get('created_at')
                else:
                    resume['task_id'] = None
                    resume['task_status'] = 'unknown'
                    resume['task_progress'] = 0
            
            return resumes
            
        except Exception as e:
            logger.error(f"Error getting user resumes: {e}")
            return []

# Global service instance
resume_service = ResumeProcessingService()
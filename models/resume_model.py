# models/resume_model.py
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class ResumeModel:
    """Resume data model for Firestore operations"""
    
    def __init__(self, db):
        self.db = db
        self.collection_name = 'resumes'
    
    def create_resume_record_processing(self, user_id: str, resume_data: Dict[str, Any]) -> str:
        """Create a new resume record in processing state"""
        try:
            resume_doc = {
                'user_id': user_id,
                'filename': resume_data.get('filename', ''),
                'file_path': resume_data.get('file_path', ''),
                'file_size': resume_data.get('file_size', 0),
                'file_hash': resume_data.get('file_hash', ''),
                'job_description': resume_data.get('job_description', ''),
                'processing_status': 'pending',
                'extracted_data': None,
                'interview_questions': None,
                'job_match_analysis': None,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'processed_at': None,
                'error_message': None
            }
            
            doc_ref = self.db.collection(self.collection_name).add(resume_doc)
            resume_id = doc_ref[1].id
            
            logger.info(f"Created resume record: {resume_id} for user: {user_id}")
            return resume_id
            
        except Exception as e:
            logger.error(f"Error creating resume record: {e}")
            raise Exception(f"Failed to create resume record: {str(e)}")
    
    def update_resume_status(self, resume_id: str, status: str, error_message: str = None):
        """Update resume processing status"""
        try:
            update_data = {
                'processing_status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if status == 'completed':
                update_data['processed_at'] = firestore.SERVER_TIMESTAMP
            
            if error_message:
                update_data['error_message'] = error_message
            
            doc_ref = self.db.collection(self.collection_name).document(resume_id)
            doc_ref.update(update_data)
            
            logger.info(f"Updated resume status: {resume_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Error updating resume status: {e}")
    
    def update_resume_with_processed_data(self, resume_id: str, processed_data: Dict[str, Any]):
        """Update resume with processed data"""
        try:
            update_data = {
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if 'extracted_data' in processed_data:
                update_data['extracted_data'] = processed_data['extracted_data']
            
            if 'interview_questions' in processed_data:
                update_data['interview_questions'] = processed_data['interview_questions']
            
            if 'job_match_analysis' in processed_data:
                update_data['job_match_analysis'] = processed_data['job_match_analysis']
            
            doc_ref = self.db.collection(self.collection_name).document(resume_id)
            doc_ref.update(update_data)
            
            logger.info(f"Updated resume with processed data: {resume_id}")
            
        except Exception as e:
            logger.error(f"Error updating resume with processed data: {e}")
    
    def get_resume_by_id(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Get resume by ID"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(resume_id)
            doc = doc_ref.get()
            
            if doc.exists:
                resume_data = doc.to_dict()
                resume_data['id'] = resume_id
                
                # Convert Firebase timestamps to ISO strings
                for field in ['created_at', 'updated_at', 'processed_at']:
                    if resume_data.get(field):
                        resume_data[field] = resume_data[field].isoformat() if hasattr(resume_data[field], 'isoformat') else str(resume_data[field])
                
                return resume_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting resume by ID: {e}")
            return None
    
    def get_user_resumes(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all resumes for a user"""
        try:
            query = self.db.collection(self.collection_name)\
                .where('user_id', '==', user_id)\
                .order_by('created_at', direction=firestore.Query.DESCENDING)
            
            docs = query.get()
            resumes = []
            
            for doc in docs:
                resume_data = doc.to_dict()
                resume_data['id'] = doc.id
                
                # Convert Firebase timestamps
                for field in ['created_at', 'updated_at', 'processed_at']:
                    if resume_data.get(field):
                        resume_data[field] = resume_data[field].isoformat() if hasattr(resume_data[field], 'isoformat') else str(resume_data[field])
                
                resumes.append(resume_data)
            
            return resumes
            
        except Exception as e:
            logger.error(f"Error getting user resumes: {e}")
            return []
    
    def get_user_resume_summary(self, user_id: str) -> List[Dict[str, Any]]:
        """Get resume summary for a user (optimized for listing)"""
        try:
            query = self.db.collection(self.collection_name)\
                .where('user_id', '==', user_id)\
                .order_by('created_at', direction=firestore.Query.DESCENDING)
            
            docs = query.get()
            resumes = []
            
            for doc in docs:
                resume_data = doc.to_dict()
                
                # Create summary with only essential fields
                resume_summary = {
                    'id': doc.id,
                    'filename': resume_data.get('filename', ''),
                    'status': resume_data.get('processing_status', 'unknown'),
                    'created_at': resume_data.get('created_at'),
                    'processed_at': resume_data.get('processed_at'),
                    'error_message': resume_data.get('error_message'),
                    'file_size': resume_data.get('file_size', 0),
                    'file_size_mb': round(resume_data.get('file_size', 0) / (1024 * 1024), 2),
                    'has_questions': bool(resume_data.get('interview_questions')),
                    'has_analysis': bool(resume_data.get('job_match_analysis')),
                    'match_score': resume_data.get('job_match_analysis', {}).get('match_score', 0) if resume_data.get('job_match_analysis') else 0,
                    'match_label': resume_data.get('job_match_analysis', {}).get('match_label', 'Not Analyzed') if resume_data.get('job_match_analysis') else 'Not Analyzed',
                    'questions_count': len(resume_data.get('interview_questions', [])) if resume_data.get('interview_questions') else 0,
                    'extracted_name': resume_data.get('extracted_data', {}).get('personal_information', {}).get('name', 'N/A') if resume_data.get('extracted_data') else 'N/A',
                    'skills_count': len(resume_data.get('extracted_data', {}).get('skills', [])) if resume_data.get('extracted_data') else 0
                }
                
                # Convert Firebase timestamps to ISO strings
                for field in ['created_at', 'processed_at']:
                    if resume_summary.get(field):
                        if hasattr(resume_summary[field], 'isoformat'):
                            resume_summary[field] = resume_summary[field].isoformat()
                        else:
                            resume_summary[field] = str(resume_summary[field])
                
                resumes.append(resume_summary)
            
            return resumes
            
        except Exception as e:
            logger.error(f"Error getting user resume summary: {e}")
            return []
    
    def get_user_resume_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get resume statistics for a user"""
        try:
            query = self.db.collection(self.collection_name).where('user_id', '==', user_id)
            docs = query.get()
            
            total_resumes = len(docs)
            completed_resumes = 0
            processing_resumes = 0
            failed_resumes = 0
            pending_resumes = 0
            total_size = 0
            
            for doc in docs:
                resume_data = doc.to_dict()
                status = resume_data.get('processing_status', 'unknown')
                
                if status == 'completed':
                    completed_resumes += 1
                elif status == 'processing':
                    processing_resumes += 1
                elif status == 'failed':
                    failed_resumes += 1
                elif status == 'pending':
                    pending_resumes += 1
                
                total_size += resume_data.get('file_size', 0)
            
            return {
                'total_resumes': total_resumes,
                'completed': completed_resumes,
                'processing': processing_resumes,
                'pending': pending_resumes,
                'failed': failed_resumes,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'success_rate': round((completed_resumes / total_resumes * 100), 1) if total_resumes > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user resume statistics: {e}")
            return {
                'total_resumes': 0,
                'completed': 0,
                'processing': 0,
                'pending': 0,
                'failed': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'success_rate': 0
            }
    
    def delete_resume(self, resume_id: str) -> bool:
        """Delete resume record"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(resume_id)
            doc_ref.delete()
            
            logger.info(f"Deleted resume: {resume_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting resume: {e}")
            return False
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get resume processing statistics"""
        try:
            all_docs = self.db.collection(self.collection_name).get()
            total_resumes = len(all_docs)
            
            completed_resumes = len(self.db.collection(self.collection_name)
                                   .where('processing_status', '==', 'completed').get())
            processing_resumes = len(self.db.collection(self.collection_name)
                                   .where('processing_status', '==', 'processing').get())
            pending_resumes = len(self.db.collection(self.collection_name)
                                .where('processing_status', '==', 'pending').get())
            
            failed_resumes = total_resumes - completed_resumes - processing_resumes - pending_resumes
            
            return {
                'total_resumes': total_resumes,
                'completed': completed_resumes,
                'processing': processing_resumes,
                'pending': pending_resumes,
                'failed': failed_resumes,
                'success_rate': (completed_resumes / total_resumes * 100) if total_resumes > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting processing statistics: {e}")
            return {'total_resumes': 0, 'completed': 0, 'processing': 0, 'pending': 0, 'failed': 0, 'success_rate': 0}
# models/profile_analysis_model.py (FIXED)
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import json
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class ProfileAnalysisModel:
    """Profile analysis data model for Firestore operations"""
    
    def __init__(self, db):
        self.db = db
        self.collection_name = 'profile_analyses'
    
    def _sanitize_for_firestore(self, data: Any) -> Any:
        """Sanitize data to be compatible with Firestore"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Convert any problematic keys
                safe_key = str(key).replace('.', '_').replace('/', '_')
                sanitized[safe_key] = self._sanitize_for_firestore(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_for_firestore(item) for item in data]
        elif isinstance(data, (int, float, str, bool)) or data is None:
            return data
        else:
            # Convert complex objects to strings
            return str(data)
    
    def _flatten_complex_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten complex nested data for Firestore storage"""
        flattened = {}
        
        def flatten_dict(d: Dict[str, Any], prefix: str = ''):
            for key, value in d.items():
                new_key = f"{prefix}_{key}" if prefix else key
                
                if isinstance(value, dict) and len(str(value)) < 1000:  # Keep small dicts
                    flattened[new_key] = self._sanitize_for_firestore(value)
                elif isinstance(value, dict):  # Flatten large dicts
                    flatten_dict(value, new_key)
                elif isinstance(value, list) and len(str(value)) < 1000:  # Keep small lists
                    flattened[new_key] = self._sanitize_for_firestore(value)
                elif isinstance(value, list):  # Convert large lists to JSON string
                    flattened[f"{new_key}_json"] = json.dumps(value)
                else:
                    flattened[new_key] = self._sanitize_for_firestore(value)
        
        flatten_dict(data)
        return flattened
    
    def create_analysis_record(self, user_id: str, analysis_data: Dict[str, Any]) -> str:
        """Create a new profile analysis record"""
        try:
            analysis_doc = {
                'user_id': user_id,
                'analysis_type': analysis_data.get('analysis_type'),  # 'linkedin' or 'github'
                'profile_url': analysis_data.get('profile_url'),  # LinkedIn URL
                'github_username': analysis_data.get('github_username'),  # GitHub username
                'status': 'pending',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'processed_at': None,
                'error_message': None,
                'grade': None,
                # Store user profile context as sanitized data
                'user_profile_context': self._sanitize_for_firestore(analysis_data.get('user_profile_context', {}))
            }
            
            doc_ref = self.db.collection(self.collection_name).add(analysis_doc)
            analysis_id = doc_ref[1].id
            
            logger.info(f"Created profile analysis record: {analysis_id} for user: {user_id}")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Error creating profile analysis record: {e}")
            raise Exception(f"Failed to create analysis record: {str(e)}")
    
    def update_analysis_status(self, analysis_id: str, status: str, error_message: str = None):
        """Update analysis status"""
        try:
            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if status == 'completed':
                update_data['processed_at'] = firestore.SERVER_TIMESTAMP
            
            if error_message:
                update_data['error_message'] = str(error_message)[:1000]  # Limit error message length
            
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc_ref.update(update_data)
            
            logger.info(f"Updated analysis status: {analysis_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Error updating analysis status: {e}")
    
    def update_analysis_with_results(self, analysis_id: str, results_data: Dict[str, Any]):
        """Update analysis with processed results - FIXED for Firestore compatibility"""
        try:
            update_data = {
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Handle analysis_results with flattening
            if 'analysis_results' in results_data:
                analysis_results = results_data['analysis_results']
                flattened_results = self._flatten_complex_data(analysis_results)
                
                # Store flattened results
                for key, value in flattened_results.items():
                    update_data[f"analysis_{key}"] = value
                
                # Also store a JSON version for complete data retrieval
                update_data['analysis_results_json'] = json.dumps(analysis_results)
            
            # Handle suggestions with flattening
            if 'suggestions' in results_data:
                suggestions = results_data['suggestions']
                flattened_suggestions = self._flatten_complex_data(suggestions)
                
                # Store flattened suggestions
                for key, value in flattened_suggestions.items():
                    update_data[f"suggestion_{key}"] = value
                
                # Also store a JSON version
                update_data['suggestions_json'] = json.dumps(suggestions)
            
            # Handle grade
            if 'grade' in results_data:
                update_data['grade'] = int(results_data['grade'])
            
            # Handle GitHub stats separately
            if 'github_stats' in results_data:
                github_stats = results_data['github_stats']
                sanitized_stats = self._sanitize_for_firestore(github_stats)
                update_data['github_stats'] = sanitized_stats
            
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc_ref.update(update_data)
            
            logger.info(f"Updated analysis with results: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error updating analysis with results: {e}")
            # Try a simpler update with just the grade
            try:
                simple_update = {
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'status': 'completed',
                    'grade': results_data.get('grade', 0),
                    'has_results': True
                }
                doc_ref = self.db.collection(self.collection_name).document(analysis_id)
                doc_ref.update(simple_update)
                logger.info(f"Applied simplified update for analysis: {analysis_id}")
            except Exception as e2:
                logger.error(f"Failed simplified update: {e2}")
    
    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis by ID - FIXED to reconstruct complex data"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc = doc_ref.get()
            
            if doc.exists:
                analysis_data = doc.to_dict()
                analysis_data['id'] = analysis_id
                
                # Reconstruct complex data from JSON if available
                if 'analysis_results_json' in analysis_data:
                    try:
                        analysis_data['analysis_results'] = json.loads(analysis_data['analysis_results_json'])
                    except:
                        pass
                
                if 'suggestions_json' in analysis_data:
                    try:
                        analysis_data['suggestions'] = json.loads(analysis_data['suggestions_json'])
                    except:
                        pass
                
                # Convert Firebase timestamps to ISO strings
                for field in ['created_at', 'updated_at', 'processed_at']:
                    if analysis_data.get(field):
                        analysis_data[field] = analysis_data[field].isoformat() if hasattr(analysis_data[field], 'isoformat') else str(analysis_data[field])
                
                return analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting analysis by ID: {e}")
            return None
    
    def get_user_analyses(self, user_id: str, analysis_type: str = None) -> List[Dict[str, Any]]:
        """Get all analyses for a user - FIXED query without ordering"""
        try:
            # Simple query without ordering to avoid index requirements
            query = self.db.collection(self.collection_name)\
                .where('user_id', '==', user_id)
            
            if analysis_type:
                query = query.where('analysis_type', '==', analysis_type)
            
            # Limit results to avoid large queries
            query = query.limit(50)
            docs = query.get()
            
            analyses = []
            for doc in docs:
                analysis_data = doc.to_dict()
                analysis_data['id'] = doc.id
                
                # Reconstruct complex data from JSON if available
                if 'analysis_results_json' in analysis_data:
                    try:
                        analysis_data['analysis_results'] = json.loads(analysis_data['analysis_results_json'])
                    except:
                        pass
                
                if 'suggestions_json' in analysis_data:
                    try:
                        analysis_data['suggestions'] = json.loads(analysis_data['suggestions_json'])
                    except:
                        pass
                
                # Convert Firebase timestamps
                for field in ['created_at', 'updated_at', 'processed_at']:
                    if analysis_data.get(field):
                        analysis_data[field] = analysis_data[field].isoformat() if hasattr(analysis_data[field], 'isoformat') else str(analysis_data[field])
                
                analyses.append(analysis_data)
            
            # Sort by created_at in Python if needed
            analyses.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return analyses
            
        except Exception as e:
            logger.error(f"Error getting user analyses: {e}")
            return []
    
    def get_user_analysis_summary(self, user_id: str) -> List[Dict[str, Any]]:
        """Get analysis summary for a user (optimized for listing) - FIXED"""
        try:
            query = self.db.collection(self.collection_name)\
                .where('user_id', '==', user_id)\
                .limit(50)
            
            docs = query.get()
            analyses = []
            
            for doc in docs:
                analysis_data = doc.to_dict()
                
                # Create summary with only essential fields
                analysis_summary = {
                    'id': doc.id,
                    'analysis_type': analysis_data.get('analysis_type'),
                    'status': analysis_data.get('status', 'unknown'),
                    'created_at': analysis_data.get('created_at'),
                    'processed_at': analysis_data.get('processed_at'),
                    'error_message': analysis_data.get('error_message'),
                    'grade': analysis_data.get('grade'),
                    'has_suggestions': bool(analysis_data.get('suggestions_json')),
                    'profile_identifier': analysis_data.get('profile_url') or analysis_data.get('github_username', 'N/A')
                }
                
                # Add type-specific information
                if analysis_data.get('analysis_type') == 'github':
                    github_stats = analysis_data.get('github_stats', {})
                    analysis_summary.update({
                        'public_repos': github_stats.get('public_repos', 0),
                        'followers': github_stats.get('followers', 0),
                        'following': github_stats.get('following', 0)
                    })
                
                # Convert Firebase timestamps to ISO strings
                for field in ['created_at', 'processed_at']:
                    if analysis_summary.get(field):
                        if hasattr(analysis_summary[field], 'isoformat'):
                            analysis_summary[field] = analysis_summary[field].isoformat()
                        else:
                            analysis_summary[field] = str(analysis_summary[field])
                
                analyses.append(analysis_summary)
            
            # Sort by created_at in Python
            analyses.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return analyses
            
        except Exception as e:
            logger.error(f"Error getting user analysis summary: {e}")
            return []
    
    def get_user_analysis_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get analysis statistics for a user"""
        try:
            query = self.db.collection(self.collection_name).where('user_id', '==', user_id)
            docs = query.get()
            
            total_analyses = len(docs)
            linkedin_analyses = 0
            github_analyses = 0
            completed_analyses = 0
            processing_analyses = 0
            failed_analyses = 0
            pending_analyses = 0
            
            grade_sum = 0
            graded_analyses = 0
            
            for doc in docs:
                analysis_data = doc.to_dict()
                analysis_type = analysis_data.get('analysis_type')
                status = analysis_data.get('status', 'unknown')
                grade = analysis_data.get('grade')
                
                if analysis_type == 'linkedin':
                    linkedin_analyses += 1
                elif analysis_type == 'github':
                    github_analyses += 1
                
                if status == 'completed':
                    completed_analyses += 1
                elif status == 'processing':
                    processing_analyses += 1
                elif status == 'failed':
                    failed_analyses += 1
                elif status == 'pending':
                    pending_analyses += 1
                
                if grade and isinstance(grade, (int, float)):
                    grade_sum += grade
                    graded_analyses += 1
            
            return {
                'total_analyses': total_analyses,
                'linkedin_analyses': linkedin_analyses,
                'github_analyses': github_analyses,
                'completed': completed_analyses,
                'processing': processing_analyses,
                'pending': pending_analyses,
                'failed': failed_analyses,
                'success_rate': round((completed_analyses / total_analyses * 100), 1) if total_analyses > 0 else 0,
                'average_grade': round((grade_sum / graded_analyses), 1) if graded_analyses > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user analysis statistics: {e}")
            return {
                'total_analyses': 0,
                'linkedin_analyses': 0,
                'github_analyses': 0,
                'completed': 0,
                'processing': 0,
                'pending': 0,
                'failed': 0,
                'success_rate': 0,
                'average_grade': 0
            }
    
    def delete_analysis(self, analysis_id: str) -> bool:
        """Delete analysis record"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc_ref.delete()
            
            logger.info(f"Deleted analysis: {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting analysis: {e}")
            return False
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get global analysis statistics"""
        try:
            all_docs = self.db.collection(self.collection_name).limit(1000).get()  # Limit for performance
            total_analyses = len(all_docs)
            
            linkedin_count = 0
            github_count = 0
            completed_count = 0
            
            for doc in all_docs:
                data = doc.to_dict()
                if data.get('analysis_type') == 'linkedin':
                    linkedin_count += 1
                elif data.get('analysis_type') == 'github':
                    github_count += 1
                
                if data.get('status') == 'completed':
                    completed_count += 1
            
            return {
                'total_analyses': total_analyses,
                'linkedin_analyses': linkedin_count,
                'github_analyses': github_count,
                'completed_analyses': completed_count,
                'success_rate': (completed_count / total_analyses * 100) if total_analyses > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting analysis statistics: {e}")
            return {
                'total_analyses': 0,
                'linkedin_analyses': 0,
                'github_analyses': 0,
                'completed_analyses': 0,
                'success_rate': 0
            }
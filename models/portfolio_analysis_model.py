# models/portfolio_analysis_model.py
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import json
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class PortfolioAnalysisModel:
    """Portfolio analysis data model for Firestore operations"""
    
    def __init__(self, db):
        self.db = db
        self.collection_name = 'portfolio_analyses'
    
    def _sanitize_for_firestore(self, data: Any) -> Any:
        """Sanitize data to be compatible with Firestore"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Convert any problematic keys
                safe_key = str(key).replace('.', '_').replace('/', '_').replace('#', '_')
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
        """Create a new portfolio analysis record"""
        try:
            analysis_doc = {
                'user_id': user_id,
                'analysis_type': 'portfolio',
                'portfolio_url': analysis_data.get('portfolio_url'),
                'status': 'pending',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'processed_at': None,
                'error_message': None,
                'score': None,
                'score_breakdown': None,
                'extracted_data': None,
                'analysis_results': None,
                'suggestions': None,
                # Store user profile context as sanitized data
                'user_profile_context': self._sanitize_for_firestore(analysis_data.get('user_profile_context', {}))
            }
            
            doc_ref = self.db.collection(self.collection_name).add(analysis_doc)
            analysis_id = doc_ref[1].id
            
            logger.info(f"Created portfolio analysis record: {analysis_id} for user: {user_id}")
            return analysis_id
            
        except Exception as e:
            logger.error(f"Error creating portfolio analysis record: {e}")
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
            
            logger.info(f"Updated portfolio analysis status: {analysis_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Error updating portfolio analysis status: {e}")
    
    def update_analysis_with_results(self, analysis_id: str, results_data: Dict[str, Any]):
        """Update analysis with processed results - FIXED for Firestore compatibility"""
        try:
            update_data = {
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Handle extracted data with flattening
            if 'extracted_data' in results_data:
                extracted_data = results_data['extracted_data']
                flattened_extracted = self._flatten_complex_data(extracted_data)
                
                # Store flattened extracted data
                for key, value in flattened_extracted.items():
                    update_data[f"extracted_{key}"] = value
                
                # Also store a JSON version for complete data retrieval
                update_data['extracted_data_json'] = json.dumps(extracted_data)
            
            # Handle analysis results with flattening
            if 'analysis_results' in results_data:
                analysis_results = results_data['analysis_results']
                flattened_results = self._flatten_complex_data(analysis_results)
                
                # Store flattened results
                for key, value in flattened_results.items():
                    update_data[f"analysis_{key}"] = value
                
                # Also store a JSON version
                update_data['analysis_results_json'] = json.dumps(analysis_results)
            
            # Handle suggestions with flattening
            if 'suggestions' in results_data:
                suggestions = results_data['suggestions']
                flattened_suggestions = self._flatten_complex_data(suggestions)
                
                # Store flattened suggestions
                for key, value in flattened_suggestions.items():
                    update_data[f"suggestion_{key}"] = value
                
                # Store JSON version
                update_data['suggestions_json'] = json.dumps(suggestions)
            
            # Handle score and score breakdown
            if 'score' in results_data:
                update_data['score'] = int(results_data['score'])
            
            if 'score_breakdown' in results_data:
                score_breakdown = results_data['score_breakdown']
                sanitized_breakdown = self._sanitize_for_firestore(score_breakdown)
                update_data['score_breakdown'] = sanitized_breakdown
                update_data['score_breakdown_json'] = json.dumps(score_breakdown)
            
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc_ref.update(update_data)
            
            logger.info(f"Updated portfolio analysis with results: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error updating portfolio analysis with results: {e}")
            # Try a simpler update with just the score
            try:
                simple_update = {
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'status': 'completed',
                    'score': results_data.get('score', 0),
                    'has_results': True
                }
                doc_ref = self.db.collection(self.collection_name).document(analysis_id)
                doc_ref.update(simple_update)
                logger.info(f"Applied simplified update for portfolio analysis: {analysis_id}")
            except Exception as e2:
                logger.error(f"Failed simplified update: {e2}")
    
    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis by ID - Reconstruct complex data"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc = doc_ref.get()
            
            if doc.exists:
                analysis_data = doc.to_dict()
                analysis_data['id'] = analysis_id
                
                # Reconstruct complex data from JSON if available
                if 'extracted_data_json' in analysis_data:
                    try:
                        analysis_data['extracted_data'] = json.loads(analysis_data['extracted_data_json'])
                    except:
                        pass
                
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
                
                if 'score_breakdown_json' in analysis_data:
                    try:
                        analysis_data['score_breakdown'] = json.loads(analysis_data['score_breakdown_json'])
                    except:
                        pass
                
                # Convert Firebase timestamps to ISO strings
                for field in ['created_at', 'updated_at', 'processed_at']:
                    if analysis_data.get(field):
                        analysis_data[field] = analysis_data[field].isoformat() if hasattr(analysis_data[field], 'isoformat') else str(analysis_data[field])
                
                return analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting portfolio analysis by ID: {e}")
            return None
    
    def get_user_analyses(self, user_id: str, analysis_type: str = None) -> List[Dict[str, Any]]:
        """Get all portfolio analyses for a user"""
        try:
            # Try modern Firestore query syntax first
            try:
                from google.cloud.firestore_v1 import Query
                
                # Start with base query
                query = self.db.collection(self.collection_name)
                
                # Add filters using the filter() method
                filters = [Query.field_path('user_id') == user_id]
                
                if analysis_type:
                    filters.append(Query.field_path('analysis_type') == analysis_type)
                
                # Apply filters
                for filter_condition in filters:
                    query = query.filter(filter_condition)
                
                # Add ordering
                query = query.order_by('created_at', direction='DESCENDING')
                
                docs = query.stream()
                analyses = []
                
                for doc in docs:
                    analysis_data = doc.to_dict()
                    analysis_data['id'] = doc.id
                    
                    # Reconstruct complex data from JSON if available
                    if 'extracted_data_json' in analysis_data:
                        try:
                            analysis_data['extracted_data'] = json.loads(analysis_data['extracted_data_json'])
                        except:
                            pass
                    
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
                    
                    if 'score_breakdown_json' in analysis_data:
                        try:
                            analysis_data['score_breakdown'] = json.loads(analysis_data['score_breakdown_json'])
                        except:
                            pass
                    
                    # Convert Firebase timestamps
                    for field in ['created_at', 'updated_at', 'processed_at']:
                        if analysis_data.get(field):
                            analysis_data[field] = analysis_data[field].isoformat() if hasattr(analysis_data[field], 'isoformat') else str(analysis_data[field])
                    
                    analyses.append(analysis_data)
                
                return analyses
                
            except Exception as index_error:
                logger.warning(f"Modern query failed, using fallback: {index_error}")
                
                # Fallback: Get all analyses and filter in memory
                docs = self.db.collection(self.collection_name).stream()
                analyses = []
                
                for doc in docs:
                    analysis_data = doc.to_dict()
                    analysis_data['id'] = doc.id
                    
                    # Filter by user_id
                    if analysis_data.get('user_id') != user_id:
                        continue
                    
                    # Filter by analysis_type if specified
                    if analysis_type and analysis_data.get('analysis_type') != analysis_type:
                        continue
                    
                    # Reconstruct complex data from JSON if available
                    if 'extracted_data_json' in analysis_data:
                        try:
                            analysis_data['extracted_data'] = json.loads(analysis_data['extracted_data_json'])
                        except:
                            pass
                    
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
                    
                    if 'score_breakdown_json' in analysis_data:
                        try:
                            analysis_data['score_breakdown'] = json.loads(analysis_data['score_breakdown_json'])
                        except:
                            pass
                    
                    # Convert Firebase timestamps
                    for field in ['created_at', 'updated_at', 'processed_at']:
                        if analysis_data.get(field):
                            analysis_data[field] = analysis_data[field].isoformat() if hasattr(analysis_data[field], 'isoformat') else str(analysis_data[field])
                    
                    analyses.append(analysis_data)
                
                # Sort by created_at descending
                analyses.sort(key=lambda x: x.get('created_at', '1900-01-01'), reverse=True)
                
                return analyses
            
        except Exception as e:
            logger.error(f"Error getting user portfolio analyses: {e}")
            return []
    
    def get_user_analysis_summary(self, user_id: str) -> List[Dict[str, Any]]:
        """Get portfolio analysis summary for a user (optimized for listing)"""
        try:
            # Try modern Firestore query syntax first
            try:
                from google.cloud.firestore_v1 import Query
                
                query = self.db.collection(self.collection_name)\
                    .filter(Query.field_path('user_id') == user_id)\
                    .order_by('created_at', direction='DESCENDING')
                
                docs = query.stream()
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
                        'score': analysis_data.get('score'),
                        'portfolio_url': analysis_data.get('portfolio_url'),
                        'has_results': bool(analysis_data.get('extracted_data_json') or analysis_data.get('analysis_results_json') or analysis_data.get('suggestions_json'))
                    }
                    
                    # Convert Firebase timestamps to ISO strings
                    for field in ['created_at', 'processed_at']:
                        if analysis_summary.get(field):
                            if hasattr(analysis_summary[field], 'isoformat'):
                                analysis_summary[field] = analysis_summary[field].isoformat()
                            else:
                                analysis_summary[field] = str(analysis_summary[field])
                    
                    analyses.append(analysis_summary)
                
                return analyses
                
            except Exception as index_error:
                logger.warning(f"Modern query failed, using fallback: {index_error}")
                
                # Fallback: Get all analyses and filter in memory
                docs = self.db.collection(self.collection_name).stream()
                analyses = []
                
                for doc in docs:
                    analysis_data = doc.to_dict()
                    
                    # Filter by user_id
                    if analysis_data.get('user_id') != user_id:
                        continue
                    
                    # Create summary with only essential fields
                    analysis_summary = {
                        'id': doc.id,
                        'analysis_type': analysis_data.get('analysis_type'),
                        'status': analysis_data.get('status', 'unknown'),
                        'created_at': analysis_data.get('created_at'),
                        'processed_at': analysis_data.get('processed_at'),
                        'error_message': analysis_data.get('error_message'),
                        'score': analysis_data.get('score'),
                        'portfolio_url': analysis_data.get('portfolio_url'),
                        'has_results': bool(analysis_data.get('extracted_data_json') or analysis_data.get('analysis_results_json') or analysis_data.get('suggestions_json'))
                    }
                    
                    # Convert Firebase timestamps to ISO strings
                    for field in ['created_at', 'processed_at']:
                        if analysis_summary.get(field):
                            if hasattr(analysis_summary[field], 'isoformat'):
                                analysis_summary[field] = analysis_summary[field].isoformat()
                            else:
                                analysis_summary[field] = str(analysis_summary[field])
                    
                    analyses.append(analysis_summary)
                
                # Sort by created_at descending
                analyses.sort(key=lambda x: x.get('created_at', '1900-01-01'), reverse=True)
                
                return analyses
            
        except Exception as e:
            logger.error(f"Error getting user portfolio analysis summary: {e}")
            return []
    
    def get_user_analysis_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio analysis statistics for a user"""
        try:
            # Try modern Firestore query syntax first
            try:
                from google.cloud.firestore_v1 import Query
                
                query = self.db.collection(self.collection_name)\
                    .filter(Query.field_path('user_id') == user_id)
                
                docs = query.stream()
                
            except Exception as index_error:
                logger.warning(f"Modern query failed, using fallback: {index_error}")
                
                # Fallback: Get all analyses and filter in memory
                docs = self.db.collection(self.collection_name).stream()
            
            total_analyses = 0
            completed_analyses = 0
            processing_analyses = 0
            failed_analyses = 0
            pending_analyses = 0
            total_score = 0
            
            for doc in docs:
                analysis_data = doc.to_dict()
                
                # Filter by user_id in fallback mode
                if analysis_data.get('user_id') != user_id:
                    continue
                
                total_analyses += 1
                status = analysis_data.get('status', 'unknown')
                
                if status == 'completed':
                    completed_analyses += 1
                    if analysis_data.get('score'):
                        total_score += analysis_data.get('score', 0)
                elif status == 'processing':
                    processing_analyses += 1
                elif status == 'failed':
                    failed_analyses += 1
                elif status == 'pending':
                    pending_analyses += 1
            
            return {
                'total_analyses': total_analyses,
                'completed_analyses': completed_analyses,
                'processing_analyses': processing_analyses,
                'failed_analyses': failed_analyses,
                'pending_analyses': pending_analyses,
                'average_score': round(total_score / completed_analyses, 1) if completed_analyses > 0 else 0,
                'success_rate': round((completed_analyses / total_analyses * 100) if total_analyses > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio analysis statistics: {e}")
            return {
                'total_analyses': 0,
                'completed_analyses': 0,
                'processing_analyses': 0,
                'failed_analyses': 0,
                'pending_analyses': 0,
                'average_score': 0,
                'success_rate': 0
            }
    
    def delete_analysis(self, analysis_id: str) -> bool:
        """Delete analysis record"""
        try:
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc_ref.delete()
            
            logger.info(f"Deleted portfolio analysis: {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting portfolio analysis: {e}")
            return False
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get global analysis statistics"""
        try:
            all_docs = self.db.collection(self.collection_name)\
                .where('analysis_type', '==', 'portfolio')\
                .limit(1000).get()  # Limit for performance
            
            total_analyses = len(all_docs)
            completed_count = 0
            
            for doc in all_docs:
                data = doc.to_dict()
                if data.get('status') == 'completed':
                    completed_count += 1
            
            return {
                'total_portfolio_analyses': total_analyses,
                'completed_portfolio_analyses': completed_count,
                'portfolio_success_rate': (completed_count / total_analyses * 100) if total_analyses > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio analysis statistics: {e}")
            return {
                'total_portfolio_analyses': 0,
                'completed_portfolio_analyses': 0,
                'portfolio_success_rate': 0
            }
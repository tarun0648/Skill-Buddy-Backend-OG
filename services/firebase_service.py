"""
Firebase Service - Integration with Firebase for interview data management
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from firebase_admin import firestore
from config.firebase_config import get_db

logger = logging.getLogger(__name__)

class FirebaseService:
    """Service for Firebase operations"""
    
    def __init__(self):
        self.db = get_db()
        self.interview_history_collection = "interview_history"
        self.interview_sessions_collection = "interview_sessions"
        self.interview_summaries_collection = "interview_summaries"
    
    def save_interview_history(self, data: Dict[str, Any]) -> str:
        """Save interview history entry to Firebase"""
        try:
            # Add timestamp if not present
            if "created_at" not in data:
                data["created_at"] = datetime.utcnow().isoformat()
            
            # Add document to collection
            doc_ref = self.db.collection(self.interview_history_collection).add(data)
            doc_id = doc_ref[1].id
            
            logger.info(f"Interview history saved with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to save interview history: {e}")
            raise Exception(f"Failed to save interview history: {e}")
    
    def get_interview_history(self, session_id: str, user_id: str, 
                            assessment_type: str = None) -> List[Dict[str, Any]]:
        """Get interview history for a session"""
        try:
            # Use a simpler query that doesn't require compound indexes
            query = self.db.collection(self.interview_history_collection)\
                .where("session_id", "==", session_id)
            
            docs = query.stream()
            
            history = []
            for doc in docs:
                item = doc.to_dict()
                # Filter by user_id in Python instead of in the query
                if item.get("user_id") == user_id:
                    if assessment_type is None or item.get("assessment_type") == assessment_type:
                        item["id"] = doc.id
                        history.append(item)
            
            # Sort by created_at
            history.sort(key=lambda x: x.get("created_at", ""))
            
            logger.info(f"Retrieved {len(history)} history entries for session {session_id}")
            return history
            
        except Exception as e:
            logger.error(f"Failed to get interview history: {e}")
            return []
    
    def save_interview_session(self, session_data: Dict[str, Any]) -> str:
        """Save interview session metadata"""
        try:
            # Add timestamp if not present
            if "created_at" not in session_data:
                session_data["created_at"] = datetime.utcnow().isoformat()
            
            session_id = session_data.get("session_id")
            if session_id:
                # Use session_id as document ID
                doc_ref = self.db.collection(self.interview_sessions_collection).document(session_id)
                doc_ref.set(session_data, merge=True)
                logger.info(f"Interview session saved: {session_id}")
                return session_id
            else:
                # Let Firestore generate ID
                doc_ref = self.db.collection(self.interview_sessions_collection).add(session_data)
                doc_id = doc_ref[1].id
                logger.info(f"Interview session saved with generated ID: {doc_id}")
                return doc_id
                
        except Exception as e:
            logger.error(f"Failed to save interview session: {e}")
            raise Exception(f"Failed to save interview session: {e}")
    
    def get_interview_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get interview session by ID"""
        try:
            doc = self.db.collection(self.interview_sessions_collection).document(session_id).get()
            
            if doc.exists:
                session_data = doc.to_dict()
                # Verify user ownership
                if session_data.get("user_id") == user_id:
                    session_data["id"] = doc.id
                    return session_data
                else:
                    logger.warning(f"User {user_id} attempted to access session {session_id} owned by {session_data.get('user_id')}")
                    return None
            else:
                logger.info(f"Interview session not found: {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get interview session: {e}")
            return None
    
    def save_interview_summary(self, summary_data: Dict[str, Any]) -> str:
        """Save interview summary"""
        try:
            # Add timestamp if not present
            if "created_at" not in summary_data:
                summary_data["created_at"] = datetime.utcnow().isoformat()
            
            session_id = summary_data.get("session_id")
            if session_id:
                # Use session_id as document ID for summaries
                doc_ref = self.db.collection(self.interview_summaries_collection).document(session_id)
                doc_ref.set(summary_data, merge=True)
                logger.info(f"Interview summary saved: {session_id}")
                return session_id
            else:
                # Let Firestore generate ID
                doc_ref = self.db.collection(self.interview_summaries_collection).add(summary_data)
                doc_id = doc_ref[1].id
                logger.info(f"Interview summary saved with generated ID: {doc_id}")
                return doc_id
                
        except Exception as e:
            logger.error(f"Failed to save interview summary: {e}")
            raise Exception(f"Failed to save interview summary: {e}")
    
    def get_interview_summary(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get interview summary by session ID"""
        try:
            doc = self.db.collection(self.interview_summaries_collection).document(session_id).get()
            
            if doc.exists:
                summary_data = doc.to_dict()
                # Verify user ownership
                if summary_data.get("user_id") == user_id:
                    summary_data["id"] = doc.id
                    return summary_data
                else:
                    logger.warning(f"User {user_id} attempted to access summary {session_id} owned by {summary_data.get('user_id')}")
                    return None
            else:
                logger.info(f"Interview summary not found: {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get interview summary: {e}")
            return None
    
    def get_user_interview_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all interview sessions for a user"""
        try:
            docs = self.db.collection(self.interview_sessions_collection)\
                .where("user_id", "==", user_id)\
                .order_by("created_at", direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            sessions = []
            for doc in docs:
                session_data = doc.to_dict()
                session_data["id"] = doc.id
                sessions.append(session_data)
            
            logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user interview sessions: {e}")
            return []
    
    def get_user_interview_summaries(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all interview summaries for a user"""
        try:
            docs = self.db.collection(self.interview_summaries_collection)\
                .where("user_id", "==", user_id)\
                .order_by("created_at", direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            summaries = []
            for doc in docs:
                summary_data = doc.to_dict()
                summary_data["id"] = doc.id
                summaries.append(summary_data)
            
            logger.info(f"Retrieved {len(summaries)} summaries for user {user_id}")
            return summaries
            
        except Exception as e:
            logger.error(f"Failed to get user interview summaries: {e}")
            return []
    
    def get_all_user_interview_data(self, user_id: str, limit: int = 100) -> Dict[str, Any]:
        """Get all interview data for a user including sessions, history, and summaries"""
        try:
            # Get user's interview sessions
            sessions = self.get_user_interview_sessions(user_id, limit)
            
            # Get user's interview summaries
            summaries = self.get_user_interview_summaries(user_id, limit)
            
            # Get all interview history for the user (without ordering to avoid index issues)
            history_docs = self.db.collection(self.interview_history_collection)\
                .where("user_id", "==", user_id)\
                .limit(limit)\
                .stream()
            
            history = []
            for doc in history_docs:
                history_item = doc.to_dict()
                history_item["id"] = doc.id
                history.append(history_item)
            
            # Sort history by created_at in Python
            history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # Group history by session_id for better organization
            history_by_session = {}
            for item in history:
                session_id = item.get("session_id", "unknown")
                if session_id not in history_by_session:
                    history_by_session[session_id] = []
                history_by_session[session_id].append(item)
            
            # Sort history within each session by created_at
            for session_id in history_by_session:
                history_by_session[session_id].sort(key=lambda x: x.get("created_at", ""))
            
            # Calculate statistics
            total_sessions = len(sessions)
            total_questions = len(history)
            total_summaries = len(summaries)
            
            # Get unique roles and topics
            roles = list(set([item.get("role", "Unknown") for item in history]))
            topics = list(set([item.get("topic", "Unknown") for item in history]))
            assessment_types = list(set([item.get("assessment_type", "Unknown") for item in history]))
            
            # Get date range
            dates = [item.get("created_at", "") for item in history if item.get("created_at")]
            date_range = {
                "earliest": min(dates) if dates else None,
                "latest": max(dates) if dates else None
            }
            
            result = {
                "user_id": user_id,
                "statistics": {
                    "total_sessions": total_sessions,
                    "total_questions": total_questions,
                    "total_summaries": total_summaries,
                    "unique_roles": len(roles),
                    "unique_topics": len(topics),
                    "unique_assessment_types": len(assessment_types)
                },
                "metadata": {
                    "roles": roles,
                    "topics": topics,
                    "assessment_types": assessment_types,
                    "date_range": date_range
                },
                "sessions": sessions,
                "history": history,
                "history_by_session": history_by_session,
                "summaries": summaries,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Retrieved all interview data for user {user_id}: {total_sessions} sessions, {total_questions} questions, {total_summaries} summaries")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all user interview data: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "sessions": [],
                "history": [],
                "history_by_session": {},
                "summaries": [],
                "statistics": {
                    "total_sessions": 0,
                    "total_questions": 0,
                    "total_summaries": 0,
                    "unique_roles": 0,
                    "unique_topics": 0,
                    "unique_assessment_types": 0
                },
                "metadata": {
                    "roles": [],
                    "topics": [],
                    "assessment_types": [],
                    "date_range": {"earliest": None, "latest": None}
                }
            }
    
    def update_interview_session(self, session_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update interview session data"""
        try:
            # Verify user ownership first
            session = self.get_interview_session(session_id, user_id)
            if not session:
                logger.warning(f"Cannot update session {session_id} - not found or unauthorized")
                return False
            
            # Add update timestamp
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            # Update the document
            doc_ref = self.db.collection(self.interview_sessions_collection).document(session_id)
            doc_ref.update(updates)
            
            logger.info(f"Interview session updated: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update interview session: {e}")
            return False
    
    def delete_interview_session(self, session_id: str, user_id: str) -> bool:
        """Delete interview session and related data"""
        try:
            # Verify user ownership first
            session = self.get_interview_session(session_id, user_id)
            if not session:
                logger.warning(f"Cannot delete session {session_id} - not found or unauthorized")
                return False
            
            # Delete session document
            self.db.collection(self.interview_sessions_collection).document(session_id).delete()
            
            # Delete related history entries
            history_docs = self.db.collection(self.interview_history_collection)\
                .where("session_id", "==", session_id)\
                .where("user_id", "==", user_id)\
                .stream()
            
            for doc in history_docs:
                doc.reference.delete()
            
            # Delete summary if exists
            try:
                self.db.collection(self.interview_summaries_collection).document(session_id).delete()
            except:
                pass  # Summary might not exist
            
            logger.info(f"Interview session and related data deleted: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete interview session: {e}")
            return False
    
    def get_interview_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get interview statistics for a user"""
        try:
            # Get session count by type
            sessions = self.get_user_interview_sessions(user_id, limit=1000)  # Get more for stats
            
            stats = {
                "total_sessions": len(sessions),
                "role_based_sessions": 0,
                "jd_based_sessions": 0,
                "completed_sessions": 0,
                "average_questions_per_session": 0,
                "most_practiced_roles": {},
                "recent_activity": [],
                "total_questions_answered": 0
            }
            
            total_questions = 0
            role_counts = {}
            
            for session in sessions:
                assessment_type = session.get("assessment_type", "role_based")
                if assessment_type == "jd_based":
                    stats["jd_based_sessions"] += 1
                else:
                    stats["role_based_sessions"] += 1
                
                if session.get("status") == "completed":
                    stats["completed_sessions"] += 1
                
                questions_count = session.get("total_questions", 0)
                total_questions += questions_count
                
                role = session.get("role", "Unknown")
                role_counts[role] = role_counts.get(role, 0) + 1
                
                # Add to recent activity (last 10)
                if len(stats["recent_activity"]) < 10:
                    stats["recent_activity"].append({
                        "session_id": session.get("id"),
                        "role": role,
                        "assessment_type": assessment_type,
                        "created_at": session.get("created_at"),
                        "status": session.get("status", "unknown")
                    })
            
            stats["total_questions_answered"] = total_questions
            if len(sessions) > 0:
                stats["average_questions_per_session"] = round(total_questions / len(sessions), 2)
            
            # Sort roles by frequency
            stats["most_practiced_roles"] = dict(sorted(role_counts.items(), key=lambda x: x[1], reverse=True)[:5])
            
            logger.info(f"Generated statistics for user {user_id}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get interview statistics: {e}")
            return {
                "total_sessions": 0,
                "error": "Failed to generate statistics"
            }
    
    def search_interview_history(self, user_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search through user's interview history"""
        try:
            # Note: Firestore doesn't support full-text search natively
            # This is a basic implementation that searches in questions and answers
            
            # Get all history for the user
            docs = self.db.collection(self.interview_history_collection)\
                .where("user_id", "==", user_id)\
                .order_by("created_at", direction=firestore.Query.DESCENDING)\
                .limit(limit * 3)\
                .stream()  # Get more to filter
            
            query_lower = query.lower()
            results = []
            
            for doc in docs:
                history_item = doc.to_dict()
                history_item["id"] = doc.id
                
                # Search in question and answer
                question = history_item.get("question", "").lower()
                answer = history_item.get("answer", "").lower()
                role = history_item.get("role", "").lower()
                
                if (query_lower in question or 
                    query_lower in answer or 
                    query_lower in role):
                    results.append(history_item)
                
                if len(results) >= limit:
                    break
            
            logger.info(f"Found {len(results)} results for query '{query}' for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search interview history: {e}")
            return []
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old interview sessions (admin function)"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            # Find old sessions
            docs = self.db.collection(self.interview_sessions_collection)\
                .where("created_at", "<", cutoff_iso)\
                .limit(100)\
                .stream()
            
            deleted_count = 0
            for doc in docs:
                session_data = doc.to_dict()
                session_id = doc.id
                user_id = session_data.get("user_id")
                
                if user_id:
                    # Use the delete method which handles related data
                    if self.delete_interview_session(session_id, user_id):
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old interview sessions")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
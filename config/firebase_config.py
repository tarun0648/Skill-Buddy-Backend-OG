"""
Firebase Configuration - Enhanced for interview system integration
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging

logger = logging.getLogger(__name__)

# Global database instance
_db = None

def init_firebase():
    """Initialize Firebase Admin SDK"""
    global _db
    
    if _db is not None:
        return _db
    
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
        logger.info("Firebase already initialized")
    except ValueError:
        # Firebase not initialized, so initialize it
        service_account_path = os.path.join(os.path.dirname(__file__), '..', 'serviceAccountKey.json')
        
        if not os.path.exists(service_account_path):
            logger.error(f"Service account file not found: {service_account_path}")
            raise FileNotFoundError(f"Service account file not found: {service_account_path}")
        
        try:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase: {e}")
            raise
    
    # Initialize Firestore client
    _db = firestore.client()
    return _db

def get_db():
    """Get Firestore database instance"""
    global _db
    if _db is None:
        _db = init_firebase()
    return _db

def test_firebase_connection():
    """Test Firebase connection"""
    try:
        db = get_db()
        # Try to access the database
        test_doc = db.collection("test").document("connection_test")
        test_doc.set({"test": "connection", "timestamp": firestore.SERVER_TIMESTAMP})
        test_doc.delete()  # Clean up test document
        logger.info("✅ Firebase connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Firebase connection test failed: {e}")
        return False

def save_history_to_firebase(data):
    """Save interview history to Firebase (backward compatibility)"""
    try:
        db = get_db()
        db.collection("interview_history").add(data)
        logger.info("✅ History saved to Firebase")
    except Exception as e:
        logger.error(f"❌ Failed to save history: {e}")
        raise

# Collection names for easy reference
COLLECTIONS = {
    'users': 'users',
    'user_profiles': 'user_profiles',
    'interview_history': 'interview_history',
    'interview_sessions': 'interview_sessions',
    'interview_summaries': 'interview_summaries',
    'resumes': 'resumes',
    'resume_analysis': 'resume_analysis',
    'profile_analysis': 'profile_analysis',
    'portfolio_analysis': 'portfolio_analysis',
    'community_posts': 'community_posts',
    'community_replies': 'community_replies',
    'tasks': 'tasks',
    'feedback': 'feedback'
}

# Helper functions for common operations
def create_user_document(user_id: str, user_data: dict):
    """Create or update user document"""
    try:
        db = get_db()
        db.collection(COLLECTIONS['users']).document(user_id).set(user_data, merge=True)
        logger.info(f"User document created/updated: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create user document: {e}")
        return False

def get_user_document(user_id: str):
    """Get user document"""
    try:
        db = get_db()
        doc = db.collection(COLLECTIONS['users']).document(user_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        logger.error(f"Failed to get user document: {e}")
        return None

def delete_user_data(user_id: str):
    """Delete all user data (GDPR compliance)"""
    try:
        db = get_db()
        batch = db.batch()
        
        # Collections that contain user data
        user_collections = [
            'users', 'user_profiles', 'interview_history', 'interview_sessions',
            'interview_summaries', 'resumes', 'resume_analysis', 'profile_analysis',
            'portfolio_analysis', 'community_posts', 'community_replies', 'tasks', 'feedback'
        ]
        
        deleted_count = 0
        
        for collection_name in user_collections:
            # Query documents where user_id field matches
            docs = db.collection(collection_name).where('user_id', '==', user_id).stream()
            
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
        
        # Also delete the main user document
        batch.delete(db.collection('users').document(user_id))
        deleted_count += 1
        
        # Commit the batch
        batch.commit()
        
        logger.info(f"Deleted {deleted_count} documents for user {user_id}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to delete user data: {e}")
        return 0

def get_collection_stats():
    """Get statistics about Firebase collections"""
    try:
        db = get_db()
        stats = {}
        
        for collection_name in COLLECTIONS.values():
            try:
                # Get approximate count (this is a rough estimate)
                docs = db.collection(collection_name).limit(1).stream()
                doc_count = len(list(docs))
                if doc_count > 0:
                    # If there's at least one doc, get a larger sample to estimate
                    sample_docs = db.collection(collection_name).limit(100).stream()
                    sample_count = len(list(sample_docs))
                    stats[collection_name] = {"estimated_count": f"{sample_count}+"}
                else:
                    stats[collection_name] = {"estimated_count": 0}
            except Exception:
                stats[collection_name] = {"estimated_count": "error"}
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {}

# Firestore query helpers
class FirestoreQueryBuilder:
    """Helper class for building Firestore queries"""
    
    def __init__(self, collection_name: str):
        self.db = get_db()
        self.query = self.db.collection(collection_name)
    
    def where(self, field: str, operator: str, value):
        """Add where clause"""
        self.query = self.query.where(field, operator, value)
        return self
    
    def order_by(self, field: str, direction=firestore.Query.ASCENDING):
        """Add order by clause"""
        self.query = self.query.order_by(field, direction=direction)
        return self
    
    def limit(self, count: int):
        """Add limit clause"""
        self.query = self.query.limit(count)
        return self
    
    def get(self):
        """Execute query and return results"""
        try:
            docs = self.query.stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def count(self):
        """Count documents (approximate)"""
        try:
            docs = list(self.query.stream())
            return len(docs)
        except Exception as e:
            logger.error(f"Count query failed: {e}")
            return 0

# Firebase config object for backward compatibility
class FirebaseConfig:
    """Firebase configuration object for backward compatibility"""
    
    def get_db(self):
        """Get Firestore database instance"""
        return get_db()
    
    def init_firebase(self):
        """Initialize Firebase Admin SDK"""
        return init_firebase()
    
    def test_firebase_connection(self):
        """Test Firebase connection"""
        return test_firebase_connection()

# Create a singleton instance for import
firebase_config = FirebaseConfig()
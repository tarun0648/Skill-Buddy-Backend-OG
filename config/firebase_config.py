# config/firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os

class FirebaseConfig:
    def __init__(self):
        self.db = None
        self.auth = auth
        self.initialize_firebase()
    
    def initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if firebase_admin._apps:
                self.db = firestore.client()
                return
            
            # Try to load from service account file
            if os.path.exists('serviceAccountKey.json'):
                cred = credentials.Certificate('serviceAccountKey.json')
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                print("Firebase initialized successfully")
            else:
                print("Firebase credentials not found")
                
        except Exception as e:
            print(f"Firebase initialization error: {e}")
    
    def get_db(self):
        """Get Firestore database instance"""
        return self.db
    
    def get_auth(self):
        """Get Firebase Auth instance"""
        return self.auth

# Global Firebase instance
firebase_config = FirebaseConfig()
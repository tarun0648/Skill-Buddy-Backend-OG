# scripts/migrate_passwords.py - Hash existing plain text passwords
"""
Migration script to hash existing plain text passwords in the database.

This script should be run ONCE to migrate existing users from plain text
passwords to hashed passwords. 

WARNING: Make sure to backup your database before running this script!
"""

import os
import sys
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.firebase_config import firebase_config
from models.user_model import UserModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('password_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PasswordMigration:
    """Handle migration of plain text passwords to hashed passwords"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        if not self.db:
            raise Exception("Failed to connect to database")
        
        self.user_model = UserModel(self.db)
        self.migrated_count = 0
        self.skipped_count = 0
        self.error_count = 0
    
    def is_password_hashed(self, password):
        """Check if password is already hashed"""
        if not password:
            return False
        
        # Check for Werkzeug hash format indicators
        hash_methods = ['pbkdf2:sha256:', 'pbkdf2:sha1:', 'pbkdf2:sha512:', 'scrypt:', 'bcrypt:']
        return any(password.startswith(method) for method in hash_methods)
    
    def migrate_user_password(self, user_id, user_data):
        """Migrate a single user's password"""
        try:
            password = user_data.get('password')
            
            if not password:
                logger.info(f"User {user_id}: No password field (likely SSO user)")
                self.skipped_count += 1
                return True
            
            if self.is_password_hashed(password):
                logger.info(f"User {user_id}: Password already hashed")
                self.skipped_count += 1
                return True
            
            # Hash the plain text password
            hashed_password = generate_password_hash(password)
            
            # Update the user with hashed password
            success = self.user_model.update_user(user_id, {
                'password': hashed_password,
                'password_migrated_at': datetime.utcnow(),
                'migration_note': 'Password hashed during migration'
            })
            
            if success:
                logger.info(f"User {user_id}: Password successfully hashed")
                self.migrated_count += 1
                return True
            else:
                logger.error(f"User {user_id}: Failed to update password")
                self.error_count += 1
                return False
                
        except Exception as e:
            logger.error(f"User {user_id}: Error migrating password - {str(e)}")
            self.error_count += 1
            return False
    
    def run_migration(self, dry_run=True):
        """Run the password migration"""
        logger.info("="*60)
        logger.info("PASSWORD MIGRATION SCRIPT")
        logger.info("="*60)
        
        if dry_run:
            logger.info("DRY RUN MODE - No actual changes will be made")
        else:
            logger.info("LIVE MODE - Passwords will be hashed")
            
        logger.info(f"Started at: {datetime.utcnow()}")
        
        try:
            # Get all users
            users = self.user_model.get_all_users(include_inactive=True)
            total_users = len(users)
            
            logger.info(f"Found {total_users} users to process")
            
            if total_users == 0:
                logger.info("No users found in database")
                return
            
            # Process each user
            for i, user in enumerate(users, 1):
                user_id = user.get('id')
                email = user.get('email', 'unknown')
                
                logger.info(f"\nProcessing user {i}/{total_users}: {email}")
                
                if dry_run:
                    # Just check what would be done
                    password = user.get('password')
                    if not password:
                        logger.info(f"  -> Would skip (no password - likely SSO)")
                        self.skipped_count += 1
                    elif self.is_password_hashed(password):
                        logger.info(f"  -> Would skip (already hashed)")
                        self.skipped_count += 1
                    else:
                        logger.info(f"  -> Would hash password")
                        self.migrated_count += 1
                else:
                    # Actually migrate the password
                    self.migrate_user_password(user_id, user)
            
            # Print summary
            logger.info("\n" + "="*60)
            logger.info("MIGRATION SUMMARY")
            logger.info("="*60)
            logger.info(f"Total users processed: {total_users}")
            logger.info(f"Passwords migrated: {self.migrated_count}")
            logger.info(f"Users skipped: {self.skipped_count}")
            logger.info(f"Errors encountered: {self.error_count}")
            
            if dry_run:
                logger.info("\nThis was a DRY RUN - no actual changes were made")
                logger.info("To perform the actual migration, run with dry_run=False")
            else:
                logger.info("\nMigration completed!")
                
        except Exception as e:
            logger.error(f"Fatal error during migration: {str(e)}")
            raise
    
    def verify_migration(self):
        """Verify that all passwords are properly hashed"""
        logger.info("="*60)
        logger.info("VERIFYING MIGRATION")
        logger.info("="*60)
        
        users = self.user_model.get_all_users(include_inactive=True)
        total_users = len(users)
        hashed_count = 0
        plain_count = 0
        no_password_count = 0
        
        for user in users:
            password = user.get('password')
            email = user.get('email', 'unknown')
            
            if not password:
                logger.info(f"{email}: No password (SSO user)")
                no_password_count += 1
            elif self.is_password_hashed(password):
                logger.info(f"{email}: Password properly hashed ✓")
                hashed_count += 1
            else:
                logger.warning(f"{email}: Password still in plain text! ⚠️")
                plain_count += 1
        
        logger.info("\n" + "="*60)
        logger.info("VERIFICATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total users: {total_users}")
        logger.info(f"Properly hashed passwords: {hashed_count}")
        logger.info(f"No password (SSO users): {no_password_count}")
        logger.info(f"Still plain text: {plain_count}")
        
        if plain_count > 0:
            logger.warning("⚠️  Some passwords are still in plain text!")
            logger.warning("   Run the migration again to fix these.")
        else:
            logger.info("✓ All passwords are properly secured!")

def main():
    """Main function to run the migration"""
    try:
        migration = PasswordMigration()
        
        # First, run a dry run to see what would be changed
        print("Running dry run first...")
        migration.run_migration(dry_run=True)
        
        # Reset counters for actual run
        migration.migrated_count = 0
        migration.skipped_count = 0
        migration.error_count = 0
        
        # Ask for confirmation
        response = input("\nDo you want to proceed with the actual migration? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            print("\nRunning actual migration...")
            migration.run_migration(dry_run=False)
            
            # Verify the migration
            print("\nVerifying migration...")
            migration.verify_migration()
        else:
            print("Migration cancelled.")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Script to delete all users from the database
"""
import sys
import os
from pathlib import Path

# Add the parent directory (backend root) to Python path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.models.user import User
from app.models.session import UserSession

def delete_all_users():
    """Delete all users and their sessions from the database"""

    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get count of users before deletion
        user_count = db.query(User).count()
        session_count = db.query(UserSession).count()

        print(f"Found {user_count} users and {session_count} sessions in the database.")

        if user_count == 0:
            print("No users found in the database.")
            return

        # Delete all user sessions first (due to foreign key constraints)
        print("Deleting all user sessions...")
        db.query(UserSession).delete()
        print(f"Deleted {session_count} user sessions.")

        # Delete all users
        print("Deleting all users...")
        db.query(User).delete()
        print(f"Deleted {user_count} users.")

        # Commit the changes
        db.commit()
        print("✅ All users and sessions have been successfully deleted from the database.")

    except Exception as e:
        print(f"❌ Error deleting users: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🗑️  Starting user deletion process...")
    delete_all_users()
    print("✅ User deletion process completed.")

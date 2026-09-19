import sys
import os
import uuid

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.db.models.college import College

def clean_and_seed_dev_db():
    print("Starting development database cleanup...")
    db: Session = SessionLocal()
    try:
        # Delete all records in correct foreign key order
        print("Cleaning old test and demo data...")
        db.execute(text("DELETE FROM verification_results"))
        db.execute(text("DELETE FROM physical_verification_appointments"))
        db.execute(text("DELETE FROM documents"))
        db.execute(text("DELETE FROM scholarship_applications"))
        db.execute(text("DELETE FROM students"))
        db.execute(text("DELETE FROM admin_officers"))
        db.execute(text("DELETE FROM colleges"))
        db.commit()
        print("Existing demo/test data successfully removed.")

        # Seed exactly ONE fresh test college
        print("Seeding exactly ONE fresh test college...")
        test_college = College(
            id=uuid.uuid4(),
            college_name="Apex Institute of Technology",
            admin_setup_code="SETUP-APEX-2026",
            is_setup_code_used=False,
            college_code=None,  # Admin will set student-facing college_code after registration
            email="contact@apex.edu",
            address="Campus Row 42, Knowledge Park",
            is_active=True
        )
        db.add(test_college)
        db.commit()
        db.refresh(test_college)
        
        print("\n==========================================")
        print("DEV DATABASE CLEANUP & SEED COMPLETE")
        print("==========================================")
        print(f"College ID: {test_college.id}")
        print(f"College Name: {test_college.college_name}")
        print(f"Private Admin Setup Code: {test_college.admin_setup_code}")
        print(f"Student-Facing College Code: {test_college.college_code} (Not set yet)")
        print("==========================================\n")

    except Exception as e:
        db.rollback()
        print(f"Error cleaning database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    clean_and_seed_dev_db()

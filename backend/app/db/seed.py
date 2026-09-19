from app.db.session import SessionLocal
from app.services.auth_service import AuthService
from app.db.models.college import College
from app.db.models.admin_officer import AdminOfficer
from app.db.models.student import Student

def seed_demo_data():
    db = SessionLocal()
    try:
        # College 1: Demo Engineering College
        college1, admin1 = AuthService.create_college_with_admin(
            db=db,
            college_name="Demo Engineering College",
            college_code="DEMO001",
            admin_full_name="Chief Admin DEMO001",
            admin_email="admin@demo001.edu",
            admin_password="AdminPassword123!",
            college_email="contact@demo001.edu",
            college_address="Main Campus, Pune, Maharashtra",
            admin_department="Scholarship Cell",
            admin_designation="Chief Verification Officer"
        )
        print(f"Seeded College 1: {college1.college_name} ({college1.college_code}), Admin: {admin1.email}")

        # College 2: Demo Institute of Technology
        college2, admin2 = AuthService.create_college_with_admin(
            db=db,
            college_name="Demo Institute of Technology",
            college_code="DEMO002",
            admin_full_name="Chief Admin DEMO002",
            admin_email="admin@demo002.edu",
            admin_password="AdminPassword123!",
            college_email="contact@demo002.edu",
            college_address="Tech Campus, Mumbai, Maharashtra",
            admin_department="Scholarship Cell",
            admin_designation="Senior Verification Officer"
        )
        print(f"Seeded College 2: {college2.college_name} ({college2.college_code}), Admin: {admin2.email}")

        # Demo Students for College 1 (DEMO001)
        demo_students = [
            ("Amit Patil", "amit.patil@example.edu", "Password123!"),
            ("Rahul Sharma", "rahul.sharma@example.edu", "Password123!"),
            ("Sneha Kulkarni", "sneha.kulkarni@example.edu", "Password123!"),
        ]
        from app.schemas.auth import StudentRegisterRequest
        for name, email, pwd in demo_students:
            existing = db.query(Student).filter(Student.email == email).first()
            if not existing:
                AuthService.register_student(
                    db,
                    StudentRegisterRequest(
                        college_code="DEMO001",
                        full_name=name,
                        email=email,
                        password=pwd
                    )
                )
                print(f"Seeded Demo Student: {name} ({email})")

    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()

import uuid
from typing import Optional, Tuple, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models.college import College
from app.db.models.student import Student
from app.db.models.admin_officer import AdminOfficer
from app.db.models.enums import UserRole
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.schemas.auth import (
    StudentRegisterRequest,
    AdminRegisterRequest,
    LoginRequest,
    AdminLoginRequest,
    TokenResponse,
    UserProfileResponse,
)

class AuthService:
    @staticmethod
    def get_college_by_code(db: Session, college_code: str) -> Optional[College]:
        """
        Lookup an active college by its unique college code.
        """
        clean_code = college_code.upper().strip()
        if not clean_code:
            return None
        return db.query(College).filter(
            College.college_code == clean_code,
            College.is_active == True
        ).first()

    @staticmethod
    def register_student(db: Session, req: StudentRegisterRequest) -> Student:
        """
        Register a new Student user bound to a valid college.
        Validates college code, hashes password, and enforces email uniqueness.
        """
        clean_email = req.email.lower().strip()
        
        # 1. Validate College Code
        if not req.college_code or not req.college_code.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid college code. Please contact your college administrator."
            )

        college = AuthService.get_college_by_code(db, req.college_code)
        if not college or not college.college_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid college code. Please contact your college administrator."
            )

        # 2. Check duplicate email in Student table
        existing_student = db.query(Student).filter(Student.email == clean_email).first()
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered"
            )
        
        # 3. Check duplicate email in Admin table
        existing_admin = db.query(AdminOfficer).filter(AdminOfficer.email == clean_email).first()
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered"
            )

        # 4. Hash password using bcrypt
        hashed_password = get_password_hash(req.password)

        new_student = Student(
            college_id=college.id,
            full_name=req.full_name,
            email=clean_email,
            password_hash=hashed_password,
            phone_number=req.phone_number,
            government_id_number=req.government_id_number,
            date_of_birth=req.date_of_birth,
            address=req.address,
            is_active=True
        )

        db.add(new_student)
        db.commit()
        db.refresh(new_student)
        return new_student

    @staticmethod
    def register_admin(db: Session, req: AdminRegisterRequest) -> TokenResponse:
        """
        Register a new Admin Officer for a College using a private Admin Setup Code.
        Verifies setup code is valid and unused, enforces 1 admin per college rule,
        hashes password, invalidates the setup code (one-time-use), and returns JWT token.
        """
        clean_setup_code = req.admin_setup_code.strip()
        clean_email = req.email.lower().strip()

        # 1. Lookup College by admin_setup_code where setup code has not been used yet
        college = db.query(College).filter(
            College.admin_setup_code == clean_setup_code,
            College.is_setup_code_used == False,
            College.is_active == True
        ).first()

        if not college:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used Admin Setup Code. Please contact your system administrator."
            )

        # 2. Check if college already has an admin officer (Rule: Exactly ONE admin per college)
        existing_admin_for_college = db.query(AdminOfficer).filter(
            AdminOfficer.college_id == college.id
        ).first()
        if existing_admin_for_college:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An administrator account already exists for this college."
            )

        # 3. Check duplicate email in Admin table
        existing_admin_email = db.query(AdminOfficer).filter(AdminOfficer.email == clean_email).first()
        if existing_admin_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered."
            )

        # 4. Check duplicate email in Student table
        existing_student_email = db.query(Student).filter(Student.email == clean_email).first()
        if existing_student_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already registered."
            )

        # 5. Create Admin Officer
        hashed_password = get_password_hash(req.password)
        new_admin = AdminOfficer(
            college_id=college.id,
            full_name=req.full_name,
            email=clean_email,
            password_hash=hashed_password,
            phone_number=req.phone_number,
            department=req.department or "Scholarship Cell",
            designation=req.designation or "Verification Officer",
            is_active=True
        )

        # 6. Invalidate Admin Setup Code (One-Time-Use)
        college.is_setup_code_used = True
        college.admin_setup_code = None

        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        # 7. Return Token Response
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        access_token = create_access_token(
            subject=str(new_admin.id),
            role=UserRole.ADMIN,
            college_id=str(new_admin.college_id)
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=new_admin.id,
            college_id=new_admin.college_id,
            email=new_admin.email,
            role=UserRole.ADMIN,
            expires_in_seconds=expires_minutes * 60
        )

    @staticmethod
    def authenticate_admin(db: Session, req: AdminLoginRequest) -> TokenResponse:
        """
        Authenticate an Admin Officer using College Code + Email + Password.
        All three credentials are required for admin authentication.
        """
        clean_code = req.college_code.upper().strip()
        clean_email = req.email.lower().strip()

        # 1. Identify College by College Code (or matching college where admin belongs)
        college = db.query(College).filter(
            College.college_code == clean_code,
            College.is_active == True
        ).first()

        # If college_code not set yet or didn't match, check if admin email belongs to a college
        if not college:
            admin_by_email = db.query(AdminOfficer).filter(AdminOfficer.email == clean_email).first()
            if admin_by_email:
                college = db.query(College).filter(College.id == admin_by_email.college_id).first()
                # If college exists and college_code matches or college_code is not configured yet
                if college and college.college_code and college.college_code != clean_code:
                    college = None

        if not college:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid college code, email, or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 2. Find Admin Officer assigned to this specific college
        admin = db.query(AdminOfficer).filter(
            AdminOfficer.email == clean_email,
            AdminOfficer.college_id == college.id
        ).first()

        if not admin or not admin.password_hash or not verify_password(req.password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid college code, email, or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive. Please contact support.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 3. Issue Token containing admin ID, role, and college_id
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        access_token = create_access_token(
            subject=str(admin.id),
            role=UserRole.ADMIN,
            college_id=str(admin.college_id)
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=admin.id,
            college_id=admin.college_id,
            email=admin.email,
            role=UserRole.ADMIN,
            expires_in_seconds=expires_minutes * 60
        )

    @staticmethod
    def authenticate_user(
        db: Session,
        req: LoginRequest
    ) -> TokenResponse:
        """
        Unified login handler supporting Student and Admin logins.
        - If role is ADMIN, requires college_code and authenticates admin.
        - If role is STUDENT or unspecified, attempts Student login first (using stored student.college_id).
        - If user is an Admin, college_code is required for authentication.
        """
        clean_email = req.email.lower().strip()

        # 1. Explicit Admin login request
        if req.role == UserRole.ADMIN:
            if not req.college_code:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="College code is required for admin login",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return AuthService.authenticate_admin(
                db,
                AdminLoginRequest(
                    college_code=req.college_code,
                    email=req.email,
                    password=req.password
                )
            )

        # 2. Attempt Student authentication (Email + Password) if role is STUDENT or None
        student = db.query(Student).filter(Student.email == clean_email).first()
        if student and student.password_hash and verify_password(req.password, student.password_hash):
            if not student.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is inactive. Please contact support.",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
            access_token = create_access_token(
                subject=str(student.id),
                role=UserRole.STUDENT,
                college_id=str(student.college_id)
            )

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user_id=student.id,
                college_id=student.college_id,
                email=student.email,
                role=UserRole.STUDENT,
                expires_in_seconds=expires_minutes * 60
            )

        # 3. Check if user is an Admin
        admin = db.query(AdminOfficer).filter(AdminOfficer.email == clean_email).first()
        if admin:
            if not req.college_code:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="College code is required for admin login",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            return AuthService.authenticate_admin(
                db,
                AdminLoginRequest(
                    college_code=req.college_code,
                    email=req.email,
                    password=req.password
                )
            )

        # 4. If neither matched
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    @staticmethod
    def get_user_profile(
        db: Session,
        user_id_str: str,
        role: UserRole
    ) -> UserProfileResponse:
        """
        Look up user profile by ID and role from JWT claims.
        Ensures user exists and account is active.
        """
        try:
            user_uuid = uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format in token claim"
            )

        if role == UserRole.STUDENT:
            student = db.query(Student).filter(Student.id == user_uuid).first()
            if not student or not student.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User no longer exists or account is inactive"
                )
            return UserProfileResponse(
                id=student.id,
                college_id=student.college_id,
                full_name=student.full_name,
                email=student.email,
                role=UserRole.STUDENT,
                phone_number=student.phone_number,
                is_active=student.is_active
            )
        elif role == UserRole.ADMIN:
            admin = db.query(AdminOfficer).filter(AdminOfficer.id == user_uuid).first()
            if not admin or not admin.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User no longer exists or account is inactive"
                )
            return UserProfileResponse(
                id=admin.id,
                college_id=admin.college_id,
                full_name=admin.full_name,
                email=admin.email,
                role=UserRole.ADMIN,
                phone_number=admin.phone_number,
                department=admin.department,
                designation=admin.designation,
                is_active=admin.is_active
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unsupported role claim"
            )

    @staticmethod
    def create_college_with_admin(
        db: Session,
        college_name: str,
        college_code: str,
        admin_full_name: str,
        admin_email: str,
        admin_password: str,
        college_email: Optional[str] = None,
        college_address: Optional[str] = None,
        admin_department: Optional[str] = "Scholarship Cell",
        admin_designation: Optional[str] = "Verification Officer"
    ) -> Tuple[College, AdminOfficer]:
        """
        Helper method to create a College and its assigned Admin Officer.
        Enforces the rule that each college has exactly ONE admin officer.
        """
        clean_code = college_code.upper().strip()
        clean_email = admin_email.lower().strip()

        # Check existing college
        college = db.query(College).filter(College.college_code == clean_code).first()
        if not college:
            college = College(
                college_name=college_name,
                college_code=clean_code,
                email=college_email,
                address=college_address,
                is_active=True
            )
            db.add(college)
            db.commit()
            db.refresh(college)

        # Check existing admin
        admin = db.query(AdminOfficer).filter(AdminOfficer.college_id == college.id).first()
        if not admin:
            hashed_password = get_password_hash(admin_password)
            admin = AdminOfficer(
                college_id=college.id,
                full_name=admin_full_name,
                email=clean_email,
                password_hash=hashed_password,
                department=admin_department,
                designation=admin_designation,
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        return college, admin

    @staticmethod
    def update_college_code(db: Session, admin_id_str: str, new_code: str) -> dict:
        clean_code = new_code.upper().strip()
        if not clean_code or len(clean_code) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="College code must be at least 3 characters long"
            )

        try:
            admin_uuid = uuid.UUID(admin_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin ID format"
            )

        admin = db.query(AdminOfficer).filter(AdminOfficer.id == admin_uuid).first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin officer not found"
            )

        # Check if another college already uses this college_code
        existing_college = db.query(College).filter(
            College.college_code == clean_code,
            College.id != admin.college_id
        ).first()

        if existing_college:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This college code is already in use by another college."
            )

        college = db.query(College).filter(College.id == admin.college_id).first()
        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College record not found"
            )

        college.college_code = clean_code
        db.commit()
        db.refresh(college)

        return {
            "college_id": str(college.id),
            "college_name": college.college_name,
            "college_code": college.college_code
        }

    @staticmethod
    def get_admin_college(db: Session, admin_id_str: str) -> dict:
        try:
            admin_uuid = uuid.UUID(admin_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin ID format"
            )

        admin = db.query(AdminOfficer).filter(AdminOfficer.id == admin_uuid).first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin officer not found"
            )

        college = db.query(College).filter(College.id == admin.college_id).first()
        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="College record not found"
            )

        return {
            "college_id": str(college.id),
            "college_name": college.college_name,
            "college_code": college.college_code,
            "admin_name": admin.full_name,
            "admin_email": admin.email
        }

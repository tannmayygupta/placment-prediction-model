import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, ForeignKey, JSON, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    profiles = relationship("StudentProfile", back_populates="user", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")

class StudentProfile(Base):
    """Stores the latest/current features of a user."""
    __tablename__ = "student_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Academics
    tenth_pct = Column(Float)
    twelfth_pct = Column(Float)
    cgpa = Column(Float)
    cgpa_scale = Column(Integer)
    branch = Column(String)
    year = Column(Integer)
    backlogs = Column(Integer)
    
    # Coding
    lc_submissions = Column(Integer)
    hr_badges = Column(Integer)
    hr_med_hard_solved = Column(Integer)
    github_contributions = Column(Integer)
    github_collaborations = Column(Integer)
    github_monthly_active = Column(Boolean)
    
    # Experience
    internship_type = Column(String)
    internship_count = Column(Integer)
    internship_stipend_above_10k = Column(Boolean)
    projects_industry = Column(Integer)
    projects_domain = Column(Integer)
    
    # Certs / Actions
    certs_global = Column(Integer)
    certs_nptel = Column(Integer)
    certs_rbu = Column(Integer)
    hackathon_first = Column(Integer)
    hackathon_second = Column(Integer)
    hackathon_third = Column(Integer)
    hackathon_participation = Column(Integer)
    
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="profiles")
    submissions = relationship("Submission", back_populates="profile")

class Submission(Base):
    """A historic snapshot of a model run for a profile."""
    __tablename__ = "submissions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    profile_id = Column(String, ForeignKey("student_profiles.id"), nullable=False)
    
    # Raw Extraction/Resume Data context
    ats_score = Column(Float, nullable=True)
    keyword_gaps = Column(JSON, nullable=True) # List[str]
    processing_ms = Column(Integer, nullable=True)
    
    # Model Outputs
    probability = Column(Float, nullable=False)
    confidence_lower = Column(Float, nullable=False)
    confidence_upper = Column(Float, nullable=False)
    
    matrix_score = Column(Float, nullable=False)
    matrix_breakdown = Column(JSON, nullable=False)
    
    shap_contributions = Column(JSON, nullable=False)
    actions = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="submissions")
    profile = relationship("StudentProfile", back_populates="submissions")

class LOR(Base):
    __tablename__ = "lors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)

    source_type = Column(String, nullable=False)
    institution = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class HackathonCert(Base):
    __tablename__ = "hackathon_certs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)

    event_name = Column(String, nullable=False)
    prize_level = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
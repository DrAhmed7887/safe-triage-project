from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime
from sqlalchemy.sql import func
from .database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, index=True, nullable=True)  # Hospital MRN / Patient ID
    name = Column(String, default="Unknown")  # Patient Name
    age = Column(Float)
    gender = Column(String)
    
    # Store vitals as JSON string or proper JSON type if supported (SQLite supports JSON text)
    vitals = Column(JSON)
    
    chief_complaint = Column(Text)
    
    # Triage Results
    triage_level = Column(Integer)
    triage_color = Column(String)
    triage_label_en = Column(String)
    triage_label_ar = Column(String)
    triage_reasoning = Column(JSON) # Store list of strings as JSON
    triage_red_flags = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

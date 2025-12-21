from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, JSON
from datetime import datetime

Base = declarative_base()

class Person(Base):
    """Person entity representing an individual in the census."""
    __tablename__ = 'persons'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False, index=True)
    dob = Column(Date, nullable=True)
    gender = Column(String, default='Unknown')  # Unknown/Male/Female/Other
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    external_ids = Column(JSON, nullable=True)  # Store as JSON dict
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Person(id={self.id}, name='{self.full_name}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON export."""
        return {
            'id': self.id,
            'full_name': self.full_name,
            'dob': self.dob.isoformat() if self.dob else None,
            'gender': self.gender,
            'address': self.address,
            'notes': self.notes,
            'external_ids': self.external_ids or {}
        }

from sqlalchemy import Column, Integer, String, Date, Text, DateTime, JSON
from datetime import datetime
from sqlalchemy import ForeignKey, UniqueConstraint

from models.person import Base

class Relationship(Base):
    """Relationship between two persons."""
    __tablename__ = 'relationships'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_a_id = Column(Integer, ForeignKey('persons.id', ondelete='CASCADE'), nullable=False)
    person_b_id = Column(Integer, ForeignKey('persons.id', ondelete='CASCADE'), nullable=False)
    relation_type = Column(String, nullable=False)  # parent, spouse, adoptive_parent, guardian
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        UniqueConstraint('person_a_id', 'person_b_id', 'relation_type', name='unique_relationship'),
    )
    
    def __repr__(self):
        return f"<Relationship({self.person_a_id} -> {self.person_b_id}: {self.relation_type})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON export."""
        return {
            'person_a_id': self.person_a_id,
            'person_b_id': self.person_b_id,
            'relation': self.relation_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'notes': self.notes
        }

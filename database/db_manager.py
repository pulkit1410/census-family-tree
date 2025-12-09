"""
Database management and operations.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_PATH, DATABASE_ECHO
from models.person import Base, Person
from models.relationship import Relationship


class AuditLog(Base):
    """Audit log for tracking changes."""
    from sqlalchemy import Column, Integer, String, Text, DateTime
    from datetime import datetime
    
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String, nullable=False)
    user = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    details = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<AuditLog({self.action} at {self.timestamp})>"


class DatabaseManager:
    """Manages database connection and operations."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=DATABASE_ECHO)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._initialized = True
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def log_action(self, session: Session, action: str, details: str = None):
        """Log an action to audit log."""
        log = AuditLog(action=action, details=details)
        session.add(log)
        session.commit()
    
    def get_all_persons(self, session: Session) -> list:
        """Get all persons ordered by name."""
        return session.query(Person).order_by(Person.full_name).all()
    
    def get_person_by_id(self, session: Session, person_id: int) -> Person:
        """Get a person by ID."""
        return session.query(Person).get(person_id)
    
    def get_relationships_for_person(self, session: Session, person_id: int) -> dict:
        """Get all relationships for a person."""
        parents = session.query(Relationship).filter_by(
            person_b_id=person_id, relation_type='parent'
        ).all()
        
        children = session.query(Relationship).filter_by(
            person_a_id=person_id, relation_type='parent'
        ).all()
        
        spouses = session.query(Relationship).filter_by(
            person_a_id=person_id, relation_type='spouse'
        ).all()
        
        return {
            'parents': parents,
            'children': children,
            'spouses': spouses
        }
    
    def search_persons(self, session: Session, search_term: str) -> list:
        """Search persons by name, ID, or address."""
        term = f"%{search_term}%"
        return session.query(Person).filter(
            (Person.full_name.like(term)) |
            (Person.id.like(term)) |
            (Person.address.like(term))
        ).order_by(Person.full_name).all()
    
    def delete_person(self, session: Session, person_id: int):
        """Delete a person and their relationships."""
        person = self.get_person_by_id(session, person_id)
        if person:
            session.delete(person)
            session.commit()
            self.log_action(session, 'delete_person', f"Deleted person ID {person_id}")
    
    def create_person(self, session: Session, **kwargs) -> Person:
        """Create a new person."""
        person = Person(**kwargs)
        session.add(person)
        session.commit()
        self.log_action(session, 'create_person', f"Created person ID {person.id}")
        return person
    
    def update_person(self, session: Session, person: Person):
        """Update a person."""
        from datetime import datetime
        person.updated_at = datetime.now()
        session.commit()
        self.log_action(session, 'update_person', f"Updated person ID {person.id}")
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from models.person import Base

class AuditLog(Base):
    """Audit log for tracking changes."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String, nullable=False)
    user = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    details = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<AuditLog({self.action} at {self.timestamp})>"
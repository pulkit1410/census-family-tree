"""
Business logic validation.
"""
from typing import Tuple
from sqlalchemy.orm import Session

from models.person import Person
from models.relationship import Relationship


class Validator:
    """Validates business rules."""
    
    @staticmethod
    def validate_relationship(session: Session, person_a_id: int, person_b_id: int,
                            relation_type: str) -> Tuple[bool, str]:
        """Validate a relationship before creation."""
        # Self-relationship check
        if person_a_id == person_b_id:
            return False, "Cannot create relationship with self."
        
        # Check if persons exist
        person_a = session.query(Person).get(person_a_id)
        person_b = session.query(Person).get(person_b_id)
        
        if not person_a or not person_b:
            return False, "One or both persons do not exist."
        
        # Age validation for parent-child
        if relation_type == 'parent' and person_a.dob and person_b.dob:
            # person_a is parent, person_b is child
            if person_a.dob >= person_b.dob:
                return False, "Parent must be born before child."
            
            age_diff = (person_b.dob - person_a.dob).days / 365.25
            if age_diff < 12:
                return False, f"Age difference ({age_diff:.1f} years) is less than 12 years. Parent-child relationship may be invalid."
        
        # Check for duplicate relationship
        existing = session.query(Relationship).filter_by(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            relation_type=relation_type
        ).first()
        
        if existing:
            return False, "This relationship already exists."
        
        return True, "Valid"
    
    @staticmethod
    def validate_person_data(full_name: str) -> Tuple[bool, str]:
        """Validate person data."""
        if not full_name or not full_name.strip():
            return False, "Name is required."
        
        if len(full_name) > 200:
            return False, "Name is too long (max 200 characters)."
        
        return True, "Valid"
    
    @staticmethod
    def validate_merge(session: Session, primary: Person, duplicates: list) -> Tuple[bool, str]:
        """Validate a merge operation."""
        if not duplicates:
            return False, "No duplicates selected to merge."
        
        if primary in duplicates:
            return False, "Primary record cannot be in duplicates list."
        
        # Check all persons exist
        for dup in duplicates:
            if not session.query(Person).get(dup.id):
                return False, f"Person ID {dup.id} does not exist."
        
        return True, "Valid"
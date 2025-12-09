from models.person import Person
from models.relationship import Relationship
from config import DUPLICATE_CONFIG
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database.db_manager import DatabaseManager

# Check for rapidfuzz availability
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    
    

class DuplicateDetector:
    """Detects and merges duplicate person records."""
    
    @staticmethod
    def find_duplicates(session: Session) -> List[List[Person]]:
        """
        Find potential duplicate persons using exact and fuzzy matching.
        Returns list of duplicate groups.
        """
        all_persons = session.query(Person).all()
        duplicate_groups = []
        processed_ids = set()
        
        for i, person_a in enumerate(all_persons):
            if person_a.id in processed_ids:
                continue
            
            group = [person_a]
            
            for person_b in all_persons[i+1:]:
                if person_b.id in processed_ids:
                    continue
                
                score = DuplicateDetector._calculate_similarity(person_a, person_b)
                
                # Exact match or high similarity
                if score >= 0.75:
                    group.append(person_b)
                    processed_ids.add(person_b.id)
            
            if len(group) > 1:
                duplicate_groups.append(group)
                for p in group:
                    processed_ids.add(p.id)
        
        return duplicate_groups
    
    @staticmethod
    def _calculate_similarity(person_a: Person, person_b: Person) -> float:
        """
        Calculate similarity score between two persons.
        Score = 0.6 * name_sim + 0.3 * dob_match + 0.1 * id_match
        """
        # Name similarity
        name_a = person_a.full_name.lower().strip()
        name_b = person_b.full_name.lower().strip()
        
        if RAPIDFUZZ_AVAILABLE:
            name_sim = fuzz.ratio(name_a, name_b) / 100.0
        else:
            # Fallback: exact match only
            name_sim = 1.0 if name_a == name_b else 0.0
        
        # DOB match
        dob_match = 0.0
        if person_a.dob and person_b.dob:
            if person_a.dob == person_b.dob:
                dob_match = 1.0
            elif person_a.dob.year == person_b.dob.year:
                dob_match = 0.5
        elif person_a.dob is None and person_b.dob is None:
            dob_match = 0.5  # Both null - partial match
        
        # External ID or address match
        id_match = 0.0
        
        # Check external IDs
        if person_a.external_ids and person_b.external_ids:
            ids_a = set(person_a.external_ids.values())
            ids_b = set(person_b.external_ids.values())
            if ids_a & ids_b:  # Intersection
                id_match = 1.0
        
        # Check address if no ID match
        if id_match == 0.0 and person_a.address and person_b.address:
            addr_a = person_a.address.lower().strip()
            addr_b = person_b.address.lower().strip()
            if RAPIDFUZZ_AVAILABLE:
                addr_sim = fuzz.ratio(addr_a, addr_b) / 100.0
                if addr_sim > 0.8:
                    id_match = addr_sim
            else:
                if addr_a == addr_b:
                    id_match = 1.0
        
        # Calculate weighted score
        score = 0.6 * name_sim + 0.3 * dob_match + 0.1 * id_match
        return score
    
    @staticmethod
    def merge_persons(session: Session, primary: Person, duplicates: List[Person]) -> Person:
        """
        Merge duplicate persons into primary record.
        Transfers relationships and removes duplicates.
        """
        details = f"Merging persons {[d.id for d in duplicates]} into {primary.id}"
        
        for dup in duplicates:
            # Merge fields (keep primary if it has value, else take from duplicate)
            if not primary.dob and dup.dob:
                primary.dob = dup.dob
            if not primary.address and dup.address:
                primary.address = dup.address
            if not primary.notes:
                primary.notes = dup.notes
            elif dup.notes:
                primary.notes += f"\n[Merged]: {dup.notes}"
            if not primary.external_ids and dup.external_ids:
                primary.external_ids = dup.external_ids
            elif dup.external_ids:
                if not primary.external_ids:
                    primary.external_ids = {}
                primary.external_ids.update(dup.external_ids)
            
            # Transfer relationships
            # Relations where duplicate is person_a
            rels_a = session.query(Relationship).filter_by(person_a_id=dup.id).all()
            for rel in rels_a:
                if rel.person_b_id == primary.id:
                    # Would create self-relation, skip
                    session.delete(rel)
                    continue
                
                # Check if relation already exists
                existing = session.query(Relationship).filter_by(
                    person_a_id=primary.id,
                    person_b_id=rel.person_b_id,
                    relation_type=rel.relation_type
                ).first()
                
                if not existing:
                    rel.person_a_id = primary.id
                else:
                    session.delete(rel)
            
            # Relations where duplicate is person_b
            rels_b = session.query(Relationship).filter_by(person_b_id=dup.id).all()
            for rel in rels_b:
                if rel.person_a_id == primary.id:
                    # Would create self-relation, skip
                    session.delete(rel)
                    continue
                
                # Check if relation already exists
                existing = session.query(Relationship).filter_by(
                    person_a_id=rel.person_a_id,
                    person_b_id=primary.id,
                    relation_type=rel.relation_type
                ).first()
                
                if not existing:
                    rel.person_b_id = primary.id
                else:
                    session.delete(rel)
            
            # Delete duplicate
            session.delete(dup)
        
        primary.updated_at = datetime.now()
        session.commit()
        
        # Log merge
        db_manager = DatabaseManager()
        db_manager.log_action(session, 'merge_persons', details)
        
        return primary

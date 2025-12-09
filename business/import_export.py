from models.person import Person
from models.relationship import Relationship
import json
from datetime import datetime
from sqlalchemy.orm import Session
from database.db_manager import DatabaseManager


class ImportExport:
    """Handles JSON import and export."""
    
    @staticmethod
    def export_to_json(self , session: Session, filepath: str):
        """Export database to JSON file."""
        persons = session.query(Person).all()
        relationships = session.query(Relationship).all()
        
        data = {
            'people': [p.to_dict() for p in persons],
            'relationships': [r.to_dict() for r in relationships]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        db_manager = DatabaseManager()
        db_manager.log_action(session, 'export_json', f"Exported to {filepath}")
    
    @staticmethod
    def import_from_json(self ,session: Session, filepath: str, remap_ids: bool = True):
        """Import data from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        id_mapping = {}  # Old ID -> New ID
        
        # Import persons
        for person_data in data.get('people', []):
            old_id = person_data['id']
            
            # Check if ID exists
            existing = session.query(Person).get(old_id) if not remap_ids else None
            
            if existing and not remap_ids:
                # Update existing
                for key, value in person_data.items():
                    if key != 'id' and hasattr(existing, key):
                        if key == 'dob' and value:
                            value = datetime.fromisoformat(value).date()
                        setattr(existing, key, value)
                id_mapping[old_id] = old_id
            else:
                # Create new
                person_data_copy = person_data.copy()
                if remap_ids:
                    person_data_copy.pop('id', None)
                
                if person_data_copy.get('dob'):
                    person_data_copy['dob'] = datetime.fromisoformat(person_data_copy['dob']).date()
                
                new_person = Person(**person_data_copy)
                session.add(new_person)
                session.flush()  # Get new ID
                id_mapping[old_id] = new_person.id
        
        session.commit()
        
        # Import relationships
        for rel_data in data.get('relationships', []):
            new_a_id = id_mapping.get(rel_data['person_a_id'])
            new_b_id = id_mapping.get(rel_data['person_b_id'])
            
            if new_a_id and new_b_id:
                # Check if exists
                existing = session.query(Relationship).filter_by(
                    person_a_id=new_a_id,
                    person_b_id=new_b_id,
                    relation_type=rel_data['relation']
                ).first()
                
                if not existing:
                    rel_data_copy = {
                        'person_a_id': new_a_id,
                        'person_b_id': new_b_id,
                        'relation_type': rel_data['relation'],
                        'notes': rel_data.get('notes')
                    }
                    
                    if rel_data.get('start_date'):
                        rel_data_copy['start_date'] = datetime.fromisoformat(rel_data['start_date']).date()
                    if rel_data.get('end_date'):
                        rel_data_copy['end_date'] = datetime.fromisoformat(rel_data['end_date']).date()
                    
                    new_rel = Relationship(**rel_data_copy)
                    session.add(new_rel)
        
        session.commit()
        db_manager = DatabaseManager()
        db_manager.log_action(session, 'import_json', f"Imported from {filepath}")


from datetime import date
from sqlalchemy.orm import Session
from models.person import Person
from models.relationship import Relationship
from database.db_manager import DatabaseManager


def create_sample_data(session: Session):
    """Create sample data if database is empty."""
    
    # Check if data exists
    count = session.query(Person).count()
    if count > 0:
        return  # Data already exists
    
    print("Creating sample data...")
    
    # Create persons
    rajesh = Person(
        full_name="Rajesh Sharma",
        dob=date(1975, 3, 21),
        gender="Male",
        address="123 Main Street, Mumbai, Maharashtra",
        notes="Head of household",
        external_ids={"aadhaar": "1234-5678-9012"}
    )
    session.add(rajesh)
    
    sita = Person(
        full_name="Sita Sharma",
        dob=date(1977, 9, 11),
        gender="Female",
        address="123 Main Street, Mumbai, Maharashtra",
        external_ids={"aadhaar": "9876-5432-1098"}
    )
    session.add(sita)
    
    aman = Person(
        full_name="Aman Sharma",
        dob=date(2001, 2, 2),
        gender="Male",
        address="123 Main Street, Mumbai, Maharashtra",
        notes="Student at University"
    )
    session.add(aman)
    
    anita = Person(
        full_name="Anita R",
        dob=date(2003, 7, 7),
        gender="Female",
        address="123 Main Street, Mumbai, Maharashtra"
    )
    session.add(anita)
    
    # Create a duplicate for testing
    aman_dup = Person(
        full_name="Aman Sharma",
        dob=date(2001, 2, 2),
        gender="Male",
        notes="Duplicate record for testing merge functionality"
    )
    session.add(aman_dup)
    
    session.commit()
    
    # Create relationships
    # Rajesh and Sita are spouses
    spouse_rel_1 = Relationship(
        person_a_id=rajesh.id,
        person_b_id=sita.id,
        relation_type='spouse',
        start_date=date(2000, 5, 15)
    )
    session.add(spouse_rel_1)
    
    spouse_rel_2 = Relationship(
        person_a_id=sita.id,
        person_b_id=rajesh.id,
        relation_type='spouse',
        start_date=date(2000, 5, 15)
    )
    session.add(spouse_rel_2)
    
    # Rajesh is parent of Aman
    parent_rel_1 = Relationship(
        person_a_id=rajesh.id,
        person_b_id=aman.id,
        relation_type='parent'
    )
    session.add(parent_rel_1)
    
    # Sita is parent of Aman
    parent_rel_2 = Relationship(
        person_a_id=sita.id,
        person_b_id=aman.id,
        relation_type='parent'
    )
    session.add(parent_rel_2)
    
    # Rajesh is parent of Anita
    parent_rel_3 = Relationship(
        person_a_id=rajesh.id,
        person_b_id=anita.id,
        relation_type='parent'
    )
    session.add(parent_rel_3)
    
    # Sita is parent of Anita
    parent_rel_4 = Relationship(
        person_a_id=sita.id,
        person_b_id=anita.id,
        relation_type='parent'
    )
    session.add(parent_rel_4)
    
    session.commit()
    
    # Log creation
    db_manager = DatabaseManager()
    db_manager.log_action(session, 'create_sample_data', 'Created sample family data')
    
    print("Sample data created successfully!")
    print(f"  - Created {session.query(Person).count()} persons")
    print(f"  - Created {session.query(Relationship).count()} relationships")
    print("  - Includes 1 duplicate record (Aman Sharma) for testing merge functionality")

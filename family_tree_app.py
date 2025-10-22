#!/usr/bin/env python3
"""
Family Tree / Census Helper Application
========================================

A desktop application for census workers to create, view, edit and manage family trees.

REQUIREMENTS:
-------------
System dependencies:
  - Graphviz (system binary): https://graphviz.org/download/
    * Windows: Download installer and add to PATH
    * Linux: sudo apt-get install graphviz
    * macOS: brew install graphviz

Python dependencies:
  pip install PySide6 sqlalchemy graphviz pillow rapidfuzz

USAGE:
------
  python family_tree_app.py

FEATURES:
---------
  - Add/edit/delete persons with detailed information
  - Create parent-child and spouse relationships
  - Visual family tree rendering with Graphviz
  - Duplicate detection with fuzzy matching
  - Merge duplicate records
  - Import/export to JSON
  - Audit logging
  - Search and filtering

KEYBOARD SHORTCUTS:
-------------------
  Ctrl+N: New person
  Ctrl+E: Edit person
  Ctrl+D: Delete person
  Ctrl+F: Find duplicates
  Ctrl+S: Export data

Author: Generated for Census Helper System
Version: 1.0
"""

import sys
import json
import io
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple, Any
from pathlib import Path

# Qt imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit,
    QTextEdit, QComboBox, QDateEdit, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QSplitter, QToolBar, QTableWidget,
    QTableWidgetItem, QCheckBox, QSpinBox, QFileDialog, QScrollArea,
    QGroupBox, QHeaderView
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QPixmap, QImage, QAction, QKeySequence

# Database imports
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Date, DateTime,
    ForeignKey, UniqueConstraint, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship as db_relationship, Session

# Other imports
import graphviz
from PIL import Image
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("Warning: rapidfuzz not available. Duplicate detection will use basic matching.")

# ============================================================================
# DATABASE MODELS
# ============================================================================

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


# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================

class DatabaseManager:
    """Manages database connection and operations."""
    
    def __init__(self, db_path='family.db'):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def log_action(self, session: Session, action: str, details: str = None):
        """Log an action to audit log."""
        log = AuditLog(action=action, details=details)
        session.add(log)
        session.commit()


# ============================================================================
# BUSINESS LOGIC - DUPLICATE DETECTION
# ============================================================================

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
        db_manager.log_action(session, 'merge_persons', details)
        
        return primary


# ============================================================================
# BUSINESS LOGIC - VALIDATION
# ============================================================================

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
        
        return True, "Valid"


# ============================================================================
# BUSINESS LOGIC - IMPORT/EXPORT
# ============================================================================

class ImportExport:
    """Handles JSON import and export."""
    
    @staticmethod
    def export_to_json(session: Session, filepath: str):
        """Export database to JSON file."""
        persons = session.query(Person).all()
        relationships = session.query(Relationship).all()
        
        data = {
            'people': [p.to_dict() for p in persons],
            'relationships': [r.to_dict() for r in relationships]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        db_manager.log_action(session, 'export_json', f"Exported to {filepath}")
    
    @staticmethod
    def import_from_json(session: Session, filepath: str, remap_ids: bool = True):
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
        db_manager.log_action(session, 'import_json', f"Imported from {filepath}")


# ============================================================================
# VISUALIZATION - GRAPHVIZ RENDERING
# ============================================================================

class TreeVisualizer:
    """Generates family tree visualizations using Graphviz."""
    
    @staticmethod
    def generate_tree(session: Session, person_id: int, depth: int = 2) -> QPixmap:
        """
        Generate family tree visualization for a person.
        Returns QPixmap for display in Qt.
        """
        person = session.query(Person).get(person_id)
        if not person:
            return QPixmap()
        
        # Create graph
        dot = graphviz.Digraph(comment=f'Family Tree for {person.full_name}')
        dot.attr(rankdir='TB')  # Top to bottom
        dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
        
        visited = set()
        
        # Add central person
        TreeVisualizer._add_person_node(dot, person, highlight=True)
        visited.add(person.id)
        
        # Add ancestors (parents)
        TreeVisualizer._add_ancestors(session, dot, person, visited, depth)
        
        # Add descendants (children)
        TreeVisualizer._add_descendants(session, dot, person, visited, depth)
        
        # Add spouses
        TreeVisualizer._add_spouses(session, dot, person, visited)
        
        # Render to PNG
        try:
            png_data = dot.pipe(format='png')
            image = QImage()
            image.loadFromData(png_data)
            return QPixmap.fromImage(image)
        except Exception as e:
            print(f"Error rendering graph: {e}")
            return QPixmap()
    
    @staticmethod
    def _add_person_node(dot, person: Person, highlight: bool = False):
        """Add a person node to the graph."""
        label = f"{person.full_name}\n(ID: {person.id})"
        if person.dob:
            label += f"\n{person.dob.strftime('%Y-%m-%d')}"
        
        color = 'gold' if highlight else 'lightblue'
        dot.node(str(person.id), label, fillcolor=color)
    
    @staticmethod
    def _add_ancestors(session: Session, dot, person: Person, visited: set, depth: int, current_depth: int = 0):
        """Recursively add ancestors (parents)."""
        if current_depth >= depth:
            return
        
        # Find parents (where person is person_b in parent relationship)
        parent_rels = session.query(Relationship).filter_by(
            person_b_id=person.id,
            relation_type='parent'
        ).all()
        
        for rel in parent_rels:
            parent = session.query(Person).get(rel.person_a_id)
            if parent and parent.id not in visited:
                TreeVisualizer._add_person_node(dot, parent)
                visited.add(parent.id)
                dot.edge(str(parent.id), str(person.id), label='parent')
                
                # Recurse
                TreeVisualizer._add_ancestors(session, dot, parent, visited, depth, current_depth + 1)
    
    @staticmethod
    def _add_descendants(session: Session, dot, person: Person, visited: set, depth: int, current_depth: int = 0):
        """Recursively add descendants (children)."""
        if current_depth >= depth:
            return
        
        # Find children (where person is person_a in parent relationship)
        child_rels = session.query(Relationship).filter_by(
            person_a_id=person.id,
            relation_type='parent'
        ).all()
        
        for rel in child_rels:
            child = session.query(Person).get(rel.person_b_id)
            if child and child.id not in visited:
                TreeVisualizer._add_person_node(dot, child)
                visited.add(child.id)
                dot.edge(str(person.id), str(child.id), label='parent')
                
                # Recurse
                TreeVisualizer._add_descendants(session, dot, child, visited, depth, current_depth + 1)
    
    @staticmethod
    def _add_spouses(session: Session, dot, person: Person, visited: set):
        """Add spouse relationships."""
        # Find spouse relationships
        spouse_rels = session.query(Relationship).filter(
            ((Relationship.person_a_id == person.id) | (Relationship.person_b_id == person.id)),
            Relationship.relation_type == 'spouse'
        ).all()
        
        for rel in spouse_rels:
            spouse_id = rel.person_b_id if rel.person_a_id == person.id else rel.person_a_id
            spouse = session.query(Person).get(spouse_id)
            
            if spouse and spouse.id not in visited:
                TreeVisualizer._add_person_node(dot, spouse)
                visited.add(spouse.id)
                dot.edge(str(person.id), str(spouse.id), label='spouse', dir='both', style='dashed')


# ============================================================================
# GUI - PERSON FORM DIALOG
# ============================================================================

class PersonFormDialog(QDialog):
    """Dialog for adding or editing a person."""
    
    def __init__(self, parent=None, person: Person = None, session: Session = None):
        super().__init__(parent)
        self.person = person
        self.session = session
        self.is_edit = person is not None
        
        self.setWindowTitle("Edit Person" if self.is_edit else "Add Person")
        self.setMinimumWidth(500)
        
        self.setup_ui()
        
        if self.is_edit:
            self.load_person_data()
    
    def setup_ui(self):
        """Setup the form UI."""
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Full Name
        self.name_input = QLineEdit()
        form.addRow("Full Name*:", self.name_input)
        
        # Date of Birth
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setDate(QDate.currentDate())
        self.dob_input.setSpecialValueText("Unknown")
        self.dob_checkbox = QCheckBox("Date of Birth Known")
        self.dob_checkbox.stateChanged.connect(self.toggle_dob)
        dob_layout = QHBoxLayout()
        dob_layout.addWidget(self.dob_input)
        dob_layout.addWidget(self.dob_checkbox)
        form.addRow("Date of Birth:", dob_layout)
        
        # Gender
        self.gender_input = QComboBox()
        self.gender_input.addItems(['Unknown', 'Male', 'Female', 'Other'])
        form.addRow("Gender:", self.gender_input)
        
        # Address
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(60)
        form.addRow("Address:", self.address_input)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        form.addRow("Notes:", self.notes_input)
        
        # External IDs
        self.ext_id_input = QTextEdit()
        self.ext_id_input.setMaximumHeight(60)
        self.ext_id_input.setPlaceholderText("Format: key=value (one per line)\ne.g., aadhaar=1234567890")
        form.addRow("External IDs:", self.ext_id_input)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_form)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def toggle_dob(self, state):
        """Toggle DOB input enabled state."""
        self.dob_input.setEnabled(state == Qt.Checked)
    
    def load_person_data(self):
        """Load person data into form."""
        self.name_input.setText(self.person.full_name)
        
        if self.person.dob:
            qdate = QDate(self.person.dob.year, self.person.dob.month, self.person.dob.day)
            self.dob_input.setDate(qdate)
            self.dob_checkbox.setChecked(True)
            self.dob_input.setEnabled(True)
        else:
            self.dob_checkbox.setChecked(False)
            self.dob_input.setEnabled(False)
        
        self.gender_input.setCurrentText(self.person.gender)
        
        if self.person.address:
            self.address_input.setPlainText(self.person.address)
        
        if self.person.notes:
            self.notes_input.setPlainText(self.person.notes)
        
        if self.person.external_ids:
            ext_id_text = '\n'.join([f"{k}={v}" for k, v in self.person.external_ids.items()])
            self.ext_id_input.setPlainText(ext_id_text)
    
    def accept_form(self):
        """Validate and accept form."""
        name = self.name_input.text().strip()
        
        valid, msg = Validator.validate_person_data(name)
        if not valid:
            QMessageBox.warning(self, "Validation Error", msg)
            return
        
        # Parse external IDs
        ext_ids = {}
        ext_id_text = self.ext_id_input.toPlainText().strip()
        if ext_id_text:
            for line in ext_id_text.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    ext_ids[key.strip()] = value.strip()
        
        # Get DOB
        dob = None
        if self.dob_checkbox.isChecked():
            qdate = self.dob_input.date()
            dob = date(qdate.year(), qdate.month(), qdate.day())
        
        # Create or update person
        if self.is_edit:
            self.person.full_name = name
            self.person.dob = dob
            self.person.gender = self.gender_input.currentText()
            self.person.address = self.address_input.toPlainText().strip() or None
            self.person.notes = self.notes_input.toPlainText().strip() or None
            self.person.external_ids = ext_ids if ext_ids else None
            self.person.updated_at = datetime.now()
            
            self.session.commit()
            db_manager.log_action(self.session, 'edit_person', f"Edited person ID {self.person.id}")
        else:
            self.person = Person(
                full_name=name,
                dob=dob,
                gender=self.gender_input.currentText(),
                address=self.address_input.toPlainText().strip() or None,
                notes=self.notes_input.toPlainText().strip() or None,
                external_ids=ext_ids if ext_ids else None
            )
            self.session.add(self.person)
            self.session.commit()
            db_manager.log_action(self.session, 'create_person', f"Created person ID {self.person.id}")
        
        self.accept()
    
    def get_person(self) -> Person:
        """Get the created/edited person."""
        return self.person


# ============================================================================
# GUI - RELATIONSHIP FORM DIALOG
# ============================================================================

class RelationshipFormDialog(QDialog):
    """Dialog for adding a relationship."""
    
    def __init__(self, parent=None, session: Session = None, person_a: Person = None):
        super().__init__(parent)
        self.session = session
        self.person_a = person_a
        self.relationship = None
        
        self.setWindowTitle("Add Relationship")
        self.setMinimumWidth(500)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the form UI."""
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        # Person A (parent/spouse)
        self.person_a_combo = QComboBox()
        self.load_persons(self.person_a_combo)
        if self.person_a:
            for i in range(self.person_a_combo.count()):
                if self.person_a_combo.itemData(i) == self.person_a.id:
                    self.person_a_combo.setCurrentIndex(i)
                    break
        form.addRow("Person A:", self.person_a_combo)
        
        # Relation Type
        self.relation_type = QComboBox()
        self.relation_type.addItems(['parent', 'spouse', 'adoptive_parent', 'guardian'])
        self.relation_type.currentTextChanged.connect(self.update_labels)
        form.addRow("Relationship Type:", self.relation_type)
        
        # Person B (child/spouse)
        self.person_b_label = QLabel("Person B (Child):")
        self.person_b_combo = QComboBox()
        self.load_persons(self.person_b_combo)
        form.addRow(self.person_b_label, self.person_b_combo)
        
        # Start Date
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setSpecialValueText("Unknown")
        self.start_checkbox = QCheckBox("Has Start Date")
        self.start_checkbox.stateChanged.connect(lambda s: self.start_date.setEnabled(s == Qt.Checked))
        start_layout = QHBoxLayout()
        start_layout.addWidget(self.start_date)
        start_layout.addWidget(self.start_checkbox)
        form.addRow("Start Date:", start_layout)
        self.start_date.setEnabled(False)
        
        # End Date
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setSpecialValueText("Unknown")
        self.end_checkbox = QCheckBox("Has End Date")
        self.end_checkbox.stateChanged.connect(lambda s: self.end_date.setEnabled(s == Qt.Checked))
        end_layout = QHBoxLayout()
        end_layout.addWidget(self.end_date)
        end_layout.addWidget(self.end_checkbox)
        form.addRow("End Date:", end_layout)
        self.end_date.setEnabled(False)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        form.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form)
        
        # Info label
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: blue; font-style: italic;")
        layout.addWidget(self.info_label)
        self.update_labels()
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_form)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_persons(self, combo: QComboBox):
        """Load all persons into combo box."""
        persons = self.session.query(Person).order_by(Person.full_name).all()
        for person in persons:
            label = f"{person.full_name} (ID: {person.id})"
            combo.addItem(label, person.id)
    
    def update_labels(self):
        """Update labels based on relationship type."""
        rel_type = self.relation_type.currentText()
        
        if rel_type == 'parent':
            self.person_b_label.setText("Person B (Child):")
            self.info_label.setText("Person A is the parent of Person B")
        elif rel_type == 'spouse':
            self.person_b_label.setText("Person B (Spouse):")
            self.info_label.setText("Person A and Person B are spouses (bidirectional)")
        elif rel_type == 'adoptive_parent':
            self.person_b_label.setText("Person B (Adopted Child):")
            self.info_label.setText("Person A is the adoptive parent of Person B")
        elif rel_type == 'guardian':
            self.person_b_label.setText("Person B (Ward):")
            self.info_label.setText("Person A is the guardian of Person B")
    
    def accept_form(self):
        """Validate and accept form."""
        person_a_id = self.person_a_combo.currentData()
        person_b_id = self.person_b_combo.currentData()
        rel_type = self.relation_type.currentText()
        
        # Validate
        valid, msg = Validator.validate_relationship(self.session, person_a_id, person_b_id, rel_type)
        
        if not valid:
            # For age warnings, show confirmation dialog
            if "12 years" in msg:
                reply = QMessageBox.question(
                    self, "Age Warning",
                    f"{msg}\n\nDo you want to proceed anyway?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            else:
                QMessageBox.warning(self, "Validation Error", msg)
                return
        
        # Get dates
        start = None
        if self.start_checkbox.isChecked():
            qdate = self.start_date.date()
            start = date(qdate.year(), qdate.month(), qdate.day())
        
        end = None
        if self.end_checkbox.isChecked():
            qdate = self.end_date.date()
            end = date(qdate.year(), qdate.month(), qdate.day())
        
        # Create relationship
        self.relationship = Relationship(
            person_a_id=person_a_id,
            person_b_id=person_b_id,
            relation_type=rel_type,
            start_date=start,
            end_date=end,
            notes=self.notes_input.toPlainText().strip() or None
        )
        self.session.add(self.relationship)
        
        # For spouse, create reciprocal relationship
        if rel_type == 'spouse':
            reciprocal = Relationship(
                person_a_id=person_b_id,
                person_b_id=person_a_id,
                relation_type='spouse',
                start_date=start,
                end_date=end,
                notes=self.notes_input.toPlainText().strip() or None
            )
            self.session.add(reciprocal)
        
        self.session.commit()
        db_manager.log_action(self.session, 'create_relationship',
                            f"Created {rel_type} relationship: {person_a_id} -> {person_b_id}")
        
        self.accept()


# ============================================================================
# GUI - DUPLICATE DETECTION DIALOG
# ============================================================================

class DuplicateDetectionDialog(QDialog):
    """Dialog for detecting and merging duplicates."""
    
    def __init__(self, parent=None, session: Session = None):
        super().__init__(parent)
        self.session = session
        self.duplicate_groups = []
        
        self.setWindowTitle("Duplicate Detection")
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
        self.find_duplicates()
    
    def setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout()
        
        # Instructions
        info = QLabel("Select duplicate records to merge. The first selected record will be the primary.")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Select', 'ID', 'Name', 'DOB', 'Address', 'Similarity Score'])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.merge_btn = QPushButton("Merge Selected")
        self.merge_btn.clicked.connect(self.merge_selected)
        button_layout.addWidget(self.merge_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.find_duplicates)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def find_duplicates(self):
        """Find and display duplicates."""
        self.table.setRowCount(0)
        self.duplicate_groups = DuplicateDetector.find_duplicates(self.session)
        
        if not self.duplicate_groups:
            QMessageBox.information(self, "No Duplicates", "No duplicate records found.")
            return
        
        row = 0
        for group in self.duplicate_groups:
            # Add separator row
            if row > 0:
                self.table.insertRow(row)
                separator = QTableWidgetItem("--- New Group ---")
                separator.setBackground(Qt.lightGray)
                self.table.setItem(row, 1, separator)
                self.table.setSpan(row, 1, 1, 5)
                row += 1
            
            # Calculate scores for group
            base_person = group[0]
            for person in group:
                self.table.insertRow(row)
                
                # Checkbox
                checkbox = QCheckBox()
                checkbox.setProperty('person_id', person.id)
                checkbox.setProperty('group_idx', len(self.duplicate_groups) - 1)
                self.table.setCellWidget(row, 0, checkbox)
                
                # Data
                self.table.setItem(row, 1, QTableWidgetItem(str(person.id)))
                self.table.setItem(row, 2, QTableWidgetItem(person.full_name))
                self.table.setItem(row, 3, QTableWidgetItem(person.dob.isoformat() if person.dob else 'N/A'))
                self.table.setItem(row, 4, QTableWidgetItem(person.address[:50] if person.address else 'N/A'))
                
                # Score
                if person.id != base_person.id:
                    score = DuplicateDetector._calculate_similarity(base_person, person)
                    self.table.setItem(row, 5, QTableWidgetItem(f"{score:.2f}"))
                else:
                    self.table.setItem(row, 5, QTableWidgetItem("Base"))
                
                row += 1
        
        self.table.resizeColumnsToContents()
    
    def merge_selected(self):
        """Merge selected records."""
        selected_persons = []
        
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                person_id = checkbox.property('person_id')
                person = self.session.query(Person).get(person_id)
                if person:
                    selected_persons.append(person)
        
        if len(selected_persons) < 2:
            QMessageBox.warning(self, "Selection Error", "Please select at least 2 records to merge.")
            return
        
        # First selected is primary
        primary = selected_persons[0]
        duplicates = selected_persons[1:]
        
        # Confirm
        names = ', '.join([p.full_name for p in duplicates])
        reply = QMessageBox.question(
            self, "Confirm Merge",
            f"Merge {names} into {primary.full_name}?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                DuplicateDetector.merge_persons(self.session, primary, duplicates)
                QMessageBox.information(self, "Success", "Records merged successfully.")
                self.find_duplicates()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error merging records: {str(e)}")


# ============================================================================
# GUI - MAIN WINDOW
# ============================================================================

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.session = db_manager.get_session()
        self.current_person = None
        
        self.setWindowTitle("Family Tree / Census Helper")
        self.setMinimumSize(1200, 800)
        
        self.setup_ui()
        self.setup_menu()
        self.setup_shortcuts()
        
        self.refresh_person_list()
    
    def setup_ui(self):
        """Setup the main UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout()
        
        # Left panel - Person list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Name, ID, DOB...")
        self.search_input.textChanged.connect(self.filter_persons)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)
        
        # Person list
        self.person_list = QListWidget()
        self.person_list.itemClicked.connect(self.on_person_selected)
        left_layout.addWidget(self.person_list)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Person")
        add_btn.clicked.connect(self.add_person)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_person)
        btn_layout.addWidget(edit_btn)
        
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self.delete_person)
        btn_layout.addWidget(del_btn)
        
        left_layout.addLayout(btn_layout)
        
        left_panel.setLayout(left_layout)
        
        # Right panel - Details and tree
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Person details
        details_group = QGroupBox("Person Details")
        details_layout = QVBoxLayout()
        self.details_label = QLabel("Select a person to view details")
        self.details_label.setWordWrap(True)
        details_layout.addWidget(self.details_label)
        
        # Relationship button
        self.add_rel_btn = QPushButton("Add Relationship")
        self.add_rel_btn.clicked.connect(self.add_relationship)
        self.add_rel_btn.setEnabled(False)
        details_layout.addWidget(self.add_rel_btn)
        
        details_group.setLayout(details_layout)
        right_layout.addWidget(details_group)
        
        # Tree visualization
        tree_group = QGroupBox("Family Tree")
        tree_layout = QVBoxLayout()
        
        # Depth control
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Tree Depth:"))
        self.depth_spin = QSpinBox()
        self.depth_spin.setMinimum(1)
        self.depth_spin.setMaximum(5)
        self.depth_spin.setValue(2)
        self.depth_spin.valueChanged.connect(self.refresh_tree)
        depth_layout.addWidget(self.depth_spin)
        depth_layout.addStretch()
        tree_layout.addLayout(depth_layout)
        
        # Tree display
        self.tree_scroll = QScrollArea()
        self.tree_label = QLabel("Select a person to view family tree")
        self.tree_label.setAlignment(Qt.AlignCenter)
        self.tree_scroll.setWidget(self.tree_label)
        self.tree_scroll.setWidgetResizable(True)
        tree_layout.addWidget(self.tree_scroll)
        
        tree_group.setLayout(tree_layout)
        right_layout.addWidget(tree_group)
        
        right_panel.setLayout(right_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        central.setLayout(main_layout)
    
    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        import_action = QAction("Import JSON...", self)
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction("Export JSON...", self)
        export_action.setShortcut(QKeySequence("Ctrl+S"))
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        add_person_action = QAction("Add Person", self)
        add_person_action.setShortcut(QKeySequence("Ctrl+N"))
        add_person_action.triggered.connect(self.add_person)
        edit_menu.addAction(add_person_action)
        
        edit_person_action = QAction("Edit Person", self)
        edit_person_action.setShortcut(QKeySequence("Ctrl+E"))
        edit_person_action.triggered.connect(self.edit_person)
        edit_menu.addAction(edit_person_action)
        
        delete_person_action = QAction("Delete Person", self)
        delete_person_action.setShortcut(QKeySequence("Ctrl+D"))
        delete_person_action.triggered.connect(self.delete_person)
        edit_menu.addAction(delete_person_action)
        
        edit_menu.addSeparator()
        
        find_dup_action = QAction("Find Duplicates", self)
        find_dup_action.setShortcut(QKeySequence("Ctrl+F"))
        find_dup_action.triggered.connect(self.find_duplicates)
        edit_menu.addAction(find_dup_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        test_action = QAction("Test Plan", self)
        test_action.triggered.connect(self.show_test_plan)
        help_menu.addAction(test_action)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        pass  # Already done in menu
    
    def refresh_person_list(self, search_term: str = ""):
        """Refresh the person list."""
        self.person_list.clear()
        
        query = self.session.query(Person)
        
        if search_term:
            term = f"%{search_term}%"
            query = query.filter(
                (Person.full_name.like(term)) |
                (Person.id.like(term)) |
                (Person.address.like(term))
            )
        
        persons = query.order_by(Person.full_name).all()
        
        for person in persons:
            dob_str = person.dob.strftime('%Y-%m-%d') if person.dob else 'N/A'
            item = QListWidgetItem(f"{person.full_name} (ID: {person.id}, DOB: {dob_str})")
            item.setData(Qt.UserRole, person.id)
            self.person_list.addItem(item)
    
    def filter_persons(self):
        """Filter persons based on search."""
        search_term = self.search_input.text().strip()
        self.refresh_person_list(search_term)
    
    def on_person_selected(self, item: QListWidgetItem):
        """Handle person selection."""
        person_id = item.data(Qt.UserRole)
        self.current_person = self.session.query(Person).get(person_id)
        
        if self.current_person:
            self.display_person_details()
            self.refresh_tree()
            self.add_rel_btn.setEnabled(True)
    
    def display_person_details(self):
        """Display details of selected person."""
        p = self.current_person
        
        details = f"<h3>{p.full_name}</h3>"
        details += f"<p><b>ID:</b> {p.id}</p>"
        details += f"<p><b>DOB:</b> {p.dob.strftime('%Y-%m-%d') if p.dob else 'Unknown'}</p>"
        details += f"<p><b>Gender:</b> {p.gender}</p>"
        
        if p.address:
            details += f"<p><b>Address:</b> {p.address}</p>"
        
        if p.external_ids:
            details += "<p><b>External IDs:</b><br>"
            for key, value in p.external_ids.items():
                details += f"&nbsp;&nbsp;{key}: {value}<br>"
            details += "</p>"
        
        if p.notes:
            details += f"<p><b>Notes:</b> {p.notes}</p>"
        
        # Show relationships
        parents = self.session.query(Relationship).filter_by(
            person_b_id=p.id, relation_type='parent'
        ).all()
        
        if parents:
            details += "<p><b>Parents:</b><br>"
            for rel in parents:
                parent = self.session.query(Person).get(rel.person_a_id)
                details += f"&nbsp;&nbsp;{parent.full_name} (ID: {parent.id})<br>"
            details += "</p>"
        
        children = self.session.query(Relationship).filter_by(
            person_a_id=p.id, relation_type='parent'
        ).all()
        
        if children:
            details += "<p><b>Children:</b><br>"
            for rel in children:
                child = self.session.query(Person).get(rel.person_b_id)
                details += f"&nbsp;&nbsp;{child.full_name} (ID: {child.id})<br>"
            details += "</p>"
        
        spouses = self.session.query(Relationship).filter_by(
            person_a_id=p.id, relation_type='spouse'
        ).all()
        
        if spouses:
            details += "<p><b>Spouses:</b><br>"
            for rel in spouses:
                spouse = self.session.query(Person).get(rel.person_b_id)
                details += f"&nbsp;&nbsp;{spouse.full_name} (ID: {spouse.id})<br>"
            details += "</p>"
        
        self.details_label.setText(details)
    
    def refresh_tree(self):
        """Refresh the family tree visualization."""
        if not self.current_person:
            return
        
        depth = self.depth_spin.value()
        pixmap = TreeVisualizer.generate_tree(self.session, self.current_person.id, depth)
        
        if not pixmap.isNull():
            # Scale to fit
            scaled = pixmap.scaled(
                self.tree_scroll.width() - 20,
                self.tree_scroll.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.tree_label.setPixmap(scaled)
        else:
            self.tree_label.setText("Error generating tree. Is Graphviz installed?")
    
    def add_person(self):
        """Add a new person."""
        dialog = PersonFormDialog(self, session=self.session)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_person_list()
            QMessageBox.information(self, "Success", "Person added successfully.")
    
    def edit_person(self):
        """Edit selected person."""
        if not self.current_person:
            QMessageBox.warning(self, "No Selection", "Please select a person to edit.")
            return
        
        dialog = PersonFormDialog(self, person=self.current_person, session=self.session)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_person_list()
            self.display_person_details()
            QMessageBox.information(self, "Success", "Person updated successfully.")
    
    def delete_person(self):
        """Delete selected person."""
        if not self.current_person:
            QMessageBox.warning(self, "No Selection", "Please select a person to delete.")
            return
        
        # Check relationships
        rel_count = self.session.query(Relationship).filter(
            (Relationship.person_a_id == self.current_person.id) |
            (Relationship.person_b_id == self.current_person.id)
        ).count()
        
        msg = f"Delete {self.current_person.full_name}?"
        if rel_count > 0:
            msg += f"\n\nThis will also delete {rel_count} relationship(s)."
        
        reply = QMessageBox.question(
            self, "Confirm Delete", msg,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            person_id = self.current_person.id
            self.session.delete(self.current_person)
            self.session.commit()
            db_manager.log_action(self.session, 'delete_person', f"Deleted person ID {person_id}")
            
            self.current_person = None
            self.refresh_person_list()
            self.details_label.setText("Select a person to view details")
            self.tree_label.setText("Select a person to view family tree")
            self.add_rel_btn.setEnabled(False)
            
            QMessageBox.information(self, "Success", "Person deleted successfully.")
    
    def add_relationship(self):
        """Add a relationship for current person."""
        if not self.current_person:
            return
        
        dialog = RelationshipFormDialog(self, session=self.session, person_a=self.current_person)
        if dialog.exec() == QDialog.Accepted:
            self.display_person_details()
            self.refresh_tree()
            QMessageBox.information(self, "Success", "Relationship added successfully.")
    
    def find_duplicates(self):
        """Open duplicate detection dialog."""
        dialog = DuplicateDetectionDialog(self, session=self.session)
        dialog.exec()
        self.refresh_person_list()
    
    def export_data(self):
        """Export data to JSON."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "family_export.json", "JSON Files (*.json)"
        )
        
        if filepath:
            try:
                ImportExport.export_to_json(self.session, filepath)
                QMessageBox.information(self, "Success", f"Data exported to {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
    
    def import_data(self):
        """Import data from JSON."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Data", "", "JSON Files (*.json)"
        )
        
        if filepath:
            reply = QMessageBox.question(
                self, "ID Handling",
                "Remap imported IDs to avoid conflicts?\n\n"
                "Yes: Assign new IDs\nNo: Keep original IDs (may fail if conflicts exist)",
                QMessageBox.Yes | QMessageBox.No
            )
            
            remap = reply == QMessageBox.Yes
            
            try:
                ImportExport.import_from_json(self.session, filepath, remap_ids=remap)
                self.refresh_person_list()
                QMessageBox.information(self, "Success", f"Data imported from {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """
        <h2>Family Tree / Census Helper</h2>
        <p>Version 1.0</p>
        <p>A desktop application for census workers to manage family trees.</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Add, edit, delete persons</li>
            <li>Create parent-child and spouse relationships</li>
            <li>Visual family tree rendering</li>
            <li>Duplicate detection and merging</li>
            <li>Import/Export to JSON</li>
            <li>Audit logging</li>
        </ul>
        <p><b>Technology:</b> Python 3.10+, PySide6, SQLAlchemy, Graphviz</p>
        """
        QMessageBox.about(self, "About", about_text)
    
    def show_test_plan(self):
        """Show test plan."""
        test_text = """
        <h2>Test Plan / Acceptance Criteria</h2>
        
        <h3>Test 1: Add Persons and Relationships</h3>
        <ol>
            <li>Add 4 persons with different details</li>
            <li>Create parent-child relationships between them</li>
            <li>Create spouse relationships</li>
            <li>Verify relationships appear in person details</li>
            <li>View family tree visualization - verify edges are correct</li>
        </ol>
        
        <h3>Test 2: Duplicate Detection and Merge</h3>
        <ol>
            <li>Create two persons with exact same name and DOB</li>
            <li>Go to Edit → Find Duplicates</li>
            <li>Verify duplicates are detected with high similarity score</li>
            <li>Select both records and merge</li>
            <li>Verify only one record remains</li>
            <li>Verify relationships transferred correctly</li>
        </ol>
        
        <h3>Test 3: Validation Rules</h3>
        <ol>
            <li>Try to create a relationship from person to themselves</li>
            <li>Verify app blocks it with error message</li>
            <li>Try to create parent-child with invalid age difference</li>
            <li>Verify warning is shown but can override</li>
        </ol>
        
        <h3>Test 4: Delete with Relationships</h3>
        <ol>
            <li>Delete a person who has children</li>
            <li>Verify confirmation dialog shows relationship count</li>
            <li>Confirm deletion</li>
            <li>Verify person and relationships are removed</li>
        </ol>
        
        <h3>Test 5: Import/Export</h3>
        <ol>
            <li>Export current database to JSON (File → Export)</li>
            <li>Open exported file and verify structure</li>
            <li>Create a fresh database (delete family.db, restart app)</li>
            <li>Import the JSON file (File → Import)</li>
            <li>Verify all persons and relationships restored</li>
            <li>Verify family tree visualizations match</li>
        </ol>
        
        <h3>Test 6: Search and Filter</h3>
        <ol>
            <li>Type name in search box</li>
            <li>Verify list filters in real-time</li>
            <li>Search by ID number</li>
            <li>Clear search and verify all persons appear</li>
        </ol>
        
        <h3>Sample Data Included</h3>
        <p>If database is empty, sample family data is automatically created:
        <ul>
            <li>Rajesh Sharma (parent)</li>
            <li>Sita Sharma (parent/spouse)</li>
            <li>Aman Sharma (child)</li>
            <li>Anita R (child)</li>
            <li>Duplicate "Aman Sharma" for testing merge</li>
        </ul>
        </p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Test Plan")
        msg.setTextFormat(Qt.RichText)
        msg.setText(test_text)
        msg.exec()
    
    def closeEvent(self, event):
        """Handle window close."""
        self.session.close()
        event.accept()


# ============================================================================
# SAMPLE DATA GENERATION
# ============================================================================

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
    db_manager.log_action(session, 'create_sample_data', 'Created sample family data')
    
    print("Sample data created successfully!")
    print(f"  - Created {session.query(Person).count()} persons")
    print(f"  - Created {session.query(Relationship).count()} relationships")
    print("  - Includes 1 duplicate record (Aman Sharma) for testing merge functionality")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""
    
    print("=" * 60)
    print("Family Tree / Census Helper Application")
    print("=" * 60)
    print()
    
    # Check Graphviz availability
    try:
        import graphviz
        # Try to create a simple graph to verify system binary
        test_graph = graphviz.Digraph()
        test_graph.node('test')
        test_graph.pipe(format='png')
        print("✓ Graphviz system binary found")
    except Exception as e:
        print("⚠ WARNING: Graphviz system binary not found or not working!")
        print("  Please install Graphviz from https://graphviz.org/download/")
        print("  Tree visualization will not work without it.")
        print(f"  Error: {e}")
        print()
    
    # Check rapidfuzz
    if RAPIDFUZZ_AVAILABLE:
        print("✓ rapidfuzz available - advanced duplicate detection enabled")
    else:
        print("⚠ rapidfuzz not available - using basic duplicate detection")
        print("  Install with: pip install rapidfuzz")
    
    print()
    print("Initializing database...")
    
    # Initialize database
    global db_manager
    db_manager = DatabaseManager('family.db')
    
    # Create sample data if needed
    session = db_manager.get_session()
    create_sample_data(session)
    session.close()
    
    print()
    print("Starting application...")
    print()
    print("KEYBOARD SHORTCUTS:")
    print("  Ctrl+N - Add new person")
    print("  Ctrl+E - Edit selected person")
    print("  Ctrl+D - Delete selected person")
    print("  Ctrl+F - Find duplicates")
    print("  Ctrl+S - Export data")
    print()
    print("=" * 60)
    print()
    
    # Create and run application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
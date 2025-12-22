from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QDateEdit, QFormLayout, QComboBox, QTextEdit, QCheckBox, QDialogButtonBox, 
                             QMessageBox, QListWidget, QListWidgetItem, QGroupBox)
from PySide6.QtCore import Qt, QDate
from models.person import Person
from models.relationship import Relationship
from database.db_manager import DatabaseManager
from datetime import date, datetime
from sqlalchemy.orm import Session

class PersonFormDialog(QDialog):
    """Dialog for adding or editing a person with parent selection."""
    
    def __init__(self, parent=None, person: Person = None, session: Session = None):
        super().__init__(parent)
        self.person = person
        self.session = session
        self.is_edit = person is not None
        self.selected_parents = []
        
        self.setWindowTitle("Edit Person" if self.is_edit else "Add Person")
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        
        self.setup_ui()
        
        if self.is_edit:
            self.load_person_data()
        else:
            # For new persons, load existing parents
            self.load_parent_list()
    
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
        
        # Parent Selection Group
        parent_group = QGroupBox("Parents (Optional)")
        parent_layout = QVBoxLayout()
        
        parent_label = QLabel("Select parents for this person (0, 1, or 2 parents):")
        parent_layout.addWidget(parent_label)
        
        # Parent list - allow multiple selection
        self.parent_list = QListWidget()
        self.parent_list.setSelectionMode(QListWidget.MultiSelection)
        self.parent_list.setMaximumHeight(150)
        parent_layout.addWidget(self.parent_list)
        
        parent_group.setLayout(parent_layout)
        layout.addWidget(parent_group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_form)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def toggle_dob(self, state):
        """Toggle DOB input enabled state."""
        self.dob_input.setEnabled(state == Qt.Checked)
    
    def load_parent_list(self):
        """Load list of available people as potential parents."""
        # Get all persons from database
        if not self.session:
            return
        
        try:
            all_persons = self.session.query(Person).all()
            
            for person in all_persons:
                item = QListWidgetItem(f"{person.full_name} (ID: {person.id})")
                item.setData(Qt.UserRole, person.id)
                self.parent_list.addItem(item)
        except Exception as e:
            print(f"Error loading parent list: {e}")
    
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
        
        # Load existing parents
        self.load_parent_list()
        self.select_current_parents()
    
    def select_current_parents(self):
        """Select current parents in the list."""
        if not self.session:
            return
        
        try:
            # Get all parent relationships for this person
            parent_rels = self.session.query(Relationship).filter(
                Relationship.person_b_id == self.person.id,
                Relationship.relation_type == 'parent'
            ).all()
            
            parent_ids = {rel.person_a_id for rel in parent_rels}
            
            # Select matching items in list
            for i in range(self.parent_list.count()):
                item = self.parent_list.item(i)
                person_id = item.data(Qt.UserRole)
                if person_id in parent_ids:
                    item.setSelected(True)
        except Exception as e:
            print(f"Error loading current parents: {e}")
    
    def accept_form(self):
        """Validate and accept form."""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Full name is required.")
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
        
        # Get selected parents
        selected_parent_ids = []
        for item in self.parent_list.selectedItems():
            parent_id = item.data(Qt.UserRole)
            selected_parent_ids.append(parent_id)
        
        # Limit to 2 parents
        if len(selected_parent_ids) > 2:
            QMessageBox.warning(self, "Validation Error", "A person can have at most 2 parents.")
            return
        
        self.selected_parents = selected_parent_ids
        
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
            
            # Update parent relationships
            self.update_parent_relationships()
            
            db_manager = DatabaseManager()
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
            
            # Add parent relationships
            self.create_parent_relationships()
            
            db_manager = DatabaseManager()
            db_manager.log_action(self.session, 'create_person', f"Created person ID {self.person.id}")
        
        self.accept()
    
    def create_parent_relationships(self):
        """Create parent relationships for newly created person."""
        for parent_id in self.selected_parents:
            try:
                relationship = Relationship(
                    person_a_id=parent_id,
                    person_b_id=self.person.id,
                    relation_type='parent'
                )
                self.session.add(relationship)
            except Exception as e:
                print(f"Error creating relationship: {e}")
        
        self.session.commit()
    
    def update_parent_relationships(self):
        """Update parent relationships for edited person."""
        if not self.session:
            return
        
        try:
            # Get existing parent relationships
            existing_rels = self.session.query(Relationship).filter(
                Relationship.person_b_id == self.person.id,
                Relationship.relation_type == 'parent'
            ).all()
            
            existing_parent_ids = {rel.person_a_id for rel in existing_rels}
            new_parent_ids = set(self.selected_parents)
            
            # Remove parents that are no longer selected
            for rel in existing_rels:
                if rel.person_a_id not in new_parent_ids:
                    self.session.delete(rel)
            
            # Add new parents
            for parent_id in new_parent_ids:
                if parent_id not in existing_parent_ids:
                    relationship = Relationship(
                        person_a_id=parent_id,
                        person_b_id=self.person.id,
                        relation_type='parent'
                    )
                    self.session.add(relationship)
            
            self.session.commit()
        except Exception as e:
            print(f"Error updating relationships: {e}")
    
    def get_person(self) -> Person:
        """Get the created/edited person."""
        return self.person

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDateEdit, QFormLayout, QComboBox, QTextEdit, QCheckBox, QDialogButtonBox, QMessageBox
from PySide6.QtCore import Qt, QDate
from models.person import Person
# from business.validator import Validator
from database.db_manager import DatabaseManager
from datetime import date, datetime
from sqlalchemy.orm import Session

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
        
        # valid, msg = Validator.validate_person_data(name)
        # if not valid:
        #     QMessageBox.warning(self, "Validation Error", msg)
        #     return
        
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
            db_manager = DatabaseManager()
            db_manager.log_action(self.session, 'create_person', f"Created person ID {self.person.id}")
        
        self.accept()
    
    def get_person(self) -> Person:
        """Get the created/edited person."""
        return self.person

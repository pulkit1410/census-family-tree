from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDateEdit, QFormLayout, QComboBox, QTextEdit, QCheckBox, QDialogButtonBox, QMessageBox
from PySide6.QtCore import Qt, QDate
from models.person import Person
from models.relationship import Relationship
# from business.validator import Validator
from database.db_manager import DatabaseManager
from datetime import date
from sqlalchemy.orm import Session

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
        # valid, msg = Validator.validate_relationship(self.session, person_a_id, person_b_id, rel_type)
        
        # if not valid:
        #     # For age warnings, show confirmation dialog
        #     if "12 years" in msg:
        #         reply = QMessageBox.question(
        #             self, "Age Warning",
        #             f"{msg}\n\nDo you want to proceed anyway?",
        #             QMessageBox.Yes | QMessageBox.No
        #         )
        #         if reply == QMessageBox.No:
        #             return
        #     else:
        #         QMessageBox.warning(self, "Validation Error", msg)
        #         return
        
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
        db_manager = DatabaseManager()
        db_manager.log_action(self.session, 'create_relationship',
                            f"Created {rel_type} relationship: {person_a_id} -> {person_b_id}")
        
        self.accept()


  
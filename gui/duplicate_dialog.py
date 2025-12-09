from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox, QCheckBox
from PySide6.QtCore import Qt
from models.person import Person
from sqlalchemy.orm import Session
from business.duplicate_detector import DuplicateDetector
from database.db_manager import DatabaseManager

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
        from business.duplicate_detector import DuplicateDetector
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

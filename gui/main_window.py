"""
Main application window.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QListWidgetItem, QPushButton, QLabel, QLineEdit, QSplitter,
    QGroupBox, QSpinBox, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from config import UI_CONFIG
from database.db_manager import DatabaseManager
from visualization.tree_renderer import FamilyTreeView
from gui.person_form import PersonFormDialog
from gui.relationship_form import RelationshipFormDialog
# from gui.duplicate_dialog import DuplicateDetectionDialog
from business.import_export import ImportExport


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.db_manager = DatabaseManager()
        self.session = self.db_manager.get_session()
        self.current_person = None
        
        self.setWindowTitle(UI_CONFIG['window_title'])
        self.setMinimumSize(UI_CONFIG['window_width'], UI_CONFIG['window_height'])
        
        self.setup_ui()
        self.setup_menu()
        self.refresh_person_list()
    
    def setup_ui(self):
        """Setup the main UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout()
        
        # Left panel - Person list
        left_panel = self.create_left_panel()
        
        # Right panel - Details and tree
        right_panel = self.create_right_panel()
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, UI_CONFIG['splitter_ratio'][0])
        splitter.setStretchFactor(1, UI_CONFIG['splitter_ratio'][1])
        
        main_layout.addWidget(splitter)
        central.setLayout(main_layout)
    
    def create_left_panel(self):
        """Create left panel with person list."""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Name, ID, DOB...")
        self.search_input.textChanged.connect(self.filter_persons)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Person list
        self.person_list = QListWidget()
        self.person_list.itemClicked.connect(self.on_person_selected)
        layout.addWidget(self.person_list)
        
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
        
        layout.addLayout(btn_layout)
        panel.setLayout(layout)
        
        return panel
    
    def create_right_panel(self):
        """Create right panel with details and tree."""
        panel = QWidget()
        layout = QVBoxLayout()
        
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
        details_group.setMaximumHeight(250)
        layout.addWidget(details_group)
        
        # Tree visualization
        tree_group = QGroupBox("Family Tree (Interactive - Drag to pan, scroll to zoom)")
        tree_layout = QVBoxLayout()
        
        # Depth control
        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Tree Depth:"))
        self.depth_spin = QSpinBox()
        self.depth_spin.setMinimum(1)
        self.depth_spin.setMaximum(5)
        self.depth_spin.setValue(3)
        self.depth_spin.valueChanged.connect(self.refresh_tree)
        depth_layout.addWidget(self.depth_spin)
        depth_layout.addStretch()
        tree_layout.addLayout(depth_layout)
        
        # Tree display
        self.tree_view = FamilyTreeView()
        tree_layout.addWidget(self.tree_view)
        
        tree_group.setLayout(tree_layout)
        layout.addWidget(tree_group)
        
        panel.setLayout(layout)
        return panel
    
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
    
    def refresh_person_list(self, search_term: str = ""):
        """Refresh the person list."""
        # Store current selection
        selected_id = None
        if self.current_person:
            selected_id = self.current_person.id

        self.person_list.clear()
        
        if search_term:
            persons = self.db_manager.search_persons(self.session, search_term)
        else:
            persons = self.db_manager.get_all_persons(self.session)
        
        for person in persons:
            dob_str = person.dob.strftime('%Y-%m-%d') if person.dob else 'N/A'
            item = QListWidgetItem(f"{person.full_name} (ID: {person.id}, DOB: {dob_str})")
            item.setData(Qt.UserRole, person.id)
            self.person_list.addItem(item)
            # Restore selection if possible
            if selected_id is not None and person.id == selected_id:
                self.person_list.setCurrentItem(item)
                self.current_person = person  # Ensure current_person is up-to-date

        # If no selection, clear current_person
        if self.person_list.currentItem() is None:
            self.current_person = None
    
    def filter_persons(self):
        """Filter persons based on search."""
        search_term = self.search_input.text().strip()
        self.refresh_person_list(search_term)
    
    def on_person_selected(self, item: QListWidgetItem):
        """Handle person selection."""
        person_id = item.data(Qt.UserRole)
        self.current_person = self.db_manager.get_person_by_id(self.session, person_id)
        
        if self.current_person:
            self.display_person_details()
            self.refresh_tree()
            self.add_rel_btn.setEnabled(True)
    
    def display_person_details(self):
        """Display details of selected person."""
        p = self.current_person
        rels = self.db_manager.get_relationships_for_person(self.session, p.id)
        
        details = f"<h3>{p.full_name}</h3>"
        details += f"<p><b>ID:</b> {p.id}</p>"
        details += f"<p><b>DOB:</b> {p.dob.strftime('%Y-%m-%d') if p.dob else 'Unknown'}</p>"
        # details += f"<p><b>Age:</b> {p.age if p.age else 'Unknown'}</p>"
        details += f"<p><b>Gender:</b> {p.gender}</p>"
        
        if p.address:
            details += f"<p><b>Address:</b> {p.address}</p>"
        
        # Show relationships
        if rels['parents']:
            details += "<p><b>Parents:</b><br>"
            for rel in rels['parents']:
                parent = self.db_manager.get_person_by_id(self.session, rel.person_a_id)
                details += f"&nbsp;&nbsp;{parent.full_name}<br>"
            details += "</p>"
        
        if rels['children']:
            details += "<p><b>Children:</b><br>"
            for rel in rels['children']:
                child = self.db_manager.get_person_by_id(self.session, rel.person_b_id)
                details += f"&nbsp;&nbsp;{child.full_name}<br>"
            details += "</p>"
        
        if rels['spouses']:
            details += "<p><b>Spouses:</b><br>"
            for rel in rels['spouses']:
                spouse = self.db_manager.get_person_by_id(self.session, rel.person_b_id)
                details += f"&nbsp;&nbsp;{spouse.full_name}<br>"
            details += "</p>"
        
        self.details_label.setText(details)
    
    def refresh_tree(self):
        """Refresh the family tree visualization."""
        if not self.current_person:
            return
        
        from models.relationship import Relationship
        
        depth = self.depth_spin.value()
        
        # Get persons and relationships for the tree
        persons = self._get_tree_persons(self.current_person.id, depth)
        relationships = self._get_tree_relationships([p.id for p in persons])
        
        self.tree_view.render_tree(persons, relationships, self.current_person.id)
    
    def _get_tree_persons(self, person_id: int, depth: int):
        """Get all persons within depth levels of the given person."""
        from models.person import Person
        from collections import deque
        
        visited = set()
        persons = []
        queue = deque([(person_id, 0)])
        
        while queue:
            pid, level = queue.popleft()
            
            if pid in visited or level > depth:
                continue
            
            visited.add(pid)
            person = self.db_manager.get_person_by_id(self.session, pid)
            if person:
                persons.append(person)
                
                # Add related persons
                rels = self.db_manager.get_relationships_for_person(self.session, pid)
                
                for rel in rels['parents']:
                    queue.append((rel.person_a_id, level + 1))
                
                for rel in rels['children']:
                    queue.append((rel.person_b_id, level + 1))
                
                for rel in rels['spouses']:
                    queue.append((rel.person_b_id, level))
        
        return persons
    
    def _get_tree_relationships(self, person_ids):
        """Get all relationships between the given persons."""
        from models.relationship import Relationship
        
        return self.session.query(Relationship).filter(
            Relationship.person_a_id.in_(person_ids),
            Relationship.person_b_id.in_(person_ids)
        ).all()
    
    def add_person(self):
        """Add a new person."""
        dialog = PersonFormDialog(self, session=self.session)
        if dialog.exec():
            self.refresh_person_list()
            QMessageBox.information(self, "Success", "Person added successfully.")
    
    def edit_person(self):
        """Edit selected person."""
        if not self.current_person:
            QMessageBox.warning(self, "No Selection", "Please select a person to edit.")
            return
        
        dialog = PersonFormDialog(self, person=self.current_person, session=self.session)
        if dialog.exec():
            self.refresh_person_list()
            self.display_person_details()
            QMessageBox.information(self, "Success", "Person updated successfully.")
    
    def delete_person(self):
        """Delete selected person."""
        if not self.current_person:
            QMessageBox.warning(self, "No Selection", "Please select a person to delete.")
            return
        
        from models.relationship import Relationship
        
        # Check relationships
        rel_count = self.session.query(Relationship).filter(
            (Relationship.person_a_id == self.current_person.id) |
            (Relationship.person_b_id == self.current_person.id)
        ).count()
        
        msg = f"Delete {self.current_person.full_name}?"
        if rel_count > 0:
            msg += f"\n\nThis will also delete {rel_count} relationship(s)."
        
        reply = QMessageBox.question(self, "Confirm Delete", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_person(self.session, self.current_person.id)
            self.current_person = None
            self.refresh_person_list()
            self.details_label.setText("Select a person to view details")
            self.tree_view.clear_tree()
            self.add_rel_btn.setEnabled(False)
            QMessageBox.information(self, "Success", "Person deleted successfully.")
    
    def add_relationship(self):
        """Add a relationship for current person."""
        if not self.current_person:
            return
        
        dialog = RelationshipFormDialog(self, session=self.session, person_a=self.current_person)
        if dialog.exec():
            self.display_person_details()
            self.refresh_tree()
            QMessageBox.information(self, "Success", "Relationship added successfully.")
    
    def find_duplicates(self):
        """Open duplicate detection dialog."""
        # dialog = DuplicateDetectionDialog(self, session=self.session)
        # dialog.exec()
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
        from config import APP_VERSION
        about_text = f"""
        <h2>Family Tree / Census Helper</h2>
        <p>Version {APP_VERSION}</p>
        <p>A modern desktop application for census workers to manage family trees.</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Interactive family tree visualization</li>
            <li>Drag & zoom navigation</li>
            <li>Add, edit, delete persons</li>
            <li>Parent-child and spouse relationships</li>
            <li>Duplicate detection and merging</li>
            <li>Import/Export to JSON</li>
        </ul>
        <p><b>Technology:</b> Python 3.10+, PySide6, SQLAlchemy</p>
        """
        QMessageBox.about(self, "About", about_text)
    
    def closeEvent(self, event):
        """Handle window close."""
        self.session.close()
        event.accept()
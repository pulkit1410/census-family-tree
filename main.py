#!/usr/bin/env python3
"""
Family Tree / Census Helper Application
========================================

A modern desktop application for census workers to create, view, edit and manage family trees.

REQUIREMENTS:
-------------
Python dependencies:
  pip install PySide6 sqlalchemy pillow rapidfuzz

USAGE:
------
  python main.py

FEATURES:
---------
  - Interactive family tree visualization with drag & zoom
  - Add/edit/delete persons with detailed information
  - Create parent-child and spouse relationships
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

Author: Census Helper System
Version: 2.0
"""

import sys
from PySide6.QtWidgets import QApplication

from config import APP_VERSION
from database.db_manager import DatabaseManager
from gui.main_window import MainWindow
# from utils.sample_data import create_sample_data


def check_dependencies():
    """Check if required dependencies are available."""
    try:
        from rapidfuzz import fuzz
        print("✓ rapidfuzz available - advanced duplicate detection enabled")
    except ImportError:
        print("⚠ rapidfuzz not available - using basic duplicate detection")
        print("  Install with: pip install rapidfuzz")


def main():
    """Main application entry point."""
    
    print("=" * 60)
    print("Family Tree / Census Helper Application")
    print(f"Version {APP_VERSION}")
    print("=" * 60)
    print()
    
    check_dependencies()
    
    print()
    print("Initializing database...")
    
    # Initialize database
    db_manager = DatabaseManager()
    
    # Create sample data if needed
    # session = db_manager.get_session()
    # create_sample_data(session)
    # session.close()
    
    print()
    print("Starting application...")
    print()
    print("FEATURES:")
    print("  - Interactive tree visualization")
    print("  - Drag nodes to reposition")
    print("  - Scroll to zoom in/out")
    print("  - Right-click drag to pan")
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
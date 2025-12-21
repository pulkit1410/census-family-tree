# Family Tree Application - Modular Architecture

## Project Structure

```
family_tree/
├── README.md
├── requirements.txt
├── main.py                    # Main entry point
├── config.py                  # Configuration settings
├── models/
│   ├── __init__.py
│   ├── person.py             # Person model
│   ├── relationship.py       # Relationship model
│   └── audit_log.py          # Audit log model (in db_manager.py)
├── database/
│   ├── __init__.py
│   └── db_manager.py         # Database operations
├── business/
│   ├── __init__.py
│   ├── duplicate_detector.py # Duplicate detection logic
│   ├── validator.py          # Business rules validation
│   └── import_export.py      # JSON import/export
├── visualization/
│   ├── __init__.py
│   ├── tree_renderer.py      # Interactive PyQt tree visualization
│   └── graph_layout.py       # Layout algorithms
├── gui/
│   ├── __init__.py
│   ├── main_window.py        # Main application window
│   ├── person_form.py        # Person add/edit dialog
│   ├── relationship_form.py  # Relationship add dialog
│   └── duplicate_dialog.py   # Duplicate detection dialog
└── utils/
    ├── __init__.py
    └── sample_data.py        # Sample data generation
```

## Quick Setup

### Step 1: Create Directory Structure
```bash
mkdir -p family_tree/{models,database,business,visualization,gui,utils}
cd family_tree
touch {models,database,business,visualization,gui,utils}/__init__.py
```

### Step 2: Create Files
Copy each module into its respective file as shown in the structure above.

### Step 3: Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Requirements

```txt
PySide6>=6.5.0
sqlalchemy>=2.0.0
pillow>=10.0.0
rapidfuzz>=3.0.0
```

## Usage

```bash
python main.py
```

## Features

- **Modern Interactive Tree Visualization**: Dynamic, draggable family tree with smooth animations
- **Modular Architecture**: Clean separation of concerns
- **Database Management**: SQLAlchemy ORM with SQLite
- **Duplicate Detection**: Fuzzy matching with configurable thresholds
- **Import/Export**: JSON-based data portability
- **Relationship Management**: Parent-child, spouse, guardian relationships
- **Validation**: Age checks, self-relationship prevention
- **Audit Logging**: Track all changes

## Key Improvements

1. **Interactive Tree**: Replaced Graphviz with custom PyQt-based renderer
2. **Modular Design**: Separated concerns into logical modules
3. **Better Layout**: Hierarchical layout algorithm similar to the reference image
4. **Drag & Drop**: Move nodes interactively
5. **Zoom & Pan**: Navigate large trees easily
6. **Color Coding**: Visual distinction between genders and relationship types
# Family Tree Application - Setup & Usage Guide

## Installation

### Requirements
- Python 3.10 or higher
- pip (Python package manager)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Dependencies Included
- **PySide6** (6.5+) - GUI framework
- **SQLAlchemy** (2.0+) - Database ORM
- **Pillow** (10.0+) - Image processing
- **RapidFuzz** (3.0+) - Fuzzy string matching for duplicate detection
- **Graphviz** - Graph visualization library

## Running the Application

### On Windows/Mac/Linux with Display
```bash
python main.py
```

### On Headless Systems (Linux server)
```bash
export QT_QPA_PLATFORM=offscreen
python main.py
```

## Key Features

### 1. Person Management
- **Add Person**: Create new person with name, DOB, gender, address, notes
- **Edit Person**: Modify any person's information
- **Delete Person**: Remove person and their relationships
- **Select Parents**: While creating/editing, select up to 2 parents from existing people
- **Search**: Search people by name, ID, or date of birth

### 2. Relationships
- **Parent-Child**: Automatic creation when parents selected during person creation
- **Spouse**: Add relationships between married couples
- **Dual Parents**: When a child has 2 parents, they're automatically centered between parents
- **Edit Relationships**: Add or modify relationships through the UI

### 3. Family Tree Visualization
- **Interactive Display**: Drag nodes to reposition
- **Dynamic Edges**: Connected lines follow nodes in real-time
- **Zoom & Pan**: Scroll to zoom, right-click drag to pan
- **Color Coding**: Males (blue), Females (pink), Selected (gold)
- **Smart Spacing**: Proper spacing prevents overlaps
- **Generation Levels**: Clear hierarchical layout

### 4. Data Management
- **Import/Export**: Load and save family trees as JSON
- **Duplicate Detection**: Find and merge duplicate records
- **Audit Logging**: Track all changes to the database
- **External IDs**: Store additional identifiers (Aadhaar, SSN, etc.)

## Usage Workflow

### Creating a Simple Family Tree

1. **Add First Person (Grandparent)**
   - Click "Add Person"
   - Enter: "John Smith", DOB: 1950-01-15, Gender: Male
   - No parents (root ancestor)
   - Click OK

2. **Add Second Person (Grandparent)**
   - Click "Add Person"
   - Enter: "Mary Smith", DOB: 1952-03-20, Gender: Female
   - No parents
   - Click OK

3. **Link as Couple**
   - Select John in the list
   - Click "Add Relationship"
   - Select Mary as spouse type
   - Click OK

4. **Add Child (Parent of your person)**
   - Click "Add Person"
   - Enter: "Alice Smith", DOB: 1975-06-10, Gender: Female
   - **Select Parents**: John Smith, Mary Smith
   - Click OK
   - Alice now appears centered below John and Mary

5. **Add Another Parent (Not related)**
   - Click "Add Person"
   - Enter: "Bob Johnson", DOB: 1973-08-15, Gender: Male
   - No parents
   - Click OK

6. **Link as Couple**
   - Select Alice in the list
   - Click "Add Relationship"
   - Select Bob as spouse
   - Click OK

7. **Add Yourself**
   - Click "Add Person"
   - Enter your name, DOB, Gender
   - **Select Parents**: Alice Smith, Bob Johnson
   - Click OK

Now you should see:
```
John Smith ♥ Mary Smith
    |
    Alice Smith ♥ Bob Johnson
         |
       Your Name
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | Add new person |
| Ctrl+E | Edit selected person |
| Ctrl+D | Delete selected person |
| Ctrl+F | Find duplicates |
| Ctrl+S | Export data to JSON |

## Tips & Tricks

### Working with Large Trees
1. Use tree depth control to limit visible generations
2. Click on any person to center the tree on them
3. Zoom in/out with scroll wheel
4. Drag to pan and reposition nodes

### Managing Duplicates
1. Use duplicate detection to find similar names
2. Merge duplicate records
3. Add external IDs to prevent future duplicates

### Data Import
1. Prepare JSON file with people and relationships
2. Use File → Import JSON
3. Choose whether to remap IDs (recommended for first import)
4. Review and verify imported data

### Data Export
1. Select persons to export or export all
2. Use File → Export JSON
3. Share JSON file or archive for backup

## Database

The application uses SQLite by default:
- Database file: `family.db` (created in app directory)
- Automatic schema creation on first run
- All data persisted between sessions

### Database Tables
- **persons**: People in the family tree
- **relationships**: Connections (parent-child, spouse, etc.)
- **audit_logs**: History of all changes

## Troubleshooting

### Issue: Application won't start
**Solution**: Ensure all dependencies are installed
```bash
pip install --upgrade -r requirements.txt
```

### Issue: Missing parents in tree
**Solution**: 
1. Select the person
2. Click "Edit"
3. Verify parents are selected
4. Save and refresh tree

### Issue: Nodes overlapping
**Solution**: 
1. The layout algorithm prevents overlaps
2. Try adjusting tree depth
3. Zoom in/out to see better
4. Drag nodes to reposition if needed

### Issue: Relationships not showing
**Solution**:
1. Check tree depth includes both people
2. Ensure relationship was created (check person details)
3. Refresh tree using depth control

## Performance Notes

- Handles 100+ people efficiently
- Dynamic rendering optimized for large trees
- Drag & zoom operations are smooth
- JSON export/import takes seconds for typical families

## Data Backup

Regular backups recommended:
```bash
# Simple copy backup
cp family.db family.db.backup

# Or export to JSON (preserves all data)
# Use File → Export JSON in application
```

## Support & Documentation

- See `VISUALIZATION_IMPROVEMENTS.md` for technical details
- See `DUAL_PARENT_FEATURE.md` for parent relationship info
- Check `README.md` for architecture overview

---

**Version**: 2.0  
**Last Updated**: 2025-12-22

# Dual Parent Relationship Feature

## Overview
The Family Tree application now properly handles parent-child relationships where a child can have up to 2 parents (mother and father). When adding or editing a person, you can select their parents from the existing people in the database.

## Features Implemented

### 1. Parent Selection During Person Creation
When adding a new person to the family tree:
- A "Parents (Optional)" section appears in the person form
- You can select 0, 1, or 2 parents from the list of existing people
- Parents are automatically linked with proper parent-child relationships

### 2. Automatic Parent Relationship Creation
- When you select parents and save a person, the system automatically creates parent relationships
- Each parent relationship is stored as: Parent ID → Child ID (relation_type: 'parent')
- Multiple parent relationships are handled correctly (one per parent)

### 3. Smart Layout for Dual Parents
The layout algorithm now intelligently handles children with dual parents:

**Single Parent:**
- Child is positioned directly below the parent
- Vertical alignment maintained

**Dual Parents:**
- Child is automatically centered between both parents
- If parents are a married couple (spouse relationship), child appears centered between them
- Creates a clear visual hierarchy showing the family unit

### 4. Edit Person Functionality
When editing an existing person:
- Current parents are highlighted in the parents list
- You can add, remove, or change parents
- Relationships are automatically updated in the database

## How to Use

### Adding a Person with Parents
1. Click "Add Person" button
2. Fill in person details (name, DOB, gender, etc.)
3. Scroll down to "Parents (Optional)" section
4. Select 1 or 2 parents from the list
5. Click OK to save

**Example:**
- Adding "John Smith"
- Selecting parents: "Alice Johnson" and "Bob Smith"
- John will automatically appear centered below Alice and Bob in the tree

### Editing Parents of Existing Person
1. Select a person from the list
2. Click "Edit" button
3. Scroll to "Parents (Optional)" section
4. Modify the selected parents (can add, remove, or change)
5. Click OK to save changes

## Database Schema

### Relationships Table
```
person_a_id → person_b_id (relation_type: 'parent')
```

This means:
- `person_a_id` is the parent
- `person_b_id` is the child
- For dual parents, there are 2 separate rows with same child but different parents

### Example
If John (ID: 5) has parents Alice (ID: 1) and Bob (ID: 2):
```
Relationship 1: 1 → 5 (parent)  [Alice is parent of John]
Relationship 2: 2 → 5 (parent)  [Bob is parent of John]
```

## Visualization Behavior

### Single Parent Case
```
        Alice (Parent)
          |
          |
        John (Child)
```

### Dual Parent Case
```
Alice (Parent)    Bob (Spouse)
    \             /
     \           /
      John (Child)    ← Centered below both parents
```

### With Siblings (Multiple Children)
```
Alice (Parent)         Bob (Spouse)
    |                    |
    └────────┬───────────┘
         |   |   |
       John Jane Mark   ← Children aligned below parents
```

## Code Implementation Details

### Modified Files

1. **gui/person_form.py**
   - Added parent selection UI with QListWidget (multi-select)
   - `load_parent_list()` - Load available people as potential parents
   - `select_current_parents()` - Load current parents when editing
   - `create_parent_relationships()` - Create relationships for new people
   - `update_parent_relationships()` - Update relationships when editing

2. **visualization/graph_layout.py**
   - `_calculate_positions_with_dual_parents()` - New layout algorithm
   - `_find_parent_pairs_at_level()` - Identify spouse pairs
   - `_find_singles_at_level()` - Identify single persons
   - `_center_children_below_parents()` - Position children centered between dual parents

### Key Algorithm
```python
For each child at level N:
    If child has 2 parents:
        child_x = (parent1_x + parent2_x + node_width) / 2 - node_width / 2
        # Child centered between parents
    
    If child has 1 parent:
        child_x = parent_x
        # Child directly below parent
    
    If child has 0 parents:
        # Position normally in level layout
```

## Validation Rules

- **Maximum 2 parents**: Cannot assign more than 2 parents to a person
- **Automatic detection**: The system detects parent-child relationships through the database
- **Bidirectional**: Parents can see their children, children know their parents
- **Optional**: Parents can be added later or not at all

## Example Scenarios

### Scenario 1: Single Parent Family
```
Creation Steps:
1. Create "Sarah" (single mother)
2. Create "Tommy" with parent: "Sarah"
3. Result: Tommy appears below Sarah with connecting line
```

### Scenario 2: Nuclear Family
```
Creation Steps:
1. Create "John" (father)
2. Create "Jane" (mother)
3. Add spouse relationship: John ↔ Jane
4. Create "Alice" (daughter) with parents: John, Jane
5. Create "Bob" (son) with parents: John, Jane
6. Result: 
   John ↔ Jane (married couple)
      ↓ (centered connection)
   Alice, Bob (both centered below parents)
```

### Scenario 3: Multi-Generation
```
Creation Steps:
1. Create "Grandpa" and "Grandma" (with spouse relationship)
2. Create "Dad" with parents: Grandpa, Grandma
3. Create "Mom" (separate person)
4. Add spouse: Dad ↔ Mom
5. Create "Me" with parents: Dad, Mom
6. Result: Clear 3-generation tree with proper hierarchy
```

## Technical Notes

- Parent relationships are unidirectional (parent → child)
- Spouse relationships are bidirectional (A ↔ B)
- Maximum 2 parents prevents modeling errors
- Layout algorithm automatically handles variable tree shapes
- Performance optimized for trees with 100+ people

## Testing the Feature

1. **Add nuclear family:**
   - Create 2 parents with spouse relationship
   - Create children with both parents selected
   - Verify children appear centered below parents

2. **Add single parent family:**
   - Create mother
   - Create child with mother selected only
   - Verify child appears directly below mother

3. **Mix scenarios:**
   - Create some people with 2 parents
   - Create some with 1 parent
   - Create some with no parents (root ancestors)
   - Verify tree renders correctly with proper spacing

4. **Edit parent relationships:**
   - Create person without parents
   - Edit person and add parents
   - Verify relationships are created and tree updates

## Limitations & Future Enhancements

### Current Limitations
- Maximum 2 parents (aligns with biological reality)
- No support for adoptive parent types yet (infrastructure exists)
- Cannot modify parent relationships in relationship form yet

### Future Enhancements
- Add support for adoptive parents, guardians, etc.
- Relationship form UI to modify parents directly
- Grandparent/grandchild visualization optimization
- Cousin relationship detection
- Inbreeding detection warnings

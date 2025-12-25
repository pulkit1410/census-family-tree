# Family Trunk Visualization - Correct Structure

## Overview
The family tree now uses a "family trunk" visualization system where:
1. Spouses are connected by a horizontal line
2. A vertical trunk extends down from the center of the couple
3. All children of that couple branch off from this single trunk

## How It Works

### Single Parent with Children
```
      Parent
         |
         |
      Child1    Child2    Child3
```
Each child connects directly to the single parent with a curved line.

### Married Couple with Children
```
Father ─────────── Mother
            |
         ┌──┼──┐
         |  |  |
      Child1 Child2 Child3
```

Structure:
- Horizontal line connects Father to Mother (spouse relationship)
- Vertical trunk goes down from the midpoint
- Horizontal branches connect from trunk to each child
- Vertical connections drop down to each child

### Multiple Generations
```
GrandFather ──── GrandMother
              |
           ┌──┼──┐
           |  |  |
       Father ─ Mother      Uncle
              |
           ┌──┤
           |  |
         You Sibling
```

## Components Implemented

### 1. SpouseLine
- Horizontal line connecting two married people
- Drawn between center points of both nodes
- Dashed pink line style
- Updates dynamically when nodes are dragged

### 2. FamilyTrunk
- Vertical trunk line extending from spouse couple midpoint
- Horizontal branches connecting to each child
- Vertical segments connecting branches to child nodes
- Creates the characteristic "H" shape with children hanging below

### 3. SingleParentLine
- For children with only one parent
- Curved bezier line from parent to child
- Creates smooth visual flow

## Rendering Logic

When rendering relationships:

1. **Identify all couples** - Find spouse relationships
2. **Create spouse lines** - Horizontal line between each couple
3. **Find children** - Identify all children of each couple
4. **Create family trunks** - Vertical trunk with child branches for couples with children
5. **Mark processed children** - Remember which children have been drawn
6. **Create single parent lines** - For remaining children (single parent or orphans)

## Visual Advantages

✅ **Clear Family Units** - Entire family grouped under one trunk
✅ **Easy to Follow** - Single line from parents to children hierarchy  
✅ **Space Efficient** - Multiple children share the same trunk
✅ **Scalable** - Handles any number of children from one couple
✅ **Dynamic** - All lines update when nodes are dragged
✅ **Professional** - Standard genealogy notation

## Example Scenarios

### Scenario 1: Simple Nuclear Family
```
        John ────────── Jane
                |
             ┌──┼──┐
             |  |  |
          Alice Bob Carol
```

### Scenario 2: Mixed Families
```
Robert ──── Susan         Tom (single parent)
         |                 |
      ┌──┼──┐              |
      |  |  |              |
    Jack Jane Kate       Mark
```

### Scenario 3: Three Generations
```
      George ────── Mary
             |
          ┌──┼──┐
          |  |  |
      David ── Lisa      Peter
            |
          ┌─┴─┐
          |   |
        Paul Emma
```

## Code Structure

### tree_renderer.py Components

**SpouseLine Class:**
- Extends QGraphicsPathItem
- Maintains references to both spouse nodes
- `get_midpoint()` - Returns center point for trunk attachment
- `update_path()` - Redraws when nodes move

**FamilyTrunk Class:**
- Extends QGraphicsPathItem
- Maintains reference to spouse line and child nodes
- Draws complete trunk structure in one path
- `update_path()` - Handles all positioning and layout

**SingleParentLine Class:**
- Extends QGraphicsPathItem
- For individual parent-child connections
- Uses bezier curve for smooth appearance
- Updates when either parent or child moves

**FamilyTreeView Class (Modified):**
- `render_tree()` - Enhanced relationship handling
- Identifies couples and their children
- Creates appropriate line types based on parent count
- Prevents duplicate child connections

## Data Flow

```
Relationships (from DB)
    ↓
Graph Structure (build_graph)
    ├─ Identify spouses
    ├─ Identify parents
    └─ Identify children
    ↓
Render Tree
    ├─ Create nodes at calculated positions
    ├─ Create spouse lines
    ├─ Create family trunks for couples with children
    ├─ Create single parent lines for remaining
    └─ Update scene with all items
```

## Performance Considerations

- SpouseLine: O(1) per couple
- FamilyTrunk: O(n) where n = number of children
- SingleParentLine: O(1) per single parent
- Total: O(couples + total_children + single_parents)

## Interactive Features

- **Drag Nodes**: All connected lines (spouse lines, trunks, branches) update in real-time
- **Zoom**: Mouse wheel to zoom in/out with smooth rendering
- **Pan**: Right-click drag to move entire tree
- **Select**: Click any person to highlight and center tree on them

## Technical Implementation Details

### Path Drawing
The FamilyTrunk path is constructed as follows:
```
1. Move to spouse line midpoint
2. Line down to trunk bottom (top of lowest child)
3. For each child:
   a. Move to trunk bottom
   b. Line right/left to child's horizontal position
   c. Line up to child's top
```

### Dynamic Updates
When a node moves (via itemChange):
1. The node triggers update on all connected lines
2. Each line (SpouseLine, FamilyTrunk, SingleParentLine) recalculates path
3. Scene updates render the new paths
4. No lag due to QGraphicsView optimization

## Testing the Feature

1. **Create nuclear family:**
   - Add Father and Mother with spouse relationship
   - Add 2-3 children with both parents selected
   - Verify trunk with branches appears

2. **Create mixed family:**
   - Add one couple with children
   - Add another single parent with children
   - Verify correct line types for each

3. **Test interaction:**
   - Drag father left
   - Verify spouse line, trunk, and branches all move
   - Drag a child
   - Verify only that child's branch moves

4. **Multiple generations:**
   - Create 3-generation family
   - Verify all trunks align properly
   - Verify no overlaps

## Compatibility

- All existing relationship data remains unchanged
- Automatic detection of parent-child and spouse relationships
- Backward compatible with existing database schema
- No migration required

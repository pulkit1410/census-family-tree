"""
Interactive family tree visualization using PyQt with dynamic graph updates.
"""
from typing import Dict, List, Set, Tuple, Optional
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, 
    QGraphicsRectItem, QGraphicsPathItem,
    QGraphicsSimpleTextItem
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath, QFont

from config import TREE_CONFIG
from models.person import Person
from models.relationship import Relationship


class PersonNode(QGraphicsRectItem):
    """A graphical node representing a person in the family tree."""
    
    def __init__(self, person: Person, x: float, y: float, is_highlight: bool = False):
        super().__init__(0, 0, TREE_CONFIG['node_width'], TREE_CONFIG['node_height'])
        
        self.person = person
        self.is_highlight = is_highlight
        self.text_items = []
        self.connected_lines = []
        
        # Position
        self.setPos(x, y)
        
        # Make draggable
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        # Styling
        self.setup_appearance()
        
        # Add text
        self.add_labels()
        
    def setup_appearance(self):
        """Setup node appearance based on person data."""
        if self.is_highlight:
            color = QColor(TREE_CONFIG['highlight_color'])
        elif self.person.gender == 'Male':
            color = QColor(TREE_CONFIG['male_color'])
        elif self.person.gender == 'Female':
            color = QColor(TREE_CONFIG['female_color'])
        else:
            color = QColor(TREE_CONFIG['unknown_color'])
        
        self.setBrush(QBrush(color))
        pen = QPen(QColor(TREE_CONFIG['border_color']), TREE_CONFIG['border_width'])
        self.setPen(pen)
    
    def add_labels(self):
        """Add text labels with proper scaling and centering."""
        node_w = TREE_CONFIG['node_width']
        node_h = TREE_CONFIG['node_height']
        base_size = TREE_CONFIG.get('font_size', 9)
        padding = 5
        
        # Prepare name with truncation
        name = self.person.full_name
        if len(name) > 20:
            name = name[:17] + "..."
        
        # Name text
        name_text = QGraphicsSimpleTextItem(name, self)
        font_bold = QFont(TREE_CONFIG['font_family'], base_size, QFont.Bold)
        name_text.setFont(font_bold)
        name_text.setBrush(QBrush(QColor("#000000")))
        name_rect = name_text.boundingRect()
        name_x = (node_w - name_rect.width()) / 2
        name_text.setPos(name_x, padding)
        self.text_items.append(name_text)
        
        # DOB text
        dob_str = self.person.dob.strftime('%Y-%m-%d') if self.person.dob else 'DOB: ?'
        dob_text = QGraphicsSimpleTextItem(dob_str, self)
        font_small = QFont(TREE_CONFIG['font_family'], max(base_size - 1, 7))
        dob_text.setFont(font_small)
        dob_text.setBrush(QBrush(QColor("#333333")))
        dob_rect = dob_text.boundingRect()
        dob_x = (node_w - dob_rect.width()) / 2
        dob_text.setPos(dob_x, padding + 22)
        self.text_items.append(dob_text)
        
        # ID text
        id_text = QGraphicsSimpleTextItem(f"ID:{self.person.id}", self)
        id_text.setFont(font_small)
        id_text.setBrush(QBrush(QColor("#666666")))
        id_rect = id_text.boundingRect()
        id_x = (node_w - id_rect.width()) / 2
        id_text.setPos(id_x, padding + 40)
        self.text_items.append(id_text)
        
        for text_item in self.text_items:
            text_item.setVisible(True)
            text_item.setZValue(1)
    
    def itemChange(self, change, value):
        """Handle item changes (position updates trigger line redraws)."""
        if change == QGraphicsItem.ItemPositionChange or change == QGraphicsItem.ItemPositionHasChanged:
            for line in self.connected_lines:
                line.update_path()
        
        return super().itemChange(change, value)
    
    def add_connected_line(self, line):
        """Register a relationship line connected to this node."""
        if line not in self.connected_lines:
            self.connected_lines.append(line)
    
    def get_center(self) -> QPointF:
        """Get the center point of the node."""
        return self.sceneBoundingRect().center()
    
    def get_top_center(self) -> QPointF:
        """Get the top center point of the node."""
        rect = self.sceneBoundingRect()
        return QPointF(rect.center().x(), rect.top())
    
    def get_bottom_center(self) -> QPointF:
        """Get the bottom center point of the node."""
        rect = self.sceneBoundingRect()
        return QPointF(rect.center().x(), rect.bottom())


class SpouseLine(QGraphicsPathItem):
    """Horizontal line connecting two spouses."""
    
    def __init__(self, node1: PersonNode, node2: PersonNode):
        super().__init__()
        
        self.node1 = node1
        self.node2 = node2
        
        self.setZValue(-1)
        
        node1.add_connected_line(self)
        node2.add_connected_line(self)
        
        pen = QPen(QColor(TREE_CONFIG['spouse_line_color']), TREE_CONFIG['spouse_line_width'])
        self.setPen(pen)
        
        self.update_path()
    
    def update_path(self):
        """Update the horizontal line between spouses."""
        center1 = self.node1.get_center()
        center2 = self.node2.get_center()
        
        path = QPainterPath()
        path.moveTo(center1)
        path.lineTo(center2)
        
        self.setPath(path)
    
    def get_midpoint(self) -> QPointF:
        """Get the midpoint of the spouse line."""
        center1 = self.node1.get_center()
        center2 = self.node2.get_center()
        return QPointF((center1.x() + center2.x()) / 2, (center1.y() + center2.y()) / 2)


class FamilyTrunk(QGraphicsPathItem):
    """Vertical trunk line from spouse couple to children with child branches."""
    
    def __init__(self, spouse_line: SpouseLine, children_nodes: List[PersonNode]):
        super().__init__()
        
        self.spouse_line = spouse_line
        self.children_nodes = children_nodes
        
        self.setZValue(-1)
        
        pen = QPen(QColor(TREE_CONFIG['parent_line_color']), TREE_CONFIG['parent_line_width'])
        self.setPen(pen)
        
        self.update_path()
    
    def update_path(self):
        """Update trunk and child branches."""
        if not self.children_nodes:
            return
        
        midpoint = self.spouse_line.get_midpoint()
        path = QPainterPath()
        
        # Start from midpoint of spouse line
        path.moveTo(midpoint)
        
        # Find lowest child to draw trunk down to
        min_child_y = min(child.get_top_center().y() for child in self.children_nodes)
        
        # Vertical trunk line down
        trunk_bottom = QPointF(midpoint.x(), min_child_y)
        path.lineTo(trunk_bottom)
        
        # Horizontal branches to each child
        for child in self.children_nodes:
            child_top = child.get_top_center()
            
            # Horizontal line from trunk to child
            path.moveTo(trunk_bottom.x(), trunk_bottom.y())
            path.lineTo(child_top.x(), trunk_bottom.y())
            
            # Vertical line from horizontal branch to child
            path.moveTo(child_top.x(), trunk_bottom.y())
            path.lineTo(child_top)
        
        self.setPath(path)


class SingleParentLine(QGraphicsPathItem):
    """Line from single parent to child."""
    
    def __init__(self, parent_node: PersonNode, child_node: PersonNode):
        super().__init__()
        
        self.parent_node = parent_node
        self.child_node = child_node
        
        self.setZValue(-1)
        
        parent_node.add_connected_line(self)
        child_node.add_connected_line(self)
        
        pen = QPen(QColor(TREE_CONFIG['parent_line_color']), TREE_CONFIG['parent_line_width'])
        self.setPen(pen)
        
        self.update_path()
    
    def update_path(self):
        """Update the line from parent to child."""
        start = self.parent_node.get_bottom_center()
        end = self.child_node.get_top_center()
        
        path = QPainterPath()
        path.moveTo(start)
        
        # Smooth bezier curve
        mid_y = (start.y() + end.y()) / 2
        control1 = QPointF(start.x(), mid_y)
        control2 = QPointF(end.x(), mid_y)
        
        path.cubicTo(control1, control2, end)
        
        self.setPath(path)


class FamilyTreeView(QGraphicsView):
    """Interactive view for displaying family trees."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Rendering quality
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Navigation
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor('#FFFFFF')))
        
        # Storage
        self.nodes: Dict[int, PersonNode] = {}
        self.lines: List = []
        
        self._zoom = 1.0
        self.setMouseTracking(True)
    
    def clear_tree(self):
        """Clear all items from the scene."""
        self.scene.clear()
        self.nodes.clear()
        self.lines.clear()
    
    def render_tree(self, persons: List[Person], relationships: List[Relationship], 
                    center_person_id: Optional[int] = None):
        """Render a family tree with proper family trunk connections."""
        from visualization.graph_layout import TreeLayoutEngine
        
        self.clear_tree()
        
        if not persons:
            return
        
        # Calculate layout
        layout_engine = TreeLayoutEngine()
        positions = layout_engine.calculate_layout(persons, relationships, center_person_id)
        
        # Create nodes
        for person in persons:
            if person.id in positions:
                x, y = positions[person.id]
                is_highlight = (person.id == center_person_id)
                node = PersonNode(person, x, y, is_highlight)
                self.scene.addItem(node)
                self.nodes[person.id] = node
        
        # Build graph structure for relationship handling
        graph = self._build_graph(relationships)
        
        # Handle relationships
        processed_couples = set()
        processed_children = set()
        
        # Create spouse lines and family trunks
        for rel in relationships:
            if rel.relation_type == 'spouse':
                couple_key = tuple(sorted([rel.person_a_id, rel.person_b_id]))
                
                if couple_key not in processed_couples:
                    parent1_id, parent2_id = couple_key
                    
                    if parent1_id in self.nodes and parent2_id in self.nodes:
                        parent1_node = self.nodes[parent1_id]
                        parent2_node = self.nodes[parent2_id]
                        
                        # Create spouse line
                        spouse_line = SpouseLine(parent1_node, parent2_node)
                        self.scene.addItem(spouse_line)
                        self.lines.append(spouse_line)
                        
                        # Find all children of this couple
                        children_ids = (graph[parent1_id]['children'] & graph[parent2_id]['children'])
                        children_nodes = [self.nodes[cid] for cid in children_ids if cid in self.nodes]
                        
                        if children_nodes:
                            # Create family trunk with branches
                            trunk = FamilyTrunk(spouse_line, children_nodes)
                            self.scene.addItem(trunk)
                            self.lines.append(trunk)
                            
                            processed_children.update(children_ids)
                        
                        processed_couples.add(couple_key)
        
        # Create single parent lines for children without both parents
        for rel in relationships:
            if rel.relation_type == 'parent':
                child_id = rel.person_b_id
                
                # Only create single parent line if child not already handled by family trunk
                if child_id not in processed_children:
                    if rel.person_a_id in self.nodes and child_id in self.nodes:
                        parent_node = self.nodes[rel.person_a_id]
                        child_node = self.nodes[child_id]
                        
                        line = SingleParentLine(parent_node, child_node)
                        self.scene.addItem(line)
                        self.lines.append(line)
        
        # Set scene bounds with padding
        if self.scene.items():
            scene_rect = self.scene.itemsBoundingRect()
            padded_rect = scene_rect.adjusted(-120, -120, 120, 120)
            self.scene.setSceneRect(padded_rect)
            
            # Fit view
            self.fitInView(padded_rect, Qt.KeepAspectRatio)
            self.scene.update()
    
    def _build_graph(self, relationships: List[Relationship]) -> Dict[int, Dict[str, Set[int]]]:
        """Build graph structure from relationships."""
        from collections import defaultdict
        
        graph = defaultdict(lambda: {'parents': set(), 'children': set(), 'spouses': set()})
        
        for rel in relationships:
            if rel.relation_type == 'parent':
                graph[rel.person_a_id]['children'].add(rel.person_b_id)
                graph[rel.person_b_id]['parents'].add(rel.person_a_id)
            elif rel.relation_type == 'spouse':
                graph[rel.person_a_id]['spouses'].add(rel.person_b_id)
                graph[rel.person_b_id]['spouses'].add(rel.person_a_id)
        
        return graph
    
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel."""
        zoom_factor = 1.15
        old_pos = self.mapToScene(event.position().toPoint())
        
        if event.angleDelta().y() > 0:
            if self._zoom < 5.0:
                self.scale(zoom_factor, zoom_factor)
                self._zoom *= zoom_factor
        else:
            if self._zoom > 0.2:
                self.scale(1 / zoom_factor, 1 / zoom_factor)
                self._zoom /= zoom_factor
        
        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)
    
    def reset_view(self):
        """Reset zoom and center the view."""
        self.resetTransform()
        self._zoom = 1.0
        if self.scene.items():
            padded_rect = self.scene.itemsBoundingRect().adjusted(-120, -120, 120, 120)
            self.scene.setSceneRect(padded_rect)
            self.fitInView(padded_rect, Qt.KeepAspectRatio)

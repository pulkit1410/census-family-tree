"""
Interactive family tree visualization using PyQt with dynamic graph updates.
"""
from typing import Dict, List, Optional
from collections import defaultdict
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsSimpleTextItem
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
        
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        self.setup_appearance()
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
        """Add text labels with proper positioning."""
        node_w = TREE_CONFIG['node_width']
        node_h = TREE_CONFIG['node_height']
        base_size = TREE_CONFIG.get('font_size', 9)
        padding = 5
        
        name = self.person.full_name
        if len(name) > 20:
            name = name[:17] + "..."
        
        name_text = QGraphicsSimpleTextItem(name, self)
        font_bold = QFont(TREE_CONFIG['font_family'], base_size, QFont.Bold)
        name_text.setFont(font_bold)
        name_text.setBrush(QBrush(QColor("#000000")))
        name_rect = name_text.boundingRect()
        name_x = (node_w - name_rect.width()) / 2
        name_text.setPos(name_x, padding)
        self.text_items.append(name_text)
        
        dob_str = self.person.dob.strftime('%Y-%m-%d') if self.person.dob else 'DOB: ?'
        dob_text = QGraphicsSimpleTextItem(dob_str, self)
        font_small = QFont(TREE_CONFIG['font_family'], max(base_size - 1, 7))
        dob_text.setFont(font_small)
        dob_text.setBrush(QBrush(QColor("#333333")))
        dob_rect = dob_text.boundingRect()
        dob_x = (node_w - dob_rect.width()) / 2
        dob_text.setPos(dob_x, padding + 22)
        self.text_items.append(dob_text)
        
        id_text = QGraphicsSimpleTextItem(f"ID:{self.person.id}", self)
        id_text.setFont(font_small)
        id_text.setBrush(QBrush(QColor("#666666")))
        id_rect = id_text.boundingRect()
        id_x = (node_w - id_rect.width()) / 2
        id_text.setPos(id_x, padding + 40)
        self.text_items.append(id_text)
    
    def itemChange(self, change, value):
        """Update all connected lines when node moves."""
        if change == QGraphicsItem.ItemPositionChange or change == QGraphicsItem.ItemPositionHasChanged:
            for line in self.connected_lines:
                line.update_path()
        return super().itemChange(change, value)
    
    def register_line(self, line):
        """Register a line connected to this node."""
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


class FamilyLine(QGraphicsPathItem):
    """
    A single unified line system handling:
    - Spouse connections (horizontal lines)
    - Parent-child connections (curved lines)
    - Family trunks with branches (for couples with multiple children)
    """
    
    def __init__(self, connected_nodes: List[PersonNode], line_type: str):
        super().__init__()
        self.connected_nodes = connected_nodes
        self.line_type = line_type  # 'spouse', 'parent_trunk', 'single_parent'
        
        self.setZValue(-1)
        self.setup_appearance()
        
        # Register this line with all connected nodes
        for node in connected_nodes:
            node.register_line(self)
        
        self.update_path()
    
    def setup_appearance(self):
        """Setup line appearance based on type."""
        if self.line_type == 'spouse':
            pen = QPen(QColor(TREE_CONFIG['spouse_line_color']), TREE_CONFIG['spouse_line_width'])
            pen.setStyle(Qt.DashLine)
        else:  # parent_trunk or single_parent
            pen = QPen(QColor(TREE_CONFIG['parent_line_color']), TREE_CONFIG['parent_line_width'])
        
        self.setPen(pen)
    
    def update_path(self):
        """Update the path based on current node positions."""
        path = QPainterPath()
        
        if self.line_type == 'spouse':
            self._update_spouse_line(path)
        elif self.line_type == 'single_parent':
            self._update_single_parent_line(path)
        elif self.line_type == 'parent_trunk':
            self._update_parent_trunk_line(path)
        
        self.setPath(path)
    
    def _update_spouse_line(self, path: QPainterPath):
        """Draw horizontal line between two spouses."""
        if len(self.connected_nodes) < 2:
            return
        
        node1, node2 = self.connected_nodes[0], self.connected_nodes[1]
        center1 = node1.get_center()
        center2 = node2.get_center()
        
        path.moveTo(center1)
        path.lineTo(center2)
    
    def _update_single_parent_line(self, path: QPainterPath):
        """Draw curved line from single parent to child."""
        if len(self.connected_nodes) < 2:
            return
        
        parent_node = self.connected_nodes[0]
        child_node = self.connected_nodes[1]
        
        start = parent_node.get_bottom_center()
        end = child_node.get_top_center()
        
        path.moveTo(start)
        mid_y = (start.y() + end.y()) / 2
        control1 = QPointF(start.x(), mid_y)
        control2 = QPointF(end.x(), mid_y)
        path.cubicTo(control1, control2, end)
    
    def _update_parent_trunk_line(self, path: QPainterPath):
        """
        Draw family trunk with branches.
        connected_nodes[0:2] = parents
        connected_nodes[2:] = children
        """
        if len(self.connected_nodes) < 3:
            return
        
        parent1 = self.connected_nodes[0]
        parent2 = self.connected_nodes[1]
        children = self.connected_nodes[2:]
        
        # Midpoint between parents
        parent1_center = parent1.get_center()
        parent2_center = parent2.get_center()
        midpoint = QPointF(
            (parent1_center.x() + parent2_center.x()) / 2,
            (parent1_center.y() + parent2_center.y()) / 2
        )
        
        # Trunk endpoint (top of lowest child)
        min_child_y = min(child.get_top_center().y() for child in children)
        trunk_bottom = QPointF(midpoint.x(), min_child_y)
        
        # Draw vertical trunk
        path.moveTo(midpoint)
        path.lineTo(trunk_bottom)
        
        # Draw branches to each child
        for child in children:
            child_top = child.get_top_center()
            
            # Horizontal branch
            path.moveTo(trunk_bottom)
            path.lineTo(QPointF(child_top.x(), trunk_bottom.y()))
            
            # Vertical drop to child
            path.lineTo(child_top)
    
    def get_spouse_midpoint(self) -> Optional[QPointF]:
        """Get midpoint of spouse line (used for trunk attachment)."""
        if self.line_type == 'spouse' and len(self.connected_nodes) >= 2:
            center1 = self.connected_nodes[0].get_center()
            center2 = self.connected_nodes[1].get_center()
            return QPointF((center1.x() + center2.x()) / 2, (center1.y() + center2.y()) / 2)
        return None


class FamilyTreeView(QGraphicsView):
    """Interactive view for displaying family trees."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor('#FFFFFF')))
        
        self.nodes: Dict[int, PersonNode] = {}
        self.lines: List[FamilyLine] = []
        
        self._zoom = 1.0
        self.setMouseTracking(True)
    
    def clear_tree(self):
        """Clear all items from the scene."""
        self.scene.clear()
        self.nodes.clear()
        self.lines.clear()
    
    def render_tree(self, persons: List[Person], relationships: List[Relationship], 
                    center_person_id: Optional[int] = None):
        """Render family tree with dynamic trunk visualization."""
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
        
        # Build graph
        graph = self._build_graph(relationships)
        
        # Track which relationships we've already drawn
        processed_couples = set()
        processed_children = set()
        
        # Draw spouse lines and family trunks
        for rel in relationships:
            if rel.relation_type == 'spouse':
                couple_key = tuple(sorted([rel.person_a_id, rel.person_b_id]))
                
                if couple_key not in processed_couples and couple_key[0] in self.nodes and couple_key[1] in self.nodes:
                    parent1_id, parent2_id = couple_key
                    parent1_node = self.nodes[parent1_id]
                    parent2_node = self.nodes[parent2_id]
                    
                    # Find children of this couple
                    children_ids = graph[parent1_id]['children'] & graph[parent2_id]['children']
                    children_nodes = [self.nodes[cid] for cid in children_ids if cid in self.nodes]
                    
                    if children_nodes:
                        # Draw trunk with children
                        all_nodes = [parent1_node, parent2_node] + children_nodes
                        trunk_line = FamilyLine(all_nodes, 'parent_trunk')
                        self.scene.addItem(trunk_line)
                        self.lines.append(trunk_line)
                        processed_children.update(children_ids)
                    else:
                        # Just draw spouse line (no children)
                        spouse_line = FamilyLine([parent1_node, parent2_node], 'spouse')
                        self.scene.addItem(spouse_line)
                        self.lines.append(spouse_line)
                    
                    processed_couples.add(couple_key)
        
        # Draw single parent lines for remaining children
        for rel in relationships:
            if rel.relation_type == 'parent' and rel.person_b_id not in processed_children:
                parent_id = rel.person_a_id
                child_id = rel.person_b_id
                
                if parent_id in self.nodes and child_id in self.nodes:
                    parent_node = self.nodes[parent_id]
                    child_node = self.nodes[child_id]
                    
                    line = FamilyLine([parent_node, child_node], 'single_parent')
                    self.scene.addItem(line)
                    self.lines.append(line)
        
        # Fit scene
        if self.scene.items():
            scene_rect = self.scene.itemsBoundingRect()
            padded_rect = scene_rect.adjusted(-120, -120, 120, 120)
            self.scene.setSceneRect(padded_rect)
            self.fitInView(padded_rect, Qt.KeepAspectRatio)
            self.scene.update()
    
    def _build_graph(self, relationships: List[Relationship]) -> Dict:
        """Build graph structure from relationships."""
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

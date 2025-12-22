"""
Interactive family tree visualization using PyQt with dynamic graph updates.
"""
from typing import Dict, List, Set, Tuple, Optional
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, 
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
    QGraphicsSimpleTextItem
)
from PySide6.QtCore import Qt, QPointF, QRectF, QVariant
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
        # When position changes, update all connected lines
        if change == QGraphicsItem.ItemPositionChange or change == QGraphicsItem.ItemPositionHasChanged:
            # Update all connected relationship lines
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
    
    def get_left_center(self) -> QPointF:
        """Get the left center point of the node."""
        rect = self.sceneBoundingRect()
        return QPointF(rect.left(), rect.center().y())
    
    def get_right_center(self) -> QPointF:
        """Get the right center point of the node."""
        rect = self.sceneBoundingRect()
        return QPointF(rect.right(), rect.center().y())


class RelationshipLine(QGraphicsPathItem):
    """A line representing a relationship between two persons."""
    
    def __init__(self, start_node: PersonNode, end_node: PersonNode, relation_type: str):
        super().__init__()
        
        self.start_node = start_node
        self.end_node = end_node
        self.relation_type = relation_type
        
        self.setZValue(-1)
        
        # Register this line with both nodes
        start_node.add_connected_line(self)
        end_node.add_connected_line(self)
        
        self.setup_appearance()
        self.update_path()
    
    def setup_appearance(self):
        """Setup line appearance based on relationship type."""
        if self.relation_type == 'spouse':
            pen = QPen(QColor(TREE_CONFIG['spouse_line_color']), TREE_CONFIG['spouse_line_width'])
            pen.setStyle(Qt.DashLine)
        else:
            pen = QPen(QColor(TREE_CONFIG['parent_line_color']), TREE_CONFIG['parent_line_width'])
        
        self.setPen(pen)
    
    def update_path(self):
        """Update the path based on node positions."""
        if self.relation_type == 'parent':
            start = self.start_node.get_bottom_center()
            end = self.end_node.get_top_center()
            
            path = QPainterPath()
            path.moveTo(start)
            
            # Smooth bezier curve
            mid_y = (start.y() + end.y()) / 2
            control1 = QPointF(start.x(), mid_y)
            control2 = QPointF(end.x(), mid_y)
            
            path.cubicTo(control1, control2, end)
        else:
            start = self.start_node.get_center()
            end = self.end_node.get_center()
            
            path = QPainterPath()
            path.moveTo(start)
            path.lineTo(end)
        
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
        self.lines: List[RelationshipLine] = []
        
        self._zoom = 1.0
        self.setMouseTracking(True)
    
    def clear_tree(self):
        """Clear all items from the scene."""
        self.scene.clear()
        self.nodes.clear()
        self.lines.clear()
    
    def render_tree(self, persons: List[Person], relationships: List[Relationship], 
                    center_person_id: Optional[int] = None):
        """Render a family tree."""
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
        
        # Create relationship lines
        for rel in relationships:
            if rel.person_a_id in self.nodes and rel.person_b_id in self.nodes:
                start_node = self.nodes[rel.person_a_id]
                end_node = self.nodes[rel.person_b_id]
                line = RelationshipLine(start_node, end_node, rel.relation_type)
                self.scene.addItem(line)
                self.lines.append(line)
        
        # Set scene bounds with padding
        scene_rect = self.scene.itemsBoundingRect()
        padded_rect = scene_rect.adjusted(-120, -120, 120, 120)
        self.scene.setSceneRect(padded_rect)
        
        # Fit view
        self.fitInView(padded_rect, Qt.KeepAspectRatio)
        self.scene.update()
        
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

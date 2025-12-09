"""
Interactive family tree visualization using PyQt.
"""
from typing import Dict, List, Set, Tuple, Optional
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, 
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem
)
from PySide6.QtCore import Qt, QPointF, QRectF
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
        # Determine color based on gender
        if self.is_highlight:
            color = QColor(TREE_CONFIG['highlight_color'])
        elif self.person.gender == 'Male':
            color = QColor(TREE_CONFIG['male_color'])
        elif self.person.gender == 'Female':
            color = QColor(TREE_CONFIG['female_color'])
        else:
            color = QColor(TREE_CONFIG['unknown_color'])
        
        # Set brush and pen
        self.setBrush(QBrush(color))
        pen = QPen(QColor(TREE_CONFIG['border_color']), TREE_CONFIG['border_width'])
        self.setPen(pen)
        
    def add_labels(self):
        """Add text labels to the node."""
        # Name label
        name_text = QGraphicsTextItem(self.person.full_name, self)
        font = QFont(TREE_CONFIG['font_family'], TREE_CONFIG['font_size'], QFont.Bold)
        name_text.setFont(font)
        name_text.setDefaultTextColor(QColor('#000000'))
        
        # Truncate name if too long
        name = self.person.full_name
        if len(name) > 20:
            name = name[:17] + "..."
        name_text.setPlainText(name)
        
        # Center the name
        name_width = name_text.boundingRect().width()
        name_text.setPos((TREE_CONFIG['node_width'] - name_width) / 2, 10)
        
        # DOB label
        dob_str = self.person.dob.strftime('%Y-%m-%d') if self.person.dob else 'DOB: Unknown'
        dob_text = QGraphicsTextItem(dob_str, self)
        font_small = QFont(TREE_CONFIG['font_family'], TREE_CONFIG['font_size'] - 2)
        dob_text.setFont(font_small)
        dob_text.setDefaultTextColor(QColor('#333333'))
        
        # Center the DOB
        dob_width = dob_text.boundingRect().width()
        dob_text.setPos((TREE_CONFIG['node_width'] - dob_width) / 2, 35)
        
        # ID label
        id_text = QGraphicsTextItem(f"ID: {self.person.id}", self)
        id_text.setFont(font_small)
        id_text.setDefaultTextColor(QColor('#666666'))
        
        # Center the ID
        id_width = id_text.boundingRect().width()
        id_text.setPos((TREE_CONFIG['node_width'] - id_width) / 2, 55)
    
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
        
        # Set z-value to be below nodes
        self.setZValue(-1)
        
        # Setup appearance
        self.setup_appearance()
        
        # Update path
        self.update_path()
    
    def setup_appearance(self):
        """Setup line appearance based on relationship type."""
        if self.relation_type == 'spouse':
            pen = QPen(QColor(TREE_CONFIG['spouse_line_color']), TREE_CONFIG['spouse_line_width'])
            pen.setStyle(Qt.DashLine)
        else:  # parent relationship
            pen = QPen(QColor(TREE_CONFIG['parent_line_color']), TREE_CONFIG['parent_line_width'])
        
        self.setPen(pen)
    
    def update_path(self):
        """Update the path based on node positions."""
        if self.relation_type == 'parent':
            # Parent to child: vertical line with optional curve
            start = self.start_node.get_bottom_center()
            end = self.end_node.get_top_center()
            
            path = QPainterPath()
            path.moveTo(start)
            
            # Add a control point for smooth curve
            mid_y = (start.y() + end.y()) / 2
            control1 = QPointF(start.x(), mid_y)
            control2 = QPointF(end.x(), mid_y)
            
            path.cubicTo(control1, control2, end)
            
        else:  # spouse: horizontal line
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
        
        # Enable smooth rendering
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Enable dragging and scrolling
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Set background
        self.setBackgroundBrush(QBrush(QColor('#F5F5F5')))
        
        # Store nodes and lines
        self.nodes: Dict[int, PersonNode] = {}
        self.lines: List[RelationshipLine] = []
        
        # Initial scale
        self._zoom = 1.0
    
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
        
        # Fit the view to show all content
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel."""
        # Zoom factor
        zoom_factor = 1.15
        
        # Get the old position
        old_pos = self.mapToScene(event.position().toPoint())
        
        # Zoom
        if event.angleDelta().y() > 0:
            # Zoom in
            self.scale(zoom_factor, zoom_factor)
            self._zoom *= zoom_factor
        else:
            # Zoom out
            self.scale(1 / zoom_factor, 1 / zoom_factor)
            self._zoom /= zoom_factor
        
        # Get the new position
        new_pos = self.mapToScene(event.position().toPoint())
        
        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        # Check if clicking on empty space for panning
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
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
"""
Interactive family tree visualization using PyQt.
"""
from typing import Dict, List, Set, Tuple, Optional
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, 
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
    QGraphicsSimpleTextItem
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
        self.text_items = []  # Store text items for debugging
        
        # Position
        self.setPos(x, y)
        
        # Make draggable
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        # Styling
        self.setup_appearance()
        
        # Add text - MUST be called after the item is positioned
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
        """Add text labels to the node using QGraphicsSimpleTextItem for better visibility."""
        base_size = TREE_CONFIG.get('font_size', 10)
        
        # Prepare name
        name = self.person.full_name
        if len(name) > 22:
            name = name[:19] + "..."
        
        # Create name text (using QGraphicsSimpleTextItem - more reliable)
        name_text = QGraphicsSimpleTextItem(name, self)
        font = QFont(TREE_CONFIG['font_family'], base_size, QFont.Bold)
        name_text.setFont(font)
        name_text.setBrush(QBrush(QColor("#000000")))
        
        # Center the name
        name_rect = name_text.boundingRect()
        name_x = (TREE_CONFIG['node_width'] - name_rect.width()) / 2
        name_text.setPos(name_x, 10)
        self.text_items.append(name_text)
        
        # Create DOB text
        dob_str = self.person.dob.strftime('%Y-%m-%d') if self.person.dob else 'DOB: ?'
        dob_text = QGraphicsSimpleTextItem(dob_str, self)
        font_small = QFont(TREE_CONFIG['font_family'], base_size - 2)
        dob_text.setFont(font_small)
        dob_text.setBrush(QBrush(QColor("#000000")))
        
        # Center the DOB
        dob_rect = dob_text.boundingRect()
        dob_x = (TREE_CONFIG['node_width'] - dob_rect.width()) / 2
        dob_text.setPos(dob_x, 32)
        self.text_items.append(dob_text)
        
        # Create ID text
        id_text = QGraphicsSimpleTextItem(f"ID: {self.person.id}", self)
        id_text.setFont(font_small)
        id_text.setBrush(QBrush(QColor("#555555")))
        
        # Center the ID
        id_rect = id_text.boundingRect()
        id_x = (TREE_CONFIG['node_width'] - id_rect.width()) / 2
        id_text.setPos(id_x, 52)
        self.text_items.append(id_text)
        
        # Ensure text is visible
        for text_item in self.text_items:
            text_item.setVisible(True)
            text_item.setZValue(1)  # Above the rectangle
    
    def paint(self, painter, option, widget=None):
        """Override paint to ensure proper rendering."""
        # Call parent paint for the rectangle
        super().paint(painter, option, widget)
        
        # Ensure text items are visible
        for text_item in self.text_items:
            if not text_item.isVisible():
                text_item.setVisible(True)
    
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
            # Parent to child: vertical line with smooth curve
            start = self.start_node.get_bottom_center()
            end = self.end_node.get_top_center()
            
            path = QPainterPath()
            path.moveTo(start)
            
            # Add control points for smooth bezier curve
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
        
        # Enable ALL rendering hints for best quality
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setRenderHint(QPainter.LosslessImageRendering, True)
        
        # Viewport update mode for better performance
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Enable dragging and scrolling
        self.setDragMode(QGraphicsView.NoDrag)  # Start with no drag, enable on right-click
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        
        # Set background
        self.setBackgroundBrush(QBrush(QColor('#F5F5F5')))
        
        # Store nodes and lines
        self.nodes: Dict[int, PersonNode] = {}
        self.lines: List[RelationshipLine] = []
        
        # Initial scale
        self._zoom = 1.0
        
        # Enable mouse tracking
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
            print("Warning: No persons to render")
            return
        
        print(f"Rendering tree with {len(persons)} persons and {len(relationships)} relationships")
        
        # Calculate layout
        layout_engine = TreeLayoutEngine()
        positions = layout_engine.calculate_layout(persons, relationships, center_person_id)
        
        print(f"Layout calculated: {len(positions)} positions")
        
        # Create nodes
        for person in persons:
            if person.id in positions:
                x, y = positions[person.id]
                is_highlight = (person.id == center_person_id)
                node = PersonNode(person, x, y, is_highlight)
                self.scene.addItem(node)
                self.nodes[person.id] = node
                print(f"Added node for {person.full_name} at ({x}, {y})")
        
        print(f"Created {len(self.nodes)} nodes")
        
        # Create relationship lines
        for rel in relationships:
            if rel.person_a_id in self.nodes and rel.person_b_id in self.nodes:
                start_node = self.nodes[rel.person_a_id]
                end_node = self.nodes[rel.person_b_id]
                
                line = RelationshipLine(start_node, end_node, rel.relation_type)
                self.scene.addItem(line)
                self.lines.append(line)
        
        print(f"Created {len(self.lines)} relationship lines")
        
        # Update scene rect and fit view
        scene_rect = self.scene.itemsBoundingRect()
        print(f"Scene bounding rect: {scene_rect}")
        
        # Add padding
        padded_rect = scene_rect.adjusted(-100, -100, 100, 100)
        self.scene.setSceneRect(padded_rect)
        
        # Fit view with some margin
        self.fitInView(padded_rect, Qt.KeepAspectRatio)
        
        # Force update
        self.scene.update()
        self.viewport().update()
        
        print("Tree rendering complete")
        
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel."""
        # Zoom factor
        zoom_factor = 1.15
        
        # Get the old position
        old_pos = self.mapToScene(event.position().toPoint())
        
        # Zoom with limits
        if event.angleDelta().y() > 0:
            # Zoom in (max 5x)
            if self._zoom < 5.0:
                self.scale(zoom_factor, zoom_factor)
                self._zoom *= zoom_factor
        else:
            # Zoom out (min 0.2x)
            if self._zoom > 0.2:
                self.scale(1 / zoom_factor, 1 / zoom_factor)
                self._zoom /= zoom_factor
        
        # Get the new position
        new_pos = self.mapToScene(event.position().toPoint())
        
        # Move scene to old position (smooth zoom to cursor)
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        # Right-click for panning
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            # Create a fake left-click event for drag to work
            fake_event = event
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
            padded_rect = self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
            self.scene.setSceneRect(padded_rect)
            self.fitInView(padded_rect, Qt.KeepAspectRatio)
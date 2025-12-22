"""
Configuration settings for the Family Tree application.
"""

# Database settings
DATABASE_PATH = 'family.db'
DATABASE_ECHO = False

# Visualization settings
TREE_CONFIG = {
    'node_width': 160,
    'node_height': 95,
    'horizontal_spacing': 100,
    'vertical_spacing': 30,
    'level_spacing': 200,
    
    # Colors
    'male_color': '#ADD8E6',  # Light blue
    'female_color': '#FFB6C1',  # Light pink
    'unknown_color': '#E0E0E0',  # Gray
    'highlight_color': '#FFD700',  # Gold
    
    # Borders and fonts
    'border_radius': 10,
    'border_width': 2,
    'border_color': '#333333',
    'font_family': 'Arial',
    'font_size': 9,
    
    # Relationship lines
    'parent_line_color': '#666666',
    'parent_line_width': 2,
    'spouse_line_color': '#FF1493',
    'spouse_line_width': 2,
    'spouse_line_style': 'dashed',
}

# Duplicate detection settings
DUPLICATE_CONFIG = {
    'threshold': 0.75,
    'name_weight': 0.6,
    'dob_weight': 0.3,
    'id_weight': 0.1,
}

# UI settings
UI_CONFIG = {
    'window_title': 'Family Tree / Census Helper',
    'window_width': 1400,
    'window_height': 900,
    'splitter_ratio': [1, 3],
}

# Application metadata
APP_VERSION = '2.0'
APP_AUTHOR = 'Census Helper System'

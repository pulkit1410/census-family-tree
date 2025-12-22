"""
Graph layout algorithm for family trees with improved spacing and collision detection.
"""
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

from config import TREE_CONFIG
from models.person import Person
from models.relationship import Relationship


class TreeLayoutEngine:
    """Calculate positions for family tree nodes using hierarchical layout with collision avoidance."""
    
    def __init__(self):
        self.node_width = TREE_CONFIG['node_width']
        self.node_height = TREE_CONFIG['node_height']
        self.h_spacing = TREE_CONFIG['horizontal_spacing']
        self.v_spacing = TREE_CONFIG['vertical_spacing']
        self.level_spacing = TREE_CONFIG['level_spacing']
    
    def calculate_layout(self, persons: List[Person], relationships: List[Relationship],
                        center_person_id: Optional[int] = None) -> Dict[int, Tuple[float, float]]:
        """
        Calculate positions for all persons in the tree with proper spacing.
        Returns dict mapping person_id -> (x, y) position.
        """
        if not persons:
            return {}
        
        # Build relationship graph
        graph = self._build_graph(relationships)
        
        # Find center person or pick one
        if center_person_id and center_person_id in {p.id for p in persons}:
            root_id = center_person_id
        else:
            root_id = persons[0].id
        
        # Calculate levels (generation depth)
        levels = self._calculate_levels(graph, root_id)
        
        # Group by levels
        level_groups = defaultdict(list)
        for person_id, level in levels.items():
            level_groups[level].append(person_id)
        
        # Calculate positions with improved spacing
        positions = self._calculate_positions_with_spacing(level_groups, graph, levels)
        
        return positions
    
    def _calculate_positions_with_spacing(self, level_groups: Dict, 
                                         graph: Dict, levels: Dict) -> Dict[int, Tuple[float, float]]:
        """Calculate positions ensuring proper spacing and family grouping."""
        positions = {}
        
        for level in sorted(level_groups.keys()):
            person_ids = level_groups[level]
            
            # Calculate y position for this level
            y = level * (self.node_height + self.level_spacing)
            
            # Group by families (spouses and their children stay together)
            family_groups = self._group_families(person_ids, graph, levels)
            
            # Calculate total width needed
            total_width = self._calculate_level_width(family_groups, graph)
            start_x = -total_width / 2
            
            current_x = start_x
            
            for family_group in family_groups:
                # Position all persons in this family group
                group_width = len(family_group) * (self.node_width + self.h_spacing) - self.h_spacing
                
                for i, person_id in enumerate(family_group):
                    x = current_x + i * (self.node_width + self.h_spacing)
                    positions[person_id] = (x, y)
                
                current_x += group_width + self.h_spacing * 2
        
        return positions
    
    def _group_families(self, person_ids: List[int], graph: Dict, levels: Dict) -> List[List[int]]:
        """Group persons by family units (spouses together)."""
        families = []
        processed = set()
        
        for person_id in person_ids:
            if person_id in processed:
                continue
            
            # Find spouse if exists
            spouses = [person_id]
            for spouse_id in graph[person_id]['spouses']:
                if spouse_id in person_ids and levels[spouse_id] == levels[person_id]:
                    spouses.append(spouse_id)
                    processed.add(spouse_id)
            
            # Sort spouses for consistent positioning
            spouses.sort()
            families.append(spouses)
            processed.add(person_id)
        
        return families
    
    def _calculate_level_width(self, family_groups: List[List[int]], graph: Dict) -> float:
        """Calculate total width needed for a level."""
        total_width = 0
        for i, family in enumerate(family_groups):
            family_width = len(family) * (self.node_width + self.h_spacing) - self.h_spacing
            total_width += family_width
            if i < len(family_groups) - 1:
                total_width += self.h_spacing * 2  # Gap between families
        return total_width
    
    def _build_graph(self, relationships: List[Relationship]) -> Dict[int, Dict[str, Set[int]]]:
        """
        Build a graph structure from relationships.
        Returns dict: person_id -> {'parents': set(), 'children': set(), 'spouses': set()}
        """
        graph = defaultdict(lambda: {'parents': set(), 'children': set(), 'spouses': set()})
        
        for rel in relationships:
            if rel.relation_type == 'parent':
                graph[rel.person_a_id]['children'].add(rel.person_b_id)
                graph[rel.person_b_id]['parents'].add(rel.person_a_id)
            elif rel.relation_type == 'spouse':
                graph[rel.person_a_id]['spouses'].add(rel.person_b_id)
                graph[rel.person_b_id]['spouses'].add(rel.person_a_id)
        
        return graph
    
    def _calculate_levels(self, graph: Dict, root_id: int) -> Dict[int, int]:
        """
        Calculate level (generation) for each person using BFS.
        Returns dict: person_id -> level
        """
        levels = {root_id: 0}
        queue = deque([root_id])
        visited = {root_id}
        
        while queue:
            current_id = queue.popleft()
            current_level = levels[current_id]
            
            # Process parents (level - 1)
            for parent_id in graph[current_id]['parents']:
                if parent_id not in visited:
                    levels[parent_id] = current_level - 1
                    queue.append(parent_id)
                    visited.add(parent_id)
            
            # Process children (level + 1)
            for child_id in graph[current_id]['children']:
                if child_id not in visited:
                    levels[child_id] = current_level + 1
                    queue.append(child_id)
                    visited.add(child_id)
            
            # Process spouses (same level)
            for spouse_id in graph[current_id]['spouses']:
                if spouse_id not in visited:
                    levels[spouse_id] = current_level
                    queue.append(spouse_id)
                    visited.add(spouse_id)
        
        return levels

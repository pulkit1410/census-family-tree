"""
Graph layout algorithm for family trees.
"""
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

from config import TREE_CONFIG
from models.person import Person
from models.relationship import Relationship


class TreeLayoutEngine:
    """Calculate positions for family tree nodes using hierarchical layout."""
    
    def __init__(self):
        self.node_width = TREE_CONFIG['node_width']
        self.node_height = TREE_CONFIG['node_height']
        self.h_spacing = TREE_CONFIG['horizontal_spacing']
        self.v_spacing = TREE_CONFIG['vertical_spacing']
        self.level_spacing = TREE_CONFIG['level_spacing']
    
    def calculate_layout(self, persons: List[Person], relationships: List[Relationship],
                        center_person_id: Optional[int] = None) -> Dict[int, Tuple[float, float]]:
        """
        Calculate positions for all persons in the tree.
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
        
        # Calculate positions
        positions = {}
        
        for level in sorted(level_groups.keys()):
            person_ids = level_groups[level]
            
            # Calculate y position for this level
            y = level * (self.node_height + self.level_spacing)
            
            # Calculate x positions to center the level
            num_persons = len(person_ids)
            total_width = num_persons * self.node_width + (num_persons - 1) * self.h_spacing
            start_x = -total_width / 2
            
            for i, person_id in enumerate(person_ids):
                x = start_x + i * (self.node_width + self.h_spacing)
                positions[person_id] = (x, y)
        
        # Adjust positions to group families together
        positions = self._adjust_for_families(positions, graph, levels)
        
        return positions
    
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
    
    def _adjust_for_families(self, positions: Dict[int, Tuple[float, float]], 
                            graph: Dict, levels: Dict[int, int]) -> Dict[int, Tuple[float, float]]:
        """
        Adjust positions to keep spouse pairs close together.
        """
        adjusted = positions.copy()
        
        # Group spouses and center them
        processed = set()
        
        for person_id in positions:
            if person_id in processed:
                continue
            
            # Find all spouses at the same level
            spouses = [person_id]
            for spouse_id in graph[person_id]['spouses']:
                if levels.get(spouse_id) == levels.get(person_id):
                    spouses.append(spouse_id)
                    processed.add(spouse_id)
            
            processed.add(person_id)
            
            # If there are spouses, adjust their positions to be adjacent
            if len(spouses) > 1:
                # Sort by current x position
                spouses.sort(key=lambda pid: positions[pid][0])
                
                # Calculate center position
                avg_x = sum(positions[pid][0] for pid in spouses) / len(spouses)
                y = positions[spouses[0]][1]
                
                # Reposition to be adjacent
                start_x = avg_x - (len(spouses) - 1) * (self.node_width + self.h_spacing // 2) / 2
                
                for i, spouse_id in enumerate(spouses):
                    x = start_x + i * (self.node_width + self.h_spacing // 2)
                    adjusted[spouse_id] = (x, y)
        
        return adjusted
"""
Graph layout algorithm for family trees with improved spacing and dual-parent handling.
"""
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

from config import TREE_CONFIG
from models.person import Person
from models.relationship import Relationship


class TreeLayoutEngine:
    """Calculate positions for family tree nodes with proper dual-parent handling."""
    
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
        Handles dual-parent relationships by positioning child centered below both parents.
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
        
        # Calculate positions with dual-parent awareness
        positions = self._calculate_positions_with_dual_parents(
            level_groups, graph, levels, persons
        )
        
        return positions
    
    def _calculate_positions_with_dual_parents(self, level_groups: Dict, 
                                               graph: Dict, levels: Dict,
                                               persons: List[Person]) -> Dict[int, Tuple[float, float]]:
        """
        Calculate positions ensuring children with dual parents are centered below both.
        """
        positions = {}
        person_map = {p.id: p for p in persons}
        
        for level in sorted(level_groups.keys()):
            person_ids = level_groups[level]
            
            # Calculate y position for this level
            y = level * (self.node_height + self.level_spacing)
            
            # Separate parent pairs and singles
            parent_pairs = self._find_parent_pairs_at_level(person_ids, graph, levels)
            singles = self._find_singles_at_level(person_ids, parent_pairs, graph, levels)
            
            # Calculate total width needed
            total_width = 0
            pair_widths = {}
            
            # Width for parent pairs
            for pair in parent_pairs:
                pair_width = 2 * (self.node_width + self.h_spacing) - self.h_spacing
                pair_widths[id(pair)] = pair_width
                total_width += pair_width + self.h_spacing * 2
            
            # Width for singles
            total_width += len(singles) * (self.node_width + self.h_spacing)
            
            start_x = -total_width / 2
            current_x = start_x
            
            # Position parent pairs
            for pair in parent_pairs:
                for i, person_id in enumerate(pair):
                    x = current_x + i * (self.node_width + self.h_spacing)
                    positions[person_id] = (x, y)
                
                current_x += pair_widths[id(pair)] + self.h_spacing * 2
            
            # Position singles
            for person_id in singles:
                positions[person_id] = (current_x, y)
                current_x += self.node_width + self.h_spacing
            
            # Adjust children positions to center below parent pairs
            positions = self._center_children_below_parents(
                positions, person_ids, graph, levels, level
            )
        
        return positions
    
    def _find_parent_pairs_at_level(self, person_ids: List[int], graph: Dict, 
                                   levels: Dict) -> List[List[int]]:
        """Find spouse pairs at the same level."""
        pairs = []
        processed = set()
        
        for person_id in person_ids:
            if person_id in processed:
                continue
            
            spouses = [person_id]
            for spouse_id in graph[person_id]['spouses']:
                if spouse_id in person_ids and levels[spouse_id] == levels[person_id]:
                    spouses.append(spouse_id)
                    processed.add(spouse_id)
            
            if len(spouses) > 1:
                spouses.sort()
                pairs.append(spouses)
                processed.add(person_id)
            else:
                processed.add(person_id)
        
        return pairs
    
    def _find_singles_at_level(self, person_ids: List[int], parent_pairs: List[List[int]],
                               graph: Dict, levels: Dict) -> List[int]:
        """Find persons without spouses at the same level."""
        paired_ids = {pid for pair in parent_pairs for pid in pair}
        singles = [pid for pid in person_ids if pid not in paired_ids]
        return singles
    
    def _center_children_below_parents(self, positions: Dict, person_ids: List[int],
                                       graph: Dict, levels: Dict, current_level: int) -> Dict[int, Tuple[float, float]]:
        """
        Adjust positions of children to center them below their parents.
        If a child has 2 parents, center the child between the parents.
        """
        adjusted = positions.copy()
        
        next_level = current_level + 1
        
        # Find all persons at next level who are children of current level
        for child_id in list(adjusted.keys()):
            if levels.get(child_id) != next_level:
                continue
            
            # Find parents of this child
            parents = list(graph[child_id]['parents'])
            
            if len(parents) == 2:
                # Child has 2 parents - center below them
                parent1_id, parent2_id = parents[0], parents[1]
                
                if parent1_id in adjusted and parent2_id in adjusted:
                    parent1_x, parent1_y = adjusted[parent1_id]
                    parent2_x, parent2_y = adjusted[parent2_id]
                    
                    # Center child between parents
                    child_x = (parent1_x + parent2_x + self.node_width) / 2 - self.node_width / 2
                    child_y = adjusted[child_id][1]
                    
                    adjusted[child_id] = (child_x, child_y)
            
            elif len(parents) == 1:
                # Single parent - child is centered below parent
                parent_id = parents[0]
                if parent_id in adjusted:
                    parent_x, parent_y = adjusted[parent_id]
                    child_x = parent_x
                    child_y = adjusted[child_id][1]
                    adjusted[child_id] = (child_x, child_y)
        
        return adjusted
    
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

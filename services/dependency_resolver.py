"""
Dependency Resolution System with Topological Sort
Detects circular dependencies and resolves correct load order
"""

from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict, deque

from core.models import Mod, ModDependency
from core.exceptions import (
    CircularDependencyError,
    MissingDependencyError,
    VersionConflictError
)
from utils.logger import LoggerMixin


class DependencyResolver(LoggerMixin):
    """Resolves mod dependencies and determines load order"""
    
    def __init__(self):
        self.mod_registry: Dict[str, Mod] = {}
    
    def register_mod(self, mod: Mod):
        """Register a mod for dependency resolution"""
        self.mod_registry[mod.id] = mod
    
    def register_mods(self, mods: List[Mod]):
        """Register multiple mods"""
        for mod in mods:
            self.register_mod(mod)
    
    def resolve_load_order(self, mods: List[Mod]) -> List[str]:
        """
        Resolve correct load order using topological sort
        
        Returns:
            List of mod IDs in correct load order
        
        Raises:
            CircularDependencyError: If circular dependency detected
            MissingDependencyError: If required dependency is missing
        """
        self.register_mods(mods)
        
        # Build dependency graph
        graph = self._build_dependency_graph(mods)
        
        # Check for circular dependencies
        self._check_circular_dependencies(graph)
        
        # Perform topological sort
        sorted_ids = self._topological_sort(graph)
        
        self.logger.info(f"Resolved load order for {len(sorted_ids)} mods")
        return sorted_ids
    
    def _build_dependency_graph(self, mods: List[Mod]) -> Dict[str, Set[str]]:
        """Build directed graph of dependencies"""
        graph = defaultdict(set)
        mod_ids = {mod.id for mod in mods}
        
        for mod in mods:
            # Add node even if no dependencies
            if mod.id not in graph:
                graph[mod.id] = set()
            
            for dep in mod.dependencies:
                if dep.mod_id not in mod_ids:
                    raise MissingDependencyError(
                        mod.id,
                        dep.mod_id,
                        dep.version_constraint
                    )
                
                # Add edge: mod depends on dep.mod_id
                graph[mod.id].add(dep.mod_id)
        
        return graph
    
    def _check_circular_dependencies(self, graph: Dict[str, Set[str]]):
        """
        Detect circular dependencies using DFS
        
        Raises:
            CircularDependencyError: If circular dependency detected
        """
        WHITE = 0  # Not visited
        GRAY = 1   # In progress
        BLACK = 2  # Completed
        
        colors = {node: WHITE for node in graph}
        parent = {}
        
        def dfs(node: str, path: List[str]):
            if colors[node] == GRAY:
                # Found cycle - build cycle path
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                raise CircularDependencyError(cycle)
            
            if colors[node] == BLACK:
                return
            
            colors[node] = GRAY
            path.append(node)
            
            for neighbor in graph[node]:
                dfs(neighbor, path.copy())
            
            colors[node] = BLACK
        
        for node in graph:
            if colors[node] == WHITE:
                dfs(node, [])
    
    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm
        
        Returns:
            List of nodes in topologically sorted order
        """
        # Calculate in-degree for each node
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] = in_degree.get(neighbor, 0) + 1
        
        # Queue of nodes with no dependencies
        queue = deque([node for node in graph if in_degree[node] == 0])
        sorted_list = []
        
        while queue:
            node = queue.popleft()
            sorted_list.append(node)
            
            # Reduce in-degree for neighbors
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If not all nodes processed, there's a cycle (shouldn't happen after check)
        if len(sorted_list) != len(graph):
            raise CircularDependencyError(
                list(set(graph.keys()) - set(sorted_list))
            )
        
        # Reverse to get correct dependency order
        # (dependencies should load before dependents)
        return sorted_list[::-1]
    
    def get_all_dependencies(self, mod_id: str, recursive: bool = True) -> List[str]:
        """
        Get all dependencies for a mod
        
        Args:
            mod_id: ID of the mod
            recursive: If True, get transitive dependencies
        
        Returns:
            List of dependency mod IDs
        """
        if mod_id not in self.mod_registry:
            return []
        
        mod = self.mod_registry[mod_id]
        
        if not recursive:
            return [dep.mod_id for dep in mod.dependencies]
        
        # BFS to get all transitive dependencies
        visited = set()
        queue = deque([mod_id])
        dependencies = []
        
        while queue:
            current_id = queue.popleft()
            if current_id in visited or current_id == mod_id:
                continue
            
            visited.add(current_id)
            dependencies.append(current_id)
            
            if current_id in self.mod_registry:
                current_mod = self.mod_registry[current_id]
                for dep in current_mod.dependencies:
                    if dep.mod_id not in visited:
                        queue.append(dep.mod_id)
        
        return dependencies
    
    def check_version_compatibility(
        self,
        mod_id: str,
        available_mods: Dict[str, str]
    ) -> Tuple[bool, List[str]]:
        """
        Check if all dependencies are satisfied with correct versions
        
        Args:
            mod_id: ID of the mod to check
            available_mods: Dict of mod_id -> version
        
        Returns:
            Tuple of (is_compatible, list_of_errors)
        """
        if mod_id not in self.mod_registry:
            return False, [f"Mod {mod_id} not found in registry"]
        
        mod = self.mod_registry[mod_id]
        errors = []
        
        for dep in mod.dependencies:
            if dep.mod_id not in available_mods:
                errors.append(
                    f"Missing dependency: {dep.mod_id} (required by {mod_id})"
                )
                continue
            
            installed_version = available_mods[dep.mod_id]
            if not self._check_version_constraint(
                installed_version,
                dep.version_constraint
            ):
                errors.append(
                    f"Version conflict: {dep.mod_id} requires {dep.version_constraint}, "
                    f"but {installed_version} is installed"
                )
        
        return len(errors) == 0, errors
    
    def _check_version_constraint(self, version: str, constraint: str) -> bool:
        """
        Check if version satisfies constraint
        
        Supports:
        - * (any version)
        - exact version (1.2.3)
        - >= operator (>=1.2.0)
        - Simple comparison
        """
        if constraint == "*":
            return True
        
        if constraint == version:
            return True
        
        # Handle >= operator
        if constraint.startswith(">="):
            required = constraint[2:].strip()
            return self._compare_versions(version, required) >= 0
        
        # Handle > operator
        if constraint.startswith(">"):
            required = constraint[1:].strip()
            return self._compare_versions(version, required) > 0
        
        # Handle <= operator
        if constraint.startswith("<="):
            required = constraint[2:].strip()
            return self._compare_versions(version, required) <= 0
        
        # Handle < operator
        if constraint.startswith("<"):
            required = constraint[1:].strip()
            return self._compare_versions(version, required) < 0
        
        return False
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare semantic versions
        
        Returns:
            -1 if v1 < v2
            0 if v1 == v2
            1 if v1 > v2
        """
        def normalize(v):
            """Convert version string to tuple of integers"""
            try:
                return tuple(map(int, v.split('.')))
            except:
                return (0, 0, 0)
        
        v1_tuple = normalize(v1)
        v2_tuple = normalize(v2)
        
        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1
        else:
            return 0
    
    def auto_resolve_dependencies(
        self,
        mod_ids: List[str],
        available_mods: Dict[str, Mod]
    ) -> List[str]:
        """
        Automatically add missing dependencies
        
        Args:
            mod_ids: List of mod IDs to install
            available_mods: Dict of available mods (from Thunderstore)
        
        Returns:
            Complete list of mod IDs including dependencies
        """
        self.logger.info(f"Auto-resolving dependencies for {len(mod_ids)} mods")
        
        required = set(mod_ids)
        to_process = deque(mod_ids)
        
        while to_process:
            current_id = to_process.popleft()
            
            if current_id not in available_mods:
                self.logger.warning(f"Mod {current_id} not available")
                continue
            
            mod = available_mods[current_id]
            self.register_mod(mod)
            
            for dep in mod.dependencies:
                if dep.mod_id not in required:
                    self.logger.info(f"Adding dependency: {dep.mod_id}")
                    required.add(dep.mod_id)
                    to_process.append(dep.mod_id)
        
        # Resolve load order
        mods_to_sort = [available_mods[mid] for mid in required if mid in available_mods]
        sorted_ids = self.resolve_load_order(mods_to_sort)
        
        self.logger.info(
            f"Auto-resolved {len(sorted_ids)} total mods "
            f"(added {len(sorted_ids) - len(mod_ids)} dependencies)"
        )
        
        return sorted_ids
    
    def find_dependents(self, mod_id: str) -> List[str]:
        """
        Find all mods that depend on this mod
        
        Args:
            mod_id: ID of the mod
        
        Returns:
            List of dependent mod IDs
        """
        dependents = []
        
        for mid, mod in self.mod_registry.items():
            if any(dep.mod_id == mod_id for dep in mod.dependencies):
                dependents.append(mid)
        
        return dependents
    
    def get_dependency_tree(self, mod_id: str, max_depth: int = 5) -> Dict:
        """
        Get dependency tree for visualization
        
        Returns:
            Nested dictionary representing dependency tree
        """
        if mod_id not in self.mod_registry:
            return {}
        
        def build_tree(current_id: str, depth: int = 0, visited: Set = None) -> Dict:
            if visited is None:
                visited = set()
            
            if depth >= max_depth or current_id in visited:
                return {"id": current_id, "name": current_id, "children": []}
            
            visited.add(current_id)
            
            if current_id not in self.mod_registry:
                return {"id": current_id, "name": current_id, "children": []}
            
            mod = self.mod_registry[current_id]
            
            return {
                "id": mod.id,
                "name": mod.name,
                "version": mod.version,
                "children": [
                    build_tree(dep.mod_id, depth + 1, visited.copy())
                    for dep in mod.dependencies
                ]
            }
        
        return build_tree(mod_id)

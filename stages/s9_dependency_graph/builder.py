"""Stage 9: Dependency Graph - build calculation graph."""

from __future__ import annotations

from collections import deque
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

from openpyxl.utils.cell import range_boundaries

from core.interfaces import Stage
from core.models import (
    CellClassificationResult,
    DependencyGraph,
    Edge,
    GraphNode,
    CircularRef,
    CalculationCluster,
)
from core.enums import CellRole


class DependencyGraphBuilder(Stage[CellClassificationResult, DependencyGraph]):
    """Build a dependency graph from classified cells."""

    MAX_RANGE_EXPANSION = 1000

    @property
    def name(self) -> str:
        return "Dependency Graph"

    @property
    def stage_number(self) -> int:
        return 9

    def validate_input(self, input_data: CellClassificationResult) -> bool:
        return isinstance(input_data, CellClassificationResult)

    async def execute(self, input_data: CellClassificationResult) -> DependencyGraph:
        nodes: Dict[str, GraphNode] = {}
        edges: List[Edge] = []

        labels_by_cell: Dict[str, str] = {}
        for sheet in input_data.sheets:
            for cell in sheet.cells:
                nodes[cell.address] = GraphNode(
                    address=cell.address,
                    role=cell.role,
                    formula=cell.formula,
                )
                if cell.label:
                    labels_by_cell[cell.address] = cell.label

        for sheet in input_data.sheets:
            for cell in sheet.cells:
                for ref in cell.references:
                    for expanded in self._expand_reference(ref):
                        if expanded not in nodes:
                            nodes[expanded] = GraphNode(
                                address=expanded,
                                role=CellRole.INPUT,
                            )
                        edges.append(Edge(source=expanded, target=cell.address))

        adjacency: Dict[str, Set[str]] = {node: set() for node in nodes}
        reverse_adjacency: Dict[str, Set[str]] = {node: set() for node in nodes}
        in_degree: Dict[str, int] = {node: 0 for node in nodes}

        for edge in edges:
            adjacency[edge.source].add(edge.target)
            reverse_adjacency[edge.target].add(edge.source)
            in_degree[edge.target] += 1

        execution_order = self._topological_sort(adjacency, in_degree)
        circular_refs = []
        if len(execution_order) < len(nodes):
            remaining = [node for node in nodes if node not in execution_order]
            circular_refs.append(CircularRef(cycle=remaining, ref_type="error"))

        depth_map = self._compute_depths(adjacency, reverse_adjacency, execution_order)
        clusters = self._compute_clusters(
            nodes, adjacency, reverse_adjacency, labels_by_cell
        )

        for node_id, node in nodes.items():
            node.in_degree = in_degree.get(node_id, 0)
            node.out_degree = len(adjacency.get(node_id, set()))
            node.depth = depth_map.get(node_id, 0)
            node.cluster = self._find_cluster_id(node_id, clusters)

        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            execution_order=execution_order,
            clusters=clusters,
            circular_refs=circular_refs,
        )

    def _topological_sort(
        self, adjacency: Dict[str, Set[str]], in_degree: Dict[str, int]
    ) -> List[str]:
        queue = deque([node for node, deg in in_degree.items() if deg == 0])
        order: List[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adjacency.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order

    def _compute_depths(
        self,
        adjacency: Dict[str, Set[str]],
        reverse_adjacency: Dict[str, Set[str]],
        execution_order: List[str],
    ) -> Dict[str, int]:
        depth_map: Dict[str, int] = {}
        for node in execution_order:
            parents = reverse_adjacency.get(node, set())
            if not parents:
                depth_map[node] = 0
            else:
                depth_map[node] = max(depth_map.get(p, 0) for p in parents) + 1
        return depth_map

    def _compute_clusters(
        self,
        nodes: Dict[str, GraphNode],
        adjacency: Dict[str, Set[str]],
        reverse_adjacency: Dict[str, Set[str]],
        labels_by_cell: Dict[str, str],
    ) -> List[CalculationCluster]:
        clusters: List[CalculationCluster] = []
        visited: Set[str] = set()
        cluster_idx = 0

        for node_id in nodes:
            if node_id in visited:
                continue
            component = self._collect_component(node_id, adjacency, reverse_adjacency)
            visited.update(component)

            inputs = []
            outputs = []
            intermediates = []

            for member in component:
                node = nodes[member]
                if node.role == CellRole.INPUT:
                    inputs.append(member)
                elif node.role == CellRole.OUTPUT:
                    outputs.append(member)
                else:
                    intermediates.append(member)

            clusters.append(
                CalculationCluster(
                    id=self._cluster_name(cluster_idx, labels_by_cell, outputs, inputs),
                    inputs=sorted(inputs),
                    outputs=sorted(outputs),
                    intermediates=sorted(intermediates),
                    semantic_purpose=self._infer_semantic_purpose(nodes, component),
                )
            )
            cluster_idx += 1

        return clusters

    def _collect_component(
        self,
        start: str,
        adjacency: Dict[str, Set[str]],
        reverse_adjacency: Dict[str, Set[str]],
    ) -> Set[str]:
        stack = [start]
        component: Set[str] = set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(adjacency.get(node, set()))
            stack.extend(reverse_adjacency.get(node, set()))
        return component

    def _find_cluster_id(
        self, node_id: str, clusters: List[CalculationCluster]
    ) -> Optional[str]:
        for cluster in clusters:
            if (
                node_id in cluster.inputs
                or node_id in cluster.outputs
                or node_id in cluster.intermediates
            ):
                return cluster.id
        return None

    def _cluster_name(
        self,
        index: int,
        labels_by_cell: Dict[str, str],
        outputs: List[str],
        inputs: List[str],
    ) -> str:
        candidates = outputs + inputs
        for cell in candidates:
            label = labels_by_cell.get(cell)
            if label:
                clean = re.sub(r"[^a-zA-Z0-9 _-]", "", label).strip()
                if clean:
                    return f"cluster_{index}_{clean.lower().replace(' ', '_')}"
        return f"cluster_{index}"

    def _infer_semantic_purpose(
        self, nodes: Dict[str, GraphNode], component: Set[str]
    ) -> Optional[str]:
        formulas = " ".join(
            [nodes[node].formula or "" for node in component if node in nodes]
        ).upper()
        if not formulas.strip():
            return None

        keyword_groups = [
            ("lookup", ["VLOOKUP", "XLOOKUP", "INDEX", "MATCH"]),
            ("aggregation", ["SUM", "SUMIF", "SUMIFS", "AVERAGE", "COUNT", "COUNTIF"]),
            ("conditional_logic", ["IF", "AND", "OR", "NOT", "IFERROR", "IFS", "SWITCH"]),
            ("date_calculation", ["DATE", "TODAY", "NOW", "YEAR", "MONTH", "DAY", "DATEDIF", "EOMONTH"]),
            ("financial_formula", ["NPV", "IRR", "PMT", "FV", "PV", "RATE"]),
            ("percentage", ["%"]),
            ("rounding", ["ROUND", "ROUNDUP", "ROUNDDOWN"]),
            ("text", ["CONCAT", "CONCATENATE", "LEFT", "RIGHT", "MID", "TEXT"]),
        ]

        scores: Dict[str, int] = {name: 0 for name, _ in keyword_groups}
        for name, tokens in keyword_groups:
            for token in tokens:
                if token == "%":
                    scores[name] += formulas.count("%")
                else:
                    scores[name] += formulas.count(token)

        top = max(scores.items(), key=lambda item: item[1])
        return top[0] if top[1] > 0 else None

    def _expand_reference(self, ref: str) -> Iterable[str]:
        if "!" not in ref:
            return []
        sheet_name, address = ref.split("!", 1)
        if ":" not in address:
            return [f"{sheet_name}!{address}"]

        try:
            min_col, min_row, max_col, max_row = range_boundaries(address)
        except ValueError:
            return []

        if None in (min_col, min_row, max_col, max_row):
            return [f"{sheet_name}!{address}"]

        total = (max_row - min_row + 1) * (max_col - min_col + 1)
        if total > self.MAX_RANGE_EXPANSION:
            return [f"{sheet_name}!{address}"]

        expanded = []
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                expanded.append(f"{sheet_name}!{self._col_letter(col)}{row}")
        return expanded

    def _col_letter(self, col_idx: int) -> str:
        result = ""
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            result = chr(65 + remainder) + result
        return result

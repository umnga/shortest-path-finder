"""Algorithm-heavy shortest path helpers for Kathmandu routing."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt
from time import perf_counter
from typing import Any, Iterable

import osmnx as ox


@dataclass
class SearchMetrics:
    """Holds algorithm execution metrics for analysis and comparison."""

    algorithm: str
    runtime_ms: float
    nodes_expanded: int
    edge_relaxations: int
    max_frontier_size: int
    path_distance_m: float
    path_nodes: int


def load_kathmandu_graph():
    """Load the drivable road network for Kathmandu."""
    return ox.graph_from_place("Kathmandu, Nepal", network_type="drive", simplify=True)


def nearest_graph_nodes(graph, start_coords: tuple[float, float], end_coords: tuple[float, float]) -> tuple[int, int]:
    """Snap start/end coordinates to nearest drivable graph nodes."""
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords

    start_node = ox.distance.nearest_nodes(graph, X=start_lon, Y=start_lat)
    end_node = ox.distance.nearest_nodes(graph, X=end_lon, Y=end_lat)
    return start_node, end_node


def solve_shortest_path(graph, start_coords: tuple[float, float], end_coords: tuple[float, float], algorithm: str) -> dict[str, Any] | None:
    """Solve shortest path between coordinates using the selected algorithm."""
    start_node, end_node = nearest_graph_nodes(graph, start_coords, end_coords)

    if algorithm == "Dijkstra":
        route, metrics = dijkstra_shortest_path(graph, start_node, end_node)
    elif algorithm == "A*":
        route, metrics = astar_shortest_path(graph, start_node, end_node)
    elif algorithm == "Bidirectional Dijkstra":
        route, metrics = bidirectional_dijkstra_shortest_path(graph, start_node, end_node)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    if not route:
        return None

    return {
        "route": route,
        "start_node": start_node,
        "end_node": end_node,
        "distance_m": metrics.path_distance_m,
        "metrics": metrics,
    }


def _min_edge_length(graph, u: int, v: int) -> float:
    edge_data = graph.get_edge_data(u, v)
    if not edge_data:
        return float("inf")
    return min(attributes.get("length", float("inf")) for attributes in edge_data.values())


def route_distance_meters(graph, route: Iterable[int]) -> float:
    """Sum the shortest edge lengths along a route."""
    nodes = list(route)
    total = 0.0
    for current_node, next_node in zip(nodes, nodes[1:]):
        edge_length = _min_edge_length(graph, current_node, next_node)
        if edge_length != float("inf"):
            total += edge_length
    return total


def route_to_coordinates(graph, route: Iterable[int]) -> list[tuple[float, float]]:
    """Convert route node ids to latitude/longitude coordinates."""
    coordinates = []
    for node_id in route:
        node_data = graph.nodes[node_id]
        coordinates.append((node_data["y"], node_data["x"]))
    return coordinates


def _reconstruct_path(parents: dict[int, int | None], start_node: int, target_node: int) -> list[int]:
    route = []
    current = target_node
    while current is not None:
        route.append(current)
        if current == start_node:
            break
        current = parents.get(current)
    if not route or route[-1] != start_node:
        return []
    route.reverse()
    return route


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6371000.0
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    hav = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * radius_m * asin(sqrt(hav))


def dijkstra_shortest_path(graph, start_node: int, target_node: int) -> tuple[list[int], SearchMetrics]:
    """Run Dijkstra's algorithm with detailed metrics."""
    started_at = perf_counter()

    distances: dict[int, float] = {start_node: 0.0}
    parents: dict[int, int | None] = {start_node: None}
    frontier: list[tuple[float, int]] = [(0.0, start_node)]

    nodes_expanded = 0
    edge_relaxations = 0
    max_frontier_size = 1

    while frontier:
        current_distance, current_node = heappop(frontier)
        if current_distance > distances.get(current_node, float("inf")):
            continue

        nodes_expanded += 1
        if current_node == target_node:
            break

        for neighbor in graph.successors(current_node):
            edge_relaxations += 1
            edge_length = _min_edge_length(graph, current_node, neighbor)
            new_distance = current_distance + edge_length
            if new_distance < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_distance
                parents[neighbor] = current_node
                heappush(frontier, (new_distance, neighbor))

        max_frontier_size = max(max_frontier_size, len(frontier))

    route = _reconstruct_path(parents, start_node, target_node)
    distance_m = route_distance_meters(graph, route) if route else 0.0

    metrics = SearchMetrics(
        algorithm="Dijkstra",
        runtime_ms=(perf_counter() - started_at) * 1000,
        nodes_expanded=nodes_expanded,
        edge_relaxations=edge_relaxations,
        max_frontier_size=max_frontier_size,
        path_distance_m=distance_m,
        path_nodes=len(route),
    )
    return route, metrics


def astar_shortest_path(graph, start_node: int, target_node: int) -> tuple[list[int], SearchMetrics]:
    """Run A* with haversine admissible heuristic and detailed metrics."""
    started_at = perf_counter()

    target_lat = graph.nodes[target_node]["y"]
    target_lon = graph.nodes[target_node]["x"]

    def heuristic(node_id: int) -> float:
        node_lat = graph.nodes[node_id]["y"]
        node_lon = graph.nodes[node_id]["x"]
        return _haversine_distance(node_lat, node_lon, target_lat, target_lon)

    g_score: dict[int, float] = {start_node: 0.0}
    parents: dict[int, int | None] = {start_node: None}
    frontier: list[tuple[float, int]] = [(heuristic(start_node), start_node)]

    nodes_expanded = 0
    edge_relaxations = 0
    max_frontier_size = 1

    while frontier:
        _, current_node = heappop(frontier)
        nodes_expanded += 1

        if current_node == target_node:
            break

        current_g = g_score.get(current_node, float("inf"))
        for neighbor in graph.successors(current_node):
            edge_relaxations += 1
            edge_length = _min_edge_length(graph, current_node, neighbor)
            tentative_g = current_g + edge_length

            if tentative_g < g_score.get(neighbor, float("inf")):
                parents[neighbor] = current_node
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor)
                heappush(frontier, (f_score, neighbor))

        max_frontier_size = max(max_frontier_size, len(frontier))

    route = _reconstruct_path(parents, start_node, target_node)
    distance_m = route_distance_meters(graph, route) if route else 0.0

    metrics = SearchMetrics(
        algorithm="A*",
        runtime_ms=(perf_counter() - started_at) * 1000,
        nodes_expanded=nodes_expanded,
        edge_relaxations=edge_relaxations,
        max_frontier_size=max_frontier_size,
        path_distance_m=distance_m,
        path_nodes=len(route),
    )
    return route, metrics


def bidirectional_dijkstra_shortest_path(graph, start_node: int, target_node: int) -> tuple[list[int], SearchMetrics]:
    """Run bidirectional Dijkstra for faster search on sparse road networks."""
    started_at = perf_counter()

    if start_node == target_node:
        metrics = SearchMetrics(
            algorithm="Bidirectional Dijkstra",
            runtime_ms=0.0,
            nodes_expanded=1,
            edge_relaxations=0,
            max_frontier_size=1,
            path_distance_m=0.0,
            path_nodes=1,
        )
        return [start_node], metrics

    forward_dist = {start_node: 0.0}
    backward_dist = {target_node: 0.0}
    forward_parent: dict[int, int | None] = {start_node: None}
    backward_parent: dict[int, int | None] = {target_node: None}

    forward_frontier: list[tuple[float, int]] = [(0.0, start_node)]
    backward_frontier: list[tuple[float, int]] = [(0.0, target_node)]

    explored_forward: set[int] = set()
    explored_backward: set[int] = set()

    best_total = float("inf")
    meeting_node: int | None = None

    nodes_expanded = 0
    edge_relaxations = 0
    max_frontier_size = 2

    while forward_frontier and backward_frontier:
        if forward_frontier[0][0] + backward_frontier[0][0] >= best_total:
            break

        if forward_frontier[0][0] <= backward_frontier[0][0]:
            current_distance, current_node = heappop(forward_frontier)
            if current_node in explored_forward:
                continue
            explored_forward.add(current_node)
            nodes_expanded += 1

            for neighbor in graph.successors(current_node):
                edge_relaxations += 1
                edge_length = _min_edge_length(graph, current_node, neighbor)
                tentative = current_distance + edge_length
                if tentative < forward_dist.get(neighbor, float("inf")):
                    forward_dist[neighbor] = tentative
                    forward_parent[neighbor] = current_node
                    heappush(forward_frontier, (tentative, neighbor))

                if neighbor in backward_dist:
                    joined_cost = tentative + backward_dist[neighbor]
                    if joined_cost < best_total:
                        best_total = joined_cost
                        meeting_node = neighbor
        else:
            current_distance, current_node = heappop(backward_frontier)
            if current_node in explored_backward:
                continue
            explored_backward.add(current_node)
            nodes_expanded += 1

            for predecessor in graph.predecessors(current_node):
                edge_relaxations += 1
                edge_length = _min_edge_length(graph, predecessor, current_node)
                tentative = current_distance + edge_length
                if tentative < backward_dist.get(predecessor, float("inf")):
                    backward_dist[predecessor] = tentative
                    backward_parent[predecessor] = current_node
                    heappush(backward_frontier, (tentative, predecessor))

                if predecessor in forward_dist:
                    joined_cost = tentative + forward_dist[predecessor]
                    if joined_cost < best_total:
                        best_total = joined_cost
                        meeting_node = predecessor

        max_frontier_size = max(max_frontier_size, len(forward_frontier) + len(backward_frontier))

    route: list[int] = []
    if meeting_node is not None:
        left = _reconstruct_path(forward_parent, start_node, meeting_node)

        right = [meeting_node]
        current = backward_parent.get(meeting_node)
        while current is not None:
            right.append(current)
            current = backward_parent.get(current)

        route = left + right[1:]

    distance_m = route_distance_meters(graph, route) if route else 0.0
    metrics = SearchMetrics(
        algorithm="Bidirectional Dijkstra",
        runtime_ms=(perf_counter() - started_at) * 1000,
        nodes_expanded=nodes_expanded,
        edge_relaxations=edge_relaxations,
        max_frontier_size=max_frontier_size,
        path_distance_m=distance_m,
        path_nodes=len(route),
    )
    return route, metrics
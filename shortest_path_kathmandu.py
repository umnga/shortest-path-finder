from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt
from time import perf_counter
from typing import Any, Iterator, Optional

import networkx as nx
import osmnx as ox


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


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


@dataclass
class EdgeCriticality:
    """Criticality score for a single graph edge."""

    u: int
    v: int
    criticality_index: float  # C_e
    baseline_distance: float
    mutated_distance: float
    is_bottleneck: bool  # True when C_e > threshold (e.g. 0.5)


@dataclass
class FrontierSnapshot:
    """Intermediate state of the algorithm frontier for visualisation."""

    expanded_node: int | None
    frontier_size: int
    frontier_nodes: list[int]
    visited_nodes: set[int]
    current_distances: dict[int, float]


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------


def load_kathmandu_graph():
    """Load the drivable road network for Kathmandu."""
    return ox.graph_from_place("Kathmandu, Nepal", network_type="drive", simplify=True)


def nearest_graph_nodes(
    graph, start_coords: tuple[float, float], end_coords: tuple[float, float]
) -> tuple[int, int]:
    """Snap start/end coordinates to nearest drivable graph nodes."""
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    start_node = ox.distance.nearest_nodes(graph, X=start_lon, Y=start_lat)
    end_node = ox.distance.nearest_nodes(graph, X=end_lon, Y=end_lat)
    return start_node, end_node


# ---------------------------------------------------------------------------
# Shortest-path solvers
# ---------------------------------------------------------------------------


def solve_shortest_path(
    graph,
    start_coords: tuple[float, float],
    end_coords: tuple[float, float],
    algorithm: str,
) -> dict[str, Any] | None:
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


def solve_shortest_path_between_nodes(
    graph,
    start_node: int,
    end_node: int,
    algorithm: str = "Dijkstra",
) -> tuple[list[int], SearchMetrics]:
    """Solve shortest path between raw node IDs."""
    if algorithm == "Dijkstra":
        return dijkstra_shortest_path(graph, start_node, end_node)
    elif algorithm == "A*":
        return astar_shortest_path(graph, start_node, end_node)
    elif algorithm == "Bidirectional Dijkstra":
        return bidirectional_dijkstra_shortest_path(graph, start_node, end_node)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _min_edge_length(graph, u: int, v: int) -> float:
    edge_data = graph.get_edge_data(u, v)
    if not edge_data:
        return float("inf")
    return min(attributes.get("length", float("inf")) for attributes in edge_data.values())


def remove_all_parallel_edges(graph, u: int, v: int) -> int:
    """Remove every parallel edge between *u* and *v* on a MultiDiGraph.

    ``graph.remove_edge(u, v)`` only removes a single parallel edge, leaving
    the nodes connected (and ``has_edge`` still True) whenever more than one
    edge exists between them. Road graphs from OSMnx are MultiDiGraphs and
    frequently have parallel edges, so severing a road requires removing all
    of them. Returns the number of edges removed.
    """
    if not graph.has_edge(u, v):
        return 0
    keys = list(graph[u][v].keys())
    for key in keys:
        graph.remove_edge(u, v, key=key)
    return len(keys)


def route_distance_meters(graph, route: list[int]) -> float:
    """Sum the shortest edge lengths along a route."""
    total = 0.0
    for current_node, next_node in zip(route, route[1:]):
        edge_length = _min_edge_length(graph, current_node, next_node)
        if edge_length != float("inf"):
            total += edge_length
    return total


def route_to_coordinates(graph, route: list[int]) -> list[tuple[float, float]]:
    """Convert route node ids into a detailed lat/lon path for drawing.

    OSMnx graphs (especially after ``simplify=True``) collapse chains of
    intersections into single edges, storing the real curved road path in
    the edge's ``geometry`` attribute. Naively connecting consecutive graph
    nodes with a straight line skips that geometry and can visually cut
    across blocks, hills, or other terrain no road actually crosses —
    especially for long edges. This uses the stored geometry when present
    and only falls back to a straight line when it isn't (e.g. on the
    synthetic benchmark grids, which have no geometry at all).
    """
    if not route:
        return []

    coords: list[tuple[float, float]] = [
        (graph.nodes[route[0]]["y"], graph.nodes[route[0]]["x"])
    ]

    for current_node, next_node in zip(route, route[1:]):
        edge_data = graph.get_edge_data(current_node, next_node)
        segment_coords: list[tuple[float, float]] | None = None

        if edge_data:
            # Multiple parallel edges may exist between the same pair of
            # nodes; use the shortest one to stay consistent with the
            # weighting logic used for routing (`_min_edge_length`).
            best_attrs = min(
                edge_data.values(), key=lambda attrs: attrs.get("length", float("inf"))
            )
            geometry = best_attrs.get("geometry")
            if geometry is not None:
                # Shapely LineString coords are (x, y) i.e. (lon, lat).
                raw = list(geometry.coords)
                u_lat = graph.nodes[current_node]["y"]
                u_lon = graph.nodes[current_node]["x"]
                v_lat = graph.nodes[next_node]["y"]
                v_lon = graph.nodes[next_node]["x"]
                start_lon, start_lat = raw[0]
                dist_to_u = abs(start_lat - u_lat) + abs(start_lon - u_lon)
                dist_to_v = abs(start_lat - v_lat) + abs(start_lon - v_lon)
                if dist_to_v < dist_to_u:
                    # Geometry is stored reversed relative to travel direction.
                    raw = list(reversed(raw))
                segment_coords = [(lat, lon) for lon, lat in raw]

        if not segment_coords:
            segment_coords = [
                (graph.nodes[current_node]["y"], graph.nodes[current_node]["x"]),
                (graph.nodes[next_node]["y"], graph.nodes[next_node]["x"]),
            ]

        # Avoid duplicating the point shared with the previous segment.
        if segment_coords[0] == coords[-1]:
            coords.extend(segment_coords[1:])
        else:
            coords.extend(segment_coords)

    return coords


def _reconstruct_path(
    parents: dict[int, int | None], start_node: int, target_node: int
) -> list[int]:
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


def _estimate_coord_scale(graph) -> float:
    """Estimate metres per coordinate-unit using the first edge with a length.

    Real OSMnx graphs store coordinates as decimal degrees (scale ~ 100,000),
    while synthetic grids use arbitrary units with small lengths (scale ~ 1).
    The heuristic is scaled by this factor so it stays admissible on both.
    """
    for u, v, length in graph.edges(data="length"):
        if length is None:
            continue
        try:
            u_data = graph.nodes[u]
            v_data = graph.nodes[v]
            d_lat = u_data["y"] - v_data["y"]
            d_lon = u_data["x"] - v_data["x"]
            euclid = sqrt(d_lat * d_lat + d_lon * d_lon)
            if euclid > 1e-12 and length > 0:
                return length / euclid
        except Exception:
            continue
    return 1.0


# ---------------------------------------------------------------------------
# Algorithm implementations
# ---------------------------------------------------------------------------


def dijkstra_shortest_path(
    graph,
    start_node: int,
    target_node: int,
    yield_snapshots: bool = False,
) -> tuple[list[int], SearchMetrics] | Iterator:
    """Run Dijkstra's algorithm with detailed metrics.

    When *yield_snapshots* is True this function returns a generator that
    yields ``FrontierSnapshot`` objects for live visualisation; otherwise it
    returns a ``(route, metrics)`` tuple.
    """
    def run():
        started_at = perf_counter()

        distances: dict[int, float] = {start_node: 0.0}
        parents: dict[int, int | None] = {start_node: None}
        frontier: list[tuple[float, int]] = [(0.0, start_node)]

        nodes_expanded = 0
        edge_relaxations = 0
        max_frontier_size = 1
        visited: set[int] = set()

        while frontier:
            current_distance, current_node = heappop(frontier)
            if current_distance > distances.get(current_node, float("inf")):
                continue

            nodes_expanded += 1
            visited.add(current_node)

            if yield_snapshots:
                yield FrontierSnapshot(
                    expanded_node=current_node,
                    frontier_size=len(frontier),
                    frontier_nodes=[n for _, n in frontier],
                    visited_nodes=set(visited),
                    current_distances=dict(distances),
                )

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

    run_gen = run()
    if yield_snapshots:
        return run_gen
    try:
        while True:
            next(run_gen)
    except StopIteration as stop:
        return stop.value


def astar_shortest_path(
    graph,
    start_node: int,
    target_node: int,
    yield_snapshots: bool = False,
) -> tuple[list[int], SearchMetrics] | Iterator:
    """Run A* with haversine admissible heuristic and detailed metrics.

    When *yield_snapshots* is True this function returns a generator that
    yields ``FrontierSnapshot`` objects for live visualisation; otherwise it
    returns a ``(route, metrics)`` tuple.
    """
    def run():
        started_at = perf_counter()

        target_lat = graph.nodes[target_node]["y"]
        target_lon = graph.nodes[target_node]["x"]
        coord_scale = _estimate_coord_scale(graph)

        def heuristic(node_id: int) -> float:
            node_lat = graph.nodes[node_id]["y"]
            node_lon = graph.nodes[node_id]["x"]
            geo_estimate = _haversine_distance(node_lat, node_lon, target_lat, target_lon)
            grid_estimate = (
                sqrt((node_lat - target_lat) ** 2 + (node_lon - target_lon) ** 2)
                * coord_scale
            )
            # min of two lower bounds keeps the heuristic admissible on both
            # real geo graphs and synthetic grids
            return min(geo_estimate, grid_estimate)

        g_score: dict[int, float] = {start_node: 0.0}
        parents: dict[int, int | None] = {start_node: None}
        frontier: list[tuple[float, int]] = [(heuristic(start_node), start_node)]

        nodes_expanded = 0
        edge_relaxations = 0
        max_frontier_size = 1
        visited: set[int] = set()
        closed: set[int] = set()

        while frontier:
            _, current_node = heappop(frontier)
            if current_node in closed:
                # Stale heap entry: a better g-score for this node was
                # already finalized, so skip re-expanding it.
                continue
            closed.add(current_node)

            nodes_expanded += 1
            visited.add(current_node)

            if yield_snapshots:
                yield FrontierSnapshot(
                    expanded_node=current_node,
                    frontier_size=len(frontier),
                    frontier_nodes=[n for _, n in frontier],
                    visited_nodes=set(visited),
                    current_distances=dict(g_score),
                )

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

    run_gen = run()
    if yield_snapshots:
        return run_gen
    try:
        while True:
            next(run_gen)
    except StopIteration as stop:
        return stop.value


def bidirectional_dijkstra_shortest_path(
    graph,
    start_node: int,
    target_node: int,
) -> tuple[list[int], SearchMetrics]:
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


# ===================================================================
# EDGE CRITICALITY / VULNERABILITY ENGINE
# ===================================================================


def compute_global_baseline(
    graph,
    sample_ratio: float = 0.15,
    algorithm: str = "Dijkstra",
    max_pairs: int = 500,
) -> float:
    """Compute the baseline global metric M_base = average shortest-path
    distance over a sampled set of origin-destination pairs.

    Uses *sample_ratio* of nodes (capped at *max_pairs* pairs) to keep
    computation tractable on large networks.
    """
    all_nodes = list(graph.nodes)
    n_samples = max(2, int(len(all_nodes) * sample_ratio))

    import random

    random.seed(42)
    sampled = random.sample(all_nodes, min(n_samples, len(all_nodes)))

    total_distance = 0.0
    pair_count = 0

    for i, src in enumerate(sampled):
        for dst in sampled[i + 1 :]:
            if pair_count >= max_pairs:
                break
            route, metrics = solve_shortest_path_between_nodes(
                graph, src, dst, algorithm
            )
            if route:
                total_distance += metrics.path_distance_m
                pair_count += 1
        if pair_count >= max_pairs:
            break

    if pair_count == 0:
        return 0.0
    return total_distance / pair_count


def compute_edge_criticality(
    graph,
    edge: tuple[int, int],
    baseline_distance: float,
    algorithm: str = "Dijkstra",
    sample_ratio: float = 0.10,
    max_pairs: int = 200,
    bottleneck_threshold: float = 0.5,
) -> EdgeCriticality:
    """Compute the Criticality Index C_e for a single edge.

    C_e = (M_mutated - M_base) / M_base

    The edge is removed from a *copy* of the graph, then the mutated
    baseline is recomputed.
    """
    u, v = edge

    # Build a subgraph copy with the edge removed
    # osmnx graphs are MultiDiGraphs, so a node pair can have more than one
    # parallel edge between them; all of them must go for the edge to be
    # truly severed.
    gc = graph.copy()
    remove_all_parallel_edges(gc, u, v)

    mutated_distance = compute_global_baseline(
        gc, sample_ratio=sample_ratio, algorithm=algorithm, max_pairs=max_pairs
    )

    if baseline_distance == 0:
        ci = 0.0
    else:
        ci = (mutated_distance - baseline_distance) / baseline_distance

    return EdgeCriticality(
        u=u,
        v=v,
        criticality_index=ci,
        baseline_distance=baseline_distance,
        mutated_distance=mutated_distance,
        is_bottleneck=ci > bottleneck_threshold,
    )


def criticality_sweep(
    graph,
    algorithm: str = "Dijkstra",
    sample_ratio: float = 0.10,
    max_pairs: int = 200,
    bottleneck_threshold: float = 0.5,
    max_edges: int | None = None,
    progress_callback=None,
) -> list[EdgeCriticality]:
    """Run the full criticality sweep over all edges in the graph.

    Returns a list of ``EdgeCriticality`` results sorted by descending
    criticality index.

    The *progress_callback* can be ``callable(current, total)`` for UI
    updates.
    """
    # 1. Compute baseline
    baseline = compute_global_baseline(
        graph, sample_ratio=sample_ratio, algorithm=algorithm, max_pairs=max_pairs
    )

    # 2. Collect unique undirected edges
    seen: set[tuple[int, int]] = set()
    edges: list[tuple[int, int]] = []
    for u in graph.nodes:
        for v in graph.successors(u):
            key = (u, v) if u < v else (v, u)
            if key not in seen:
                seen.add(key)
                edges.append((u, v))

    if max_edges is not None:
        edges = edges[:max_edges]

    # 3. Sweep
    results: list[EdgeCriticality] = []
    for idx, (u, v) in enumerate(edges):
        if progress_callback:
            progress_callback(idx + 1, len(edges))

        try:
            ec = compute_edge_criticality(
                graph,
                (u, v),
                baseline,
                algorithm=algorithm,
                sample_ratio=sample_ratio,
                max_pairs=max_pairs,
                bottleneck_threshold=bottleneck_threshold,
            )
            results.append(ec)
        except Exception:
            continue

    results.sort(key=lambda r: r.criticality_index, reverse=True)
    return results


# ===================================================================
# SYNTHETIC GRID GENERATOR
# ===================================================================


def generate_synthetic_grid(rows: int, cols: int, edge_length: float = 1.0) -> nx.MultiDiGraph:
    """Generate a synthetic grid graph of *rows* x *cols* nodes.

    Returns a directed MultiDiGraph (mirroring the OSMnx road network) so the
    same shortest-path implementations can run on it unchanged. Each node is
    connected to its immediate right, bottom and diagonal neighbours with
    weight *edge_length* (edges are added in both directions). This is used
    for empirical scaling benchmarks.
    """
    G = nx.MultiDiGraph()
    node_id = 0
    for r in range(rows):
        for c in range(cols):
            G.add_node(node_id, y=float(r), x=float(c))
            node_id += 1

    def _add_bidirectional(u: int, v: int, length: float) -> None:
        G.add_edge(u, v, length=length)
        G.add_edge(v, u, length=length)

    # Horizontal edges
    for r in range(rows):
        for c in range(cols - 1):
            u = r * cols + c
            v = r * cols + c + 1
            _add_bidirectional(u, v, edge_length)

    # Vertical edges
    for r in range(rows - 1):
        for c in range(cols):
            u = r * cols + c
            v = (r + 1) * cols + c
            _add_bidirectional(u, v, edge_length)

    # Some diagonal shortcuts
    import random

    random.seed(42)
    for r in range(rows - 1):
        for c in range(cols - 1):
            if random.random() < 0.3:
                u = r * cols + c
                v = (r + 1) * cols + (c + 1)
                _add_bidirectional(u, v, edge_length * 1.4)

    return G


@dataclass
class BenchmarkResult:
    """Results of a single scaling benchmark run."""

    grid_label: str
    num_nodes: int
    num_edges: int
    dijkstra_runtime_ms: float
    full_sweep_runtime_s: float
    bottlenecks_found: int


def run_benchmark_sweep(
    grid_sizes: list[tuple[int, int]] | None = None,
    algorithm: str = "Dijkstra",
    sweep_max_edges: int = 50,
    progress_callback=None,
) -> list[BenchmarkResult]:
    """Run the empirical profiling sweep across synthetic grids.

    Returns a list of ``BenchmarkResult`` matching the table in the
    proposal slides.
    """
    if grid_sizes is None:
        grid_sizes = [(5, 5), (10, 10), (20, 25)]

    results: list[BenchmarkResult] = []
    total = len(grid_sizes)

    for idx, (rows, cols) in enumerate(grid_sizes):
        label = f"{rows * cols} Nodes"
        if progress_callback:
            progress_callback(idx + 1, total, label)

        G = generate_synthetic_grid(rows, cols, edge_length=1.0)
        nodes = list(G.nodes)
        num_nodes = len(nodes)
        num_edges = G.number_of_edges()

        # Single Dijkstra runtime (average over 10 random pairs)
        dijkstra_times: list[float] = []
        import random

        random.seed(0)
        for _ in range(10):
            src, dst = random.sample(nodes, 2)
            t0 = perf_counter()
            try:
                route, metrics = solve_shortest_path_between_nodes(
                    G, src, dst, algorithm
                )
            except Exception:
                continue
            dijkstra_times.append((perf_counter() - t0) * 1000)

        avg_dijkstra = sum(dijkstra_times) / max(len(dijkstra_times), 1)

        # Full criticality sweep (limited edges)
        t0 = perf_counter()
        criticalities = criticality_sweep(
            G,
            algorithm=algorithm,
            sample_ratio=0.5,
            max_pairs=50,
            max_edges=sweep_max_edges,
        )
        sweep_time = perf_counter() - t0

        bottlenecks = sum(1 for ec in criticalities if ec.is_bottleneck)

        results.append(
            BenchmarkResult(
                grid_label=label,
                num_nodes=num_nodes,
                num_edges=num_edges,
                dijkstra_runtime_ms=round(avg_dijkstra, 2),
                full_sweep_runtime_s=round(sweep_time, 2),
                bottlenecks_found=bottlenecks,
            )
        )

    return results
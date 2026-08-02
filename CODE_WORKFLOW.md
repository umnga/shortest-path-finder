# Code Workflow — Route Finder (UrbanResilience Analyzer)

A detailed, point-by-point walkthrough of how the Route Finder feature works in this project.

---

## 1. Project Overview

This is a **Streamlit web application** that lets users pick two points on a map of Kathmandu and compare three shortest-path algorithms side by side:

1. **Dijkstra**
2. **A\***
3. **Bidirectional Dijkstra**

The project is split into two Python files:

| File | Role |
|------|------|
| `shortest_path_kathmandu.py` | Algorithmic engine (graph loading, shortest-path solvers) |
| `app.py` | Streamlit dashboard (UI, map rendering, user interaction) |

---

## 2. Dependencies & Setup

`requirements.txt` lists the packages:

- **streamlit** — web UI framework
- **osmnx** — downloads real road network data from OpenStreetMap
- **folium** — interactive map rendering
- **streamlit-folium** — bridges Folium maps into Streamlit
- **networkx** — graph data structure (MultiDiGraph)
- **pandas** — data tables

**Run command:** `streamlit run app.py`

---

## 3. Startup Flow (app.py)

### 3.1 Imports
- Imports the algorithmic functions from `shortest_path_kathmandu.py`:
  - `dijkstra_shortest_path`
  - `astar_shortest_path`
  - `solve_shortest_path`
  - `load_kathmandu_graph`
  - `nearest_graph_nodes`
  - `route_to_coordinates`
- Imports UI libraries: `streamlit`, `folium`, `streamlit_folium`, `pandas`, `networkx`.

### 3.2 Constants
- `ALGORITHMS = ["Dijkstra", "A*", "Bidirectional Dijkstra"]` — the three selectable algorithms.
- `ROUTE_COLORS` — each algorithm gets a distinct color on the map:
  - Dijkstra → `#c4432f` (red)
  - A* → `#3f7d5c` (green)
  - Bidirectional Dijkstra → `#3a5a8c` (blue)

### 3.3 Page Configuration & CSS
- `st.set_page_config(...)` sets the page title, icon, and wide layout.
- A large CSS string (`PAGE_CSS`) is injected via `st.markdown(..., unsafe_allow_html=True)` to style the app with a custom "paper/moss" theme.

### 3.4 Session State Initialization
- Streamlit reruns the whole script on every interaction, so state is stored in `st.session_state`.
- Initialized keys relevant to Route Finder:
  - `start_coords` — clicked start point (lat, lng)
  - `end_coords` — clicked destination point (lat, lng)
  - `selection_mode` — whether the next click sets Start or Destination
  - `click_count`, `consumed_clicks` — deduplication of map clicks

### 3.5 Graph Loading (Cached)
```python
@st.cache_resource
def get_graph():
    return load_kathmandu_graph()
```
- `load_kathmandu_graph()` (in the engine file) calls:
  ```python
  ox.graph_from_place("Kathmandu, Nepal", network_type="drive", simplify=True)
  ```
- This downloads the **drivable road network** of Kathmandu from OpenStreetMap as a `networkx.MultiDiGraph`.
- `@st.cache_resource` ensures the graph is loaded **only once** across all reruns (it's expensive).

### 3.6 Hero & Tabs
- A hero banner is rendered with HTML.
- The **Route Finder** tab is the first of three tabs.

---

## 4. Route Finder — Sidebar Controls

The sidebar contains:

- **Radio** — "Next click sets" → Start or Destination (horizontal).
- **Multiselect** — "Algorithms to run" → which of the three algorithms to execute (default: all three).
- **Checkbox** — "Show frontier expansion" → visualizes visited nodes as dots on the map.
- **Swap button** — swaps the start and end coordinates.
- **Clear button** — resets both points.
- **Panels**:
  - "Selected coordinates" — shows the current start/end lat-lng.
  - "Network profile" — shows total node and edge counts of the Kathmandu graph.

---

## 5. Route Finder — Route Computation

### 5.1 Trigger
- When both `start_coords` and `end_coords` are set **and** at least one algorithm is selected, the app loops over each selected algorithm and calls:
  ```python
  solve_shortest_path(graph, start_coords, end_coords, algorithm)
  ```

### 5.2 `solve_shortest_path()` (engine)
This function does:

1. **Snap coordinates to nearest graph nodes** via `nearest_graph_nodes()`:
   ```python
   start_node = ox.distance.nearest_nodes(graph, X=start_lon, Y=start_lat)
   end_node = ox.distance.nearest_nodes(graph, X=end_lon, Y=end_lat)
   ```
   This converts the clicked (lat, lng) into actual graph node IDs.

2. **Dispatch to the correct algorithm**:
   - `"Dijkstra"` → `dijkstra_shortest_path(graph, start_node, end_node)`
   - `"A*"` → `astar_shortest_path(graph, start_node, end_node)`
   - `"Bidirectional Dijkstra"` → `bidirectional_dijkstra_shortest_path(graph, start_node, end_node)`

3. **Return a result dict**:
   ```python
   {
       "route": route,            # list of node IDs
       "start_node": start_node,
       "end_node": end_node,
       "distance_m": metrics.path_distance_m,
       "metrics": metrics,        # SearchMetrics object
   }
   ```

- Results are stored in a `results` dict keyed by algorithm name.
- If an algorithm fails, the error is stored in an `errors` dict.

---

## 6. Route Finder — Map Rendering

A `folium.Map` centered on Kathmandu (27.7172, 85.3240) is created with the "CartoDB positron" tile style.

### 6.1 Markers
- **Start marker** — green circle (`#2d4530`).
- **End marker** — red circle (`#7f1d1d`).

### 6.2 Route Polylines
- For each algorithm with a result:
  1. `route_to_coordinates(graph, route)` converts the node-ID route into a detailed lat/lon path.
  2. A `folium.PolyLine` is drawn in the algorithm's color with weight 5 and opacity 0.82.

### 6.3 Dashed Connector Lines
- A dashed line connects the clicked start point to the actual snapped route start.
- A dashed line connects the route end to the clicked destination point.
- This shows the user where their click was vs. where the road network actually starts.

### 6.4 Frontier Visualization (optional)
- If "Show frontier expansion" is checked:
  1. The algorithm is re-run in **snapshot mode** (`yield_snapshots=True`).
  2. The generator yields `FrontierSnapshot` objects after each node expansion.
  3. The app collects the final `visited_nodes` set.
  4. Each visited node is drawn as a small translucent dot (radius 1.5, opacity 0.3) in the algorithm's color.
- This visually shows **how much of the graph each algorithm searched**.

---

## 7. Route Finder — Results Table

`build_results_table_html()` generates an HTML table comparing all algorithms:

| Column | Description |
|--------|-------------|
| Algorithm | Name with color dot |
| Dist (km) | Path distance in kilometers |
| Time (ms) | Runtime in milliseconds |
| Expanded | Nodes expanded (with a visual bar proportional to max) |
| Relax. | Edge relaxations count |
| Max frontier | Largest frontier size (in expanded dialog) |
| Path pts | Number of points in the path |

- **Badges** highlight:
  - Fastest algorithm
  - Smallest search space (fewest nodes expanded)
  - Shortest distance (in expanded dialog)
- An **"Expand" button** opens a full comparison dialog with all columns.

---

## 8. Route Finder — Click Handling

- `st_folium` returns `last_clicked` (lat/lng) when the user clicks the map.
- The app **deduplicates clicks** using `consumed_clicks` — this prevents the same click from being processed twice on rerun.
- Depending on `selection_mode`:
  - If "Start" → sets `st.session_state.start_coords`.
  - If "Destination" → sets `st.session_state.end_coords`.
- Then calls `st.rerun()` to recompute routes with the new point.

---

## 9. Algorithmic Engine (shortest_path_kathmandu.py)

### 9.1 Data Structures (Dataclasses)

| Dataclass | Purpose |
|-----------|---------|
| `SearchMetrics` | Stores runtime, nodes expanded, edge relaxations, max frontier size, path distance, path node count for one algorithm run. |
| `FrontierSnapshot` | Captures the intermediate search state (expanded node, frontier, visited, distances) for live visualization. |

### 9.2 Graph Loading & Helpers

- **`load_kathmandu_graph()`** — downloads the OSMnx road network.
- **`nearest_graph_nodes()`** — snaps (lat, lon) to nearest graph node IDs.
- **`_min_edge_length()`** — returns the shortest length among parallel edges between u and v.
- **`route_distance_meters()`** — sums edge lengths along a route.
- **`route_to_coordinates()`** — converts a node route into a detailed lat/lon path, using the stored `geometry` attribute of OSMnx edges (so routes follow real curved roads, not straight lines).
- **`_reconstruct_path()`** — walks the `parents` dict backward from target to start to rebuild the route.
- **`_haversine_distance()`** — great-circle distance between two lat/lon points (used as A* heuristic).
- **`_estimate_coord_scale()`** — estimates meters-per-coordinate-unit so the A* heuristic stays admissible.

### 9.3 Dijkstra (`dijkstra_shortest_path`)

- Uses a **binary min-heap** priority queue (`heapq`).
- Maintains `distances`, `parents`, and a `visited` set.
- **Greedy relaxation**: pops the node with the smallest tentative distance, relaxes all outgoing edges.
- Tracks `nodes_expanded`, `edge_relaxations`, `max_frontier_size`.
- **Snapshot mode**: if `yield_snapshots=True`, returns a generator yielding `FrontierSnapshot` after each expansion (for visualization).
- Complexity: **O((V + E) log V)**.

### 9.4 A* (`astar_shortest_path`)

- Same structure as Dijkstra but uses an **admissible heuristic** `f(n) = g(n) + h(n)`.
- `h(n)` = min of:
  - Haversine great-circle distance to target (for real geo graphs).
  - Euclidean distance × coordinate scale (for synthetic grids).
- Uses a `closed` set to skip stale heap entries (nodes already finalized).
- Tends to expand **fewer nodes** than Dijkstra because it's guided toward the target.

### 9.5 Bidirectional Dijkstra (`bidirectional_dijkstra_shortest_path`)

- Runs **two simultaneous searches**: forward from start, backward from target.
- Maintains two distance maps, two parent maps, two frontiers.
- **Termination condition**: stops when `forward_frontier[0][0] + backward_frontier[0][0] >= best_total` (the two searches have met and no better path is possible).
- When a node is reached by both searches, it records a candidate `meeting_node` and `best_total`.
- Reconstructs the route by joining the forward path (start → meeting) with the reversed backward path (meeting → target).
- Much faster on sparse road networks because it explores roughly half the graph.

---

## 10. End-to-End Data Flow Summary

```
User clicks map
      │
      ▼
st_folium returns last_clicked (lat, lng)
      │
      ▼
Session state updated (start_coords / end_coords)
      │
      ▼
solve_shortest_path() snaps coords to nodes
      │
      ▼
Algorithm dispatched (Dijkstra / A* / Bidirectional)
      │
      ▼
Returns (route, SearchMetrics)
      │
      ▼
route_to_coordinates() → detailed lat/lon path
      │
      ▼
Folium polylines drawn on map + results table rendered
```

---

## 11. Key Design Decisions

1. **MultiDiGraph handling** — OSMnx returns directed multigraphs with parallel edges. All edge operations (`_min_edge_length`) account for this.
2. **Admissible A* heuristic** — takes the min of haversine and scaled-Euclidean estimates so it works on real geo data without overestimating.
3. **Snapshot generators** — Dijkstra/A* can yield intermediate states for live visualization without duplicating code.
4. **Caching** — the expensive OSMnx graph load is cached with `@st.cache_resource`.
5. **Geometry-aware route drawing** — uses OSMnx edge `geometry` attributes so routes follow real curved roads instead of straight lines between intersections.
6. **Click deduplication** — `consumed_clicks` prevents the same map click from being processed twice on Streamlit reruns.

---

## 12. Complexity Analysis

| Operation | Complexity |
|-----------|------------|
| Dijkstra (single run) | O((V + E) log V) |
| A* (single run) | O((V + E) log V) worst case, often better with good heuristic |
| Bidirectional Dijkstra | O((V + E) log V), explores ~half the graph in practice |

---

## 13. How to Run

```bash
# 1. Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.
# UrbanResilience Analyzer

A Graph-Based Traffic & Criticality Analyzer for Kathmandu's road network.

Course Project — COMP 314: Algorithms and Complexity  
Kathmandu University, Department of Computer Science and Engineering  
May 2026

---

## Features

### Route Finder
- Interactive map of Kathmandu's drivable road network (OSMnx data)
- Click to set start/destination points
- Three shortest-path algorithms: **Dijkstra**, **A\***, **Bidirectional Dijkstra**
- Side-by-side comparison table with runtime, nodes expanded, edge relaxations, max frontier size
- **Frontier expansion visualization** — visited nodes rendered as translucent dots

### Edge Criticality & Vulnerability Engine
- **Criticality Index** Cₑ = (Mₘᵤₜₐₜₑd − Mₐₛₑ) / Mₐₛₑ per edge
- Full sweep over graph edges with sampled origin-destination pairs
- Bottleneck detection (Cₑ > 0.5)
- **Bottleneck map overlay** — red Polylines with intensity proportional to Cₑ
- **Interactive edge-elimination sandbox** — sever any edge by node ID, recompute the route, and see the impact

### Empirical Benchmarks
- **Synthetic grid generator** for controlled scaling experiments
- Runs full profiling suite across configurable grid sizes
- Reports Dijkstra runtime, full sweep runtime, and bottleneck count
- Live chart of scaling behaviour

---

## Architecture

```
app.py                          ← Streamlit dashboard (3 tabs)
shortest_path_kathmandu.py      ← Algorithmic engine + criticality + benchmarks
requirements.txt                ← Python dependencies
```

### `shortest_path_kathmandu.py`
| Module | Description |
|--------|-------------|
| `SearchMetrics` | Dataclass for algorithm execution metrics |
| `EdgeCriticality` | Criticality score for a single edge |
| `FrontierSnapshot` | Intermediate search state for live visualisation |
| `load_kathmandu_graph()` | Load Kathmandu road network via OSMnx |
| `dijkstra_shortest_path()` | Dijkstra with optional snapshot generator |
| `astar_shortest_path()` | A* with haversine admissible heuristic |
| `bidirectional_dijkstra_shortest_path()` | Bidirectional Dijkstra |
| `compute_global_baseline()` | M_base over sampled OD pairs |
| `compute_edge_criticality()` | Cₑ for a single edge |
| `criticality_sweep()` | Full edge criticality sweep |
| `generate_synthetic_grid()` | Synthetic grid graph generator |
| `run_benchmark_sweep()` | Empirical profiling suite |

---

## Setup

```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

---

## Syllabus Integration

- **Greedy Strategies (Chapter 2)** — Dijkstra's greedy relaxation
- **Advanced Graph Data Structures** — adjacency list storage, binary min-heap priority queue
- **Empirical Performance Profiling** — O((V+E) log V) per pass, O(E·(V+E) log V) full sweep
- **Heuristic Search** — A* with admissible haversine heuristic

---

## How to Use

1. **Route Finder tab**: Click on the map to set a start point (green), then a destination (red). Select algorithms in the sidebar and toggle frontier visualisation.
2. **Vulnerability tab**: Run a criticality sweep to find structural bottlenecks, or use the sandbox to sever a specific edge.
3. **Benchmarks tab**: Run the scaling benchmark suite on synthetic grids and observe the empirical complexity chart.
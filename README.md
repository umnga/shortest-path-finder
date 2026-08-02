# UrbanResilience Analyzer

A Graph-Based Shortest-Path Finder for Kathmandu's road network.

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

---

## Architecture

```
app.py                          ← Streamlit dashboard
shortest_path_kathmandu.py      ← Algorithmic engine (shortest-path solvers)
requirements.txt                ← Python dependencies
```

### `shortest_path_kathmandu.py`
| Module | Description |
|--------|-------------|
| `SearchMetrics` | Dataclass for algorithm execution metrics |
| `FrontierSnapshot` | Intermediate search state for live visualisation |
| `load_kathmandu_graph()` | Load Kathmandu road network via OSMnx |
| `dijkstra_shortest_path()` | Dijkstra with optional snapshot generator |
| `astar_shortest_path()` | A* with haversine admissible heuristic |
| `bidirectional_dijkstra_shortest_path()` | Bidirectional Dijkstra |

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
- **Heuristic Search** — A* with admissible haversine heuristic

---

## How to Use

1. **Route Finder**: Click on the map to set a start point (green), then a destination (red). Select algorithms in the sidebar and toggle frontier visualisation.
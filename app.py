import time

import folium
import networkx as nx
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from shortest_path_kathmandu import (
    BenchmarkResult,
    EdgeCriticality,
    FrontierSnapshot,
    astar_shortest_path,
    compute_edge_criticality,
    compute_global_baseline,
    criticality_sweep,
    dijkstra_shortest_path,
    generate_synthetic_grid,
    load_kathmandu_graph,
    nearest_graph_nodes,
    remove_all_parallel_edges,
    route_to_coordinates,
    run_benchmark_sweep,
    solve_shortest_path,
    solve_shortest_path_between_nodes,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALGORITHMS = ["Dijkstra", "A*", "Bidirectional Dijkstra"]
ROUTE_COLORS = {
    "Dijkstra": "#c4432f",
    "A*": "#3f7d5c",
    "Bidirectional Dijkstra": "#3a5a8c",
}
ALGO_ORDER = {"Dijkstra": 0, "A*": 1, "Bidirectional Dijkstra": 2}
BOTTLENECK_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="UrbanResilience Analyzer",
    page_icon="\U0001f3d9\ufe0f",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

PAGE_CSS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
    "<style>"
    ":root {"
    "  --paper: #f7f6ef; --paper-raised: #ffffff; --ink: #1a2318; --ink-soft: #5b6a58;"
    "  --moss-deep: #1a2318; --moss: #2d4530; --sage: #8a9a7e; --hairline: #d9d5c5; --clay: #c4432f;"
    "  --amber: #d4a017;"
    "}"
    "html, body, [class*='css'] { font-family: 'IBM Plex Sans', sans-serif; }"
    ".stApp { background: var(--paper); color: var(--ink); }"
    ".block-container { padding-top: 1.2rem; max-width: 1500px; }"
    "#root > div:nth-child(1) > div > div > div > div { gap: 0; }"
    # Sidebar
    "section[data-testid='stSidebar'] { background: var(--moss-deep); border-right: 1px solid rgba(255,255,255,0.06); }"
    "section[data-testid='stSidebar'] * { color: #e9ede4; }"
    "section[data-testid='stSidebar'] h1, section[data-testid='stSidebar'] h2, section[data-testid='stSidebar'] h3 { font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; color: #f7f6ef; font-size: 0.95rem; letter-spacing: 0.02em; margin-bottom: 0.2rem; }"
    "section[data-testid='stSidebar'] [data-testid='stCaptionContainer'] { color: #93a38d; font-size: 0.78rem; }"
    "section[data-testid='stSidebar'] hr { border-color: rgba(255,255,255,0.08); }"
    "section[data-testid='stSidebar'] div[data-testid='stWidgetLabel'] p { font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; letter-spacing: 0.09em; text-transform: uppercase; color: var(--sage); font-weight: 500; }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] { gap: 0.4rem; }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] label { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 0.35rem 0.7rem; transition: background 0.15s; }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] label:hover { background: rgba(255,255,255,0.09); }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] label div:first-child { border-color: var(--sage) !important; }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] label p { text-transform: none; font-family: 'IBM Plex Sans', sans-serif; font-size: 0.85rem; color: #f7f6ef; letter-spacing: 0; }"
    "section[data-testid='stSidebar'] .stMultiSelect [data-baseweb='select'] > div { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.14); border-radius: 4px; }"
    "section[data-testid='stSidebar'] span[data-baseweb='tag'] { background: var(--clay) !important; border-radius: 3px !important; font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; }"
    "section[data-testid='stSidebar'] .stButton button { background: transparent; border: 1px solid rgba(255,255,255,0.22); border-radius: 4px; color: #f7f6ef; font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; font-size: 0.84rem; padding: 0.4rem 0; transition: all 0.15s; }"
    "section[data-testid='stSidebar'] .stButton button:hover { background: var(--clay); border-color: var(--clay); color: #fff; }"
    "section[data-testid='stSidebar'] .stButton button:focus:not(:active) { color: #f7f6ef; }"
    # Heroes / panels
    ".hero { background: var(--moss-deep); padding: 1.2rem 1.6rem; border-radius: 4px; margin-bottom: 0.8rem; border-left: 3px solid var(--clay); }"
    ".hero .eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--sage); margin: 0 0 0.3rem; }"
    ".hero h1 { margin: 0; font-size: 1.5rem; font-weight: 600; color: #f7f6ef; letter-spacing: -0.01em; }"
    ".hero p { margin: 0.3rem 0 0; color: #b9c4b3; font-size: 0.85rem; max-width: 70ch; }"
    # Panels
    ".panel { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; padding: 0.7rem 0.9rem; margin-bottom: 0.6rem; }"
    ".panel-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--sage); margin: 0 0 0.5rem; display: block; }"
    ".coord-row { display: flex; justify-content: space-between; align-items: baseline; padding: 0.15rem 0; font-size: 0.8rem; }"
    ".coord-row .role { color: #a9b6a3; }"
    ".coord-row .role::before { content: ''; display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; position: relative; top: -1px; }"
    ".coord-row.start .role::before { background: #7fb885; }"
    ".coord-row.end .role::before { background: #d97a6c; }"
    ".mono { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; color: #f7f6ef; }"
    # Results table
    ".results-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; }"
    ".results-header .panel-label { color: var(--ink-soft); margin: 0; }"
    ".results-wrap { border: 1px solid var(--hairline); border-radius: 4px; overflow: hidden; background: var(--paper-raised); }"
    "table.results { width: 100%; border-collapse: collapse; font-family: 'IBM Plex Mono', monospace; }"
    "table.results thead th { text-align: right; font-family: 'IBM Plex Sans', sans-serif; font-size: 0.66rem; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600; color: var(--ink-soft); background: #eeece0; padding: 0.45rem 0.65rem; border-bottom: 1px solid var(--hairline); }"
    "table.results thead th:first-child, table.results td.algo-cell { text-align: left; }"
    "table.results td { padding: 0.45rem 0.65rem; text-align: right; font-size: 0.78rem; border-bottom: 1px solid var(--hairline); color: var(--ink); }"
    "table.results tr:last-child td { border-bottom: none; }"
    "table.results td.algo-cell { font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; font-size: 0.8rem; }"
    ".algo-dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 6px; position: relative; top: -1px; }"
    ".expansion-track { width: 54px; height: 5px; background: #eeece0; border-radius: 3px; display: inline-block; overflow: hidden; vertical-align: middle; margin-right: 6px; }"
    ".expansion-fill { height: 100%; border-radius: 3px; }"
    ".expansion-cell { display: flex; align-items: center; justify-content: flex-end; gap: 2px; }"
    ".badge-row td { background: #f1f4ec; font-family: 'IBM Plex Sans', sans-serif; font-size: 0.72rem; color: var(--moss-deep); padding: 0.4rem 0.65rem; border-bottom: none; }"
    ".badge-row .badge { display: inline-flex; align-items: center; gap: 4px; margin-right: 1rem; }"
    ".badge .badge-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--clay); display: inline-block; }"
    ".error-line { font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; color: #8c2f22; background: #fbeeec; border: 1px solid #e8cac4; border-radius: 4px; padding: 0.45rem 0.65rem; margin-bottom: 0.4rem; }"
    ".empty-state { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: var(--ink-soft); border: 1px dashed var(--hairline); border-radius: 4px; padding: 1rem 0.8rem; text-align: center; }"
    # Tabs
    ".stTabs [data-baseweb='tab-list'] { gap: 0; }"
    ".stTabs [data-baseweb='tab'] { font-family: 'IBM Plex Sans', sans-serif; font-size: 0.8rem; font-weight: 500; letter-spacing: 0.02em; }"
    ".stTabs [aria-selected='true'] { color: var(--clay) !important; }"
    # Metric cards
    ".metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.6rem; margin-bottom: 0.8rem; }"
    ".metric-card { background: var(--paper-raised); border: 1px solid var(--hairline); border-radius: 4px; padding: 0.6rem 0.8rem; }"
    ".metric-card .label { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-soft); }"
    ".metric-card .value { font-family: 'IBM Plex Sans', sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--ink); margin-top: 0.15rem; }"
    ".metric-card .sub { font-size: 0.72rem; color: var(--ink-soft); }"
    # Criticality table
    ".crit-table { width: 100%; border-collapse: collapse; font-size: 0.78rem; }"
    ".crit-table th { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-soft); background: #eeece0; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--hairline); text-align: left; }"
    ".crit-table td { padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--hairline); }"
    ".criticality-bar { display: inline-block; height: 6px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }"
    ".btn-secondary { border: 1px solid var(--hairline); background: var(--paper-raised); color: var(--ink-soft); border-radius: 4px; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; letter-spacing: 0.06em; text-transform: uppercase; padding: 0.3rem 0.7rem; cursor: pointer; }"
    ".btn-secondary:hover { border-color: var(--clay); color: var(--clay); }"
    # Benchmark table
    "table.bench { width: 100%; border-collapse: collapse; font-size: 0.78rem; }"
    "table.bench th { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-soft); background: #eeece0; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--hairline); text-align: right; }"
    "table.bench th:first-child { text-align: left; }"
    "table.bench td { padding: 0.35rem 0.5rem; border-bottom: 1px solid var(--hairline); text-align: right; }"
    "table.bench td:first-child { text-align: left; font-weight: 600; }"
    "</style>"
)

st.markdown(PAGE_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

for key, default in [
    ("start_coords", None),
    ("end_coords", None),
    ("selection_mode", "Start"),
    ("click_count", 0),
    ("consumed_clicks", []),
    ("active_tab", "\U0001f5fa\ufe0f Route Finder"),
    ("criticality_results", None),
    ("benchmark_results", None),
    ("sandbox_edge", None),
    ("sandbox_result", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


@st.cache_resource
def get_graph():
    return load_kathmandu_graph()


graph = get_graph()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fmt_coords(coords):
    if not coords:
        return "Not set"
    return f"{coords[0]:.5f}, {coords[1]:.5f}"


def clear_points():
    st.session_state.start_coords = None
    st.session_state.end_coords = None
    st.session_state.click_count = 0
    st.session_state.consumed_clicks = []


def build_results_table_html(results, extra_cols=False):
    max_expanded = max(p["metrics"].nodes_expanded for p in results.values()) or 1
    best_time_name = min(results.items(), key=lambda kv: kv[1]["metrics"].runtime_ms)[0]
    best_expanded_name = min(results.items(), key=lambda kv: kv[1]["metrics"].nodes_expanded)[0]
    best_dist_name = min(results.items(), key=lambda kv: kv[1]["metrics"].path_distance_m)[0]

    header_cols = "<th>Algorithm</th><th>Dist (km)</th><th>Time (ms)</th><th>Expanded</th><th>Relax.</th>"
    if extra_cols:
        header_cols += "<th>Max frontier</th>"
    header_cols += "<th>Path pts</th>"

    row_parts = []
    for name, payload in sorted(results.items(), key=lambda x: x[0]):
        metrics = payload["metrics"]
        color = ROUTE_COLORS.get(name, "#5b6a58")
        expansion_pct = max(4, round(100 * metrics.nodes_expanded / max_expanded))
        row = (
            "<tr>"
            f'<td class="algo-cell"><span class="algo-dot" style="background:{color};"></span>{name}</td>'
            f"<td>{metrics.path_distance_m / 1000:.2f}</td>"
            f"<td>{metrics.runtime_ms:.2f}</td>"
            '<td><span class="expansion-cell">'
            f'<span class="expansion-track"><span class="expansion-fill" style="width:{expansion_pct}%; background:{color};"></span></span>'
            f"{metrics.nodes_expanded:,}</span></td>"
            f"<td>{metrics.edge_relaxations:,}</td>"
        )
        if extra_cols:
            row += f"<td>{metrics.max_frontier_size:,}</td>"
        row += f"<td>{metrics.path_nodes:,}</td></tr>"
        row_parts.append(row)

    badge_cols = 6 + (1 if extra_cols else 0)
    badges = (
        f'<span class="badge"><span class="badge-dot"></span>Fastest \u2014 {best_time_name}</span>'
        f'<span class="badge"><span class="badge-dot"></span>Smallest search space \u2014 {best_expanded_name}</span>'
    )
    if extra_cols:
        badges += f'<span class="badge"><span class="badge-dot"></span>Shortest distance \u2014 {best_dist_name}</span>'
    badge_row = f'<tr class="badge-row"><td colspan="{badge_cols}">{badges}</td></tr>'

    return (
        f'<div class="results-wrap"><table class="results"><thead><tr>{header_cols}</tr></thead><tbody>'
        + "".join(row_parts)
        + badge_row
        + "</tbody></table></div>"
    )


@st.dialog("Algorithm comparison", width="large")
def show_comparison_dialog(results):
    st.markdown(build_results_table_html(results, extra_cols=True), unsafe_allow_html=True)


# ===================================================================
# HERO
# ===================================================================

HERO_HTML = (
    '<div class="hero">'
    '<p class="eyebrow">UrbanResilience \u00b7 COMP 314 Algorithms & Complexity</p>'
    "<h1>Kathmandu Route Lab</h1>"
    "<p>Pick two points on the map and compare shortest-path algorithms side "
    "by side, by runtime and by how much of the graph each one had to search. "
    "Then probe edge vulnerability and run scaling benchmarks on synthetic grids.</p>"
    "</div>"
)

st.markdown(HERO_HTML, unsafe_allow_html=True)

# ===================================================================
# TABS
# ===================================================================

tab_labels = ["\U0001f5fa\ufe0f Route Finder", "\u26a0\ufe0f Vulnerability", "\U0001f4ca Benchmarks"]
tab_icons = ["\U0001f5fa\ufe0f", "\u26a0\ufe0f", "\U0001f4ca"]
tab1, tab2, tab3 = st.tabs(tab_labels)

# ===================================================================
# TAB 1 \u2014 ROUTE FINDER
# ===================================================================

with tab1:
    # --- Sidebar Controls ---
    with st.sidebar:
        st.header("Controls")
        st.caption("The next map click updates the selected endpoint.")

        st.radio(
            "Next click sets",
            ["Start", "Destination"],
            key="selection_mode",
            horizontal=True,
        )

        selected_algorithms = st.multiselect(
            "Algorithms to run",
            ALGORITHMS,
            default=ALGORITHMS,
        )

        show_frontier = st.checkbox("Show frontier expansion", value=False)

        action_cols = st.columns(2)
        if action_cols[0].button("Swap", use_container_width=True):
            if st.session_state.start_coords and st.session_state.end_coords:
                st.session_state.start_coords, st.session_state.end_coords = (
                    st.session_state.end_coords,
                    st.session_state.start_coords,
                )
                st.rerun()
        if action_cols[1].button("Clear", use_container_width=True):
            clear_points()
            st.rerun()

        # Coords panel
        coords_html = (
            '<div class="panel">'
            '<span class="panel-label">Selected coordinates</span>'
            '<div class="coord-row start"><span class="role">Start</span>'
            f'<span class="mono">{fmt_coords(st.session_state.start_coords)}</span></div>'
            '<div class="coord-row end"><span class="role">Destination</span>'
            f'<span class="mono">{fmt_coords(st.session_state.end_coords)}</span></div>'
            "</div>"
        )
        st.markdown(coords_html, unsafe_allow_html=True)

        # Network profile
        network_html = (
            '<div class="panel">'
            '<span class="panel-label">Network profile</span>'
            f'<div class="coord-row"><span class="role">Nodes</span><span class="mono">{len(graph.nodes):,}</span></div>'
            f'<div class="coord-row"><span class="role">Edges</span><span class="mono">{len(graph.edges):,}</span></div>'
            "</div>"
        )
        st.markdown(network_html, unsafe_allow_html=True)

    # --- Compute routes ---
    results = {}
    errors = {}
    if st.session_state.start_coords and st.session_state.end_coords and selected_algorithms:
        for algorithm in selected_algorithms:
            try:
                solution = solve_shortest_path(
                    graph,
                    st.session_state.start_coords,
                    st.session_state.end_coords,
                    algorithm,
                )
                if solution:
                    results[algorithm] = solution
                else:
                    errors[algorithm] = "No route found"
            except Exception as exc:
                errors[algorithm] = str(exc)

    # --- Build map ---
    m = folium.Map(location=[27.7172, 85.3240], zoom_start=12, tiles="CartoDB positron")

    # Start marker
    if st.session_state.start_coords:
        folium.CircleMarker(
            location=st.session_state.start_coords,
            radius=7,
            color="#2d4530",
            fill=True,
            fill_color="#2d4530",
            fill_opacity=0.95,
            weight=2,
            tooltip="Start",
        ).add_to(m)

    # End marker
    if st.session_state.end_coords:
        folium.CircleMarker(
            location=st.session_state.end_coords,
            radius=7,
            color="#7f1d1d",
            fill=True,
            fill_color="#7f1d1d",
            fill_opacity=0.95,
            weight=2,
            tooltip="Destination",
        ).add_to(m)

    # Routes
    for algorithm, payload in results.items():
        route_coords = route_to_coordinates(graph, payload["route"])
        route_color = ROUTE_COLORS[algorithm]

        if route_coords:
            folium.PolyLine(
                route_coords,
                color=route_color,
                weight=5,
                opacity=0.82,
                tooltip=algorithm,
            ).add_to(m)

            # Dashed connection lines
            if st.session_state.start_coords:
                folium.PolyLine(
                    [st.session_state.start_coords, route_coords[0]],
                    color=route_color,
                    weight=2,
                    dash_array="5, 5",
                    opacity=0.6,
                ).add_to(m)
            if st.session_state.end_coords:
                folium.PolyLine(
                    [route_coords[-1], st.session_state.end_coords],
                    color=route_color,
                    weight=2,
                    dash_array="5, 5",
                    opacity=0.6,
                ).add_to(m)

    # --- Frontier visualisation (show visited nodes) ---
    if show_frontier and st.session_state.start_coords and st.session_state.end_coords:
        for algorithm in selected_algorithms:
            if algorithm in results:
                start_node, end_node = (
                    results[algorithm]["start_node"],
                    results[algorithm]["end_node"],
                )
                # Re-run the search in snapshot mode to get visited nodes
                snapshot_fn = {
                    "Dijkstra": dijkstra_shortest_path,
                    "A*": astar_shortest_path,
                }.get(algorithm)
                if snapshot_fn is not None:
                    gen = snapshot_fn(graph, start_node, end_node, yield_snapshots=True)
                    visited = set()
                    for snap in gen:
                        visited = snap.visited_nodes
                        frontier_nodes = snap.frontier_nodes
                    # Plot visited nodes as small dots
                    visited_coords = []
                    for n in visited:
                        nd = graph.nodes[n]
                        visited_coords.append((nd["y"], nd["x"]))
                    if visited_coords:
                        folium.CircleMarker(
                            location=visited_coords[0],  # dummy; we use FeatureGroup
                            radius=0,
                            color="#c4432f",
                        ).add_to(m)
                        # Add visited as a FeatureGroup
                        fg = folium.FeatureGroup(name=f"{algorithm} visited")
                        for lat, lon in visited_coords:
                            folium.CircleMarker(
                                location=(lat, lon),
                                radius=1.5,
                                color=ROUTE_COLORS[algorithm],
                                fill=True,
                                fill_color=ROUTE_COLORS[algorithm],
                                fill_opacity=0.3,
                                weight=0,
                            ).add_to(fg)
                        fg.add_to(m)

    # --- Map layout ---
    map_col, metrics_col = st.columns([3.5, 1.5])

    with map_col:
        map_state = st_folium(
            m,
            width=980,
            height=660,
            key="route_lab_map",
            returned_objects=["last_clicked"],
        )

    with metrics_col:
        header_cols = st.columns([2.4, 1])
        with header_cols[0]:
            st.markdown(
                '<span class="panel-label" style="margin-bottom:0;">Algorithm results</span>',
                unsafe_allow_html=True,
            )
        with header_cols[1]:
            if results:
                if st.button("Expand", type="secondary", use_container_width=True):
                    show_comparison_dialog(results)

        if not st.session_state.start_coords or not st.session_state.end_coords:
            st.markdown(
                '<div class="empty-state">No route yet.<br>Click a start point, '
                "then a destination, on the map to the left.</div>",
                unsafe_allow_html=True,
            )
        elif not selected_algorithms:
            st.markdown(
                '<div class="empty-state">No algorithms selected.<br>Pick at '
                "least one in the sidebar.</div>",
                unsafe_allow_html=True,
            )
        else:
            if results:
                st.markdown(build_results_table_html(results), unsafe_allow_html=True)
            if errors:
                for name, message in errors.items():
                    st.markdown(
                        f'<div class="error-line">{name}: {message}</div>',
                        unsafe_allow_html=True,
                    )

    # --- Click handling ---
    if map_state and map_state.get("last_clicked"):
        last_click = map_state["last_clicked"]
        clicked_coords = (last_click["lat"], last_click["lng"])

        already_consumed = (
            st.session_state.consumed_clicks
            and st.session_state.consumed_clicks[-1] == clicked_coords
        )

        if not already_consumed:
            st.session_state.consumed_clicks.append(clicked_coords)
            st.session_state.click_count += 1

            if st.session_state.selection_mode == "Start":
                st.session_state.start_coords = clicked_coords
            else:
                st.session_state.end_coords = clicked_coords
            st.rerun()

# ===================================================================
# TAB 2 \u2014 VULNERABILITY / EDGE CRITICALITY
# ===================================================================

with tab2:
    st.markdown(
        '<span class="panel-label" style="font-size:0.8rem;color:var(--ink);">'
        "Edge Criticality & Vulnerability Engine</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "The <b>Criticality Index</b> <i>C<sub>e</sub></i> measures how much the "
        "average shortest-path distance increases when an edge is removed. "
        "Edges with <i>C<sub>e</sub></i> > 0.5 are flagged as structural bottlenecks.",
        unsafe_allow_html=True,
    )

    crit_col1, crit_col2 = st.columns([1, 1])

    with crit_col1:
        sweep_algo = st.selectbox(
            "Algorithm for criticality sweep",
            ALGORITHMS,
            index=0,
            key="sweep_algo",
        )
        max_edges_sweep = st.slider(
            "Max edges to test",
            min_value=10,
            max_value=200,
            value=50,
            step=10,
            key="max_edges_sweep",
        )
        sample_ratio = st.slider(
            "OD pair sample ratio",
            min_value=0.05,
            max_value=0.5,
            value=0.1,
            step=0.05,
            key="sample_ratio",
        )

        if st.button("Run Criticality Sweep", type="primary", use_container_width=True):
            with st.spinner("Running criticality sweep (this may take a while)..."):
                bar = st.progress(0.0, text="Analysing edges...")
                latest_iteration = st.empty()

                def progress_cb(current, total):
                    bar.progress(current / total)
                    latest_iteration.text(f"Edge {current} / {total}")

                results_list = criticality_sweep(
                    graph,
                    algorithm=sweep_algo,
                    sample_ratio=sample_ratio,
                    max_pairs=100,
                    bottleneck_threshold=BOTTLENECK_THRESHOLD,
                    max_edges=max_edges_sweep,
                    progress_callback=progress_cb,
                )
                st.session_state.criticality_results = results_list

    with crit_col2:
        if st.session_state.criticality_results:
            results_list = st.session_state.criticality_results

            # Summary metrics
            num_bottlenecks = sum(1 for r in results_list if r.is_bottleneck)
            avg_ci = (
                sum(r.criticality_index for r in results_list) / len(results_list)
                if results_list
                else 0
            )
            max_ci = max(r.criticality_index for r in results_list) if results_list else 0

            st.markdown(
                f'<div class="metric-grid">'
                f'<div class="metric-card"><div class="label">Edges tested</div><div class="value">{len(results_list)}</div></div>'
                f'<div class="metric-card"><div class="label">Bottlenecks (C<sub>e</sub>>0.5)</div><div class="value" style="color:#c4432f;">{num_bottlenecks}</div></div>'
                f'<div class="metric-card"><div class="label">Avg C<sub>e</sub></div><div class="value">{avg_ci:.3f}</div></div>'
                f'<div class="metric-card"><div class="label">Max C<sub>e</sub></div><div class="value">{max_ci:.3f}</div></div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    # Criticality results table
    if st.session_state.criticality_results:
        results_list = st.session_state.criticality_results

        st.markdown("### Criticality rankings")
        st.markdown("Sorted by descending C<sub>e</sub> \u2014 highest-impact edges first.")

        top_n = st.slider("Show top N edges", 5, 50, 10, key="top_n_crit")

        rows_html = ""
        for r in results_list[:top_n]:
            bar_width = min(100, max(1, r.criticality_index * 60))
            bar_color = "#c4432f" if r.is_bottleneck else "#8a9a7e"
            bottleneck_label = "\u26a0\ufe0f Yes" if r.is_bottleneck else "No"
            row = (
                f"<tr>"
                f"<td style='font-family:IBM Plex Mono,monospace;font-size:0.72rem;'>{r.u} \u2192 {r.v}</td>"
                f"<td>{r.criticality_index:.4f}</td>"
                f'<td><span class="criticality-bar" style="width:{bar_width}px;background:{bar_color};"></span>{r.criticality_index:.2f}</td>'
                f"<td>{r.baseline_distance:.1f}m</td>"
                f"<td>{r.mutated_distance:.1f}m</td>"
                f"<td>{bottleneck_label}</td>"
                f"</tr>"
            )
            rows_html += row

        st.markdown(
            f'<table class="crit-table">'
            f"<thead><tr><th>Edge</th><th>C<sub>e</sub></th><th>Impact</th><th>Base dist</th><th>Mutated dist</th><th>Bottleneck</th></tr></thead>"
            f"<tbody>{rows_html}</tbody></table>",
            unsafe_allow_html=True,
        )

        # Bottleneck map overlay
        st.markdown("### Bottleneck map overlay")
        st.markdown("High-criticality edges shown in red on the Kathmandu map.")

        bottlenecks = [r for r in results_list if r.is_bottleneck]

        if bottlenecks:
            crit_map = folium.Map(
                location=[27.7172, 85.3240], zoom_start=12, tiles="CartoDB positron"
            )

            for r in bottlenecks[:20]:  # limit to 20 for performance
                try:
                    u_data = graph.nodes[r.u]
                    v_data = graph.nodes[r.v]
                    coords = [(u_data["y"], u_data["x"]), (v_data["y"], v_data["x"])]
                    # Intensity proportional to C_e
                    intensity = min(1.0, r.criticality_index / 2.0)
                    opacity_val = 0.4 + 0.5 * intensity
                    folium.PolyLine(
                        coords,
                        color="#c4432f",
                        weight=3 + 4 * intensity,
                        opacity=opacity_val,
                        tooltip=f"C<sub>e</sub> = {r.criticality_index:.3f}",
                    ).add_to(crit_map)
                except Exception:
                    continue

            st_folium(crit_map, width=980, height=500, key="crit_map")
        else:
            st.info("No bottlenecks found in the current sweep.")

    else:
        st.info("Run a criticality sweep from the left panel to see results here.")

    # -----------------------------------------------------------------------
    # Edge-elimination sandbox
    # -----------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### \U0001f9ea Edge-Elimination Sandbox")
    st.markdown(
        "Remove a specific edge from the network and see how it impacts "
        "the route between the currently selected start and destination."
    )

    sandbox_col1, sandbox_col2 = st.columns([1, 1])

    with sandbox_col1:
        # Let user pick an edge by node IDs
        st.markdown("**Remove an edge**")
        all_nodes = list(graph.nodes)
        node_u = st.number_input(
            "From node (u)",
            min_value=min(all_nodes),
            max_value=max(all_nodes),
            value=min(all_nodes),
            step=1,
            key="sandbox_u",
        )
        node_v = st.number_input(
            "To node (v)",
            min_value=min(all_nodes),
            max_value=max(all_nodes),
            value=min(all_nodes) + 1 if len(all_nodes) > 1 else min(all_nodes),
            step=1,
            key="sandbox_v",
        )

        if st.button("Sever Edge & Recompute", use_container_width=True):
            if not st.session_state.start_coords or not st.session_state.end_coords:
                st.warning("Please select start and destination points on the Route Finder tab first.")
            else:
                # Build a mutated copy
                try:
                    gc = graph.copy()
                    remove_all_parallel_edges(gc, int(node_u), int(node_v))

                    # Compute baseline (with original graph)
                    start_n, end_n = nearest_graph_nodes(
                        graph,
                        st.session_state.start_coords,
                        st.session_state.end_coords,
                    )

                    route_orig, metrics_orig = solve_shortest_path_between_nodes(
                        graph, start_n, end_n, sweep_algo
                    )
                    route_mut, metrics_mut = solve_shortest_path_between_nodes(
                        gc, start_n, end_n, sweep_algo
                    )

                    baseline_dist = metrics_orig.path_distance_m if route_orig else 0.0
                    mutated_dist = metrics_mut.path_distance_m if route_mut else 0.0

                    ci = (
                        (mutated_dist - baseline_dist) / baseline_dist
                        if baseline_dist > 0
                        else 0
                    )

                    st.session_state.sandbox_result = {
                        "original_route": route_orig,
                        "mutated_route": route_mut,
                        "baseline_dist": baseline_dist,
                        "mutated_dist": mutated_dist,
                        "criticality_index": ci,
                        "original_expanded": metrics_orig.nodes_expanded,
                        "mutated_expanded": metrics_mut.nodes_expanded,
                        "original_time": metrics_orig.runtime_ms,
                        "mutated_time": metrics_mut.runtime_ms,
                    }
                    st.session_state.sandbox_edge = (int(node_u), int(node_v))
                except Exception as exc:
                    st.error(f"Error: {exc}")

    with sandbox_col2:
        if st.session_state.sandbox_result:
            sr = st.session_state.sandbox_result
            edge = st.session_state.sandbox_edge

            st.markdown(
                f'<div class="metric-grid">'
                f'<div class="metric-card"><div class="label">Edge Severed</div><div class="value" style="font-size:1rem;">{edge[0]} \u2192 {edge[1]}</div></div>'
                f'<div class="metric-card"><div class="label">Criticality Index</div><div class="value" style="color:{"#c4432f" if sr["criticality_index"] > 0.5 else "#2d4530"};">{sr["criticality_index"]:.4f}</div></div>'
                f'<div class="metric-card"><div class="label">Original path</div><div class="value" style="font-size:0.9rem;">{sr["baseline_dist"]:.1f}m</div><div class="sub">{sr["original_expanded"]} nodes</div></div>'
                f'<div class="metric-card"><div class="label">Mutated path</div><div class="value" style="font-size:0.9rem;">{sr["mutated_dist"]:.1f}m</div><div class="sub">{sr["mutated_expanded"]} nodes</div></div>'
                f"</div>",
                unsafe_allow_html=True,
            )

            # Show sandbox map
            sandbox_map = folium.Map(
                location=[27.7172, 85.3240], zoom_start=12, tiles="CartoDB positron"
            )

            if sr["original_route"]:
                orig_coords = route_to_coordinates(graph, sr["original_route"])
                folium.PolyLine(
                    orig_coords, color="#8a9a7e", weight=4, opacity=0.7,
                    tooltip="Original",
                ).add_to(sandbox_map)

            if sr["mutated_route"]:
                mut_coords = route_to_coordinates(graph, sr["mutated_route"])
                folium.PolyLine(
                    mut_coords, color="#c4432f", weight=4, opacity=0.9,
                    tooltip="After removal",
                ).add_to(sandbox_map)

            st_folium(sandbox_map, width=780, height=400, key="sandbox_map")

# ===================================================================
# TAB 3 \u2014 BENCHMARKS
# ===================================================================

with tab3:
    st.markdown(
        '<span class="panel-label" style="font-size:0.8rem;color:var(--ink);">'
        "Empirical Complexity Profiling</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "Run Dijkstra on synthetic grids of increasing size to measure "
        "asymptotic scaling behaviour and identify bottlenecks.",
        unsafe_allow_html=True,
    )

    bench_col1, bench_col2 = st.columns([1, 1.5])

    with bench_col1:
        bench_algo = st.selectbox(
            "Algorithm",
            ALGORITHMS,
            index=0,
            key="bench_algo",
        )
        grid_sizes_input = st.text_input(
            "Grid sizes (rows x cols, comma-separated)",
            value="5x5, 10x10, 20x25",
        )
        sweep_limit_edges = st.slider(
            "Max edges per sweep",
            min_value=10,
            max_value=100,
            value=50,
            step=10,
            key="bench_edges",
        )

        if st.button("Run Benchmark Suite", type="primary", use_container_width=True):
            # Parse grid sizes
            sizes = []
            for part in grid_sizes_input.split(","):
                part = part.strip()
                if "x" in part:
                    r, c = part.split("x")
                    sizes.append((int(r.strip()), int(c.strip())))

            if not sizes:
                st.error("Invalid grid sizes. Use format: 5x5, 10x10, 20x25")
            else:
                with st.spinner("Running benchmarks..."):
                    bar = st.progress(0.0, text="Benchmarking...")
                    latest_iteration = st.empty()

                    def bench_progress_cb(current, total, label=""):
                        bar.progress(current / total)
                        latest_iteration.text(f"[{current}/{total}] {label}")

                    bench_results = run_benchmark_sweep(
                        grid_sizes=sizes,
                        algorithm=bench_algo,
                        sweep_max_edges=sweep_limit_edges,
                        progress_callback=bench_progress_cb,
                    )
                    st.session_state.benchmark_results = bench_results

    with bench_col2:
        if st.session_state.benchmark_results:
            bench_results = st.session_state.benchmark_results

            # Build table
            rows_html = ""
            for br in bench_results:
                rows_html += (
                    f"<tr>"
                    f"<td>{br.grid_label}</td>"
                    f"<td>{br.num_nodes:,}</td>"
                    f"<td>{br.num_edges:,}</td>"
                    f"<td>{br.dijkstra_runtime_ms} ms</td>"
                    f"<td>{br.full_sweep_runtime_s} s</td>"
                    f"<td>{br.bottlenecks_found}</td>"
                    f"</tr>"
                )

            st.markdown(
                f'<table class="bench">'
                f"<thead><tr><th>Grid</th><th>Nodes</th><th>Edges</th>"
                f"<th>Dijkstra time</th><th>Sweep time</th><th>Bottlenecks</th></tr></thead>"
                f"<tbody>{rows_html}</tbody></table>",
                unsafe_allow_html=True,
            )

            # Also show as a DataFrame for charting
            df = pd.DataFrame(
                [
                    {
                        "Grid": br.grid_label,
                        "Nodes": br.num_nodes,
                        "Edges": br.num_edges,
                        "Dijkstra (ms)": br.dijkstra_runtime_ms,
                        "Sweep (s)": br.full_sweep_runtime_s,
                        "Bottlenecks": br.bottlenecks_found,
                    }
                    for br in bench_results
                ]
            )
            # Seconds scaled to milliseconds so both series share the same axis
            df["Sweep (s) * 1000"] = df["Sweep (s)"] * 1000

            st.markdown("### Scaling chart")
            st.line_chart(
                df.set_index("Grid")[["Dijkstra (ms)", "Sweep (s) * 1000"]],
                use_container_width=True,
            )
        else:
            st.info("Run the benchmark suite from the left panel to see results.")

st.markdown("---")
st.markdown(
    '<div style="text-align:center;font-family:IBM Plex Mono,monospace;font-size:0.68rem;color:var(--ink-soft);padding:1rem;">'
    "UrbanResilience Analyzer \u00b7 COMP 314 Algorithms & Complexity \u00b7 KU 2026"
    "</div>",
    unsafe_allow_html=True,
)
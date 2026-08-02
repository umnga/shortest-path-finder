import folium
import streamlit as st
from streamlit_folium import st_folium

from shortest_path_kathmandu import (
    astar_shortest_path,
    dijkstra_shortest_path,
    load_kathmandu_graph,
    route_to_coordinates,
    solve_shortest_path,
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
    # Metric cards
    ".metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.6rem; margin-bottom: 0.8rem; }"
    ".metric-card { background: var(--paper-raised); border: 1px solid var(--hairline); border-radius: 4px; padding: 0.6rem 0.8rem; }"
    ".metric-card .label { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-soft); }"
    ".metric-card .value { font-family: 'IBM Plex Sans', sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--ink); margin-top: 0.15rem; }"
    ".metric-card .sub { font-size: 0.72rem; color: var(--ink-soft); }"
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
    "by side, by runtime and by how much of the graph each one had to search.</p>"
    "</div>"
)

st.markdown(HERO_HTML, unsafe_allow_html=True)

# ===================================================================
# ROUTE FINDER
# ===================================================================

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

st.markdown("---")
st.markdown(
    '<div style="text-align:center;font-family:IBM Plex Mono,monospace;font-size:0.68rem;color:var(--ink-soft);padding:1rem;">'
    "UrbanResilience Analyzer \u00b7 COMP 314 Algorithms & Complexity \u00b7 KU 2026"
    "</div>",
    unsafe_allow_html=True,
)
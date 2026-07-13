import folium
import streamlit as st
from streamlit_folium import st_folium

from shortest_path_kathmandu import (
    load_kathmandu_graph,
    route_to_coordinates,
    solve_shortest_path,
)


ALGORITHMS = ["Dijkstra", "A*", "Bidirectional Dijkstra"]
# Route colors double as the accent color for each algorithm's row in the
# results table, so the map and the data panel read as one system.
ROUTE_COLORS = {
    "Dijkstra": "#c4432f",
    "A*": "#3f7d5c",
    "Bidirectional Dijkstra": "#3a5a8c",
}

st.set_page_config(page_title="Kathmandu Algorithmic Router", layout="wide")

# NOTE: every rule below is a single-line string with no embedded "\n".
# Streamlit's markdown renderer only honors unsafe_allow_html on the FIRST
# line of a multi-line string passed to st.markdown -- everything after a
# literal newline gets shown as escaped text instead of parsed as HTML.
# Comments here are plain Python "#" comments, not CSS /* */ strings,
# since a bare /* */ token outside quotes is invalid Python syntax.
PAGE_CSS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
    "<style>"
    ":root {"
    "  --paper: #f7f6ef; --paper-raised: #ffffff; --ink: #1a2318; --ink-soft: #5b6a58;"
    "  --moss-deep: #1a2318; --moss: #2d4530; --sage: #8a9a7e; --hairline: #d9d5c5; --clay: #c4432f;"
    "}"
    "html, body, [class*='css'] { font-family: 'IBM Plex Sans', sans-serif; }"
    ".stApp { background: var(--paper); color: var(--ink); }"
    ".block-container { padding-top: 1.6rem; max-width: 1400px; }"
    # Sidebar shell
    "section[data-testid='stSidebar'] { background: var(--moss-deep); border-right: 1px solid rgba(255,255,255,0.06); }"
    "section[data-testid='stSidebar'] * { color: #e9ede4; }"
    "section[data-testid='stSidebar'] h1, section[data-testid='stSidebar'] h2, section[data-testid='stSidebar'] h3 { font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; color: #f7f6ef; font-size: 0.95rem; letter-spacing: 0.02em; margin-bottom: 0.2rem; }"
    "section[data-testid='stSidebar'] [data-testid='stCaptionContainer'] { color: #93a38d; font-size: 0.78rem; line-height: 1.5; }"
    "section[data-testid='stSidebar'] hr { border-color: rgba(255,255,255,0.08); }"
    # Widget labels ("Next click sets", "Algorithms to run")
    "section[data-testid='stSidebar'] div[data-testid='stWidgetLabel'] p { font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; letter-spacing: 0.09em; text-transform: uppercase; color: var(--sage); font-weight: 500; }"
    # Radio (Start/Destination)
    "section[data-testid='stSidebar'] div[role='radiogroup'] { gap: 0.4rem; }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] label { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 0.35rem 0.7rem; transition: background 0.15s; }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] label:hover { background: rgba(255,255,255,0.09); }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] label div:first-child { border-color: var(--sage) !important; }"
    "section[data-testid='stSidebar'] div[role='radiogroup'] label p { text-transform: none; font-family: 'IBM Plex Sans', sans-serif; font-size: 0.85rem; color: #f7f6ef; letter-spacing: 0; }"
    # Multiselect (Algorithms)
    "section[data-testid='stSidebar'] .stMultiSelect [data-baseweb='select'] > div { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.14); border-radius: 4px; }"
    "section[data-testid='stSidebar'] span[data-baseweb='tag'] { background: var(--clay) !important; border-radius: 3px !important; font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; }"
    # Buttons (Swap / Clear)
    "section[data-testid='stSidebar'] .stButton button { background: transparent; border: 1px solid rgba(255,255,255,0.22); border-radius: 4px; color: #f7f6ef; font-family: 'IBM Plex Sans', sans-serif; font-weight: 500; font-size: 0.84rem; padding: 0.4rem 0; transition: all 0.15s; }"
    "section[data-testid='stSidebar'] .stButton button:hover { background: var(--clay); border-color: var(--clay); color: #fff; }"
    "section[data-testid='stSidebar'] .stButton button:focus:not(:active) { color: #f7f6ef; }"
    # Hero
    ".hero { background: var(--moss-deep); padding: 1.4rem 1.6rem; border-radius: 4px; margin-bottom: 1.1rem; border-left: 3px solid var(--clay); }"
    ".hero .eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--sage); margin: 0 0 0.4rem; }"
    ".hero h1 { margin: 0; font-size: 1.7rem; font-weight: 600; color: #f7f6ef; letter-spacing: -0.01em; }"
    ".hero p { margin: 0.4rem 0 0; color: #b9c4b3; font-size: 0.92rem; max-width: 60ch; }"
    # Sidebar info panels (coordinates / network profile)
    ".panel { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 4px; padding: 0.8rem 0.95rem; margin-bottom: 0.7rem; }"
    ".panel-label { font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--sage); margin: 0 0 0.55rem; display: block; }"
    ".coord-row { display: flex; justify-content: space-between; align-items: baseline; padding: 0.18rem 0; font-size: 0.82rem; }"
    ".coord-row .role { color: #a9b6a3; }"
    ".coord-row .role::before { content: ''; display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; position: relative; top: -1px; }"
    ".coord-row.start .role::before { background: #7fb885; }"
    ".coord-row.end .role::before { background: #d97a6c; }"
    ".mono { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; color: #f7f6ef; }"
    # Results panel (main area, light theme)
    ".results-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.6rem; }"
    ".results-header .panel-label { color: var(--ink-soft); margin: 0; }"
    ".results-wrap { border: 1px solid var(--hairline); border-radius: 4px; overflow: hidden; background: var(--paper-raised); }"
    "table.results { width: 100%; border-collapse: collapse; font-family: 'IBM Plex Mono', monospace; }"
    "table.results thead th { text-align: right; font-family: 'IBM Plex Sans', sans-serif; font-size: 0.66rem; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 600; color: var(--ink-soft); background: #eeece0; padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--hairline); }"
    "table.results thead th:first-child, table.results td.algo-cell { text-align: left; }"
    "table.results td { padding: 0.55rem 0.7rem; text-align: right; font-size: 0.8rem; border-bottom: 1px solid var(--hairline); color: var(--ink); }"
    "table.results tr:last-child td { border-bottom: none; }"
    "table.results td.algo-cell { font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; font-size: 0.82rem; }"
    ".algo-dot { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 7px; position: relative; top: -1px; }"
    ".expansion-track { width: 64px; height: 6px; background: #eeece0; border-radius: 3px; display: inline-block; overflow: hidden; vertical-align: middle; margin-right: 8px; }"
    ".expansion-fill { height: 100%; border-radius: 3px; }"
    ".expansion-cell { display: flex; align-items: center; justify-content: flex-end; gap: 2px; }"
    ".badge-row td { background: #f1f4ec; font-family: 'IBM Plex Sans', sans-serif; font-size: 0.74rem; color: var(--moss-deep); padding: 0.5rem 0.7rem; border-bottom: none; }"
    ".badge-row .badge { display: inline-flex; align-items: center; gap: 5px; margin-right: 1.1rem; }"
    ".badge .badge-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--clay); display: inline-block; }"
    ".error-line { font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; color: #8c2f22; background: #fbeeec; border: 1px solid #e8cac4; border-radius: 4px; padding: 0.5rem 0.7rem; margin-bottom: 0.4rem; }"
    ".empty-state { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: var(--ink-soft); border: 1px dashed var(--hairline); border-radius: 4px; padding: 1.1rem 0.9rem; text-align: center; line-height: 1.6; }"
    # Expand button, targeted via :has() on its title attribute so it
    # doesn't need a custom component -- st.button's help text renders
    # as a title attr on hover, which isn't reliable enough, so instead
    # we give the button its own key and target the generated test id.
    "div[data-testid='stElementContainer']:has(button[kind='secondary']) .stButton button[kind='secondary'] { }"
    "button[data-testid='baseButton-secondary'] { border: 1px solid var(--hairline); background: var(--paper-raised); color: var(--ink-soft); border-radius: 4px; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; letter-spacing: 0.06em; text-transform: uppercase; padding: 0.3rem 0.7rem; }"
    "button[data-testid='baseButton-secondary']:hover { border-color: var(--clay); color: var(--clay); }"
    # Dialog (expanded comparison)
    "div[data-testid='stDialog'] { background: var(--paper); }"
    "div[data-testid='stDialog'] h1, div[data-testid='stDialog'] h2, div[data-testid='stDialog'] h3 { font-family: 'IBM Plex Sans', sans-serif; color: var(--ink); }"
    "div[data-testid='stDialog'] table.results td, div[data-testid='stDialog'] table.results th { font-size: 0.88rem; padding: 0.75rem 1rem; }"
    "</style>"
)

HERO_HTML = (
    '<div class="hero">'
    '<p class="eyebrow">Pathfinding &middot; Kathmandu street network</p>'
    "<h1>Kathmandu Route Lab</h1>"
    "<p>Pick two points on the map and compare shortest-path algorithms side "
    "by side, by runtime and by how much of the graph each one had to search.</p>"
    "</div>"
)

st.markdown(PAGE_CSS, unsafe_allow_html=True)
st.markdown(HERO_HTML, unsafe_allow_html=True)


@st.cache_resource
def get_graph():
    return load_kathmandu_graph()


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
    """Builds the <table class="results"> HTML shared by the compact
    sidebar view and the expanded dialog view. extra_cols adds the
    Max Frontier column, only shown in the expanded view since the
    sidebar is too narrow for it."""
    max_expanded = max(p["metrics"].nodes_expanded for p in results.values()) or 1
    best_time_name = min(results.items(), key=lambda kv: kv[1]["metrics"].runtime_ms)[0]
    best_expanded_name = min(results.items(), key=lambda kv: kv[1]["metrics"].nodes_expanded)[0]
    best_dist_name = min(results.items(), key=lambda kv: kv[1]["metrics"].path_distance_m)[0]

    header_cols = "<th>Algorithm</th><th>Dist (km)</th><th>Time (ms)</th><th>Expanded</th><th>Relax.</th>"
    if extra_cols:
        header_cols += "<th>Max frontier</th>"
    header_cols += "<th>Path pts</th>"

    row_parts = []
    for name, payload in results.items():
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
        row += f"<td>{metrics.path_nodes:,}</td>"
        row += "</tr>"
        row_parts.append(row)

    badge_cols = 6 + (1 if extra_cols else 0)
    badges = (
        f'<span class="badge"><span class="badge-dot"></span>Fastest &mdash; {best_time_name}</span>'
        f'<span class="badge"><span class="badge-dot"></span>Smallest search space &mdash; {best_expanded_name}</span>'
    )
    if extra_cols:
        badges += f'<span class="badge"><span class="badge-dot"></span>Shortest distance &mdash; {best_dist_name}</span>'
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


if "start_coords" not in st.session_state:
    st.session_state.start_coords = None
if "end_coords" not in st.session_state:
    st.session_state.end_coords = None
if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = "Start"
if "click_count" not in st.session_state:
    st.session_state.click_count = 0
if "consumed_clicks" not in st.session_state:
    st.session_state.consumed_clicks = []

graph = get_graph()

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

    network_html = (
        '<div class="panel">'
        '<span class="panel-label">Network profile</span>'
        f'<div class="coord-row"><span class="role">Nodes</span><span class="mono">{len(graph.nodes):,}</span></div>'
        f'<div class="coord-row"><span class="role">Edges</span><span class="mono">{len(graph.edges):,}</span></div>'
        "</div>"
    )
    st.markdown(network_html, unsafe_allow_html=True)

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

m = folium.Map(location=[27.7172, 85.3240], zoom_start=12, tiles="CartoDB positron")

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

map_col, metrics_col = st.columns([3.3, 1.2])

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
            "least one in the sidebar to run the comparison.</div>",
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

# --- Click handling -------------------------------------------------------
# st_folium keeps returning the most recent `last_clicked` value on every
# rerun, even reruns that weren't caused by a new click (e.g. toggling the
# radio, pressing Swap/Clear, or changing the algorithm multiselect). If we
# only compare the dict's lat/lng to the last one we processed, a genuine
# new click can be dropped in a race with one of those other reruns. Fix:
# track the last consumed click's identity separately from the raw
# component return value.
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
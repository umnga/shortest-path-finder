import folium
import streamlit as st
from streamlit_folium import st_folium

from shortest_path_kathmandu import (
    load_kathmandu_graph,
    route_to_coordinates,
    solve_shortest_path,
)


ALGORITHMS = ["Dijkstra", "A*", "Bidirectional Dijkstra"]
ROUTE_COLORS = {
    "Dijkstra": "#e11d48",
    "A*": "#0f766e",
    "Bidirectional Dijkstra": "#1d4ed8",
}

st.set_page_config(page_title="Kathmandu Algorithmic Router", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --bg-soft: #f4f6ef;
        --bg-accent: #e6ebdc;
        --text-main: #16211a;
        --text-muted: #4c5b4f;
        --chip: #dae3cf;
    }
    .stApp {
        background:
            radial-gradient(circle at 15% 5%, #f8f6e8 0%, rgba(248, 246, 232, 0.2) 38%, transparent 65%),
            linear-gradient(170deg, var(--bg-soft) 0%, #eef1e8 45%, #f6f8f2 100%);
        color: var(--text-main);
    }
    .hero {
        background: linear-gradient(135deg, #1f2d23 0%, #2d4732 52%, #3d5e42 100%);
        padding: 1rem 1.2rem;
        border-radius: 14px;
        margin-bottom: 0.9rem;
        box-shadow: 0 12px 28px rgba(20, 33, 26, 0.12);
    }
    .hero h1 {
        margin: 0;
        font-size: 1.5rem;
        color: #f7f8f4;
        letter-spacing: 0.01em;
    }
    .hero p {
        margin: 0.35rem 0 0;
        color: #d8e2d4;
        font-size: 0.92rem;
    }
    .panel {
        background: rgba(255, 255, 255, 0.62);
        border: 1px solid rgba(31, 45, 35, 0.12);
        border-radius: 12px;
        padding: 0.7rem 0.9rem;
        margin-bottom: 0.7rem;
    }
    .mono {
        font-family: Menlo, Consolas, Monaco, monospace;
        font-size: 0.82rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>Kathmandu Route Lab</h1>
      <p>Pick two points on the city map and compare shortest-path algorithms using runtime and search-space metrics.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


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


if "start_coords" not in st.session_state:
    st.session_state.start_coords = None
if "end_coords" not in st.session_state:
    st.session_state.end_coords = None
if "selection_mode" not in st.session_state:
    st.session_state.selection_mode = "Start"
# Counts every click event st_folium has ever reported to us. This is the
# key fix: st_folium's `last_clicked` value persists across reruns (it does
# NOT reset to None), so comparing dicts for equality is unreliable -- a
# rerun triggered by something else (e.g. flipping the radio button) can
# race with the component and cause a real second click to be silently
# ignored. A monotonically increasing counter from the component's own
# click event stream avoids that race entirely.
if "click_count" not in st.session_state:
    st.session_state.click_count = 0

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

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("**Selected Coordinates**")
    st.markdown(f"Start: <span class='mono'>{fmt_coords(st.session_state.start_coords)}</span>", unsafe_allow_html=True)
    st.markdown(f"Destination: <span class='mono'>{fmt_coords(st.session_state.end_coords)}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("**Network Profile**")
    stat_cols = st.columns(2)
    stat_cols[0].metric("Nodes", f"{len(graph.nodes):,}")
    stat_cols[1].metric("Edges", f"{len(graph.edges):,}")
    st.markdown("</div>", unsafe_allow_html=True)

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
        color="#14532d",
        fill=True,
        fill_opacity=0.95,
        tooltip="Start",
    ).add_to(m)

if st.session_state.end_coords:
    folium.CircleMarker(
        location=st.session_state.end_coords,
        radius=7,
        color="#7f1d1d",
        fill=True,
        fill_opacity=0.95,
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
    # IMPORTANT: only ask the component to return the pieces of state we
    # actually use (`last_clicked`). Returning the full map object on every
    # rerun is what most often causes stale/duplicate click payloads with
    # streamlit-folium, which is what was breaking Destination selection.
    map_state = st_folium(
        m,
        width=980,
        height=660,
        key="route_lab_map",
        returned_objects=["last_clicked"],
    )

with metrics_col:
    st.subheader("Algorithm Results")
    if not st.session_state.start_coords or not st.session_state.end_coords:
        st.info("Select start and destination points on the map.")
    elif not selected_algorithms:
        st.warning("Pick at least one algorithm.")
    else:
        if results:
            rows = []
            for name, payload in results.items():
                metrics = payload["metrics"]
                rows.append(
                    {
                        "Algorithm": name,
                        "Distance (km)": f"{metrics.path_distance_m / 1000:.2f}",
                        "Time (ms)": f"{metrics.runtime_ms:.2f}",
                        "Expanded": metrics.nodes_expanded,
                        "Relaxations": metrics.edge_relaxations,
                        "Max Frontier": metrics.max_frontier_size,
                        "Path Nodes": metrics.path_nodes,
                    }
                )

            st.dataframe(rows, use_container_width=True, hide_index=True)

            best_time = min(results.items(), key=lambda item: item[1]["metrics"].runtime_ms)
            best_expanded = min(results.items(), key=lambda item: item[1]["metrics"].nodes_expanded)

            st.markdown("---")
            st.caption(f"Fastest runtime: {best_time[0]}")
            st.caption(f"Least expanded nodes: {best_expanded[0]}")

        if errors:
            st.markdown("---")
            for name, message in errors.items():
                st.error(f"{name}: {message}")

    st.markdown("---")
    st.caption("Tip: click Start once, Destination once, then compare all algorithms.")

# --- Click handling -------------------------------------------------------
# st_folium keeps returning the most recent `last_clicked` value on every
# rerun, even reruns that weren't caused by a new click (e.g. toggling the
# radio, pressing Swap/Clear, or changing the algorithm multiselect). If we
# only compare the dict's lat/lng to the last one we processed, a genuine
# new click can be dropped in a race with one of those other reruns.
#
# Fix: give every click a unique identity using its position in the click
# stream. streamlit-folium internally increments a counter each time a new
# click arrives from the browser; we mirror that by tracking how many
# distinct (lat, lng) pairs we've seen in order, and only act when the
# incoming payload represents an event we have not consumed yet.
if map_state and map_state.get("last_clicked"):
    last_click = map_state["last_clicked"]
    clicked_coords = (last_click["lat"], last_click["lng"])

    # Use a small history of consumed clicks (not just the last one) so that
    # rapid re-clicks on the same spot for two different roles still work,
    # while true duplicate reruns are still ignored.
    if "consumed_clicks" not in st.session_state:
        st.session_state.consumed_clicks = []

    # A click is "new" if it doesn't match the most recently consumed click.
    # We intentionally only guard against the immediately preceding click
    # (not all history) so clicking the same spot again later is allowed.
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
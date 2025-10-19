# main.py
# Women's Safety Route Finder
# Uses system time (datetime) to detect day/night automatically.

from graph_loader import build_graph
from safety_scoring import compute_edge_weight, DIST_CAP
from pathfinder import dijkstra, yen_k_shortest, distance_map
from datetime import datetime
import copy

def print_nodes_once(nodes):
    print("Nodes (id: name):")
    for i, k in enumerate(sorted(nodes.keys()), 1):
        print(f"  {i}. {k}: {nodes[k]['name']}")
    print()

def parse_node_choice(user_input: str, nodes_sorted: list):
    s = user_input.strip()
    if not s:
        return None
    if s.isdigit():
        idx = int(s) - 1
        if 0 <= idx < len(nodes_sorted):
            return nodes_sorted[idx]
        return None
    s_up = s.upper()
    for n in nodes_sorted:
        if n.upper() == s_up:
            return n
    return None

def ask_node(prompt: str, nodes_sorted: list):
    while True:
        user = input(prompt + " (enter id or number): ").strip()
        node = parse_node_choice(user, nodes_sorted)
        if node is None:
            print("Invalid entry. Enter a valid node id (e.g. A) or its number from the list shown earlier.")
            continue
        return node

def ask_choice_simple(prompt: str, options: list):
    print(prompt)
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    sel = input("Choose number (or press Enter for 1): ").strip()
    try:
        idx = int(sel) - 1
        return options[max(0, min(idx, len(options)-1))]
    except:
        return options[0]

def ask_text(prompt: str):
    return input(prompt).strip()

def detect_time_of_day():
    """Determine if it's day or night based on local system time."""
    now = datetime.now()
    hour = now.hour
    if 6 <= hour < 18:
        tod = "day"
    else:
        tod = "night"
    print(f"Detected current time: {now.strftime('%H:%M')} → Mode set to {tod.upper()}")
    return tod

def build_edge_weights(edges, mode, time_of_day):
    weights = {}
    breakdowns = {}
    for e in edges:
        w, bd = compute_edge_weight(e, mode, time_of_day)
        weights[e["id"]] = w
        breakdowns[e["id"]] = bd
    return weights, breakdowns

def prune_graph_remove_nodes(adj, avoid_nodes_set):
    adj2 = {}
    for u, nbrs in adj.items():
        if u in avoid_nodes_set:
            continue
        new_nbrs = []
        for v, e in nbrs:
            if v in avoid_nodes_set:
                continue
            new_nbrs.append((v, e))
        adj2[u] = new_nbrs
    return adj2

def chain_must_pass(adj, start, must_pass_nodes, end, weight_map):
    seg_nodes = []
    seg_edges = []
    total_cost = 0.0
    cur = start
    for mp in must_pass_nodes + [end]:
        nodes_part, cost_part, edges_part = dijkstra(adj, cur, mp, weight_map)
        if nodes_part is None:
            return None, float('inf'), None
        if not seg_nodes:
            seg_nodes += nodes_part
        else:
            seg_nodes += nodes_part[1:]
        seg_edges += edges_part
        total_cost += cost_part
        cur = mp
    return seg_nodes, total_cost, seg_edges

def display_route(title, nodes, cost, edges, breakdowns, weight_kind="mixed"):
    if nodes is None:
        print(f"{title}: No route found.")
        return

    total_distance = sum(int(e.get("distance_m", 0)) for e in edges)
    total_safety = 0.0
    for e in edges:
        eid = e["id"]
        bd = breakdowns.get(eid, {})
        if isinstance(bd, dict):
            for k, v in bd.items():
                if isinstance(v, dict) and "contrib" in v:
                    try:
                        total_safety += float(v["contrib"])
                    except:
                        pass

    print(f"{title}: {' -> '.join(nodes)}")
    print(f"  Distance = {total_distance} m")
    print(f"  Safety score (sum of edge safety weights) = {total_safety:.4f}")
    if weight_kind == "distance":
        print(f"  Algorithm total_cost (distance objective): {cost:.3f} m")
    elif weight_kind == "safety":
        print(f"  Algorithm total_cost (safety objective): {cost:.4f} (lower = safer)")
    else:
        print(f"  Algorithm total_cost (combined/mixed weights): {cost:.4f}")
    print("  Edge contributions (approx safety contrib per edge):")
    for e in edges:
        eid = e["id"]
        bd = breakdowns.get(eid, {})
        contrib = 0.0
        if isinstance(bd, dict):
            for k, v in bd.items():
                if isinstance(v, dict) and "contrib" in v:
                    contrib += float(v["contrib"])
        print(f"    {eid}: dist={int(e.get('distance_m',0))}m, safety_contrib={contrib:.4f}")
    print()

def main_loop():
    nodes, edges, adj = build_graph()
    nodes_sorted = sorted(nodes.keys())

    print_nodes_once(nodes)

    start = ask_node("Select START node", nodes_sorted)
    end = ask_node("Select END node", nodes_sorted)
    while end == start:
        print("END cannot be the same as START. Choose a different END node.")
        end = ask_node("Select END node", nodes_sorted)

    mode = ask_choice_simple("Select mode:", ["walking", "two_wheeler", "car"])

    # Auto time detection
    time_of_day = detect_time_of_day()

    avoid_nodes_raw = ask_text("Avoid nodes (comma separated ids, or press Enter to skip): ")
    avoid_nodes = [x.strip() for x in avoid_nodes_raw.split(",") if x.strip()]
    if start in avoid_nodes:
        print(f"Note: Start node '{start}' was in avoid list — removing it.")
        avoid_nodes.remove(start)
    if end in avoid_nodes:
        print(f"Note: End node '{end}' was in avoid list — removing it.")
        avoid_nodes.remove(end)

    must_pass_raw = ask_text("Must-pass nodes in order (comma separated ids, or press Enter to skip): ")
    must_pass_nodes = [x.strip() for x in must_pass_raw.split(",") if x.strip()]

    # Build weights
    safety_map, breakdowns = build_edge_weights(edges, mode, time_of_day)

    adj_pruned = prune_graph_remove_nodes(adj, set(avoid_nodes))

    # Pathfinding
    dist_map = distance_map(adj_pruned)
    dpath_nodes, dpath_cost, dpath_edges = dijkstra(adj_pruned, start, end, dist_map)
    safe_nodes, safe_cost, safe_edges = dijkstra(adj_pruned, start, end, safety_map)

    combined_map = {}
    for eid, s in safety_map.items():
        d_norm = min(dist_map.get(eid, 0.0) / DIST_CAP, 1.0)
        combined_map[eid] = s + 1.0 * d_norm
    kpaths = yen_k_shortest(adj_pruned, start, end, combined_map, K=3)

    if must_pass_nodes:
        chain_nodes, chain_cost, chain_edges = chain_must_pass(adj_pruned, start, must_pass_nodes, end, combined_map)
        if chain_nodes is None:
            print("Could not compute route obeying must-pass constraints.")
        else:
            print("\n--- Route satisfying must-pass nodes ---")
            display_route("Must-pass route", chain_nodes, chain_cost, chain_edges, breakdowns)

    print("\n--- Candidate Routes ---\n")
    display_route("Shortest (distance only)", dpath_nodes, dpath_cost, dpath_edges, breakdowns, weight_kind="distance")
    display_route("Safest (safety only)", safe_nodes, safe_cost, safe_edges, breakdowns, weight_kind="safety")
    print("Top balanced alternatives (safety + distance):")
    if not kpaths:
        print("  No balanced alternatives found.")
    else:
        for i, (nodes_i, cost_i, edges_i) in enumerate(kpaths, 1):
            display_route(f"  Option {i}", nodes_i, cost_i, edges_i, breakdowns, weight_kind="mixed")

if __name__ == "__main__":
    main_loop()

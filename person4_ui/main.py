# main.py
# CLI glue: choose start/end, mode, time; compute safety weights; run shortest/safest/balanced.

from graph_loader import build_graph
from safety_scoring import compute_edge_weight, DIST_CAP
from pathfinder import dijkstra, yen_k_shortest, path_distance_weight_map, summarize_edges

def ask_choice(prompt, options):
    print(prompt)
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    sel = input("Choose number: ").strip()
    try:
        idx = int(sel) - 1
        return options[idx]
    except:
        print("Invalid choice; defaulting to first option.")
        return options[0]

def build_safety_weight_map(edges, mode, time_of_day):
    wmap = {}
    breakdowns = {}
    for e in edges:
        w, bd = compute_edge_weight(e, mode, time_of_day)
        wmap[e["id"]] = w
        breakdowns[e["id"]] = bd
    return wmap, breakdowns

def combined_weight_map(adj, safety_map, dist_coeff=1.0):
    # Combine safety + small normalized distance to diversify options
    combined = {}
    dist_map = path_distance_weight_map(adj)
    for eid, s in safety_map.items():
        d_norm = min(dist_map.get(eid, 0.0) / DIST_CAP, 1.0)
        combined[eid] = s + dist_coeff * d_norm
    return combined

def show_path(tag, nodes, cost, edges, breakdowns):
    if nodes is None:
        print(f"{tag}: No path.")
        return
    print(f"{tag}: {' -> '.join(nodes)}")
    sm = summarize_edges(edges)
    print(f"  Distance: {sm['distance_m']} m | edges: {sm['edges']} | total_cost: {cost:.3f}")
    print("  Edge contributions (safety total per edge):")
    for e in edges:
        eid = e["id"]
        total = sum(v["contrib"] for k, v in breakdowns.get(eid, {}).items() if isinstance(v, dict) and "contrib" in v)
        print(f"    {eid}  dist={int(e.get('distance_m',0))}m  safety={total:.3f}")

def main():
    nodes, edges, adj = build_graph()
    node_ids = sorted(nodes.keys())
    print("Available nodes:", ", ".join(f"{nid}({nodes[nid]['name']})" for nid in node_ids))

    start = ask_choice("Select START:", node_ids)
    end   = ask_choice("Select END:",   node_ids)
    mode  = ask_choice("Mode:", ["walking", "two_wheeler", "car"])  # 'car' as per your JSON
    time  = ask_choice("Time:", ["day", "night"])

    # Build safety weights for chosen mode/time
    safety_map, breakdowns = build_safety_weight_map(edges, mode, time)

    # Shortest-by-distance
    dist_map = path_distance_weight_map(adj)
    s_nodes, s_cost, s_edges = dijkstra(adj, start, end, dist_map)

    # Safest-by-safety
    safe_nodes, safe_cost, safe_edges = dijkstra(adj, start, end, safety_map)

    # Balanced Top-K
    comb_map = combined_weight_map(adj, safety_map, dist_coeff=1.0)
    kpaths = yen_k_shortest(adj, start, end, comb_map, K=3)

    print("\n--- RESULTS ---")
    show_path("Shortest (distance only)", s_nodes, s_cost, s_edges, breakdowns)
    show_path("Safest (safety only)", safe_nodes, safe_cost, safe_edges, breakdowns)
    print("\nTop-3 Balanced (safety + small distance):")
    if not kpaths:
        print("  No balanced paths found.")
    else:
        for i, (nodes_i, cost_i, edges_i) in enumerate(kpaths, 1):
            show_path(f"  Option {i}", nodes_i, cost_i, edges_i, breakdowns)

if __name__ == "__main__":
    main()

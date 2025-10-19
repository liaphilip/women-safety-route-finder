# main.py
# Phases 1,4,6,7,9: Input, constraint handling, safety analysis, user interaction loop, final output
from graph_loader import build_graph
from safety_scoring import compute_edge_weight, DIST_CAP
from pathfinder import dijkstra, yen_k_shortest, distance_map, summarize_route
import copy

def ask_choice(prompt: str, options: list):
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

def build_edge_weights(edges, mode, time_of_day):
    weights = {}
    breakdowns = {}
    for e in edges:
        w, bd = compute_edge_weight(e, mode, time_of_day)
        weights[e["id"]] = w
        breakdowns[e["id"]] = bd
    return weights, breakdowns

def prune_graph(adj, avoid_nodes, avoid_edges):
    adj2 = {}
    for u, nbrs in adj.items():
        if u in avoid_nodes:
            continue
        adj2[u] = []
        for v, e in nbrs:
            if v in avoid_nodes or e["id"] in avoid_edges:
                continue
            adj2[u].append((v, e))
    return adj2

def chain_must_pass(adj, start, must_pass_nodes, end, weight_map):
    """
    Chains several required nodes: start -> must1 -> must2 -> ... -> end
    Returns combined nodes list, total cost, combined edges list, or None if any segment fails.
    """
    seg_nodes = []
    seg_edges = []
    total_cost = 0.0
    cur = start
    for mp in must_pass_nodes + [end]:
        nodes_part, cost_part, edges_part = dijkstra(adj, cur, mp, weight_map)
        if nodes_part is None:
            return None, float('inf'), None
        # append nodes (avoid duplicating junction)
        if not seg_nodes:
            seg_nodes += nodes_part
        else:
            seg_nodes += nodes_part[1:]
        seg_edges += edges_part
        total_cost += cost_part
        cur = mp
    return seg_nodes, total_cost, seg_edges

def display_route(title, nodes, cost, edges, breakdowns):
    if nodes is None:
        print(f"{title}: No route found.")
        return
    print(f"{title}: {' -> '.join(nodes)}")
    s = summarize_route(edges)
    print(f"  Distance: {s['distance_m']} m | edges: {s['n_edges']} | total_cost: {cost:.3f}")
    print("  Edge breakdown (edge_id: approximate safety contrib):")
    for e in edges:
        eid = e["id"]
        bd = breakdowns.get(eid, {})
        # compute a readable sum of contribs
        total_contrib = 0.0
        if isinstance(bd, dict):
            for k,v in bd.items():
                if isinstance(v, dict) and "contrib" in v:
                    total_contrib += float(v["contrib"])
        print(f"    {eid} (dist {int(e.get('distance_m',0))}m) -> safety ≈ {total_contrib:.3f}")
    print()

def main_loop():
    nodes, edges, adj = build_graph()
    node_keys = sorted(nodes.keys())
    print("Nodes (id: name):")
    for k in node_keys:
        print(f"  {k}: {nodes[k]['name']}")
    print()

    # Input Phase
    start = ask_choice("Select START node:", node_keys)
    end = ask_choice("Select END node:", node_keys)
    mode = ask_choice("Select mode:", ["walking", "two_wheeler", "car"])
    time_of_day = ask_choice("Select time of day:", ["day", "night"])
    # preset/custom (for now only preset available; hook for customization)
    weight_pref = ask_choice("Weight preference:", ["preset", "custom (not implemented)"])

    # Optional constraints
    avoid_nodes_raw = ask_text("Avoid nodes (comma separated ids, or press Enter to skip): ")
    avoid_nodes = [x.strip() for x in avoid_nodes_raw.split(",") if x.strip()]
    avoid_edges_raw = ask_text("Avoid edges (comma separated edge ids, or press Enter to skip): ")
    avoid_edges = [x.strip() for x in avoid_edges_raw.split(",") if x.strip()]
    must_pass_raw = ask_text("Must-pass nodes in order (comma separated ids, or press Enter to skip): ")
    must_pass_nodes = [x.strip() for x in must_pass_raw.split(",") if x.strip()]

    # Data loaded -> Weight calc
    safety_map, breakdowns = build_edge_weights(edges, mode, time_of_day)

    # Constraint handling: prune graph
    adj_pruned = prune_graph(adj, set(avoid_nodes), set(avoid_edges))

    # Pathfinding Phase
    # 1) Shortest by distance (distance_map)
    dist_map = distance_map(adj_pruned)
    dpath_nodes, dpath_cost, dpath_edges = dijkstra(adj_pruned, start, end, dist_map)

    # 2) Safest by safety_map
    safe_nodes, safe_cost, safe_edges = dijkstra(adj_pruned, start, end, safety_map)

    # 3) Balanced Top-K (safety + small distance term)
    combined_map = {}
    for eid, s in safety_map.items():
        d_norm = min(dist_map.get(eid, 0.0) / DIST_CAP, 1.0)
        combined_map[eid] = s + 1.0 * d_norm
    kpaths = yen_k_shortest(adj_pruned, start, end, combined_map, K=3)

    # If must_pass provided: compute chain on combined_map (user wants include nodes)
    if must_pass_nodes:
        chain_nodes, chain_cost, chain_edges = chain_must_pass(adj_pruned, start, must_pass_nodes, end, combined_map)
        if chain_nodes is None:
            print("Could not compute route obeying must-pass constraints with current graph/constraints.")
        else:
            print("\n--- Route satisfying must-pass nodes ---")
            display_route("Must-pass route", chain_nodes, chain_cost, chain_edges, breakdowns)

    # Safety Analysis Phase & initial display
    print("\n--- Candidate Routes ---\n")
    display_route("Shortest (distance only)", dpath_nodes, dpath_cost, dpath_edges, breakdowns)
    display_route("Safest (safety only)", safe_nodes, safe_cost, safe_edges, breakdowns)
    print("Top balanced alternatives (safety + distance):")
    if not kpaths:
        print("  No balanced alternatives found.")
    else:
        for i, (nodes_i, cost_i, edges_i) in enumerate(kpaths, 1):
            display_route(f"  Option {i}", nodes_i, cost_i, edges_i, breakdowns)

    # User interaction loop: accept / refine / exit
    while True:
        print("Options:")
        print("  1. Accept a route")
        print("  2. Reject and add/remove constraints and recompute")
        print("  3. Show breakdown for a specific edge")
        print("  4. Exit without accepting")
        choice = input("Choose (1-4): ").strip()
        if choice == "1":
            # let user pick which to accept
            print("Which route to accept?")
            print("  1. Shortest")
            print("  2. Safest")
            for i in range(len(kpaths)):
                print(f"  {3+i}. Balanced Option {i+1}")
            pick = input("Choose number: ").strip()
            try:
                p = int(pick)
                if p == 1:
                    chosen = ("Shortest", dpath_nodes, dpath_cost, dpath_edges)
                elif p == 2:
                    chosen = ("Safest", safe_nodes, safe_cost, safe_edges)
                else:
                    idx = p - 3
                    if 0 <= idx < len(kpaths):
                        nodes_i, cost_i, edges_i = kpaths[idx]
                        chosen = (f"Balanced Option {idx+1}", nodes_i, cost_i, edges_i)
                    else:
                        print("Invalid choice.")
                        continue
                # final output
                print("\n=== FINAL ROUTE SELECTED ===")
                display_route(chosen[0], chosen[1], chosen[2], chosen[3], breakdowns)
                print("Final route accepted. Exiting.")
                return
            except Exception:
                print("Invalid input. Try again.")
                continue

        elif choice == "2":
            # allow user to update avoid/include and recompute
            print("Update constraints and recompute.")
            avoid_nodes_raw = ask_text("Avoid nodes (comma separated ids, or press Enter to keep current): ")
            if avoid_nodes_raw.strip():
                avoid_nodes = [x.strip() for x in avoid_nodes_raw.split(",") if x.strip()]
            avoid_edges_raw = ask_text("Avoid edges (comma separated ids, or press Enter to keep current): ")
            if avoid_edges_raw.strip():
                avoid_edges = [x.strip() for x in avoid_edges_raw.split(",") if x.strip()]
            must_pass_raw = ask_text("Must-pass nodes in order (comma separated ids, or press Enter to keep current): ")
            if must_pass_raw.strip():
                must_pass_nodes = [x.strip() for x in must_pass_raw.split(",") if x.strip()]

            # prune and recompute (repeat earlier steps)
            adj_pruned = prune_graph(adj, set(avoid_nodes), set(avoid_edges))
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
                    print("Could not compute route obeying must-pass constraints with current graph/constraints.")
                else:
                    print("\n--- Route satisfying must-pass nodes ---")
                    display_route("Must-pass route", chain_nodes, chain_cost, chain_edges, breakdowns)

            # show again
            print("\n--- Recomputed Candidate Routes ---\n")
            display_route("Shortest (distance only)", dpath_nodes, dpath_cost, dpath_edges, breakdowns)
            display_route("Safest (safety only)", safe_nodes, safe_cost, safe_edges, breakdowns)
            print("Top balanced alternatives (safety + distance):")
            if not kpaths:
                print("  No balanced alternatives found.")
            else:
                for i, (nodes_i, cost_i, edges_i) in enumerate(kpaths, 1):
                    display_route(f"  Option {i}", nodes_i, cost_i, edges_i, breakdowns)
            continue

        elif choice == "3":
            eid = input("Enter edge id to show full breakdown (e.g., A-B-1): ").strip()
            bd = breakdowns.get(eid)
            if not bd:
                print("Edge id not found in breakdowns.")
            else:
                print(f"Breakdown for edge {eid}:")
                for k, v in bd.items():
                    if isinstance(v, dict):
                        print(f"  {k}: risk={v.get('risk')}, coeff={v.get('coeff')}, time_mult={v.get('time_mult')}, contrib={v.get('contrib')}")
                    else:
                        print(f"  {k}: {v}")
            continue

        elif choice == "4":
            print("Exiting without selecting a final route.")
            return
        else:
            print("Invalid option. Choose 1-4.")

if __name__ == "__main__":
    main_loop()

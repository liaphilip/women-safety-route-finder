# main.py
# CLI with accept/recompute loop and custom-weight input handling
from graph_loader import build_graph
from safety_scoring import compute_edge_weight, DIST_CAP
from pathfinder import dijkstra, yen_k_shortest, distance_map
from datetime import datetime
import copy

try:
    import matplotlib.pyplot as plt
    import networkx as nx
    HAVE_PLOTTING = True
except Exception:
    HAVE_PLOTTING = False

# ---------- Helpers ----------

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
    now = datetime.now()
    hour = now.hour
    if 6 <= hour < 18:
        tod = "day"
    else:
        tod = "night"
    print(f"Detected current time: {now.strftime('%H:%M')} → Mode set to {tod.upper()}")
    return tod

def parse_coeff_overrides(text: str):
    """
    Parse strings like:
      "lighting:2,cctv:1.5,crime:mul:1.2"
    Returns dict feature -> value or ("mul", factor)
    """
    out = {}
    if not text:
        return out
    parts = [p.strip() for p in text.split(",") if p.strip()]
    for p in parts:
        # formats:
        # feat:value
        # feat:mul:value
        pieces = p.split(":")
        if len(pieces) == 2:
            feat, val = pieces
            try:
                out[feat.strip()] = float(val.strip())
            except:
                pass
        elif len(pieces) == 3 and pieces[1].lower() == "mul":
            feat = pieces[0].strip()
            try:
                val = float(pieces[2].strip())
                out[feat] = ("mul", val)
            except:
                pass
        else:
            # ignore malformed
            pass
    return out

def build_edge_weights_with_overrides(edges, mode, time_of_day, coeff_override):
    weights = {}
    breakdowns = {}
    for e in edges:
        w, bd = compute_edge_weight(e, mode, time_of_day, coeff_override)
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
    print()

# ---------- (optional) plotting helpers if available ----------
if HAVE_PLOTTING:
    def build_networkx_graph(nodes_dict, edges_list):
        G = nx.Graph()
        for nid, meta in nodes_dict.items():
            G.add_node(nid, name=meta.get("name", nid))
        for e in edges_list:
            u, v = e["u"], e["v"]
            G.add_edge(u, v, id=e.get("id"), distance_m=e.get("distance_m", 0), edge_obj=e)
        return G

    def plot_full_graph(nodes, edges):
        G = build_networkx_graph(nodes, edges)
        pos = nx.spring_layout(G, seed=42)
        plt.figure(figsize=(8,6))
        nx.draw_networkx_nodes(G, pos, node_color="skyblue", node_size=700)
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.7)
        labels = {n: G.nodes[n].get("name", n) for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=9)
        edge_labels = {(u,v): d.get("distance_m","") for u,v,d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        plt.title("Full Graph — Locations")
        plt.axis("off")
        plt.tight_layout()
        plt.show()

    def plot_path_highlight(nodes, edges, path_nodes):
        if not path_nodes:
            return
        G = build_networkx_graph(nodes, edges)
        pos = nx.spring_layout(G, seed=42)
        plt.figure(figsize=(8,6))
        nx.draw_networkx_nodes(G, pos, node_color="lightgray", node_size=500)
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.4, edge_color="gray")
        labels = {n: G.nodes[n].get("name", n) for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=8)
        path_edges = []
        for i in range(len(path_nodes)-1):
            a, b = path_nodes[i], path_nodes[i+1]
            if G.has_edge(a, b):
                path_edges.append((a, b))
        nx.draw_networkx_nodes(G, pos, nodelist=path_nodes, node_color="skyblue", node_size=700)
        nx.draw_networkx_edges(G, pos, edgelist=path_edges, width=4.0, edge_color="blue")
        edge_labels = {}
        for u, v in path_edges:
            data = G.get_edge_data(u, v, default={})
            edge_labels[(u, v)] = data.get("distance_m", "")
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        plt.axis("off")
        plt.tight_layout()
        plt.show()

# ---------- Main loop (with interaction + custom weight handling) ----------
def chain_must_pass(adj, start, must_pass_nodes, end, weight_map):
    """
    Computes a route that passes through all 'must_pass_nodes' in the given order.
    It chains Dijkstra results: start -> must1 -> must2 -> ... -> end
    Returns (full_node_sequence, total_cost, edge_list)
    """
    from pathfinder import dijkstra  # safe import here

    seg_nodes = []
    seg_edges = []
    total_cost = 0.0
    cur = start

    for mp in must_pass_nodes + [end]:
        nodes_part, cost_part, edges_part = dijkstra(adj, cur, mp, weight_map)
        if nodes_part is None:
            # path not found for a segment
            return None, float('inf'), None

        # concatenate, skipping the first node (to avoid duplicates)
        if not seg_nodes:
            seg_nodes += nodes_part
        else:
            seg_nodes += nodes_part[1:]
        seg_edges += edges_part
        total_cost += cost_part
        cur = mp

    return seg_nodes, total_cost, seg_edges

def main_loop():
    nodes, edges, adj = build_graph()
    nodes_sorted = sorted(nodes.keys())

    # optional: show full graph initially
    if HAVE_PLOTTING:
        try:
            plot_full_graph(nodes, edges)
        except Exception as ex:
            print("Plot warning:", ex)

    print_nodes_once(nodes)

    # pick start/end
    start = ask_node("Select START node", nodes_sorted)
    end = ask_node("Select END node", nodes_sorted)
    while end == start:
        print("END cannot be the same as START. Choose a different END node.")
        end = ask_node("Select END node", nodes_sorted)

    mode = ask_choice_simple("Select mode:", ["walking", "two_wheeler", "car"])

    time_of_day = detect_time_of_day()

    # Ask whether to use preset or custom weight importance
    wp = ask_choice_simple("Weight preference:", ["preset", "custom"])
    coeff_override = {}
    if wp == "custom":
        print("Enter custom importance overrides as comma separated pairs.")
        print("Format examples:")
        print("  lighting:2  -> sets coefficient for lighting to 2")
        print("  cctv:mul:1.5 -> multiplies preset cctv coeff by 1.5")
        print("  lighting:2,cctv:mul:1.5,crime:3")
        raw = ask_text("Enter overrides (or press Enter to cancel): ")
        coeff_override = parse_coeff_overrides(raw)

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

    # compute weights with possible overrides
    safety_map, breakdowns = build_edge_weights_with_overrides(edges, mode, time_of_day, coeff_override)

    # initial pruning
    adj_pruned = prune_graph_remove_nodes(adj, set(avoid_nodes))

    # pathfinding (distance, safety, combined)
    dist_map = distance_map(adj_pruned)
    dpath_nodes, dpath_cost, dpath_edges = dijkstra(adj_pruned, start, end, dist_map)
    safe_nodes, safe_cost, safe_edges = dijkstra(adj_pruned, start, end, safety_map)
    combined_map = {}
    for eid, s in safety_map.items():
        d_norm = min(dist_map.get(eid, 0.0) / DIST_CAP, 1.0)
        combined_map[eid] = s + 1.0 * d_norm
    kpaths = yen_k_shortest(adj_pruned, start, end, combined_map, K=3)

    # if must-pass chain
    if must_pass_nodes:
        chain_nodes = None
        try:
            chain_nodes, chain_cost, chain_edges = chain_must_pass(adj_pruned, start, must_pass_nodes, end, combined_map)
            if chain_nodes is None:
                print("Could not compute route obeying must-pass constraints.")
            else:
                print("\n--- Route satisfying must-pass nodes ---")
                display_route("Must-pass route", chain_nodes, chain_cost, chain_edges, breakdowns, weight_kind="mixed")
        except Exception:
            pass

    # display candidate routes
    def show_candidates():
        print("\n--- Candidate Routes ---\n")
        display_route("Shortest (distance only)", dpath_nodes, dpath_cost, dpath_edges, breakdowns, weight_kind="distance")
        display_route("Safest (safety only)", safe_nodes, safe_cost, safe_edges, breakdowns, weight_kind="safety")
        print("Top balanced alternatives (safety + distance):")
        if not kpaths:
            print("  No balanced alternatives found.")
        else:
            for i, (nodes_i, cost_i, edges_i) in enumerate(kpaths, 1):
                display_route(f"  Option {i}", nodes_i, cost_i, edges_i, breakdowns, weight_kind="mixed")
    show_candidates()

    # optional plot first balanced
    #if HAVE_PLOTTING and kpaths:
     #   try:
      #      first_nodes, _, _ = kpaths[0]
       #     plot_path_highlight(nodes, edges, first_nodes)
        #except Exception as ex:
         #   print("Plot warning:", ex)

    # Interaction loop (accept or recompute)
    while True:
        print("\nOptions:")
        print("  1. Accept a route")
        print("  2. Reject and update constraints (avoid/must-pass/custom weights) then recompute")
        print("  3. Show breakdown for a specific edge")
        print("  4. Exit without accepting")
        choice = input("Choose (1-4): ").strip()

        if choice == "1":
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
                print("\n=== FINAL ROUTE SELECTED ===")
                display_route(chosen[0], chosen[1], chosen[2], chosen[3], breakdowns, weight_kind="mixed")
                if HAVE_PLOTTING:
                    try:
                        plot_path_highlight(nodes, edges, chosen[1])
                    except Exception as ex:
                        print("Plot warning (accepted route):", ex)

                print("Final route accepted. Exiting.")
                return
            except Exception:
                print("Invalid input. Try again.")
                continue

        elif choice == "2":
            # allow user to update avoid nodes, must-pass, or custom weights (or keep same)
            print("Update constraints and/or custom weights.")
            avoid_nodes_raw = ask_text("Avoid nodes (comma separated ids, or press Enter to keep current): ")
            if avoid_nodes_raw.strip():
                avoid_nodes = [x.strip() for x in avoid_nodes_raw.split(",") if x.strip()]
                if start in avoid_nodes:
                    print(f"Note: Start node '{start}' was in avoid list — removing it.")
                    avoid_nodes.remove(start)
                if end in avoid_nodes:
                    print(f"Note: End node '{end}' was in avoid list — removing it.")
                    avoid_nodes.remove(end)

            must_pass_raw = ask_text("Must-pass nodes in order (comma separated ids, or press Enter to keep current): ")
            if must_pass_raw.strip():
                must_pass_nodes = [x.strip() for x in must_pass_raw.split(",") if x.strip()]

            wp_new = ask_choice_simple("Weight preference (keep current):", ["keep current", "preset", "custom"])
            if wp_new == "custom":
                raw = ask_text("Enter overrides (e.g. lighting:2,cctv:mul:1.5) or press Enter to cancel: ")
                coeff_override = parse_coeff_overrides(raw)
            elif wp_new == "preset":
                coeff_override = {}
            # else keep current

            # recompute everything with new constraints/weights
            safety_map, breakdowns = build_edge_weights_with_overrides(edges, mode, time_of_day, coeff_override)
            adj_pruned = prune_graph_remove_nodes(adj, set(avoid_nodes))
            dist_map = distance_map(adj_pruned)
            dpath_nodes, dpath_cost, dpath_edges = dijkstra(adj_pruned, start, end, dist_map)
            safe_nodes, safe_cost, safe_edges = dijkstra(adj_pruned, start, end, safety_map)
            combined_map = {}
            for eid, s in safety_map.items():
                d_norm = min(dist_map.get(eid, 0.0) / DIST_CAP, 1.0)
                combined_map[eid] = s + 1.0 * d_norm
            kpaths = yen_k_shortest(adj_pruned, start, end, combined_map, K=3)

            # show updated candidates and (optionally) plot
            show_candidates()
            if HAVE_PLOTTING and kpaths:
                try:
                    first_nodes, _, _ = kpaths[0]
                    plot_path_highlight(nodes, edges, first_nodes)
                except Exception as ex:
                    print("Plot warning:", ex)
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

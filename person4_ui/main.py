# main.py
# CLI with accept/recompute loop and custom-weight input handling
from graph_loader import build_graph
from safety_scoring import compute_edge_weight, DIST_CAP, MODE_PRESETS
from pathfinder import dijkstra, yen_k_shortest, distance_map
from datetime import datetime
import copy
import json, os

try:
    import matplotlib.pyplot as plt
    import networkx as nx
    HAVE_PLOTTING = True
except Exception:
    HAVE_PLOTTING = False

# ---------- Helpers ----------

def print_nodes_once(nodes):
    # kept for compatibility; intentionally no-op
    pass

def parse_node_choice(user_input: str, nodes_sorted: list, nodes_dict: dict):
    """Parse user input into a node id.
    Accepts:
      - number (1-based index into nodes_sorted)
      - exact node id (case-insensitive)
      - exact location name (case-insensitive)
      - prefix of location name (case-insensitive)
    Returns node id string or None if not matched.
    """
    if user_input is None:
        return None
    s = user_input.strip()
    if not s:
        return None

    # number selection (1-based index)
    if s.isdigit():
        idx = int(s) - 1
        if 0 <= idx < len(nodes_sorted):
            return nodes_sorted[idx]
        return None

    s_up = s.upper()

    # exact match by node id
    for nid in nodes_sorted:
        if nid.upper() == s_up:
            return nid

    # exact match by node display name
    for nid in nodes_sorted:
        name = nodes_dict.get(nid, {}).get("name", "")
        if name and name.strip().upper() == s_up:
            return nid

    # prefix match by node display name
    matches = []
    for nid in nodes_sorted:
        name = nodes_dict.get(nid, {}).get("name", "")
        if name and name.strip().upper().startswith(s_up):
            matches.append(nid)

    # if exactly one prefix match, return it; otherwise ambiguous -> None
    if len(matches) == 1:
        return matches[0]
    return None

def show_locations_friendly(nodes):
    """Friendly list of available locations for the user to pick from."""
    print("Available locations:")
    for i, k in enumerate(sorted(nodes.keys()), 1):
        name = nodes[k].get("name", k)
        print(f"  {i}. {name}  (id: {k})")
    print("Tip: you can type the number, the id (e.g. A) or the location name (or a prefix).")
    print()

# small helper to convert minutes to HH:MM if needed
def _format_minutes(m):
    if m < 60:
        return f"{int(round(m))} min"
    h = int(m // 60)
    rem = int(round(m % 60))
    return f"{h}h {rem}m"

FRIENDLY_NAMES = {
    "crime": "Crime",
    "lighting": "Lighting",
    "cctv": "CCTV coverage",
    "crowd_density": "Crowd level",
    "traffic_density": "Traffic level",
    "accidents_reported": "Accident reports",
    "road_condition": "Road condition",
    "stray_animals": "Stray animals",
    "nearest_police_m": "Distance to nearest police",
    "sidewalk": "Sidewalk presence",
    "shops_visibility": "Shops / visibility",
    "traffic_behavior": "Driver behavior",
    "parking_safety": "Parking safety",
    "distance_penalty": "Distance penalty"
}

def _friendly_breakdown_print(bd):
    if not isinstance(bd, dict):
        print("  No breakdown available.")
        return
    for feat, val in bd.items():
        name = FRIENDLY_NAMES.get(feat, feat)
        if isinstance(val, dict):
            risk = val.get("risk", 0.0)
            contrib = val.get("contrib", 0.0)
            coeff = val.get("coeff", "")
            # present risk as percent for layman
            print(f"  - {name}: risk {round(risk*100)}%  |  impact {round(contrib,4)} (coeff {coeff})")
        else:
            print(f"  - {name}: {val}")

def display_route(title, nodes_seq, cost, edges, breakdowns, mode="walking", weight_kind="mixed"):
    """More user-friendly route summary with ETA and plain-language safety info."""
    if nodes_seq is None:
        print(f"{title}: No route found.")
        return

    # total distance
    total_distance = sum(int(e.get("distance_m", 0)) for e in edges)

    # estimate travel time by mode (simple average speeds)
    speed_kmh = {"walking": 5.0, "two_wheeler": 20.0, "car": 40.0}
    sp = speed_kmh.get(mode, 5.0)
    est_minutes = (total_distance / 1000.0) / sp * 60.0

    # interpret safety: lower total contrib -> safer
    total_safety = 0.0
    for e in edges:
        eid = e.get("id")
        bd = breakdowns.get(eid, {})
        if isinstance(bd, dict):
            for k, v in bd.items():
                if isinstance(v, dict) and "contrib" in v:
                    try:
                        total_safety += float(v["contrib"])
                    except:
                        pass

    safety_msg = "safer" if total_safety < 5 else ("moderately safe" if total_safety < 12 else "less safe")
    print(f"{title}")
    print(f"  Route: {' → '.join(nodes_seq)}")
    print(f"  Distance: {total_distance} m   •   Est. travel time: {_format_minutes(est_minutes)} ({mode})")
    print(f"  Safety summary: {safety_msg}  (score: {total_safety:.3f}; lower is safer)")
    if weight_kind == "distance":
        print(f"  Objective used: shortest distance (meters). Algorithm cost = {cost:.3f}")
    elif weight_kind == "safety":
        print(f"  Objective used: safety-first. Algorithm cost = {cost:.4f} (lower = safer)")
    else:
        print(f"  Objective used: balanced (safety + distance). Algorithm cost = {cost:.4f}")
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
def ask_choice(prompt, options):
    """Ask user to choose from a list of options."""
    while True:
        print(f"{prompt}")
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        choice = input("Choose (number): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print("Invalid choice. Please try again.")

# small helper: simpler variant that accepts a default label list
def ask_choice_simple(prompt, options):
    return ask_choice(prompt, options)

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

def ask_node(prompt, nodes_sorted, nodes_dict):
    """Ask user to select a node and return the node id."""
    while True:
        user_input = input(f"{prompt} ").strip()
        if not user_input:
            continue
        nid = parse_node_choice(user_input, nodes_sorted, nodes_dict)
        if nid:
            return nid
        print("Location not found. Please try again or type 'list' to show available locations.")
        if user_input.lower() == "list":
            print()
            show_locations_friendly(nodes_dict)

def ask_text(prompt):
    return input(f"{prompt} ").strip()

def detect_time_of_day():
    """Simple day/night detector based on hour."""
    h = datetime.now().hour
    return "day" if 7 <= h < 19 else "night"

def parse_coeff_overrides(raw: str):
    """
    Parse string like "lighting:2,cctv:mul:1.5,crime:3" into dict.
    Values are either float or ("mul", float) tuples.
    We ignore invalid entries
    """
    out = {}
    if not raw:
        return out
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        segs = part.split(":")
        try:
            if len(segs) == 3 and segs[1].lower() == "mul":
                out[segs[0].strip()] = ("mul", float(segs[2]))
            elif len(segs) == 2:
                out[segs[0].strip()] = float(segs[1])
            else:
                if "=" in part:
                    k, v = part.split("=", 1)
                    out[k.strip()] = float(v)
        except Exception:
            continue
    return out

def build_edge_weights_with_overrides(edges, mode, time_of_day, coeff_override):
    """
    Returns (safety_map, breakdowns)
    safety_map: edge_id -> weight (float)
    breakdowns: edge_id -> breakdown dict returned from compute_edge_weight
    """
    safety_map = {}
    breakdowns = {}
    for e in edges:
        eid = e.get("id")
        if not eid:
            continue
        w, bd = compute_edge_weight(e, mode, time_of_day, coeff_override)
        safety_map[eid] = float(w)
        breakdowns[eid] = bd
    return safety_map, breakdowns

def prune_graph_remove_nodes(adj, avoid_set):
    """Return a new adjacency dict without nodes in avoid_set and without edges to them."""
    avoid_set = set(avoid_set or [])
    new_adj = {}
    for n, nbrs in adj.items():
        if n in avoid_set:
            continue
        new_nbrs = []
        for v, e in nbrs:
            if v in avoid_set:
                continue
            # skip edges that reference removed nodes
            new_nbrs.append((v, e))
        new_adj[n] = new_nbrs
    return new_adj

def ask_custom_importance(mode_key: str):
    """
    Prompt user to set importance weights (0..1) for every attribute in MODE_PRESETS[mode_key].
    These are importance multipliers only (do NOT modify raw edge data).
    We apply the multiplier to the preset coefficient: final_coeff = preset_coeff * user_weight.
    Returns a dict feature -> absolute coeff (float) suitable for compute_edge_weight overrides.
    """
    presets = MODE_PRESETS.get(mode_key, {})
    if not presets:
        print("No presets for mode; using defaults.")
        presets = {}

    print("\nSet importance for each factor on a 0.0 (ignore) to 1.0 (full) scale.")
    print("Press Enter to keep the default importance (1.0).\n")

    overrides = {}
    for key, base_coeff in presets.items():
        friendly = FRIENDLY_NAMES.get(key, key)
        # show current normalized to 1.0 meaning keep full preset
        raw = input(f"  {friendly} (default shown as 1.00, preset coeff {base_coeff:.2f}) => enter 0.0-1.0 or Enter: ").strip()
        if raw == "":
            continue
        try:
            val = float(raw)
            if not (0.0 <= val <= 1.0):
                print("    Value must be between 0 and 1 — skipping.")
                continue
            # convert normalized to absolute coeff by scaling preset coefficient
            overrides[key] = float(base_coeff * val)
        except Exception:
            print("    Invalid number — skipping.")
            continue

    if overrides:
        print("\nApplied importance overrides (these adjust weighting only):")
        for k, v in overrides.items():
            print(f"  {FRIENDLY_NAMES.get(k,k)} => coeff {v:.3f}")
    else:
        print("No importance overrides provided; using presets.")
    print()
    return overrides

def load_dynamic_layer(path="data/dynamic.json"):
    """
    Optional JSON file with per-edge or per-node dynamic updates.
    Example:
    {
      "edges": {"A-B-1": {"cctv": 0, "stray_animals": 1}},
      "nodes": {"N1": {"some_node_attr": 1}}
    }
    Returns dict with 'edges' and 'nodes' keys (may be empty).
    """
    if not os.path.exists(path):
        return {"edges": {}, "nodes": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print("Warning: failed to load dynamic layer:", ex)
        return {"edges": {}, "nodes": {}}

def apply_dynamic_updates_to_edges(edges, dynamic):
    """
    Merge dynamic edge updates into the edges list in-place.
    Only overwrites keys present in dynamic; does not delete other attributes.
    """
    edge_updates = dynamic.get("edges", {}) if dynamic else {}
    if not edge_updates:
        return
    by_id = {e.get("id"): e for e in edges if e.get("id")}
    for eid, updates in edge_updates.items():
        e = by_id.get(eid)
        if not e:
            continue
        for k, v in updates.items():
            e[k] = v

def main_loop():
    nodes, edges, adj = build_graph()
    nodes_sorted = sorted(nodes.keys())

    # optional: show full graph initially
    if HAVE_PLOTTING:
        try:
            plot_full_graph(nodes, edges)
        except Exception as ex:
            print("Plot warning:", ex)

    show_locations_friendly(nodes)

    # pick start/end
    start = ask_node("Where are you starting from?", nodes_sorted, nodes)
    end = ask_node("Where would you like to go?", nodes_sorted, nodes)
    while end == start:
        print("Destination cannot be the same as your starting point. Please choose a different destination.")
        end = ask_node("Where would you like to go?", nodes_sorted, nodes)

    mode = ask_choice("How will you travel?", ["walking", "two_wheeler", "car"])

    time_of_day = detect_time_of_day()

    # Ask whether to use preset or custom weight importance
    wp = ask_choice("Do you want the default route preferences or custom importance?", ["preset", "custom"])
    coeff_override = {}
    if wp == "custom":
        # Ask user a 0..1 importance for each attribute (these values scale the preset coeffs)
        coeff_override = ask_custom_importance(mode)

    # load/apply optional dynamic updates BEFORE scoring (does not modify source files)
    dynamic = load_dynamic_layer()   # reads data/dynamic.json if present
    apply_dynamic_updates_to_edges(edges, dynamic)

    avoid_nodes_raw = ask_text("Any locations to avoid? (enter ids, comma separated, or press Enter to skip): ")
    avoid_nodes = [x.strip() for x in avoid_nodes_raw.split(",") if x.strip()]
    if start in avoid_nodes:
        print(f"Note: Start location '{start}' was in your avoid list — it has been removed.")
        avoid_nodes.remove(start)
    if end in avoid_nodes:
        print(f"Note: Destination '{end}' was in your avoid list — it has been removed.")
        avoid_nodes.remove(end)

    must_pass_raw = ask_text("Any mandatory stops along the way? (ids, in order, comma separated; press Enter to skip): ")
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
                print("Could not compute a route that visits all mandatory stops in the requested order.")
            else:
                print("\n--- Route satisfying required stops ---")
                display_route("Route with required stops", chain_nodes, chain_cost, chain_edges, breakdowns, mode=mode, weight_kind="mixed")
        except Exception:
            pass

    # display candidate routes
    def show_candidates():
        print("\n--- Suggested routes for you ---\n")
        display_route("Quickest option", dpath_nodes, dpath_cost, dpath_edges, breakdowns, mode=mode, weight_kind="distance")
        display_route("Safest option", safe_nodes, safe_cost, safe_edges, breakdowns, mode=mode, weight_kind="safety")
        print("Balanced alternatives (safety + distance):")
        if not kpaths:
            print("  No balanced alternatives found.")
        else:
            for i, (nodes_i, cost_i, edges_i) in enumerate(kpaths, 1):
                display_route(f"  Option {i}", nodes_i, cost_i, edges_i, breakdowns, mode=mode, weight_kind="mixed")
    show_candidates()

    # optional plot first balanced
    # if HAVE_PLOTTING and kpaths:
    #     try:
    #         first_nodes, _, _ = kpaths[0]
    #         plot_path_highlight(nodes, edges, first_nodes)
    #     except Exception as ex:
    #         print("Plot warning:", ex)

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
                coeff_override = ask_custom_importance(mode)
            elif wp_new == "preset":
                coeff_override = {}
            # else keep current

            # reload dynamic layer (in case it changed) and apply
            dynamic = load_dynamic_layer()
            apply_dynamic_updates_to_edges(edges, dynamic)

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
                _friendly_breakdown_print(bd)
            continue

        elif choice == "4":
            print("Exiting without selecting a final route.")
            return

        else:
            print("Invalid option. Choose 1-4.")

if __name__ == "__main__":
    main_loop()

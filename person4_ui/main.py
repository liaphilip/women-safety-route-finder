import copy
import datetime
import sys
from pprint import pprint

# Import project modules (assumed present)
import graph_loader
import safety_scoring
import pathfinder

# -------------------------
# Helpers / Adapters
# -------------------------

def build_weights_from_graph(graph, mode, time_str):
    """
    Build a weights mapping for all directed edges in graph.

    Returns two things:
    - weights_uv: dict mapping (u, v) -> weight (float)
    - edge_attrs_map: dict mapping (u, v) -> attrs (so we can compute breakdowns later)
    """
    weights_uv = {}
    edge_attrs_map = {}
    for u, neighbors in graph.items():
        for edge in neighbors:
            v = edge["to"]
            attrs = edge.get("attrs", {})
            try:
                w = safety_scoring.compute_edge_weight(attrs, mode, time_str)
            except Exception as e:
                # fallback: if scoring fails, use a simple heuristic
                # prefer distance if present, else 1.0
                dist = attrs.get("distance", 1.0)
                w = float(dist)
            weights_uv[(u, v)] = float(w)
            edge_attrs_map[(u, v)] = attrs
    return weights_uv, edge_attrs_map

def remove_nodes_from_graph(graph, avoid_nodes):
    """Return a deep-copied graph with avoid_nodes removed (and edges to/from them)."""
    g = copy.deepcopy(graph)
    for n in list(g.keys()):
        if n in avoid_nodes:
            g.pop(n, None)
        else:
            # filter neighbors
            g[n] = [e for e in g.get(n, []) if e["to"] not in avoid_nodes]
    return g

def path_to_edge_pairs(path):
    """Convert node path ['A','B','C'] -> [('A','B'),('B','C')]"""
    return list(zip(path, path[1:]))

def compute_path_breakdown(path, edge_attrs_map, weights_uv):
    """
    Compute breakdown for a single path:
    - total_distance (sum of distance attrs)
    - total_weight (safety sum)
    - per-attribute sums (crime, lighting, traffic, accidents) if present
    """
    edge_pairs = path_to_edge_pairs(path)
    totals = {"distance": 0.0, "safety_weight": 0.0}
    per_attr = {}
    for (u, v) in edge_pairs:
        attrs = edge_attrs_map.get((u, v), {})
        w = weights_uv.get((u, v), 0.0)
        totals["safety_weight"] += w
        totals["distance"] += float(attrs.get("distance", 0.0))
        # collect some likely attributes if present
        for k, val in attrs.items():
            if k == "distance": 
                continue
            # only numeric attrs
            try:
                fv = float(val)
            except Exception:
                continue
            per_attr[k] = per_attr.get(k, 0.0) + fv
    return totals, per_attr

def force_include_nodes_and_get_paths(graph, start, end, include_nodes, mode, time_str, k=3):
    """
    If include_nodes is non-empty, break problem into segments:
    start -> include1 -> include2 -> ... -> end
    For each segment, call pathfinder.get_paths and stitch the top path for that segment.
    Returns a single list of candidate full paths (attempts up to k) — simplified approach:
    - For robustness we compute only the top simple stitched path (not combinatorially all k^m)
    - If you need to enumerate combinations across segment alternatives, extend this function.
    """
    seq = [start] + include_nodes + [end]
    stitched_path = []
    weights_uv, edge_attrs_map = build_weights_from_graph(graph, mode, time_str)
    # We'll try to get the top path for each segment and append (avoid duplicate junction nodes)
    for i in range(len(seq)-1):
        s = seq[i]
        t = seq[i+1]
        try:
            # pathfinder is expected to accept graph and weights. Adapt if needed.
            seg_paths = pathfinder.get_paths(graph, s, t, weights_uv, k=1)
            if not seg_paths:
                raise ValueError(f"No path between segment {s} -> {t}")
            seg_path = seg_paths[0]
        except Exception as e:
            # failure: return empty to indicate no path possible with constraints
            return []
        if not stitched_path:
            stitched_path = seg_path[:]  # start fresh
        else:
            # append seg_path but avoid duplicating the first node (already present)
            stitched_path.extend(seg_path[1:])
    return [stitched_path]  # return list-of-paths to match expected interface

# -------------------------
# CLI
# -------------------------

def print_header():
    print("="*48)
    print(" WomenSafetyRoute — CLI (Person 4)".center(48))
    print("="*48)

def prompt_menu():
    print("\nMenu:")
    print("1) List nodes")
    print("2) List sample edges (from a node)")
    print("3) Set start and destination")
    print("4) Set mode & time")
    print("5) Add include node (force pass-through)")
    print("6) Add avoid node")
    print("7) Clear include / avoid lists")
    print("8) Find top-3 routes")
    print("9) Reload graph from data files")
    print("0) Quit")
    return input("Choose an option: ").strip()

def cli_main():
    print_header()
    print("Loading graph from graph_loader.load_graph() ...")
    try:
        graph = graph_loader.load_graph()
    except Exception as e:
        print("ERROR loading graph:", e)
        sys.exit(1)

    start = None
    end = None
    mode = "walking"   # default preset
    time_str = datetime.datetime.now().strftime("%H:%M")  # default current time (HH:MM)
    include_nodes = []
    avoid_nodes = []

    while True:
        print(f"\nCurrent -> start: {start} | end: {end} | mode: {mode} | time: {time_str}")
        print(f"Include nodes: {include_nodes} | Avoid nodes: {avoid_nodes}")
        choice = prompt_menu()

        if choice == "1":
            nodes = sorted(list(graph.keys()))
            print(f"\nNodes ({len(nodes)}):")
            for n in nodes[:200]:
                print(" -", n)
            if len(nodes) > 200:
                print(f"... (and {len(nodes)-200} more)")

        elif choice == "2":
            n = input("Enter node id to list outgoing edges from: ").strip()
            if n not in graph:
                print("Node not found.")
            else:
                print(f"Outgoing edges from {n}:")
                for e in graph[n]:
                    to = e["to"]
                    attrs = e.get("attrs", {})
                    print(f" -> {to} | attrs:", attrs)

        elif choice == "3":
            start = input("Start node: ").strip()
            end = input("Destination node: ").strip()
            if start not in graph:
                print("Warning: start node not in graph.")
            if end not in graph:
                print("Warning: end node not in graph.")

        elif choice == "4":
            mode = input("Mode (walking/cycling/driving): ").strip().lower() or mode
            time_str = input("Time (HH:MM, e.g. 21:30) or press Enter for now: ").strip() or time_str
            # quick validation
            try:
                datetime.datetime.strptime(time_str, "%H:%M")
            except Exception:
                print("Invalid time format. Reverting to current time.")
                time_str = datetime.datetime.now().strftime("%H:%M")

        elif choice == "5":
            n = input("Include node to force route through (enter node id): ").strip()
            if n:
                include_nodes.append(n)
                print("Added:", n)

        elif choice == "6":
            n = input("Avoid node (remove from graph for routing): ").strip()
            if n:
                avoid_nodes.append(n)
                print("Added avoid:", n)

        elif choice == "7":
            include_nodes.clear()
            avoid_nodes.clear()
            print("Cleared include and avoid lists.")

        elif choice == "8":
            if not start or not end:
                print("Please set start and destination first (menu option 3).")
                continue

            # Apply avoid nodes by creating a filtered copy
            working_graph = remove_nodes_from_graph(graph, set(avoid_nodes))

            # If include nodes are present, we force them by stitching subpaths.
            if include_nodes:
                print("Computing path that passes through include nodes (in order)...")
                paths = force_include_nodes_and_get_paths(working_graph, start, end, include_nodes, mode, time_str, k=3)
                if not paths:
                    print("No feasible path found with these include/avoid constraints.")
                    continue
                # else proceed using these paths (top candidates)
                # Build weights & attrs for the working graph for reporting
                weights_uv, edge_attrs_map = build_weights_from_graph(working_graph, mode, time_str)
            else:
                # Normal behavior: compute top-3 using pathfinder with weights
                weights_uv, edge_attrs_map = build_weights_from_graph(working_graph, mode, time_str)
                try:
                    paths = pathfinder.get_paths(working_graph, start, end, weights_uv, k=3)
                except TypeError:
                    # fallback if pathfinder expects (graph, start, end, weights) without k param
                    try:
                        paths = pathfinder.get_paths(working_graph, start, end, weights_uv)
                        if not isinstance(paths, list):
                            paths = [paths]
                        paths = paths[:3]
                    except Exception as e:
                        print("Error calling pathfinder.get_paths:", e)
                        continue
                except Exception as e:
                    print("Error computing paths:", e)
                    continue

            if not paths:
                print("No paths found.")
                continue

            # Report the candidate paths and their breakdowns
            print("\nTop routes found:")
            for idx, p in enumerate(paths, start=1):
                totals, per_attr = compute_path_breakdown(p, edge_attrs_map, weights_uv)
                print("-"*40)
                print(f"Route {idx}: {' -> '.join(p)}")
                print(f"  Distance: {totals['distance']:.2f} units")
                print(f"  Safety score (lower better): {totals['safety_weight']:.3f}")
                # print top per-attributes (sort by magnitude)
                if per_attr:
                    print("  Attributes breakdown (sum):")
                    # show most meaningful entries: crime, lighting, traffic, accidents if present
                    for k in sorted(per_attr.keys()):
                        print(f"    {k}: {per_attr[k]:.3f}")
                else:
                    print("  (No additional numeric edge attributes found)")
            print("-"*40)

        elif choice == "9":
            print("Reloading graph from data files...")
            try:
                graph = graph_loader.load_graph()
                print("Reloaded.")
            except Exception as e:
                print("Failed to reload graph:", e)

        elif choice == "0":
            print("Exiting. Bye!")
            break

        else:
            print("Unknown choice — try again.")


if __name__ == "__main__":
    cli_main()
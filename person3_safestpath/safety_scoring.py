from copy import deepcopy

# ---------------------------
# Configuration: caps & presets
# ---------------------------
DEFAULT_CAPS = {
    "distance_cap": 10000.0,   # meters
    "police_cap": 2000.0,      # meters
    "accidents_cap": 10.0      # count
}

# Preset coefficients per transport mode (relative importances).
# Keys: distance, lighting, CCTV, crime, traffic, crowd, accidents, stray, roadcond, police
PRESET_COEFFS = {
    "walking": {
        "distance": 0.12,
        "lighting": 0.18,
        "CCTV": 0.12,
        "crime": 0.25,
        "traffic": 0.03,
        "crowd": 0.12,
        "accidents": 0.03,
        "stray": 0.08,
        "roadcond": 0.05,
        "police": 0.02
    },
    "two_wheeler": {
        "distance": 0.12,
        "lighting": 0.13,
        "CCTV": 0.06,
        "crime": 0.18,
        "traffic": 0.18,
        "crowd": 0.04,
        "accidents": 0.14,
        "stray": 0.05,
        "roadcond": 0.06,
        "police": 0.04
    },
    "car": {
        "distance": 0.15,
        "lighting": 0.08,
        "CCTV": 0.04,
        "crime": 0.08,
        "traffic": 0.30,
        "crowd": 0.02,
        "accidents": 0.20,
        "stray": 0.00,
        "roadcond": 0.10,
        "police": 0.03
    }
}

# Time-of-day multipliers for certain factors
TIME_MULTIPLIERS = {
    "morning": {"crime": 0.8, "lighting": 0.9, "traffic": 1.3, "police": 1.0},
    "day":     {"crime": 1.0, "lighting": 1.0, "traffic": 1.0, "police": 1.0},
    "evening": {"crime": 1.3, "lighting": 1.8, "traffic": 0.9, "police": 1.0},
    "night":   {"crime": 1.8, "lighting": 2.5, "traffic": 0.6, "police": 1.2}
}

# ---------------------------
# Internal helpers
# ---------------------------
def safe_get(d, *keys, default=None):
    """Return first existing key in dict d or default."""
    if d is None:
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def normalisation(attrs, caps=None):
    """
    Normalize attribute dictionary (flat attr names) to 0..1.
    Expected input keys (if present): distance_m, lighting, CCTV, crime,
      crowd_density, traffic_density, accidents_reported, stray_animals,
      road_condition, nearest_police_m
    Returns dict of normalized values.
    """
    caps = caps or DEFAULT_CAPS
    res = {}

    dist = float(safe_get(attrs, "distance_m", "distance", 0.0))
    res["dist_norm"] = min(max(dist, 0.0), caps["distance_cap"]) / caps["distance_cap"]

    lighting = float(safe_get(attrs, "lighting", 5.0))
    res["lighting_norm"] = min(max(lighting, 0.0), 10.0) / 10.0

    cctv_raw = safe_get(attrs, "CCTV", "cctv", 0)
    # interpret small ints 0/1 or scale 0-10
    try:
        cctv_raw = float(cctv_raw)
    except Exception:
        cctv_raw = 0.0
    if cctv_raw <= 1.0:
        res["cctv_norm"] = max(0.0, min(cctv_raw, 1.0))
    else:
        res["cctv_norm"] = max(0.0, min(cctv_raw, 10.0)) / 10.0

    crime = float(safe_get(attrs, "crime", 0.0))
    res["crime_norm"] = min(max(crime, 0.0), 10.0) / 10.0

    traffic = float(safe_get(attrs, "traffic_density", "traffic", 0.0))
    res["traffic_norm"] = min(max(traffic, 0.0), 10.0) / 10.0

    crowd = float(safe_get(attrs, "crowd_density", "crowd", 0.0))
    res["crowd_norm"] = min(max(crowd, 0.0), 10.0) / 10.0

    acc = float(safe_get(attrs, "accidents_reported", "accidents", 0.0))
    res["acc_norm"] = min(max(acc, 0.0), caps["accidents_cap"]) / caps["accidents_cap"]

    stray = float(safe_get(attrs, "stray_animals", 0.0))
    res["stray_norm"] = min(max(stray, 0.0), 10.0) / 10.0

    roadcond = float(safe_get(attrs, "road_condition", 7.0))
    res["roadcond_norm"] = min(max(roadcond, 0.0), 10.0) / 10.0

    police_m = float(safe_get(attrs, "nearest_police_m", "nearest_police_distance_m", caps["police_cap"]))
    res["police_norm"] = 1.0 - min(max(police_m, 0.0), caps["police_cap"]) / caps["police_cap"]

    return res

def crowd_risk(crowd_norm):
    """Map crowd_norm (0..1) to risk (0..1): low crowd -> high risk; moderate -> low risk; huge crowd -> moderate risk."""
    if crowd_norm < 0.2:
        return 1.0
    if crowd_norm < 0.5:
        return 0.2
    if crowd_norm < 0.85:
        return 0.35
    return 0.7

# ---------------------------
# Core computation
# ---------------------------
def calc_edgeW(attrs,
                        mode="walking",
                        time_of_day="day",
                        caps=None,
                        verbose=False):
    """
    Compute safety weight (0..1, higher = more unsafe) for a flat attributes dict.
    attrs: dictionary with (optional) keys used in normalisation
    mode: 'walking', 'two_wheeler', 'car'
    time_of_day: 'morning', 'day', 'evening', 'night'
    """
    caps = caps or DEFAULT_CAPS
    mode = mode if mode in PRESET_COEFFS else "walking"
    time_of_day = time_of_day if time_of_day in TIME_MULTIPLIERS else "day"

    norms = normalisation(attrs, caps=caps)
    crowd_risk_val = crowd_risk(norms["crowd_norm"])

    # copy preset coeffs and apply time multipliers
    coeffs = deepcopy(PRESET_COEFFS[mode])
    time_mult = TIME_MULTIPLIERS.get(time_of_day, {})
    for key, mult in time_mult.items():
        if key in coeffs:
            coeffs[key] *= mult

    # normalize coefficients to sum to 1 (absolute to avoid sign issues)
    total = sum(abs(v) for v in coeffs.values())
    if total <= 0:
        # fallback uniform
        n = len(coeffs)
        coeffs = {k: 1.0/n for k in coeffs}
    else:
        coeffs = {k: v/total for k, v in coeffs.items()}

    # combine into a raw risk (0..1)
    raw = 0.0
    raw += coeffs.get("distance", 0.0) * norms["dist_norm"]
    raw += coeffs.get("lighting", 0.0) * (1.0 - norms["lighting_norm"])  # poor lighting increases risk
    raw += coeffs.get("CCTV", 0.0) * (1.0 - norms["cctv_norm"])          # no CCTV increases risk
    raw += coeffs.get("crime", 0.0) * norms["crime_norm"]
    raw += coeffs.get("traffic", 0.0) * norms["traffic_norm"]
    raw += coeffs.get("crowd", 0.0) * crowd_risk_val
    raw += coeffs.get("accidents", 0.0) * norms["acc_norm"]
    raw += coeffs.get("stray", 0.0) * norms["stray_norm"]
    raw += coeffs.get("roadcond", 0.0) * (1.0 - norms["roadcond_norm"])   # bad road = risk
    raw += coeffs.get("police", 0.0) * (1.0 - norms["police_norm"])       # far police increases risk

    # clamp
    weight = float(max(0.0, min(raw, 1.0)))

    if verbose:
        debug = {
            "norms": norms,
            "crowd_risk": crowd_risk_val,
            "coeffs_norm": coeffs,
            "raw": raw,
            "weight": weight
        }
        return weight, debug
    return weight

# ---------------------------
# JSON wrapper: use your 'modes->mode->time' structure
# ---------------------------
def calc_edgeW_from_json(edge_json, mode="walking", time_of_day="day", caps=None, verbose=False):
    """
    edge_json expected structure:
    {
      "u": ...,
      "v": ...,
      "distance_m": ...,
      "modes": {
         "walking": { "day": {...}, "night": {...} },
         "car": { "day": {...}, ... },
         ...
      }
    }
    """
    caps = caps or DEFAULT_CAPS
    # defensive: if modes missing, fallback to flat attributes at edge_json level
    modes = edge_json.get("modes")
    base_attrs = {}
    if modes and isinstance(modes, dict):
        mode_block = modes.get(mode, {})
        time_block = mode_block.get(time_of_day, {})
        # merge distance + time_block
        base_attrs.update(time_block if isinstance(time_block, dict) else {})
    else:
        # fallback: try to take attributes directly from edge_json
        base_attrs.update(edge_json)

    # ensure distance present
    if "distance_m" not in base_attrs and "distance" in edge_json:
        base_attrs["distance_m"] = edge_json.get("distance")
    elif "distance_m" not in base_attrs:
        base_attrs["distance_m"] = edge_json.get("distance_m", 0.0)

    # call flat compute
    return calc_edgeW(base_attrs, mode=mode, time_of_day=time_of_day, caps=caps, verbose=verbose)

# ---------------------------
# NetworkX helper and batch functions
# ---------------------------
def calc_edgeW_from_netGX(G, mode="walking", time_of_day="day", caps=None, distance_key="distance_m", set_attr_name="safety_weight"):
    """
    Compute safety weight for all edges in a networkx Graph G and set attribute
    G[u][v][set_attr_name] = weight.
    This expects edge data to be a dict that either:
      - contains 'modes' structure for mode/time OR
      - contains flat attributes directly (lighting, crime, etc.)
    """
    try:
        import networkx as nx
    except ImportError:
        raise ImportError("networkx required for this helper")

    caps = caps or DEFAULT_CAPS
    for u, v, data in G.edges(data=True):
        # data might be the 'edge_json' or flat attrs
        try:
            # if it has 'modes' key it's likely the edge_json format
            if "modes" in data:
                w = calc_edgeW_from_json(data, mode=mode, time_of_day=time_of_day, caps=caps)
            else:
                # flatten: copy data and ensure distance key naming
                flat = dict(data)
                if distance_key in data and "distance_m" not in flat:
                    flat["distance_m"] = data[distance_key]
                w = calc_edgeW(flat, mode=mode, time_of_day=time_of_day, caps=caps)
        except Exception:
            # fallback: safe default
            w = 1.0
        G[u][v][set_attr_name] = w
    return G

def calc_all_edges_fromL(edges_list, mode="walking", time_of_day="day", caps=None):
    """
    edges_list: list of edge_json dicts (as loaded from edges.json)
    returns: list of tuples (index, edge_id_or_uv, weight)
    """
    caps = caps or DEFAULT_CAPS
    out = []
    for i, e in enumerate(edges_list):
        w = calc_edgeW_from_json(e, mode=mode, time_of_day=time_of_day, caps=caps)
        out.append((i, (e.get("u", e.get("source_id")), e.get("v", e.get("target_id"))), w))
    return out

# ---------------------------
# Path scoring helper
# ---------------------------
def calc_path_safety(graph_like, path, weight_attr="safety_weight", distance_attr="distance_m"):
    """
    Compute total safety weight (sum) and total distance for a given path (list of nodes).
    graph_like can be networkx.Graph or adjacency dict {u: {v: {attrs}}}.
    Returns: (total_weight, total_distance, per_edge_list)
      where per_edge_list = [(u,v, attrs, weight, distance), ...]
    """
    total_w = 0.0
    total_d = 0.0
    per = []
    # try networkx detection
    is_nx = False
    try:
        import networkx as nx
        is_nx = isinstance(graph_like, nx.Graph)
    except Exception:
        is_nx = False

    for a, b in zip(path[:-1], path[1:]):
        attrs = None
        if is_nx:
            if graph_like.has_edge(a, b):
                attrs = graph_like[a][b]
        else:
            # adjacency dict
            if isinstance(graph_like, dict) and a in graph_like and b in graph_like[a]:
                attrs = graph_like[a][b]

        if attrs is None:
            raise KeyError(f"Edge ({a},{b}) not found in graph for path safety compute")

        w = attrs.get(weight_attr)
        if w is None:
            # compute on the fly from attrs (best effort)
            w = calc_edgeW(attrs)

        d = attrs.get(distance_attr) or attrs.get("distance") or attrs.get("distance_m") or 0.0
        total_w += float(w)
        total_d += float(d)
        per.append((a, b, attrs, float(w), float(d)))
    return total_w, total_d, per

# ---------------------------
# Quick demonstration / self-test
# ---------------------------
if __name__ == "__main__":
    # small demo edge JSON (walking/night)
    demo_edge = {
        "u": "A", "v": "B", "distance_m": 400,
        "modes": {
            "walking": {
                "day": {
                    "crime": 3, "crowd_density": 6, "stray_animals": 2,
                    "nearest_police_m": 200, "shops_visibility": 7, "cctv": 1
                },
                "night": {
                    "lighting": 2, "crime": 8, "crowd_density": 1,
                    "stray_animals": 6, "nearest_police_m": 200,
                    "shops_visibility": 4, "cctv": 0
                }
            },
            "car": {
                "day": {"traffic_density": 8, "accidents_reported": 1, "crime": 2, "cctv": 1, "road_condition": 8},
                "night": {"traffic_density": 2, "accidents_reported": 3, "lighting": 4, "crime": 6, "cctv": 0, "road_condition": 7}
            }
        }
    }

    print("Demo weights for demo_edge:")
    w_walking_night, dbg = calc_edgeW_from_json(demo_edge, mode="walking", time_of_day="night", verbose=True)
    print("walking/night weight:", w_walking_night)
    print("debug:", dbg)

    w_car_day = calc_edgeW_from_json(demo_edge, mode="car", time_of_day="day")
    print("car/day weight:", w_car_day)

    # show batch example
    edges_list = [demo_edge]
    print("Batch compute:", calc_all_edges_fromL(edges_list, mode="walking", time_of_day="night"))

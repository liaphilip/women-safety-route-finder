# safety_scoring.py
# Phase 3: Weight Calculation

from typing import Tuple, Dict
import copy

# Set some max values for normalization
DIST_CAP = 2000.0
POLICE_CAP = 1500.0

def clamp01(x: float) -> float:
    try:
        val = float(x)
        if val < 0.0:
            return 0.0
        if val > 1.0:
            return 1.0
        return val
    except:
        return 0.0 # if it's not a number, just return 0


def _u_shaped_crowd(crowd01: float) -> float:
    # U-shaped risk for crowds (0..1, higher is worse)
    # 0.2 (empty) -> 1.0 (bad)
    # 0.5 (medium) -> 0.2 (good)
    # 0.9 (full) -> 0.7 (bad)
    if crowd01 < 0.2: return 1.0 # too empty
    if crowd01 < 0.5: return 0.2 # just right
    if crowd01 < 0.8: return 0.5 # a bit crowded
    return 0.7 # too crowded

# These are the magic nos for scoring
# mode coefficients (presets)
MODE_PRESETS = {
    "walking": {
        "crime": 2.5, "lighting": 2.2, "cctv": 1.6, "crowd_density": 1.6,
        "stray_animals": 1.2, "nearest_police_m": 1.2, "sidewalk": 1.8,
        "shops_visibility": 1.4, "road_condition": 0.8,
        "traffic_density": 0.6, "accidents_reported": 0.6, "traffic_behavior": 0.8,
        "parking_safety": 0.3
    },
    "two_wheeler": {
        "crime": 1.5, "lighting": 1.4, "cctv": 1.0, "crowd_density": 0.9,
        "stray_animals": 1.0, "nearest_police_m": 0.8, "sidewalk": 0.2,
        "shops_visibility": 0.6, "road_condition": 1.6,
        "traffic_density": 1.7, "accidents_reported": 1.8, "traffic_behavior": 1.9,
        "parking_safety": 0.2
    },
    "car": {
        "crime": 0.8, "lighting": 0.9, "cctv": 0.5, "crowd_density": 0.5,
        "stray_animals": 0.6, "nearest_police_m": 0.5, "sidewalk": 0.1,
        "shops_visibility": 0.3, "road_condition": 1.8,
        "traffic_density": 2.0, "accidents_reported": 2.3, "traffic_behavior": 2.2,
        "parking_safety": 1.2
    }
}

# Multipliers for day vs night
TIME_MULTS = {
    "day":   {"crime": 0.9, "lighting": 0.8, "traffic_density": 1.1},
    "night": {"crime": 1.8, "lighting": 2.5, "traffic_density": 0.8}
}

def _to01(val, scale=10.0) -> float:
    # convert a 0-10 score to 0-1
    try:
        return clamp01(float(val) / float(scale))
    except Exception:
        return 0.0

def _get_mode_key(mode: str) -> str:
    # make sure mode is one of the 3 keys
    m = (mode or "walking").lower()
    if m in ("car","two_wheeler","walking"):
        return m
    if m in ("driving",): return "car"
    if m in ("bike","bicycle","two-wheeler"): return "two_wheeler"
    return "walking" # default

def compute_edge_weight(edge: dict, mode: str, time_of_day: str, custom_weights: Dict[str, float]=None) -> Tuple[float, Dict]:

    mode_key = _get_mode_key(mode)
    time_slot = time_of_day if time_of_day in TIME_MULTS else ("night" if time_of_day=="night" else "day")

    # copy coeffs so we don't modify global presets
    coeffs = copy.deepcopy(MODE_PRESETS[mode_key])

    # apply custom weights from user
    if custom_weights:
        for k, v in custom_weights.items():
            try:
                if isinstance(v, (list, tuple)) and len(v) == 2 and str(v[0]).lower() == "mul":
                    # this handles the ("mul", 1.5) case, which is a bit complex but leaving it
                    coeffs[k] = coeffs.get(k, 0.0) * float(v[1])
                else:
                    # this just overwrites the base coefficient
                    coeffs[k] = float(v)
            except Exception:
                # ignore malformed override entries
                pass

    # distance normalisation
    dist_m = float(edge.get("distance_m", 0.0))
    dist01 = clamp01(dist_m / DIST_CAP)

    # get attribute block safely
    block = {}
    try:
        block = edge.get("modes", {}).get(mode_key, {}).get(time_slot, {})
    except Exception:
        block = {} # just use empty if anything goes wrong

    # get all attributes from the JSON data, default to 0
    crime = _to01(block.get("crime", 0))
    lighting = _to01(block.get("lighting", 0))
    cctv = 1.0 if block.get("cctv", 0) else 0.0 # 1 or 0
    crowd = _to01(block.get("crowd_density", block.get("crowd", 0)))
    traffic = _to01(block.get("traffic_density", 0))
    accidents = _to01(block.get("accidents_reported", 0))
    road_cond = _to01(block.get("road_condition", 0))
    # handle typos in data
    stray = _to01(block.get("stray_animals", block.get("stray_animice", 0))) 
    nearest_police = float(block.get("nearest_police_m", edge.get("nearest_police_m", POLICE_CAP)))
    sidewalk = 1.0 if block.get("sidewalk", 0) else 0.0 # 1 or 0
    shops = _to01(block.get("shops_visibility", 0))
    traffic_behavior = _to01(block.get("traffic_behavior", 0))
    parking_safety = _to01(block.get("parking_safety", 0))

    # convert to risk metrics (0..1 where higher = worse)
    # e.g. for lighting, 10/10 is good (0.0 risk), 0/10 is bad (1.0 risk)
    risks = {
        "crime": crime,
        "lighting": 1.0 - lighting,
        "cctv": 1.0 - cctv,
        "crowd_density": _u_shaped_crowd(crowd),
        "traffic_density": traffic,
        "accidents_reported": accidents,
        "road_condition": 1.0 - road_cond,
        "stray_animals": stray,
        "nearest_police_m": 1.0 - clamp01(min(nearest_police, POLICE_CAP) / POLICE_CAP), # flip it
        "sidewalk": 1.0 - sidewalk,
        "shops_visibility": 1.0 - shops,
        "traffic_behavior": traffic_behavior,
        "parking_safety": 1.0 - parking_safety
    }

    tms = TIME_MULTS[time_slot]

    total = 0.0
    breakdown = {}
    for feat, risk in risks.items():
        coeff = coeffs.get(feat, 0.0) # get the coefficient from our presets
        tm = 1.0 # time multiplier
        if feat in ("crime", "lighting", "traffic_density"):
            tm = tms.get(feat, 1.0)
        
        contrib = risk * coeff * tm
        
        
        breakdown[feat] = {"risk": round(risk,3), "coeff": coeff, "time_mult": tm, "contrib": round(contrib,4)}
        total += contrib

    # small distance penalty to discourage long detours.
    total += 0.5 * dist01
    breakdown["distance_penalty"] = {"risk": round(dist01,3), "coeff": 0.5, "time_mult":1.0, "contrib": round(0.5*dist01,4)}



    return round(total,6), breakdown

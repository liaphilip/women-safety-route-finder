
Person 3 — Safety Scoring Module
--------------------------------
Functions:
- compute_edge_weight_from_json(edge_json, mode='walking', time_of_day='day', caps=None, verbose=False)
    -> computes safety weight (0..1) for an edge described in your JSON format (with 'modes').
- compute_edge_weight(attrs_dict, mode='walking', time_of_day='day', caps=None, verbose=False)
    -> computes safety weight (0..1) for a flat dict of attributes (normalized helpers).
- compute_all_edge_weights_networkx(G, mode='walking', time_of_day='day', caps=None, distance_key='distance_m')
    -> sets G[u][v]['safety_weight'] for each edge in a networkx.Graph
- compute_all_edge_weights_from_edges_list(edges_list, mode='walking', time_of_day='day', caps=None)
    -> returns list of (edge_idx, weight)
- compute_path_safety(graph_like, path, weight_attr='safety_weight', distance_attr='distance_m')
    -> returns (total_weight, total_distance, per_edge_details)

Design notes:
- Weight is normalized to [0,1] (1 = most unsafe).
- Mode presets and time multipliers are adjustable.

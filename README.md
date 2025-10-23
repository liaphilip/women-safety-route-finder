# Safety Route Finder

A route planning system that prioritizes safety of many individuals by considering multiple safety factors along with traditional routing metrics like distance and travel time.

## * Features

- **Multi-Factor Safety Analysis**: Evaluates routes based on lighting, CCTV coverage, crowd density, crime rates, and more
- **Multiple Transport Modes**: Optimized routing for walking, two-wheeler, and car travel
- **Time-Of- The-Day Routing**:safety calculations for day vs. night travel
- **Flexible Route Options**: 
  - Shortest distance route
  - Safest route
  - Balanced routes (safety + efficiency)
- **Custom Safety Preferences**: Adjust importance weights for different safety factors
- **Constraint Support**: 
  - can avoid specific locations
  - can choose important attributes
  - can proritize specific routes 
- **Visual Route Display**: Interactive graph visualization with matplotlib

## * Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/women-safety-router.git
cd women-safety-router

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
#insatll matplotlib for visualization
pip install matplotlib
```

### Basic Usage

```bash
python -m src.ui.cli
```

Follow the interactive prompts to:
1. Select start and destination points
2. Choose transportation mode
3. Set time of day (auto-detected)
4. Optionally customize safety preferences
5. Review and select from multiple route options

### Example Session

```
Available locations:
  1. Crossroad A  (id: A)
  2. Park Entrance  (id: B)
  3. Mall Entrance  (id: C)
  ...

Where are you starting from? B
Where would you like to go? J
How will you travel?
  1. walking
  2. two_wheeler
  3. car
Choose (number): 1

--- Suggested routes for you ---

Quickest option
  Route: B → D → E → F → J
  Distance: 1620 m   •   Est. travel time: 19 min (walking)
  Safety summary: moderately safe  (score: 8.234)

Safest option
  Route: B → A → ... → J
  Distance: 2100 m   •   Est. travel time: 25 min (walking)
  Safety summary: safer  (score: 4.127)
```

## * How It Works

### Safety Scoring System

Each route segment (edge) is evaluated based on:

**For Walking:**
- Crime rate (high priority)
- Street lighting quality
- CCTV presence
- Crowd density (U-shaped: avoid both empty and overcrowded)
- Proximity to police stations
- Sidewalk availability
- Shop visibility
- Stray animal presence

**For Two-Wheeler:**
- Road condition (high priority)
- Traffic density and behavior
- Accident history
- Plus selected walking factors

**For Car:**
- Traffic conditions (highest priority)
- Parking safety
- Road condition
- Reduced emphasis on pedestrian factors

### *Algorithm

1. **Graph Construction**: Locations (nodes) and paths (edges) with safety attributes
2. **Weight Calculation**: Multi-factor safety score for each edge based on mode and time
3. **Path Finding**: 
   - Dijkstra's algorithm for single optimal path
   - Yen's K-shortest paths for alternatives
4. **Route Presentation**: User-friendly display with distance, time, and safety metrics

### *Project Structure
```text
RouteSafetyFinder/
│
├── main.py                # Main program (CLI)
├── graph_loader.py        # Loads nodes and edges into adjacency list
├── pathfinder.py          # Dijkstra’s and Yen’s K-shortest path algorithms
├── safety_scoring.py      # Computes safety weights for each road segment
│
├── data/
│   ├── nodes.json         # Node data (locations)
│   ├── edges.json         # Edge data (distances, safety attributes)
│
└── README.md              # Documentation
```
## * Configuration

### Custom Safety Weights

You can adjust the importance of each safety factor (0.0 to 1.0 scale):

```
Set importance for each factor:
  Crime (preset coeff 2.50) => enter 0.0-1.0: 0.8
  Lighting (preset coeff 2.20) => enter 0.0-1.0: 1.0
  CCTV coverage (preset coeff 1.60) => enter 0.0-1.0: 0.6
  ...
```

### Dynamic Updates

Create `data/dynamic.json` to override safety attributes in real-time:

```json
{
  "edges": {
    "A-B": {
      "cctv": 0,
      "lighting": 3,
      "crime": 5
    }
  }
}
```

## * Data Format

### Nodes (data/nodes.json)
```json
[
  {"id": "A", "name": "Crossroad A"},
  {"id": "B", "name": "Park Entrance"}
]
```

### Edges (data/edges.json)
```json
[
  {
    "id": "A-B",
    "u": "A",
    "v": "B",
    "distance_m": 320,
    "modes": {
      "walking": {
        "day": {
          "crime": 2,
          "crowd_density": 3,
          "cctv": 1,
          "lighting": 7
        },
        "night": {
          "crime": 4,
          "lighting": 3,
          "crowd_density": 1
        }
      }
    }
  }
]
```

## * Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test module
python -m pytest tests/test_pathfinder.py

# Run with coverage
python -m pytest --cov=src tests/
```

## * Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## * Requirements

- Python 3.8+
- matplotlib (for visualization)
- networkx (for graph plotting)

See `requirements.txt` for complete list.

## * Future Enhancements

- [ ] Web-based UI
- [ ] Mobile app integration
- [ ] Real-time data integration (crime reports, traffic)
- [ ] Machine learning for safety prediction
- [ ] Community-sourced safety ratings
- [ ] Integration with mapping services
- [ ] Multi-language support
- [ ] Accessibility features


## * Acknowledgments

- Inspired by the need for safer navigation options for women and many 
- Built as part of [Datastructure/Safetey-route-finder]


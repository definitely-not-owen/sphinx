"""
Analyze when each planet is optimal based on experiment data.
Helps identify optimal switching points including Planet 1.
"""
import json
from typing import Dict, List, Tuple


def load_planet_data(data_files: Dict[int, str]) -> Dict[int, Dict[int, float]]:
    """Load survival rates for each planet at each trip number."""
    planet_data = {}
    for planet, filename in data_files.items():
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                planet_data[planet] = {
                    trip['step_number']: trip['survival_rate']
                    for trip in data['trips']
                }
        except FileNotFoundError:
            print(f"Warning: Could not load {filename}")
            return {}
    return planet_data


def find_optimal_planet_at_each_trip(planet_data: Dict[int, Dict[int, float]]) -> Dict[int, int]:
    """
    Find which planet is optimal at each trip number.
    
    Returns:
        Dictionary mapping trip_number -> best_planet
    """
    optimal_strategy = {}
    
    # Find max trip number across all planets
    max_trip = max(
        max(trips.keys()) if trips else 0
        for trips in planet_data.values()
    )
    
    # For each trip, find the planet with highest survival rate
    for trip_num in range(1, max_trip + 1):
        best_planet = 0
        best_rate = planet_data[0].get(trip_num, 0)
        
        for planet in [1, 2]:
            rate = planet_data[planet].get(trip_num, 0)
            if rate > best_rate:
                best_rate = rate
                best_planet = planet
        
        optimal_strategy[trip_num] = best_planet
    
    return optimal_strategy


def analyze_planet_usage(optimal_strategy: Dict[int, int]) -> Dict:
    """Analyze how often each planet is used in optimal strategy."""
    usage = {0: 0, 1: 0, 2: 0}
    transitions = []
    
    prev_planet = None
    for trip_num in sorted(optimal_strategy.keys()):
        planet = optimal_strategy[trip_num]
        usage[planet] += 1
        
        if prev_planet is not None and planet != prev_planet:
            transitions.append((trip_num, prev_planet, planet))
        
        prev_planet = planet
    
    return {
        "usage": usage,
        "transitions": transitions,
        "total_trips": len(optimal_strategy),
    }


def print_optimal_analysis(planet_data: Dict[int, Dict[int, float]]):
    """Print analysis of optimal planet selection."""
    optimal_strategy = find_optimal_planet_at_each_trip(planet_data)
    analysis = analyze_planet_usage(optimal_strategy)
    
    print("="*60)
    print("OPTIMAL PLANET ANALYSIS")
    print("="*60)
    
    print("\nPlanet Usage:")
    planet_names = ["On a Cob Planet", "Cronenberg World", "The Purge Planet"]
    for planet in [0, 1, 2]:
        count = analysis["usage"][planet]
        percentage = (count / analysis["total_trips"]) * 100
        print(f"  Planet {planet} ({planet_names[planet]}): {count} trips ({percentage:.1f}%)")
    
    print("\nKey Transitions:")
    for trip_num, from_planet, to_planet in analysis["transitions"][:10]:  # Show first 10
        print(f"  Trip {trip_num}: Planet {from_planet} -> Planet {to_planet}")
    
    if len(analysis["transitions"]) > 10:
        print(f"  ... and {len(analysis['transitions']) - 10} more transitions")
    
    # Find ranges where each planet dominates
    print("\nPlanet Dominance Ranges:")
    current_planet = optimal_strategy[1]
    start_trip = 1
    
    ranges = []
    for trip_num in sorted(optimal_strategy.keys()):
        planet = optimal_strategy[trip_num]
        if planet != current_planet:
            ranges.append((start_trip, trip_num - 1, current_planet))
            start_trip = trip_num
            current_planet = planet
    
    # Add final range
    ranges.append((start_trip, max(optimal_strategy.keys()), current_planet))
    
    for start, end, planet in ranges:
        print(f"  Trips {start}-{end}: Planet {planet} ({planet_names[planet]})")
    
    return optimal_strategy


if __name__ == "__main__":
    data_files = {
        0: "data/planet_0_count_3_20251115_164620.json",
        1: "data/planet_1_count_3_20251115_164753.json",
        2: "data/planet_2_count_3_20251115_164927.json",
    }
    
    planet_data = load_planet_data(data_files)
    if planet_data:
        optimal_strategy = print_optimal_analysis(planet_data)
        
        # Save optimal strategy
        output_file = "data/optimal_strategy.json"
        with open(output_file, 'w') as f:
            json.dump(optimal_strategy, f, indent=2)
        print(f"\nOptimal strategy saved to: {output_file}")


"""
Analysis script for Morty Express Challenge data.
Processes collected experiment data and visualizes survival rate patterns.
"""
import json
import os
import glob
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np


def load_experiment_data(filename: str) -> Dict:
    """Load experiment data from JSON file."""
    with open(filename, "r") as f:
        return json.load(f)


def find_latest_experiments() -> Dict[int, str]:
    """
    Find the latest experiment files for each planet.
    
    Returns:
        Dictionary mapping planet number to filename
    """
    planet_files = {0: None, 1: None, 2: None}
    
    # Find all experiment files
    pattern = "data/planet_*_count_*.json"
    files = glob.glob(pattern)
    
    # Group by planet and find latest
    for planet in [0, 1, 2]:
        planet_pattern = f"data/planet_{planet}_count_*.json"
        planet_files_list = glob.glob(planet_pattern)
        if planet_files_list:
            # Sort by modification time, get latest
            planet_files_list.sort(key=os.path.getmtime, reverse=True)
            planet_files[planet] = planet_files_list[0]
    
    return planet_files


def calculate_survival_trends(trips_data: List[Dict]) -> Tuple[List[int], List[float]]:
    """
    Extract survival rate trends over time.
    
    Returns:
        Tuple of (step_numbers, survival_rates)
    """
    step_numbers = [trip["step_number"] for trip in trips_data]
    survival_rates = [trip["survival_rate"] for trip in trips_data]
    return step_numbers, survival_rates


def calculate_moving_average(values: List[float], window: int = 10) -> List[float]:
    """Calculate moving average to smooth out noise."""
    if len(values) < window:
        return values
    
    smoothed = []
    for i in range(len(values)):
        start = max(0, i - window // 2)
        end = min(len(values), i + window // 2 + 1)
        smoothed.append(np.mean(values[start:end]))
    return smoothed


def analyze_planet_patterns(trips_data: List[Dict]) -> Dict:
    """
    Analyze patterns in planet survival data.
    
    Returns:
        Dictionary with analysis results
    """
    if not trips_data:
        return {}
    
    step_numbers, survival_rates = calculate_survival_trends(trips_data)
    
    # Calculate rate of change
    if len(survival_rates) > 1:
        # Calculate derivative (rate of change)
        rate_of_change = np.diff(survival_rates)
        avg_rate_of_change = np.mean(rate_of_change)
        
        # Check if trend is increasing, decreasing, or stable
        if avg_rate_of_change > 0.01:
            trend = "increasing"
        elif avg_rate_of_change < -0.01:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        rate_of_change = []
        avg_rate_of_change = 0
        trend = "insufficient_data"
    
    # Calculate variance (how much it fluctuates)
    variance = np.var(survival_rates) if survival_rates else 0
    
    # Final values
    initial_rate = survival_rates[0] if survival_rates else 0
    final_rate = survival_rates[-1] if survival_rates else 0
    total_change = final_rate - initial_rate
    
    return {
        "total_trips": len(trips_data),
        "initial_survival_rate": initial_rate,
        "final_survival_rate": final_rate,
        "total_change": total_change,
        "avg_rate_of_change": avg_rate_of_change,
        "trend": trend,
        "variance": variance,
        "step_numbers": step_numbers,
        "survival_rates": survival_rates,
    }


def visualize_comparison(experiment_files: Dict[int, str], output_file: str = "data/comparison.png"):
    """
    Visualize survival rates for all three planets on the same graph.
    
    Args:
        experiment_files: Dictionary mapping planet number to filename
        output_file: Output filename for the plot
    """
    plt.figure(figsize=(12, 8))
    
    planet_names = ["On a Cob Planet", "Cronenberg World", "The Purge Planet"]
    colors = ["#2ecc71", "#e74c3c", "#3498db"]
    
    for planet in [0, 1, 2]:
        if experiment_files[planet] and os.path.exists(experiment_files[planet]):
            data = load_experiment_data(experiment_files[planet])
            trips_data = data["trips"]
            
            step_numbers, survival_rates = calculate_survival_trends(trips_data)
            
            # Plot raw data
            plt.plot(
                step_numbers,
                survival_rates,
                label=f"Planet {planet} ({planet_names[planet]})",
                color=colors[planet],
                alpha=0.3,
                linewidth=1,
            )
            
            # Plot smoothed data
            smoothed = calculate_moving_average(survival_rates, window=20)
            plt.plot(
                step_numbers,
                smoothed,
                color=colors[planet],
                linewidth=2,
                alpha=0.8,
            )
        else:
            print(f"Warning: No data found for Planet {planet}")
    
    plt.xlabel("Trip Number (Steps Taken)", fontsize=12)
    plt.ylabel("Survival Rate (%)", fontsize=12)
    plt.title("Survival Rate Comparison Across Planets Over Time", fontsize=14, fontweight="bold")
    plt.legend(loc="best", fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig(output_file, dpi=150)
    print(f"\nComparison plot saved to: {output_file}")
    plt.close()


def visualize_individual_planets(experiment_files: Dict[int, str]):
    """Create individual plots for each planet."""
    planet_names = ["On a Cob Planet", "Cronenberg World", "The Purge Planet"]
    colors = ["#2ecc71", "#e74c3c", "#3498db"]
    
    for planet in [0, 1, 2]:
        if experiment_files[planet] and os.path.exists(experiment_files[planet]):
            data = load_experiment_data(experiment_files[planet])
            trips_data = data["trips"]
            
            step_numbers, survival_rates = calculate_survival_trends(trips_data)
            smoothed = calculate_moving_average(survival_rates, window=20)
            
            plt.figure(figsize=(10, 6))
            plt.plot(step_numbers, survival_rates, alpha=0.3, color=colors[planet], linewidth=1)
            plt.plot(step_numbers, smoothed, color=colors[planet], linewidth=2)
            plt.xlabel("Trip Number", fontsize=12)
            plt.ylabel("Survival Rate (%)", fontsize=12)
            plt.title(f"Planet {planet}: {planet_names[planet]}", fontsize=14, fontweight="bold")
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            output_file = f"data/planet_{planet}_analysis.png"
            plt.savefig(output_file, dpi=150)
            print(f"Planet {planet} plot saved to: {output_file}")
            plt.close()


def print_analysis_summary(analyses: Dict[int, Dict]):
    """Print summary of analysis results."""
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    
    planet_names = ["On a Cob Planet", "Cronenberg World", "The Purge Planet"]
    
    for planet in [0, 1, 2]:
        if planet in analyses and analyses[planet]:
            analysis = analyses[planet]
            print(f"\nPlanet {planet} ({planet_names[planet]}):")
            print(f"  Total Trips: {analysis['total_trips']}")
            print(f"  Initial Survival Rate: {analysis['initial_survival_rate']:.2f}%")
            print(f"  Final Survival Rate: {analysis['final_survival_rate']:.2f}%")
            print(f"  Total Change: {analysis['total_change']:+.2f}%")
            print(f"  Average Rate of Change: {analysis['avg_rate_of_change']:.4f}% per trip")
            print(f"  Trend: {analysis['trend']}")
            print(f"  Variance: {analysis['variance']:.2f}")
        else:
            print(f"\nPlanet {planet} ({planet_names[planet]}): No data available")
    
    # Compare which changes fastest
    print("\n" + "-"*60)
    print("COMPARISON:")
    print("-"*60)
    
    rates_of_change = {}
    for planet in [0, 1, 2]:
        if planet in analyses and analyses[planet]:
            rates_of_change[planet] = abs(analyses[planet]["avg_rate_of_change"])
    
    if rates_of_change:
        sorted_planets = sorted(rates_of_change.items(), key=lambda x: x[1], reverse=True)
        print("\nPlanets ranked by rate of change (fastest to slowest):")
        for i, (planet, rate) in enumerate(sorted_planets, 1):
            planet_name = planet_names[planet]
            print(f"  {i}. Planet {planet} ({planet_name}): {rate:.4f}% per trip")


def main():
    """Main analysis function."""
    print("="*60)
    print("MORTY EXPRESS - DATA ANALYSIS")
    print("="*60)
    
    # Find latest experiment files
    experiment_files = find_latest_experiments()
    
    print("\nFound experiment files:")
    planet_names = ["On a Cob Planet", "Cronenberg World", "The Purge Planet"]
    for planet in [0, 1, 2]:
        if experiment_files[planet]:
            print(f"  Planet {planet} ({planet_names[planet]}): {experiment_files[planet]}")
        else:
            print(f"  Planet {planet} ({planet_names[planet]}): No data found")
    
    # Analyze each planet
    analyses = {}
    for planet in [0, 1, 2]:
        if experiment_files[planet] and os.path.exists(experiment_files[planet]):
            data = load_experiment_data(experiment_files[planet])
            trips_data = data["trips"]
            analyses[planet] = analyze_planet_patterns(trips_data)
    
    # Print summary
    print_analysis_summary(analyses)
    
    # Create visualizations
    if any(experiment_files.values()):
        print("\n" + "="*60)
        print("GENERATING VISUALIZATIONS")
        print("="*60)
        
        visualize_comparison(experiment_files)
        visualize_individual_planets(experiment_files)
        
        print("\nAnalysis complete!")
    else:
        print("\nNo experiment data found. Run explore.py first.")


if __name__ == "__main__":
    main()


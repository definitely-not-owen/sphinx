"""
Benchmark script to test and compare different solution strategies.
Runs each strategy multiple times and tracks performance metrics.
"""
import json
import time
from datetime import datetime
from typing import Dict, List
from solve import (
    run_hybrid_control_strategy,
    run_hybrid_transition_enforcer_strategy,
    run_hybrid_planet2_priority_strategy,
    run_hybrid_schedule_phase_strategy,
)

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available, skipping visualization")


def run_strategy_benchmark(strategy_name: str, strategy_func, num_runs: int = 3) -> List[Dict]:
    """
    Run a strategy multiple times and collect performance data.
    
    Args:
        strategy_name: Name of the strategy
        strategy_func: Function to run the strategy
        num_runs: Number of times to run the strategy
    
    Returns:
        List of result dictionaries
    """
    print("\n" + "="*60)
    print(f"BENCHMARKING: {strategy_name}")
    print("="*60)
    
    results = []
    
    for run_num in range(1, num_runs + 1):
        print(f"\n--- Run {run_num}/{num_runs} ---")
        
        try:
            start_time = time.time()
            final_status = strategy_func()
            elapsed_time = time.time() - start_time
            
            survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
            
            # Extract mission log if available
            mission_log = final_status.get('mission_log', [])
            
            # Calculate planet usage statistics
            planet_usage = {0: 0, 1: 0, 2: 0}
            planet_successes = {0: 0, 1: 0, 2: 0}
            for mission in mission_log:
                planet = mission.get('planet', 0)
                planet_usage[planet] += 1
                if mission.get('survived', False):
                    planet_successes[planet] += 1
            
            result = {
                "strategy": strategy_name,
                "run_number": run_num,
                "timestamp": datetime.now().isoformat(),
                "survival_rate": survival_rate,
                "morties_saved": final_status['morties_on_planet_jessica'],
                "morties_lost": final_status['morties_lost'],
                "total_trips": final_status.get('steps_taken', 0),
                "elapsed_time_seconds": elapsed_time,
                "mission_log": mission_log,
                "planet_usage": planet_usage,
                "planet_successes": planet_successes,
            }
            
            results.append(result)
            
            print(f"Run {run_num} complete:")
            print(f"  Survival Rate: {survival_rate:.2f}%")
            print(f"  Morties Saved: {final_status['morties_on_planet_jessica']}")
            print(f"  Time: {elapsed_time:.1f}s")
            print(f"  Planet Usage: {planet_usage}")
            print(f"  Planet Successes: {planet_successes}")
            
            # Wait between runs to avoid rate limiting
            if run_num < num_runs:
                print("Waiting 3 seconds before next run...")
                time.sleep(3)
        
        except Exception as e:
            print(f"Error in run {run_num}: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "strategy": strategy_name,
                "run_number": run_num,
                "error": str(e),
            })
    
    return results


def calculate_statistics(results: List[Dict]) -> Dict:
    """
    Calculate statistics for a set of results.
    
    Args:
        results: List of result dictionaries
    
    Returns:
        Dictionary with statistics
    """
    if not results:
        return {}
    
    # Filter out errors
    valid_results = [r for r in results if "error" not in r]
    
    if not valid_results:
        return {"error": "No valid results"}
    
    import statistics
    
    survival_rates = [r["survival_rate"] for r in valid_results]
    morties_saved = [r["morties_saved"] for r in valid_results]
    elapsed_times = [r.get("elapsed_time_seconds", 0) for r in valid_results]
    total_trips = [r.get("total_trips", 0) for r in valid_results]
    
    # Calculate additional metrics
    avg_survival = statistics.mean(survival_rates)
    stdev_survival = statistics.stdev(survival_rates) if len(survival_rates) > 1 else 0
    
    # Calculate confidence interval (95%)
    margin = 1.96 * stdev_survival / (len(survival_rates) ** 0.5) if len(survival_rates) > 1 else 0
    
    return {
        "num_runs": len(valid_results),
        "avg_survival_rate": avg_survival,
        "median_survival_rate": statistics.median(survival_rates),
        "stdev_survival_rate": stdev_survival,
        "min_survival_rate": min(survival_rates),
        "max_survival_rate": max(survival_rates),
        "ci_95_lower": avg_survival - margin,
        "ci_95_upper": avg_survival + margin,
        "avg_morties_saved": statistics.mean(morties_saved),
        "min_morties_saved": min(morties_saved),
        "max_morties_saved": max(morties_saved),
        "avg_time_seconds": statistics.mean(elapsed_times) if elapsed_times else 0,
        "avg_total_trips": statistics.mean(total_trips) if total_trips else 0,
    }


def save_benchmark_results(all_results: Dict[str, List[Dict]], filename: str = None):
    """
    Save benchmark results to JSON file.
    
    Args:
        all_results: Dictionary mapping strategy names to their results
        filename: Optional filename (auto-generated if None)
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/benchmark_{timestamp}.json"
    
    # Calculate statistics for each strategy
    benchmark_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "strategies_tested": list(all_results.keys()),
        },
        "results": all_results,
        "statistics": {
            strategy: calculate_statistics(results)
            for strategy, results in all_results.items()
        },
    }
    
    with open(filename, "w") as f:
        json.dump(benchmark_data, f, indent=2)
    
    print(f"\nBenchmark data saved to: {filename}")
    return filename


def print_comparison_summary(all_results: Dict[str, List[Dict]]):
    """
    Print a comparison summary of all strategies.
    
    Args:
        all_results: Dictionary mapping strategy names to their results
    """
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    
    stats = {}
    for strategy, results in all_results.items():
        stats[strategy] = calculate_statistics(results)
    
    # Sort by average survival rate
    sorted_strategies = sorted(
        stats.items(),
        key=lambda x: x[1].get("avg_survival_rate", 0),
        reverse=True
    )
    
    print("\nStrategies ranked by average survival rate:\n")
    for rank, (strategy, stat) in enumerate(sorted_strategies, 1):
        if "error" in stat:
            print(f"{rank}. {strategy}: ERROR - {stat['error']}")
        else:
            print(f"{rank}. {strategy}:")
            print(f"   Average Survival Rate: {stat['avg_survival_rate']:.2f}%")
            print(f"   Median Survival Rate: {stat.get('median_survival_rate', stat['avg_survival_rate']):.2f}%")
            print(f"   Standard Deviation: {stat.get('stdev_survival_rate', 0):.2f}%")
            print(f"   95% Confidence Interval: [{stat.get('ci_95_lower', stat['avg_survival_rate']):.2f}%, {stat.get('ci_95_upper', stat['avg_survival_rate']):.2f}%]")
            print(f"   Range: {stat['min_survival_rate']:.2f}% - {stat['max_survival_rate']:.2f}%")
            print(f"   Average Morties Saved: {stat['avg_morties_saved']:.0f}")
            print(f"   Average Total Trips: {stat.get('avg_total_trips', 0):.0f}")
            print(f"   Average Time: {stat['avg_time_seconds']:.1f}s")
            print()


def load_previous_benchmark(filename: str) -> Dict:
    """Load previous benchmark results for comparison."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def analyze_benchmark_file(filename: str):
    """
    Analyze a benchmark results file and print detailed comparison.
    
    Args:
        filename: Path to benchmark JSON file
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        print("="*60)
        print(f"ANALYZING BENCHMARK: {filename}")
        print("="*60)
        
        if "statistics" in data:
            print_comparison_summary(data["results"])
        
        # Show individual run details
        print("\nDetailed Results:")
        print("-"*60)
        for strategy, results in data["results"].items():
            print(f"\n{strategy}:")
            for result in results:
                if "error" not in result:
                    print(f"  Run {result['run_number']}: "
                          f"{result['survival_rate']:.2f}% "
                          f"({result['morties_saved']} saved)")
                    if "planet_usage" in result:
                        print(f"    Planet Usage: {result['planet_usage']}")
                        if "planet_successes" in result:
                            print(f"    Planet Successes: {result['planet_successes']}")
                else:
                    print(f"  Run {result['run_number']}: ERROR - {result['error']}")
    
    except FileNotFoundError:
        print(f"Error: File {filename} not found")
    except Exception as e:
        print(f"Error analyzing file: {e}")


def main():
    """Run benchmarks for all strategies."""
    print("="*60)
    print("MORTY EXPRESS - STRATEGY BENCHMARK")
    print("="*60)
    print("\nThis will test multiple strategies and compare their performance.")
    print("Each strategy will be run multiple times for statistical significance.")
    
    # Configuration
    num_runs_per_strategy = 3  # Adjust based on how many runs you want
    
    all_results = {}
    
    # # Strategy 1: Data-driven adaptive (Planet 2 early, Planet 0 later)
    # print("\n" + "="*60)
    # print("STRATEGY 1: Data-Driven Adaptive")
    # print("="*60)
    # print("Strategy: Use Planet 2 (0-120 trips), then Planet 0 (120+)")
    # results = run_strategy_benchmark(
    #     "Data-Driven Adaptive",
    #     run_adaptive_solution,
    #     num_runs=num_runs_per_strategy
    # )
    # all_results["Data-Driven Adaptive"] = results
    
    # # Wait between strategies
    # print("\nWaiting 5 seconds before next strategy...")
    # time.sleep(5)
    
    # # Strategy 2: Time-based with optimal switch points
    # print("\n" + "="*60)
    # print("STRATEGY 2: Time-Based (Optimal Switch Points)")
    # print("="*60)
    # print("Strategy: Switch from Planet 2 to Planet 0 at trip 120")
    # results = run_strategy_benchmark(
    #     "Time-Based Optimal",
    #     run_time_based_strategy,
    #     num_runs=num_runs_per_strategy
    # )
    # all_results["Time-Based Optimal"] = results
    
    # # Wait between strategies
    # print("\nWaiting 5 seconds before next strategy...")
    # time.sleep(5)
    
    # # Strategy 3: Optimal data-driven (loads from experiment data)
    # print("\n" + "="*60)
    # print("STRATEGY 3: Optimal Data-Driven")
    # print("="*60)
    # print("Strategy: Use best planet at each trip from experiment data")
    # results = run_strategy_benchmark(
    #     "Optimal Data-Driven",
    #     run_optimal_data_strategy,
    #     num_runs=num_runs_per_strategy
    # )
    # all_results["Optimal Data-Driven"] = results
    
    # Strategy 4: Three-planet strategy (includes Planet 1) - TESTED
    # print("\n" + "="*60)
    # print("STRATEGY 4: Three-Planet Strategy")
    # print("="*60)
    # print("Strategy: Uses all three planets based on optimal analysis")
    # results = run_strategy_benchmark(
    #     "Three-Planet Strategy",
    #     run_three_planet_strategy,
    #     num_runs=num_runs_per_strategy
    # )
    # all_results["Three-Planet Strategy"] = results
    # 
    # # Wait between strategies
    # print("\nWaiting 5 seconds before next strategy...")
    # time.sleep(5)
    # 
    # # Strategy 5: Adaptive morty count - TESTED
    # print("\n" + "="*60)
    # print("STRATEGY 5: Adaptive Morty Count")
    # print("="*60)
    # print("Strategy: Varies morty count (3->2->1) based on trip number")
    # results = run_strategy_benchmark(
    #     "Adaptive Morty Count",
    #     run_adaptive_morty_count_strategy,
    #     num_runs=num_runs_per_strategy
    # )
    # all_results["Adaptive Morty Count"] = results
    # 
    # # Wait between strategies
    # print("\nWaiting 5 seconds before next strategy...")
    # time.sleep(5)
    # 
    # # Strategy 6: Three-planet + adaptive morty count - TESTED
    # print("\n" + "="*60)
    # print("STRATEGY 6: Three-Planet + Adaptive Morty Count")
    # print("="*60)
    # print("Strategy: Uses all planets + varies morty count based on planet")
    # results = run_strategy_benchmark(
    #     "Three-Planet + Adaptive Morty",
    #     run_three_planet_adaptive_morty_strategy,
    #     num_runs=num_runs_per_strategy
    # )
    # all_results["Three-Planet + Adaptive Morty"] = results
    
    strategy_variants = [
        (
            "Hybrid Control (Aggressive Payloads)",
            run_hybrid_control_strategy,
            "Baseline hybrid selector with aggressive payload logic",
        ),
        (
            "Hybrid + Transition Enforcer",
            run_hybrid_transition_enforcer_strategy,
            "Schedule-aware enforcement of streak limits and transition quality",
        ),
        (
            "Hybrid + Planet 2 Priority",
            run_hybrid_planet2_priority_strategy,
            "Schedule-weighted confidence model that adapts per-planet emphasis",
        ),
        (
            "Hybrid + Schedule Phases",
            run_hybrid_schedule_phase_strategy,
            "Follows schedule blocks while probing alternates and exiting weak phases",
        ),
    ]
    
    for idx, (name, func, description) in enumerate(strategy_variants, start=1):
        print("\n" + "="*60)
        print(f"STRATEGY {idx}: {name}")
        print("="*60)
        print(f"Strategy: {description}")
        results = run_strategy_benchmark(name, func, num_runs=num_runs_per_strategy)
        all_results[name] = results
        
        if idx < len(strategy_variants):
            print("\nWaiting 5 seconds before next strategy...")
            time.sleep(5)
    
    # Save results
    filename = save_benchmark_results(all_results)
    
    # Print comparison
    print_comparison_summary(all_results)
    
    # Create visualization if matplotlib is available
    if HAS_MATPLOTLIB:
        try:
            visualize_benchmark_results(all_results, filename.replace('.json', '_comparison.png'))
        except Exception as e:
            print(f"Warning: Could not create visualization: {e}")
    
    print("="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)
    print(f"\nResults saved to: {filename}")
    print("\nYou can now:")
    print("1. Review the results to see which strategy performs best")
    print("2. Refine strategies based on the data")
    print("3. Run more iterations for better statistics")


def visualize_benchmark_results(all_results: Dict[str, List[Dict]], output_file: str):
    """
    Create visualization comparing strategy performance.
    
    Args:
        all_results: Dictionary mapping strategy names to their results
        output_file: Output filename for the plot
    """
    if not HAS_MATPLOTLIB:
        return
    
    strategies = list(all_results.keys())
    avg_rates = []
    min_rates = []
    max_rates = []
    
    for strategy in strategies:
        stats = calculate_statistics(all_results[strategy])
        if "error" not in stats:
            avg_rates.append(stats["avg_survival_rate"])
            min_rates.append(stats["min_survival_rate"])
            max_rates.append(stats["max_survival_rate"])
        else:
            avg_rates.append(0)
            min_rates.append(0)
            max_rates.append(0)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x_pos = range(len(strategies))
    width = 0.6
    
    # Create bars
    bars = ax.bar(x_pos, avg_rates, width, label='Average', color='#2ecc71', alpha=0.8)
    
    # Add error bars (min-max range)
    errors = [[avg - min_r for avg, min_r in zip(avg_rates, min_rates)],
              [max_r - avg for max_r, avg in zip(max_rates, avg_rates)]]
    ax.errorbar(x_pos, avg_rates, yerr=errors, fmt='none', color='black', capsize=5, capthick=2)
    
    # Add value labels on bars
    for i, (bar, avg) in enumerate(zip(bars, avg_rates)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{avg:.2f}%',
                ha='center', va='bottom', fontweight='bold')
    
    ax.set_xlabel('Strategy', fontsize=12)
    ax.set_ylabel('Survival Rate (%)', fontsize=12)
    ax.set_title('Strategy Performance Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(strategies, rotation=15, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    print(f"\nComparison visualization saved to: {output_file}")
    plt.close()


if __name__ == "__main__":
    import sys
    
    # Allow analyzing a specific benchmark file
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        analyze_benchmark_file(filename)
    else:
        # Run full benchmark
        main()


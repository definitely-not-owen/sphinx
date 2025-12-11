"""
Exploration script for Morty Express Challenge.
Runs full episodes sending all Morties to a single planet to collect survival data.
Supports parallel execution for faster data collection.
"""
import json
import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from main import start_episode, send_morties, get_status

# Lock for thread-safe printing
print_lock = threading.Lock()


def run_single_planet_experiment(planet: int, morty_count: int = 3) -> List[Dict]:
    """
    Run a full episode sending all Morties through a single planet.
    
    Args:
        planet: Planet index (0, 1, or 2)
        morty_count: Number of Morties to send per trip (1, 2, or 3)
    
    Returns:
        List of dictionaries containing trip data
    """
    with print_lock:
        print(f"\n{'='*60}")
        print(f"[Planet {planet}] Starting experiment: {morty_count} Morties per trip")
        print(f"{'='*60}")
    
    # Start new episode
    initial_state = start_episode()
    with print_lock:
        print(f"[Planet {planet}] Episode started: {initial_state}")
    
    trips_data = []
    cumulative_survived = 0
    cumulative_total = 0
    
    morties_remaining = initial_state["morties_in_citadel"]
    step_number = 0
    
    while morties_remaining > 0:
        # Determine how many to send (can't send more than available)
        send_count = min(morty_count, morties_remaining)
        
        # Send Morties
        result = send_morties(planet=planet, morty_count=send_count)
        
        step_number = result["steps_taken"]
        survived = result["survived"]
        morties_sent = result["morties_sent"]
        morties_remaining = result["morties_in_citadel"]
        
        # Update cumulative stats
        cumulative_total += 1  # Count trips, not individual Morties
        if survived:
            cumulative_survived += 1
        
        # Calculate survival rate (based on trips, not individual Morties)
        survival_rate = (cumulative_survived / cumulative_total) * 100 if cumulative_total > 0 else 0
        
        # Record trip data
        trip_data = {
            "step_number": step_number,
            "planet": planet,
            "morties_sent": morties_sent,
            "survived": survived,
            "cumulative_survived": cumulative_survived,
            "cumulative_total": cumulative_total,
            "survival_rate": survival_rate,
            "morties_remaining": morties_remaining,
            "morties_on_planet_jessica": result["morties_on_planet_jessica"],
            "morties_lost": result["morties_lost"],
        }
        trips_data.append(trip_data)
        
        # Progress update every 50 trips
        if step_number % 50 == 0:
            with print_lock:
                print(f"[Planet {planet}] Step {step_number}: {survival_rate:.2f}% survival rate, "
                      f"{morties_remaining} Morties remaining")
        
        # Small delay to avoid rate limiting (reduced for faster execution)
        time.sleep(0.05)
    
    # Final status
    final_status = get_status()
    with print_lock:
        print(f"\n[Planet {planet}] Experiment complete!")
        print(f"[Planet {planet}] Final stats:")
        print(f"  Total trips: {cumulative_total}")
        print(f"  Successful trips: {cumulative_survived}")
        print(f"  Final survival rate: {survival_rate:.2f}%")
        print(f"  Morties on Planet Jessica: {final_status['morties_on_planet_jessica']}")
        print(f"  Morties lost: {final_status['morties_lost']}")
    
    return trips_data


def save_experiment_data(trips_data: List[Dict], planet: int, morty_count: int):
    """
    Save experiment data to JSON file.
    
    Args:
        trips_data: List of trip data dictionaries
        planet: Planet index used in experiment
        morty_count: Number of Morties sent per trip
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/planet_{planet}_count_{morty_count}_{timestamp}.json"
    
    experiment_data = {
        "metadata": {
            "planet": planet,
            "morty_count": morty_count,
            "timestamp": timestamp,
            "total_trips": len(trips_data),
            "final_survival_rate": trips_data[-1]["survival_rate"] if trips_data else 0,
        },
        "trips": trips_data,
    }
    
    with open(filename, "w") as f:
        json.dump(experiment_data, f, indent=2)
    
    with print_lock:
        print(f"[Planet {planet}] Data saved to: {filename}")
    return filename


def run_experiment_and_save(planet: int, morty_count: int) -> Tuple[int, Dict]:
    """
    Wrapper function to run experiment and save data.
    Used for parallel execution.
    
    Args:
        planet: Planet index (0, 1, or 2)
        morty_count: Number of Morties to send per trip
    
    Returns:
        Tuple of (planet, results_dict)
    """
    try:
        trips_data = run_single_planet_experiment(planet, morty_count)
        filename = save_experiment_data(trips_data, planet, morty_count)
        return planet, {
            "filename": filename,
            "total_trips": len(trips_data),
            "final_survival_rate": trips_data[-1]["survival_rate"] if trips_data else 0,
            "final_morties_saved": trips_data[-1]["morties_on_planet_jessica"] if trips_data else 0,
        }
    except Exception as e:
        with print_lock:
            print(f"[Planet {planet}] Error: {e}")
        return planet, {"error": str(e)}


def run_all_exploration_experiments(morty_count: int = 3, parallel: bool = False):
    """
    Run exploration experiments for all three planets.
    
    Args:
        morty_count: Number of Morties to send per trip (default: 3)
        parallel: If True, run experiments in parallel (default: True)
                   Note: If API only allows one episode per token, set to False
    """
    print("="*60)
    print("MORTY EXPRESS - EXPLORATION EXPERIMENTS")
    print("="*60)
    print(f"Running experiments with {morty_count} Morties per trip")
    if parallel:
        print("Running 3 episodes in PARALLEL for faster execution")
        print("(If you get errors, try parallel=False)")
    else:
        print("Running 3 episodes sequentially")
    print("="*60)
    
    results = {}
    planet_names = ["On a Cob Planet", "Cronenberg World", "The Purge Planet"]
    
    if parallel:
        # Run experiments in parallel using ThreadPoolExecutor
        # Note: Each experiment starts its own episode, so they should be independent
        # However, if API limits one episode per token, this may cause conflicts
        start_time = time.time()
        
        # Add small staggered delay to avoid simultaneous episode starts
        def run_with_delay(planet, delay):
            time.sleep(delay)
            return run_experiment_and_save(planet, morty_count)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all experiments with staggered delays
            delays = [0, 0.5, 1.0]  # Stagger episode starts by 0.5s each
            futures = {
                executor.submit(run_with_delay, planet, delays[i]): planet
                for i, planet in enumerate([0, 1, 2])
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    planet, result = future.result()
                    results[planet] = result
                    with print_lock:
                        planet_name = planet_names[planet]
                        if "error" not in result:
                            print(f"\n[Planet {planet}] ({planet_name}) completed!")
                        else:
                            print(f"\n[Planet {planet}] ({planet_name}) failed: {result['error']}")
                except Exception as e:
                    with print_lock:
                        print(f"\n[Planet {planet}] Exception: {e}")
                    results[planet] = {"error": str(e)}
        
        elapsed_time = time.time() - start_time
        print(f"\nAll experiments completed in {elapsed_time:.1f} seconds")
    else:
        # Sequential execution (original behavior)
        for planet in [0, 1, 2]:
            planet_name = planet_names[planet]
            print(f"\n\n{'#'*60}")
            print(f"PLANET {planet}: {planet_name}")
            print(f"{'#'*60}")
            
            try:
                trips_data = run_single_planet_experiment(planet, morty_count)
                filename = save_experiment_data(trips_data, planet, morty_count)
                results[planet] = {
                    "filename": filename,
                    "total_trips": len(trips_data),
                    "final_survival_rate": trips_data[-1]["survival_rate"] if trips_data else 0,
                    "final_morties_saved": trips_data[-1]["morties_on_planet_jessica"] if trips_data else 0,
                }
            except Exception as e:
                print(f"Error running experiment for planet {planet}: {e}")
                results[planet] = {"error": str(e)}
            
            # Small delay between experiments (reduced for faster execution)
            if planet < 2:
                time.sleep(0.5)
    
    # Summary
    print("\n\n" + "="*60)
    print("EXPERIMENT SUMMARY")
    print("="*60)
    for planet in [0, 1, 2]:
        planet_name = planet_names[planet]
        if "error" not in results[planet]:
            print(f"\nPlanet {planet} ({planet_name}):")
            print(f"  Survival Rate: {results[planet]['final_survival_rate']:.2f}%")
            print(f"  Morties Saved: {results[planet]['final_morties_saved']}")
            print(f"  Total Trips: {results[planet]['total_trips']}")
            print(f"  Data file: {results[planet]['filename']}")
        else:
            print(f"\nPlanet {planet} ({planet_name}): ERROR - {results[planet]['error']}")
    
    return results


def run_multi_run_experiments(num_runs: int = 10, morty_count: int = 3) -> Dict[int, List[Dict]]:
    """
    Run the single-planet experiment multiple times per planet and collect results.
    
    Args:
        num_runs: Number of episodes per planet
        morty_count: Morties per trip (fixed at 3 per requirements)
    
    Returns:
        Dictionary mapping planet -> list of run dictionaries (with trips + filename)
    """
    planet_runs: Dict[int, List[Dict]] = {0: [], 1: [], 2: []}
    planet_names = ["On a Cob Planet", "Cronenberg World", "The Purge Planet"]
    
    for planet in [0, 1, 2]:
        for run_idx in range(1, num_runs + 1):
            print("\n" + "#" * 60)
            print(f"PLANET {planet} ({planet_names[planet]}): Run {run_idx}/{num_runs}")
            print("#" * 60)
            trips_data = run_single_planet_experiment(planet, morty_count)
            filename = save_experiment_data(trips_data, planet, morty_count)
            planet_runs[planet].append(
                {
                    "run_index": run_idx,
                    "filename": filename,
                    "trips": trips_data,
                }
            )
            # Short delay between runs to respect API limits
            time.sleep(0.5)
    return planet_runs


def build_schedule_from_runs(
    planet_runs: Dict[int, List[Dict]],
    output_filename: str = None,
) -> str:
    """
    Build a planet schedule by comparing per-trip success rates across planets.
    
    Args:
        planet_runs: Dictionary from planet -> list of run dicts
        output_filename: Optional path for saving schedule JSON
    
    Returns:
        Path to the generated schedule file
    """
    success_by_step: Dict[int, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
    max_step = 0
    
    for planet, runs in planet_runs.items():
        for run in runs:
            for trip in run["trips"]:
                step = trip["step_number"]
                survived = 1 if trip.get("survived") else 0
                success_by_step[planet][step].append(survived)
                if step > max_step:
                    max_step = step
    
    schedule = []
    for step in range(1, max_step + 1):
        best_planet = None
        best_rate = -1.0
        planet_rates = {}
        for planet in [0, 1, 2]:
            trials = success_by_step[planet].get(step, [])
            if not trials:
                continue
            avg_rate = (sum(trials) / len(trials)) * 100
            planet_rates[planet] = avg_rate
            if avg_rate > best_rate:
                best_rate = avg_rate
                best_planet = planet
        
        if best_planet is not None:
            schedule.append(
                {
                    "step_number": step,
                    "planet": best_planet,
                    "average_success_rate": best_rate,
                    "planet_rates": planet_rates,
                }
            )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_filename is None:
        output_filename = f"data/planet_schedule_{timestamp}.json"
    
    schedule_payload = {
        "metadata": {
            "timestamp": timestamp,
            "num_runs_per_planet": {planet: len(runs) for planet, runs in planet_runs.items()},
            "max_step": max_step,
        },
        "schedule": schedule,
    }
    
    with open(output_filename, "w") as f:
        json.dump(schedule_payload, f, indent=2)
    
    print("\n" + "=" * 60)
    print("PLANET SCHEDULE GENERATED")
    print("=" * 60)
    print(f"Schedule saved to: {output_filename}")
    print(f"Entries: {len(schedule)} (covering up to step {max_step})")
    
    return output_filename


if __name__ == "__main__":
    NUM_RUNS_PER_PLANET = 10
    DEFAULT_MORTY_COUNT = 3
    
    print("=" * 60)
    print("MORTY EXPRESS - MULTI-RUN EXPLORATION + SCHEDULE BUILDER")
    print("=" * 60)
    print(f"Running {NUM_RUNS_PER_PLANET} episodes per planet with {DEFAULT_MORTY_COUNT} Morties/trip")
    
    planet_runs_data = run_multi_run_experiments(
        num_runs=NUM_RUNS_PER_PLANET,
        morty_count=DEFAULT_MORTY_COUNT,
    )
    build_schedule_from_runs(planet_runs_data)


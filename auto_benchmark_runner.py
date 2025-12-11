#!/usr/bin/env python3
"""
Automation harness for iterating on Morty Express strategies.

Features:
1. Runs benchmark.py and captures the generated benchmark file.
2. Invokes analyze_benchmark.py on the new benchmark to record rich analysis.
3. Loads the benchmark JSON, aggregates mission statistics, and surfaces
   concrete improvement directions for the next strategy iteration.
4. Supports multi-iteration loops so we can refine strategies continuously.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

from analyze_benchmark import (
    analyze_strategy_performance,
    load_benchmark,
    suggest_improvements,
)


WORKSPACE_ROOT = Path(__file__).parent
BENCHMARK_PATTERN = re.compile(r"Results saved to:\s*(data/benchmark_[0-9_]+\.json)")


def run_subprocess(cmd: List[str]) -> subprocess.CompletedProcess:
    """Run a subprocess command, echoing stdout/stderr for transparency."""
    print(f"\n[CMD] {' '.join(cmd)}\n")
    completed = subprocess.run(
        cmd,
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.stdout:
        print(completed.stdout)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr)

    if completed.returncode != 0:
        raise RuntimeError(f"Command {' '.join(cmd)} failed with exit code {completed.returncode}")
    return completed


def run_benchmark() -> Path:
    """Execute benchmark.py and return the generated benchmark JSON path."""
    completed = run_subprocess([sys.executable, "benchmark.py"])
    match = BENCHMARK_PATTERN.search(completed.stdout)
    if not match:
        raise RuntimeError("Could not locate benchmark output path in benchmark.py output")
    benchmark_path = WORKSPACE_ROOT / match.group(1)
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark file {benchmark_path} was not created")
    return benchmark_path


def run_analysis(benchmark_path: Path) -> None:
    """Run analyze_benchmark.py for the specified benchmark file."""
    run_subprocess([sys.executable, "analyze_benchmark.py", str(benchmark_path)])


def aggregate_planet_stats(mission_logs: List[dict]) -> Dict[int, Dict[str, float]]:
    """Compute survival stats per planet from combined mission logs."""
    usage = {0: {"trips": 0, "successes": 0}, 1: {"trips": 0, "successes": 0}, 2: {"trips": 0, "successes": 0}}
    for mission in mission_logs:
        planet = mission.get("planet", 0)
        survived = mission.get("survived", False)
        usage.setdefault(planet, {"trips": 0, "successes": 0})
        usage[planet]["trips"] += 1
        if survived:
            usage[planet]["successes"] += 1
    planet_rates = {}
    for planet, stats in usage.items():
        trips = stats["trips"]
        if trips == 0:
            continue
        planet_rates[planet] = {
            "trips": trips,
            "success_rate": (stats["successes"] / trips) * 100,
        }
    return planet_rates


def aggregate_morty_stats(mission_logs: List[dict]) -> Dict[int, Dict[str, float]]:
    """Compute survival stats per morty count."""
    usage = {}
    for mission in mission_logs:
        count = mission.get("morty_count", 0)
        if count <= 0:
            continue
        survived = mission.get("survived", False)
        usage.setdefault(count, {"trips": 0, "successes": 0})
        usage[count]["trips"] += 1
        if survived:
            usage[count]["successes"] += 1
    morty_rates = {}
    for count, stats in usage.items():
        trips = stats["trips"]
        if trips == 0:
            continue
        morty_rates[count] = {
            "trips": trips,
            "success_rate": (stats["successes"] / trips) * 100,
        }
    return morty_rates


def derive_directions(benchmark_data: Dict) -> Dict[str, List[str]]:
    """
    Inspect benchmark JSON and surface actionable improvement ideas per strategy.

    Uses the existing analysis helpers plus additional heuristics that look at
    planet usage, decay, and morty-count success rates.
    """
    directions: Dict[str, List[str]] = {}
    for strategy, results in benchmark_data["results"].items():
        analysis = analyze_strategy_performance(results)
        if "error" in analysis:
            directions[strategy] = [f"Analysis failed: {analysis['error']}"]
            continue

        suggestions = []
        stats = benchmark_data["statistics"].get(strategy, {})
        avg_survival = stats.get("avg_survival_rate", 0)
        if avg_survival < 60:
            suggestions.append(
                f"Average survival {avg_survival:.2f}% is far from 90% target. "
                "Consider rebuilding planet schedule or introducing new data sources."
            )

        patterns = analysis.get("combined_patterns", {})
        mission_logs = []
        for result in results:
            mission_logs.extend(result.get("mission_log", []))

        planet_rates = aggregate_planet_stats(mission_logs)
        if planet_rates:
            best_planet = max(planet_rates.items(), key=lambda kv: kv[1]["success_rate"])
            worst_planet = min(planet_rates.items(), key=lambda kv: kv[1]["success_rate"])
            diff = best_planet[1]["success_rate"] - worst_planet[1]["success_rate"]
            suggestions.append(
                f"Planet {best_planet[0]} leads with {best_planet[1]['success_rate']:.1f}%. "
                f"Planet {worst_planet[0]} trails at {worst_planet[1]['success_rate']:.1f}% "
                f"(Δ {diff:.1f}%). Rebalance usage accordingly."
            )

        decay_info = patterns.get("planet_decay", {})
        for planet, decay in decay_info.items():
            if decay.get("avg_decay", 0) > 5:
                suggestions.append(
                    f"Planet {planet} decays by {decay['avg_decay']:.1f}% over sustained runs. "
                    "Shorten its streaks or insert cooldown periods."
                )

        morty_analysis = patterns.get("morty_count_analysis", {})
        morty_rates = aggregate_morty_stats(mission_logs)
        if morty_rates:
            best_count = max(morty_rates.items(), key=lambda kv: kv[1]["success_rate"])
            suggestions.append(
                f"Morty count {best_count[0]} rows achieve {best_count[1]['success_rate']:.1f}%. "
                "Bias sends toward this count when odds are favorable."
            )

        success_by_count = morty_analysis.get("success_by_count", {})
        if success_by_count:
            low_counts = [c for c, data in success_by_count.items() if data["survival_rate"] < 45]
            if low_counts:
                suggestions.append(
                    "Low survival for morty counts "
                    + ", ".join(str(c) for c in low_counts)
                    + ". Avoid those payload sizes unless forced."
                )

        transitions = patterns.get("num_transitions", 0)
        total_trips = patterns.get("total_trips", 1)
        transition_ratio = transitions / total_trips if total_trips else 0
        if transition_ratio < 0.05:
            suggestions.append(
                f"Only {transitions} transitions in {total_trips} trips. "
                "Introduce more frequent planet switches to track drifting odds."
            )

        # Merge in suggestions from analyze_benchmark's helper.
        extra_suggestions = suggest_improvements(benchmark_data).get(strategy, [])
        suggestions.extend(extra_suggestions)

        # Deduplicate while preserving order.
        seen = set()
        deduped = []
        for item in suggestions:
            if item not in seen:
                deduped.append(item)
                seen.add(item)
        directions[strategy] = deduped

    return directions


def iteration_loop(iterations: int, sleep_seconds: float) -> None:
    """Run benchmark/analysis loops for the requested number of iterations."""
    for i in range(1, iterations + 1):
        print(f"\n{'='*60}\nITERATION {i}/{iterations}\n{'='*60}")
        benchmark_path = run_benchmark()
        print(f"\n[info] Benchmark file: {benchmark_path}")

        print("\n[info] Running detailed analysis...\n")
        run_analysis(benchmark_path)

        benchmark_data = load_benchmark(str(benchmark_path))
        directions = derive_directions(benchmark_data)

        for strategy, recs in directions.items():
            print(f"\n--- Improvement directions for {strategy} ---")
            if not recs:
                print("No actionable suggestions (strategy already stable).")
                continue
            for idx, suggestion in enumerate(recs, 1):
                print(f"{idx}. {suggestion}")

        if i < iterations:
            print(f"\n[info] Sleeping {sleep_seconds:.1f}s before next iteration...\n")
            time.sleep(sleep_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate benchmark/analyze/refine loops.")
    parser.add_argument(
        "-n",
        "--iterations",
        type=int,
        default=1,
        help="Number of benchmark/analysis iterations to run (default: 1)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=5.0,
        help="Seconds to wait between iterations (default: 5)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    iteration_loop(args.iterations, args.sleep)


if __name__ == "__main__":
    main()


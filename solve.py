"""
Solution script for Morty Express Challenge.
Implements adaptive algorithms that react to observed planet survival patterns.

Latest benchmark insights (2025-11-15 18:50 UTC):
- Planet 1 delivered the highest recent survival rate (~61%) when sampled.
- Planet 0 ramps up late-game (~51% recent survival).
- Planet 2 dominates early but drops quickly (~43% overall when overused).

Refinement goals:
- Switch planets more frequently during mid-game to track shifting odds.
- Use sliding-window performance stats so we don't get stuck on Planet 2.
- Bias late-game toward Planets 0/1 while still probing others.
"""
import json
import os
import time
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple
from main import start_episode, send_morties, get_status


PLANET_SCHEDULE_PATH = "data/planet_schedule_20251116_001549.json"


def load_planet_schedule(path: str = PLANET_SCHEDULE_PATH) -> Dict[int, Dict]:
    """Load planet schedule produced by explore.py multi-run experiments."""
    if not path or not os.path.exists(path):
        return {}
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    
    schedule_entries = data.get("schedule", [])
    schedule_map = {}
    for entry in schedule_entries:
        step = entry.get("step_number")
        if step is not None:
            schedule_map[int(step)] = entry
    return schedule_map


PLANET_SCHEDULE = load_planet_schedule()
PLANET_SCHEDULE_MAX_STEP = max(PLANET_SCHEDULE.keys()) if PLANET_SCHEDULE else 0


def get_schedule_entry(step_number: int) -> Optional[Dict]:
    if not PLANET_SCHEDULE:
        return None
    if step_number in PLANET_SCHEDULE:
        return PLANET_SCHEDULE[step_number]
    return PLANET_SCHEDULE.get(PLANET_SCHEDULE_MAX_STEP)


def get_schedule_planet(step_number: int) -> Tuple[Optional[int], Optional[Dict]]:
    """
    Return (planet, entry_dict) for the requested trip step based on schedule.
    Falls back to last known entry if beyond schedule range.
    """
    entry = get_schedule_entry(step_number)
    if entry is None:
        return None, None
    return entry.get("planet"), entry


def get_schedule_ranked_planets(step_number: int) -> List[Tuple[int, float]]:
    entry = get_schedule_entry(step_number)
    if not entry:
        return []
    planet_rates = entry.get("planet_rates", {})
    ranked = sorted(
        ((int(planet), rate) for planet, rate in planet_rates.items()),
        key=lambda kv: kv[1],
        reverse=True,
    )
    return ranked


def build_schedule_ranges() -> List[Dict]:
    if not PLANET_SCHEDULE:
        return []
    sorted_steps = sorted(PLANET_SCHEDULE.keys())
    ranges = []
    start = sorted_steps[0]
    current_planet = PLANET_SCHEDULE[start]["planet"]
    rate_sum = PLANET_SCHEDULE[start].get("average_success_rate", 0)
    count = 1
    for step in sorted_steps[1:]:
        entry = PLANET_SCHEDULE[step]
        planet = entry.get("planet")
        rate = entry.get("average_success_rate", 0)
        if planet == current_planet:
            rate_sum += rate
            count += 1
        else:
            ranges.append(
                {
                    "start": start,
                    "end": step - 1,
                    "planet": current_planet,
                    "avg_rate": rate_sum / count if count else 0,
                    "length": (step - start),
                }
            )
            start = step
            current_planet = planet
            rate_sum = rate
            count = 1
    ranges.append(
        {
            "start": start,
            "end": sorted_steps[-1],
            "planet": current_planet,
            "avg_rate": rate_sum / count if count else 0,
            "length": (sorted_steps[-1] - start + 1),
        }
    )
    return ranges


SCHEDULE_RANGES = build_schedule_ranges()


def find_schedule_range(step_number: int) -> Optional[Dict]:
    if not SCHEDULE_RANGES:
        return None
    for schedule_range in SCHEDULE_RANGES:
        if schedule_range["start"] <= step_number <= schedule_range["end"]:
            return schedule_range
    return SCHEDULE_RANGES[-1] if step_number > SCHEDULE_RANGES[-1]["end"] else None


class AdaptiveStrategy:
    """
    Adaptive strategy that learns which planet is best at each point in time.
    """
    
    def __init__(
        self,
        exploration_trips: int = 100,
        morty_count: int = 3,
        recent_window: int = 40,
        max_same_planet_streak: int = 40,
    ):
        """
        Initialize strategy.
        
        Args:
            exploration_trips: Number of trips to spend exploring each planet
            morty_count: Number of Morties to send per trip
            recent_window: Sliding window size for recent survival stats
            max_same_planet_streak: Max consecutive trips on same planet
        """
        self.exploration_trips = exploration_trips
        self.morty_count = morty_count
        self.recent_window = recent_window
        self.max_same_planet_streak = max_same_planet_streak
        
        # Track survival rates for each planet at different trip numbers
        self.planet_stats = {
            0: {"successes": 0, "total": 0, "survival_rate": 0.0},
            1: {"successes": 0, "total": 0, "survival_rate": 0.0},
            2: {"successes": 0, "total": 0, "survival_rate": 0.0},
        }
        
        # Track survival rates by trip number range (for time-based switching)
        self.trip_range_stats = {}  # Will store: {trip_range: {planet: survival_rate}}
        
        # Sliding window of recent results per planet
        self.recent_results: Dict[int, Deque[int]] = {
            0: deque(maxlen=self.recent_window),
            1: deque(maxlen=self.recent_window),
            2: deque(maxlen=self.recent_window),
        }
        
        # Prevent staying on one planet forever
        self.last_planet: Optional[int] = None
        self.same_planet_streak: int = 0
    
    def update_stats(self, planet: int, survived: bool):
        """Update statistics for a planet after a trip."""
        stats = self.planet_stats[planet]
        stats["total"] += 1
        if survived:
            stats["successes"] += 1
        stats["survival_rate"] = (stats["successes"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        
        # Maintain sliding window
        self.recent_results[planet].append(1 if survived else 0)
        
        # Track streak
        if self.last_planet == planet:
            self.same_planet_streak += 1
        else:
            self.same_planet_streak = 1
        self.last_planet = planet
    
    def get_best_planet(self, current_trip: int) -> int:
        """
        Determine the best planet to use at the current trip number.
        
        Args:
            current_trip: Current trip number
        
        Returns:
            Best planet index (0, 1, or 2)
        """
        # During exploration phase, cycle through planets
        if current_trip < self.exploration_trips * 3:
            # Explore: cycle through planets evenly
            planet_index = (current_trip // self.exploration_trips) % 3
            return planet_index
        
        # After exploration, use the planet with best current survival rate
        best_planet = 0
        best_rate = self.planet_stats[0]["survival_rate"]
        
        for planet in [1, 2]:
            rate = self.planet_stats[planet]["survival_rate"]
            if rate > best_rate:
                best_rate = rate
                best_planet = planet
        
        return best_planet
    
    def adaptive_get_best_planet(self, current_trip: int) -> int:
        """
        Data-driven adaptive selection based on analysis results.
        
        Strategy based on observed patterns:
        - Trips 0-120: Planet 2 is best (starts at 100%, stays high)
        - Trips 120+: Planet 0 becomes best (improving trend)
        
        Args:
            current_trip: Current trip number
        
        Returns:
            Best planet index
        """
        # Data-driven strategy: Use Planet 2 early, Planet 0 later
        # Based on analysis: Planet 2 best until ~trip 120, then Planet 0 becomes best
        if current_trip < 120:
            return 2  # Planet 2 (The Purge Planet) - best early performance
        else:
            return 0  # Planet 0 (On a Cob Planet) - improving trend, becomes best
    
    def data_driven_get_best_planet(self, current_trip: int) -> int:
        """
        Alternative data-driven strategy with smooth transition.
        Uses Planet 2 early, then transitions to Planet 0 around trip 120.
        
        Args:
            current_trip: Current trip number
        
        Returns:
            Best planet index
        """
        # Smooth transition: mostly Planet 2 early, mostly Planet 0 later
        if current_trip < 100:
            return 2  # Planet 2 dominates early
        elif current_trip < 140:
            # Transition period: mix of Planet 2 and Planet 0
            # Use Planet 2 60% of the time, Planet 0 40%
            return 2 if (current_trip % 5) < 3 else 0
        else:
            return 0  # Planet 0 dominates later
    
    def three_planet_strategy(self, current_trip: int) -> int:
        """
        Strategy that includes all three planets based on optimal analysis.
        
        Based on analysis:
        - Trips 1-6: Planet 1 (best early)
        - Trips 7-128: Planet 2 (best mid-early)
        - Trips 129-164: Planet 0 (improving)
        - Trips 165-166: Planet 1 (brief optimal)
        - Trips 167-204: Planet 0
        - Trips 205-209: Planet 1
        - Trips 210-211: Planet 0
        - Trips 212-323: Planet 2
        - Trips 324+: Planet 1
        
        Args:
            current_trip: Current trip number
        
        Returns:
            Best planet index
        """
        if current_trip <= 6:
            return 1  # Planet 1 best early
        elif current_trip <= 128:
            return 2  # Planet 2 best mid-early
        elif current_trip <= 164:
            return 0  # Planet 0 improving
        elif current_trip <= 166:
            return 1  # Planet 1 brief optimal
        elif current_trip <= 204:
            return 0  # Planet 0
        elif current_trip <= 209:
            return 1  # Planet 1
        elif current_trip <= 211:
            return 0  # Planet 0
        elif current_trip <= 323:
            return 2  # Planet 2
        else:
            return 1  # Planet 1 late
    
    def get_recent_success_rate(self, planet: int, window: Optional[int] = None) -> float:
        """
        Return recent success rate for a planet using a sliding window.
        Falls back to lifetime survival rate if not enough data.
        """
        results = list(self.recent_results[planet])
        if not results:
            return self.planet_stats[planet]["survival_rate"]
        
        if window and len(results) > window:
            results = results[-window:]
        
        return (sum(results) / len(results)) * 100 if results else self.planet_stats[planet]["survival_rate"]
    
    def dynamic_adaptive_strategy(self, current_trip: int) -> int:
        """
        Updated dynamic strategy based on latest benchmark insights.
        - Use Planet 2 heavily for the first ~40 trips to capture its early dominance.
        - Introduce Planet 1 sooner (it showed ~61% survival when sampled).
        - Blend in Planet 0 mid/late game based on sliding-window performance.
        - Force periodic switches so we don't get stuck on a single planet.
        """
        # Early game bootstrap
        if current_trip < 40:
            return 2
        if current_trip < 80:
            return 2 if (current_trip % 10) < 7 else 1
        
        # Mid-game: rely on sliding-window performance
        if current_trip < 170:
            window = 30
            rates = {
                0: self.get_recent_success_rate(0, window),
                1: self.get_recent_success_rate(1, window) + 2.0,  # reward Planet 1
                2: self.get_recent_success_rate(2, window) - 1.5,  # penalize Planet 2 decay
            }
            ranked = sorted(
                rates.items(),
                key=lambda kv: (kv[1], self.planet_stats[kv[0]]["total"]),
                reverse=True,
            )
            choice = ranked[0][0]
            if self.same_planet_streak >= self.max_same_planet_streak and len(ranked) > 1:
                choice = ranked[1][0]
            return choice
        
        # Late game: Planet 0 + Planet 1 mix with occasional Planet 2 probes
        window = 40
        rates = {
            0: self.get_recent_success_rate(0, window) + 1.5,
            1: self.get_recent_success_rate(1, window) + 2.5,
            2: self.get_recent_success_rate(2, window) - 3.0,
        }
        ranked = sorted(
            rates.items(),
            key=lambda kv: (kv[1], self.planet_stats[kv[0]]["total"]),
            reverse=True,
        )
        choice = ranked[0][0]
        if self.same_planet_streak >= self.max_same_planet_streak and len(ranked) > 1:
            choice = ranked[1][0]
        return choice
    
    def compute_hybrid_scores(self, current_trip: int) -> Dict[int, float]:
        """Return scoring map used by hybrid strategies."""
        base_planet = self.three_planet_strategy(current_trip)
        window_planet = self.windowed_performance_strategy(current_trip)
        perf_planet = self.performance_based_strategy(current_trip)
        
        scores = {}
        for planet in [0, 1, 2]:
            score = self.get_recent_success_rate(planet, 35)
            
            if planet == base_planet:
                score += 1.5
            if planet == window_planet:
                score += 1.0
            if planet == perf_planet:
                score += 1.0
            
            # Time-based biases (inspired by best historical run)
            if current_trip < 60 and planet == 2:
                score += 2.5
            elif 60 <= current_trip < 150 and planet == 1:
                score += 2.0
            elif current_trip >= 150 and planet == 0:
                score += 2.0
            
            scores[planet] = score
        return scores
    
    def hybrid_planet_strategy(self, current_trip: int) -> int:
        """
        Hybrid planet selector that blends:
        - Best historical schedule (three-planet strategy)
        - Windowed performance scores
        - Performance-based ranking
        """
        scores = self.compute_hybrid_scores(current_trip)
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        choice = ranked[0][0]
        if self.same_planet_streak >= self.max_same_planet_streak and len(ranked) > 1:
            choice = ranked[1][0]
        return choice
    
    def choose_morty_count(self, planet: int, current_trip: int, morties_remaining: int) -> int:
        """
        Choose how many Morties to send based on predicted survival and phase.
        Mirrors the best historical run by sending more Morties when odds are high.
        """
        if morties_remaining <= 0:
            return 0
        
        predicted = self.get_recent_success_rate(planet, 35)
        
        if current_trip < 60:
            base = 3
        elif predicted >= 55:
            base = 3
        elif predicted >= 45:
            base = 2
        else:
            base = 1
        
        # Planet-specific adjustments
        if planet == 2 and current_trip >= 120:
            base = min(base, 2)  # Planet 2 decays late
        if planet == 0 and current_trip >= 180:
            base = min(3, base + 1)  # Planet 0 improves late
        
        # Ensure we don't strand Morties
        if morties_remaining <= base:
            return morties_remaining
        
        return min(base, morties_remaining)
    
    def aggressive_morty_count(self, planet: int, current_trip: int, morties_remaining: int) -> int:
        """
        Aggressively send 3 Morties whenever recent odds are favorable.
        Falls back gradually instead of jumping straight to singles.
        """
        if morties_remaining <= 0:
            return 0
        
        if current_trip < 150:
            base = 3
        else:
            predicted = self.get_recent_success_rate(planet, 25)
            if predicted >= 52:
                base = 3
            elif predicted >= 44:
                base = 2
            else:
                base = 1
        
        if planet == 2 and current_trip > 120:
            base = min(base, 2)
        if planet == 0 and current_trip > 200 and base < 3:
            base += 1  # Planet 0 improves late, push back toward 3
        
        return min(base, morties_remaining)
    
    def performance_based_strategy(self, current_trip: int) -> int:
        """
        Strategy that adapts based on observed performance statistics.
        Switches planets more dynamically based on recent success rates.
        
        Args:
            current_trip: Current trip number
        
        Returns:
            Best planet index based on performance
        """
        # Early exploration: mostly Planet 2 with Planet 1 sprinkled in
        if current_trip < 30:
            return 2 if (current_trip % 6) != 0 else 1
        
        window = 40 if current_trip > 80 else 25
        rates = {
            planet: self.get_recent_success_rate(planet, window)
            for planet in [0, 1, 2]
        }
        
        # Bias schedule informed by benchmark analysis
        if current_trip > 120:
            rates[1] += 2.5  # Planet 1 strongest in recent data
            rates[0] += 1.0  # Planet 0 catches up
            rates[2] -= 1.5  # Planet 2 degrades mid/late
        
        ranked = sorted(
            rates.items(),
            key=lambda kv: (kv[1], self.planet_stats[kv[0]]["total"]),
            reverse=True,
        )
        choice = ranked[0][0]
        
        # Force a switch if we've been on the same planet too long
        if self.same_planet_streak >= self.max_same_planet_streak and len(ranked) > 1:
            choice = ranked[1][0]
        
        return choice
    
    def windowed_performance_strategy(self, current_trip: int) -> int:
        """
        Fully sliding-window-based strategy with enforced exploration.
        """
        if current_trip < 20:
            return 2
        
        dynamic_window = 50 if current_trip > 180 else 30
        rates = {
            planet: self.get_recent_success_rate(planet, dynamic_window)
            for planet in [0, 1, 2]
        }
        
        if current_trip >= 80:
            rates[1] += 3.0
        if current_trip >= 150:
            rates[0] += 2.0
            rates[2] -= 2.0
        
        ranked = sorted(
            rates.items(),
            key=lambda kv: (kv[1], self.planet_stats[kv[0]]["total"]),
            reverse=True,
        )
        choice = ranked[0][0]
        
        if self.same_planet_streak >= self.max_same_planet_streak and len(ranked) > 1:
            choice = ranked[1][0]
        
        return choice
    
    def get_morty_count(self, current_trip: int, morties_remaining: int) -> int:
        """
        Determine how many morties to send based on trip number and remaining morties.
        
        Strategy ideas:
        - Early trips: Send more (3) when survival rates are high
        - Mid trips: Vary based on planet performance
        - Late trips: Send fewer (1-2) when survival rates are lower
        
        Args:
            current_trip: Current trip number
            morties_remaining: Number of morties left in citadel
        
        Returns:
            Number of morties to send (1, 2, or 3)
        """
        # Default: always send 3
        return min(3, morties_remaining)
    
    def adaptive_morty_count(self, current_trip: int, morties_remaining: int, planet: int) -> int:
        """
        Adaptive morty count strategy based on trip number and planet.
        
        Strategy:
        - Early trips (0-50): Send 3 (high survival rates)
        - Mid trips (50-200): Send 2 (moderate survival)
        - Late trips (200+): Send 1 (lower survival, more trips = more data)
        
        Args:
            current_trip: Current trip number
            morties_remaining: Number of morties left
            planet: Planet being used
        
        Returns:
            Number of morties to send (1, 2, or 3)
        """
        if morties_remaining <= 0:
            return 0
        
        if current_trip < 50:
            # Early: send 3 when survival is high
            return min(3, morties_remaining)
        elif current_trip < 200:
            # Mid: send 2 for balance
            return min(2, morties_remaining)
        else:
            # Late: send 1 to maximize number of trips/data
            return min(1, morties_remaining)
    
    def planet_based_morty_count(self, current_trip: int, morties_remaining: int, planet: int) -> int:
        """
        Vary morty count based on which planet is being used.
        
        Strategy:
        - Planet 0 (improving): Send more early (1-2), more later (3) as it improves
        - Planet 1 (decreasing): Send more early (3), fewer later (1-2)
        - Planet 2 (decreasing fast): Send more early (3), fewer later (1)
        
        Args:
            current_trip: Current trip number
            morties_remaining: Number of morties left
            planet: Planet being used
        
        Returns:
            Number of morties to send (1, 2, or 3)
        """
        if morties_remaining <= 0:
            return 0
        
        if planet == 0:
            # Planet 0 improves over time
            if current_trip < 100:
                return min(1, morties_remaining)  # Start small
            elif current_trip < 200:
                return min(2, morties_remaining)  # Increase
            else:
                return min(3, morties_remaining)  # Max when best
        elif planet == 1:
            # Planet 1 decreases over time
            if current_trip < 50:
                return min(3, morties_remaining)  # Max early
            elif current_trip < 150:
                return min(2, morties_remaining)  # Moderate
            else:
                return min(1, morties_remaining)  # Min late
        else:  # planet == 2
            # Planet 2 decreases fastest
            if current_trip < 50:
                return min(3, morties_remaining)  # Max early
            elif current_trip < 100:
                return min(2, morties_remaining)  # Moderate
            else:
                return min(1, morties_remaining)  # Min late


def load_optimal_strategy_from_data(data_files: Optional[Dict[int, str]] = None) -> Dict[int, int]:
    """
    Load optimal planet selection from pre-computed data.
    Returns a mapping of trip_number -> best_planet.
    
    Args:
        data_files: Optional dict mapping planet to filename
    
    Returns:
        Dictionary mapping trip number to optimal planet
    """
    if data_files is None:
        # Use default data files
        data_files = {
            0: "data/planet_0_count_3_20251115_164620.json",
            1: "data/planet_1_count_3_20251115_164753.json",
            2: "data/planet_2_count_3_20251115_164927.json",
        }
    
    # Load all planet data
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
    
    # Find best planet at each trip number
    optimal_strategy = {}
    max_trip = max(
        max(trips.keys()) if trips else 0
        for trips in planet_data.values()
    )
    
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


def run_adaptive_solution(strategy: AdaptiveStrategy = None) -> Dict:
    """
    Run the adaptive solution algorithm.
    
    Args:
        strategy: Optional strategy instance (creates default if None)
    
    Returns:
        Final game state dictionary with mission_log added
    """
    if strategy is None:
        strategy = AdaptiveStrategy(exploration_trips=100, morty_count=3)
    
    print("="*60)
    print("MORTY EXPRESS - ADAPTIVE SOLUTION")
    print("="*60)
    
    # Start episode
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []  # Track each mission: (trip_number, planet, morty_count, survived)
    
    while morties_remaining > 0:
        # Determine how many to send
        send_count = min(strategy.morty_count, morties_remaining)
        
        # Choose planet using data-driven strategy
        planet = strategy.adaptive_get_best_planet(current_trip)
        
        # Send Morties
        result = send_morties(planet=planet, morty_count=send_count)
        
        # Update strategy
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        # Log this mission
        mission_log.append({
            "trip_number": result["steps_taken"],
            "planet": planet,
            "morty_count": send_count,
            "survived": survived,
        })
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        # Progress updates
        if current_trip % 150 == 0:
            print(f"\nTrip {current_trip}:")
            print(f"  Sent {send_count} Morties to Planet {planet}")
            print(f"  Result: {'Survived' if survived else 'Lost'}")
            print(f"  Morties remaining: {morties_remaining}")
            print(f"  Morties saved: {result['morties_on_planet_jessica']}")
            print("  Planet stats:")
            for p in [0, 1, 2]:
                stats = strategy.planet_stats[p]
                print(f"    Planet {p}: {stats['survival_rate']:.2f}% "
                      f"({stats['successes']}/{stats['total']})")
        
        # Small delay
        time.sleep(0.1)
    
    # Final status
    final_status = get_status()
    final_status["mission_log"] = mission_log  # Add mission log to return value
    
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    print(f"  Morties lost: {final_status['morties_lost']}")
    survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    print("\nFinal Planet Statistics:")
    for planet in [0, 1, 2]:
        stats = strategy.planet_stats[planet]
        print(f"  Planet {planet}: {stats['survival_rate']:.2f}% "
              f"({stats['successes']}/{stats['total']} trips)")
    
    return final_status


def run_time_based_strategy(switch_points: Optional[List[Tuple[int, int]]] = None) -> Dict:
    """
    Run a time-based switching strategy based on data analysis.
    Switch planets at specific trip numbers based on observed patterns.
    
    Args:
        switch_points: List of trip numbers to switch planets
                      Format: [(trip_num, planet), ...]
                      If None, uses data-driven optimal switching points
    
    Returns:
        Final game state dictionary
    """
    if switch_points is None:
        # Data-driven optimal switching points based on analysis:
        # - Planet 2 best early (0-120)
        # - Planet 0 best later (120+)
        switch_points = [
            (0, 2),    # Start with Planet 2 (best early performance)
            (120, 0),  # Switch to Planet 0 at trip 120 (becomes best)
        ]
    
    print("="*60)
    print("MORTY EXPRESS - TIME-BASED STRATEGY")
    print("="*60)
    
    # Start episode
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    switch_index = 0
    current_planet = switch_points[0][1] if switch_points else 0
    mission_log = []
    
    planet_stats = {0: {"successes": 0, "total": 0}, 1: {"successes": 0, "total": 0}, 2: {"successes": 0, "total": 0}}
    
    while morties_remaining > 0:
        # Check if we should switch planets
        if switch_index < len(switch_points) - 1:
            next_switch_trip, next_planet = switch_points[switch_index + 1]
            if current_trip >= next_switch_trip:
                switch_index += 1
                if switch_index < len(switch_points):
                    current_planet = switch_points[switch_index][1]
                    print(f"\nSwitching to Planet {current_planet} at trip {current_trip}")
        
        # Determine how many to send
        send_count = min(3, morties_remaining)
        
        # Send Morties
        result = send_morties(planet=current_planet, morty_count=send_count)
        
        # Update stats
        survived = result["survived"]
        planet_stats[current_planet]["total"] += 1
        if survived:
            planet_stats[current_planet]["successes"] += 1
        
        # Log this mission
        mission_log.append({
            "trip_number": result["steps_taken"],
            "planet": current_planet,
            "morty_count": send_count,
            "survived": survived,
        })
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        # Progress updates
        if current_trip % 150 == 0:
            print(f"\nTrip {current_trip}: Planet {current_planet}, "
                  f"{'Survived' if survived else 'Lost'}, "
                  f"{morties_remaining} remaining")
        
        time.sleep(0.1)
    
    # Final status
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_optimal_data_strategy() -> Dict:
    """
    Run solution using optimal strategy loaded from pre-computed data.
    Uses the best planet at each trip number based on actual experiment data.
    
    Returns:
        Final game state dictionary
    """
    print("="*60)
    print("MORTY EXPRESS - OPTIMAL DATA-DRIVEN STRATEGY")
    print("="*60)
    
    # Load optimal strategy from data
    optimal_strategy = load_optimal_strategy_from_data()
    
    if not optimal_strategy:
        print("Warning: Could not load optimal strategy, falling back to adaptive")
        return run_adaptive_solution()
    
    print(f"Loaded optimal strategy for {len(optimal_strategy)} trips")
    
    # Start episode
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    
    while morties_remaining > 0:
        # Determine how many to send
        send_count = min(3, morties_remaining)
        
        # Use optimal planet from data, or default to Planet 2 if not found
        planet = optimal_strategy.get(current_trip + 1, 2)
        
        # Send Morties
        result = send_morties(planet=planet, morty_count=send_count)
        
        # Log this mission
        mission_log.append({
            "trip_number": result["steps_taken"],
            "planet": planet,
            "morty_count": send_count,
            "survived": result["survived"],
        })
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        # Progress updates
        if current_trip % 150 == 0:
            print(f"\nTrip {current_trip}: Planet {planet}, "
                  f"{'Survived' if result['survived'] else 'Lost'}, "
                  f"{morties_remaining} remaining")
        
        time.sleep(0.1)
    
    # Final status
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_three_planet_strategy() -> Dict:
    """
    Run solution using three-planet strategy that includes Planet 1.
    
    Returns:
        Final game state dictionary
    """
    print("="*60)
    print("MORTY EXPRESS - THREE-PLANET STRATEGY")
    print("="*60)
    print("Strategy: Uses all three planets based on optimal analysis")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    
    while morties_remaining > 0:
        send_count = min(strategy.morty_count, morties_remaining)
        planet = strategy.three_planet_strategy(current_trip)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        # Log this mission
        mission_log.append({
            "trip_number": result["steps_taken"],
            "planet": planet,
            "morty_count": send_count,
            "survived": survived,
        })
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 50 == 0:
            print(f"\nTrip {current_trip}: Planet {planet}, "
                  f"{'Survived' if survived else 'Lost'}, "
                  f"{morties_remaining} remaining")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_adaptive_morty_count_strategy() -> Dict:
    """
    Run solution with adaptive morty count (varies based on trip number).
    
    Returns:
        Final game state dictionary
    """
    print("="*60)
    print("MORTY EXPRESS - ADAPTIVE MORTY COUNT STRATEGY")
    print("="*60)
    print("Strategy: Varies morty count (3->2->1) based on trip number")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    
    while morties_remaining > 0:
        planet = strategy.adaptive_get_best_planet(current_trip)
        send_count = strategy.adaptive_morty_count(current_trip, morties_remaining, planet)
        
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        # Log this mission
        mission_log.append({
            "trip_number": result["steps_taken"],
            "planet": planet,
            "morty_count": send_count,
            "survived": survived,
        })
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 50 == 0:
            print(f"\nTrip {current_trip}: Planet {planet}, Count {send_count}, "
                  f"{'Survived' if survived else 'Lost'}, "
                  f"{morties_remaining} remaining")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_three_planet_adaptive_morty_strategy() -> Dict:
    """
    Run solution combining three-planet strategy with adaptive morty count.
    
    Returns:
        Final game state dictionary
    """
    print("="*60)
    print("MORTY EXPRESS - THREE-PLANET + ADAPTIVE MORTY COUNT")
    print("="*60)
    print("Strategy: Uses all planets + varies morty count based on planet")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    
    while morties_remaining > 0:
        planet = strategy.three_planet_strategy(current_trip)
        send_count = strategy.planet_based_morty_count(current_trip, morties_remaining, planet)
        
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        # Log this mission
        mission_log.append({
            "trip_number": result["steps_taken"],
            "planet": planet,
            "morty_count": send_count,
            "survived": survived,
        })
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 50 == 0:
            print(f"\nTrip {current_trip}: Planet {planet}, Count {send_count}, "
                  f"{'Survived' if survived else 'Lost'}, "
                  f"{morties_remaining} remaining")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_dynamic_adaptive_strategy() -> Dict:
    """
    Run solution using dynamic adaptive strategy that switches planets more frequently.
    
    Returns:
        Final game state dictionary
    """
    print("="*60)
    print("MORTY EXPRESS - DYNAMIC ADAPTIVE STRATEGY")
    print("="*60)
    print("Strategy: Switches planets more frequently based on trip ranges")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    
    while morties_remaining > 0:
        planet = strategy.hybrid_planet_strategy(current_trip)
        send_count = strategy.choose_morty_count(planet, current_trip, morties_remaining)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        # Log this mission
        mission_log.append({
            "trip_number": result["steps_taken"],
            "planet": planet,
            "morty_count": send_count,
            "survived": survived,
        })
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 150 == 0:
            print(f"\nTrip {current_trip}: Planet {planet}, "
                  f"{'Survived' if survived else 'Lost'}, "
                  f"{morties_remaining} remaining")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_hybrid_planet2_cooldown_strategy() -> Dict:
    """
    Hybrid strategy with enforced cooldowns for Planet 2 to prevent long decay streaks.
    """
    print("="*60)
    print("MORTY EXPRESS - HYBRID + PLANET 2 COOLDOWN")
    print("="*60)
    print("Strategy: Hybrid selector + automatic cooldowns when Planet 2 decays")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    planet2_streak = 0
    cooldown_remaining = 0
    cooldown_length = 30
    max_planet2_streak = 20
    
    while morties_remaining > 0:
        base_scores = strategy.compute_hybrid_scores(current_trip)
        adjusted_scores = dict(base_scores)
        if cooldown_remaining > 0 and 2 in adjusted_scores:
            adjusted_scores.pop(2)
        if not adjusted_scores:
            adjusted_scores = dict(base_scores)
        
        planet = max(adjusted_scores.items(), key=lambda kv: kv[1])[0]
        
        recent_p2 = strategy.get_recent_success_rate(2, 30)
        if planet == 2:
            planet2_streak += 1
            if (
                planet2_streak >= max_planet2_streak
                or (strategy.planet_stats[2]["total"] > 40 and recent_p2 < 55)
            ):
                cooldown_remaining = cooldown_length
                planet2_streak = 0
                fallback_scores = dict(base_scores)
                fallback_scores.pop(2, None)
                if fallback_scores:
                    planet = max(fallback_scores.items(), key=lambda kv: kv[1])[0]
        else:
            planet2_streak = 0
        
        send_count = strategy.choose_morty_count(planet, current_trip, morties_remaining)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        mission_log.append(
            {
                "trip_number": result["steps_taken"],
                "planet": planet,
                "morty_count": send_count,
                "survived": survived,
            }
        )
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        cooldown_remaining = max(0, cooldown_remaining - 1)
        
        if current_trip % 150 == 0:
            print(
                f"\nTrip {current_trip}: Planet {planet}, "
                f"{'Survived' if survived else 'Lost'}, "
                f"{morties_remaining} remaining"
            )
            print(f"  Planet 2 cooldown remaining: {cooldown_remaining}")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status["morties_on_planet_jessica"] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_hybrid_planet1_bias_strategy() -> Dict:
    """
    Hybrid strategy that explicitly biases towards Planet 1 usage mid/late game.
    """
    print("="*60)
    print("MORTY EXPRESS - HYBRID + PLANET 1 EMPHASIS")
    print("="*60)
    print("Strategy: Hybrid selector + forced Planet 1 sampling and bonuses")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    last_planet1_trip = -100
    force_interval = 30
    
    while morties_remaining > 0:
        scores = strategy.compute_hybrid_scores(current_trip)
        if 1 in scores:
            since_planet1 = current_trip - last_planet1_trip
            bonus = max(0.0, 4.0 - (since_planet1 / 15.0))
            if current_trip < 200:
                bonus += 1.5
            scores[1] += bonus
            if since_planet1 > force_interval:
                planet = 1
            else:
                planet = max(scores.items(), key=lambda kv: kv[1])[0]
        else:
            planet = max(scores.items(), key=lambda kv: kv[1])[0]
        
        if planet == 1:
            last_planet1_trip = current_trip
        
        send_count = strategy.choose_morty_count(planet, current_trip, morties_remaining)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        mission_log.append(
            {
                "trip_number": result["steps_taken"],
                "planet": planet,
                "morty_count": send_count,
                "survived": survived,
            }
        )
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 150 == 0:
            print(
                f"\nTrip {current_trip}: Planet {planet}, "
                f"{'Survived' if survived else 'Lost'}, "
                f"{morties_remaining} remaining"
            )
            print(f"  Trips since Planet 1: {current_trip - last_planet1_trip}")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status["morties_on_planet_jessica"] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_hybrid_control_strategy() -> Dict:
    """
    Hybrid strategy that keeps Morty payloads high whenever odds allow.
    """
    print("="*60)
    print("MORTY EXPRESS - HYBRID CONTROL STRATEGY")
    print("="*60)
    print("Strategy: Hybrid selector + bias toward 3-Morty sends when survival odds permit")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    
    while morties_remaining > 0:
        planet = strategy.hybrid_planet_strategy(current_trip)
        send_count = strategy.aggressive_morty_count(planet, current_trip, morties_remaining)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        mission_log.append(
            {
                "trip_number": result["steps_taken"],
                "planet": planet,
                "morty_count": send_count,
                "survived": survived,
            }
        )
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 150 == 0:
            print(
                f"\nTrip {current_trip}: Planet {planet}, Count {send_count}, "
                f"{'Survived' if survived else 'Lost'}, "
                f"{morties_remaining} remaining"
            )
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status["morties_on_planet_jessica"] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_hybrid_transition_enforcer_strategy() -> Dict:
    """
    Hybrid control variant that enforces frequent planet switches to avoid decay.
    """
    print("="*60)
    print("MORTY EXPRESS - HYBRID + TRANSITION ENFORCER")
    print("="*60)
    print("Strategy: Hybrid control plus max streak caps and streak-based penalties")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    last_planet: Optional[int] = None
    same_planet_streak = 0
    base_max_same_planet_streak = 18
    
    while morties_remaining > 0:
        step_number = current_trip + 1
        scores = strategy.compute_hybrid_scores(current_trip)
        schedule_planet, schedule_entry = get_schedule_planet(step_number)
        dynamic_max_same_planet = base_max_same_planet_streak
        if schedule_planet is not None and schedule_entry is not None:
            avg_rate = schedule_entry.get("average_success_rate", 50)
            schedule_bonus = (avg_rate - 50) / 12.0
            scores[schedule_planet] = scores.get(schedule_planet, 0) + schedule_bonus
            for planet, rate in schedule_entry.get("planet_rates", {}).items():
                planet_idx = int(planet)
                if planet_idx != schedule_planet:
                    scores[planet_idx] = scores.get(planet_idx, 0) - max(0, (avg_rate - rate) / 28.0)
            schedule_range = find_schedule_range(step_number)
            if schedule_range:
                dynamic_max_same_planet = max(
                    10, min(26, schedule_range.get("length", 20) // 2 + 8)
                )
        for idx, (sched_planet, rate) in enumerate(get_schedule_ranked_planets(step_number)):
            scores[sched_planet] = scores.get(sched_planet, 0) + (rate - 50) / 18.0 - idx * 0.35
        if last_planet is not None and same_planet_streak >= dynamic_max_same_planet:
            scores.pop(last_planet, None)
            if not scores:
                scores = strategy.compute_hybrid_scores(current_trip)
        
        # penalize planets after back-to-back failures
        for planet in [0, 1, 2]:
            recent_rate = strategy.get_recent_success_rate(planet, 20)
            if recent_rate and recent_rate < 42:
                scores[planet] = scores.get(planet, 0) - 1.8
        
        planet = max(scores.items(), key=lambda kv: kv[1])[0]
        send_count = strategy.aggressive_morty_count(planet, current_trip, morties_remaining)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        mission_log.append(
            {
                "trip_number": result["steps_taken"],
                "planet": planet,
                "morty_count": send_count,
                "survived": survived,
            }
        )
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if planet == last_planet:
            same_planet_streak += 1
        else:
            same_planet_streak = 1
        last_planet = planet
        
        if current_trip % 150 == 0:
            print(
                f"\nTrip {current_trip}: Planet {planet}, Count {send_count}, "
                f"{'Survived' if survived else 'Lost'}, "
                f"{morties_remaining} remaining"
            )
            print(f"  Current streak on Planet {planet}: {same_planet_streak}")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status["morties_on_planet_jessica"] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_hybrid_planet2_priority_strategy() -> Dict:
    """
    Hybrid control variant that biases toward Planet 2 and limits Planet 1 decay streaks.
    """
    print("="*60)
    print("MORTY EXPRESS - HYBRID + PLANET 2 PRIORITY")
    print("="*60)
    print("Strategy: Hybrid control plus dynamic Planet 2 bonuses and Planet 1 cooldowns")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    planet_confidence = {0: 0.0, 1: 0.0, 2: 0.0}
    forced_switch_cooldown = {0: 0, 1: 0, 2: 0}
    
    while morties_remaining > 0:
        step_number = current_trip + 1
        scores = strategy.compute_hybrid_scores(current_trip)
        schedule_ranked = get_schedule_ranked_planets(step_number)
        preferred_planet = schedule_ranked[0][0] if schedule_ranked else None
        preferred_rate = schedule_ranked[0][1] if schedule_ranked else 0
        if preferred_planet is not None:
            scores[preferred_planet] = scores.get(preferred_planet, 0) + (preferred_rate - 50) / 10.0
        for rank, (planet_idx, rate) in enumerate(schedule_ranked[1:], start=1):
            scores[planet_idx] = scores.get(planet_idx, 0) + (rate - 50) / 14.0 - rank * 0.5
        for planet in [0, 1, 2]:
            recent = strategy.get_recent_success_rate(planet, 30)
            if recent:
                scores[planet] = scores.get(planet, 0) + (recent - 55) / 18.0 + planet_confidence.get(planet, 0)
            if forced_switch_cooldown[planet] > 0:
                scores[planet] = scores.get(planet, 0) - 2.0
        if preferred_planet is not None:
            preferred_recent = strategy.get_recent_success_rate(preferred_planet, 25)
            if preferred_recent and preferred_rate - preferred_recent > 12:
                scores[preferred_planet] -= 2.5
        if not scores:
            scores = strategy.compute_hybrid_scores(current_trip)
        planet = max(scores.items(), key=lambda kv: kv[1])[0]
        for key in forced_switch_cooldown:
            if forced_switch_cooldown[key] > 0 and key != planet:
                forced_switch_cooldown[key] -= 1
        
        send_count = strategy.aggressive_morty_count(planet, current_trip, morties_remaining)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        mission_log.append(
            {
                "trip_number": result["steps_taken"],
                "planet": planet,
                "morty_count": send_count,
                "survived": survived,
            }
        )
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        planet_confidence[planet] = max(
            -4.0, min(6.0, planet_confidence.get(planet, 0) + (1.2 if survived else -1.5))
        )
        if not survived and strategy.get_recent_success_rate(planet, 15) < 45:
            forced_switch_cooldown[planet] = 8
        
        if current_trip % 150 == 0:
            print(
                f"\nTrip {current_trip}: Planet {planet}, Count {send_count}, "
                f"{'Survived' if survived else 'Lost'}, "
                f"{morties_remaining} remaining"
            )
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status["morties_on_planet_jessica"] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_hybrid_aggressive_payload_strategy() -> Dict:
    """
    Backwards-compatible wrapper for prior naming.
    """
    return run_hybrid_control_strategy()


def run_hybrid_schedule_guided_strategy() -> Dict:
    """
    Hybrid control variant that closely follows the empirical planet schedule
    but adapts when live data disagrees with historical averages.
    """
    print("="*60)
    print("MORTY EXPRESS - HYBRID + SCHEDULE GUIDED")
    print("="*60)
    print("Strategy: Follow generated schedule, fall back to hybrid logic when needed")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    exploration_interval = 45  # periodic deviation to probe other planets
    
    while morties_remaining > 0:
        schedule_planet, schedule_entry = get_schedule_planet(current_trip + 1)
        schedule_rate = schedule_entry.get("average_success_rate", 0) if schedule_entry else 0
        planet_rates = schedule_entry.get("planet_rates", {}) if schedule_entry else {}
        
        fallback_planet = strategy.hybrid_planet_strategy(current_trip)
        target_planet = schedule_planet if schedule_planet is not None else fallback_planet
        
        if schedule_planet is not None:
            recent_rate = strategy.get_recent_success_rate(schedule_planet, 25)
            if recent_rate and schedule_rate and recent_rate < schedule_rate - 12:
                target_planet = fallback_planet
            elif current_trip % exploration_interval == 0:
                # Briefly sample second-best schedule planet if available
                sorted_planets = sorted(
                    ((int(p), r) for p, r in planet_rates.items()),
                    key=lambda kv: kv[1],
                    reverse=True,
                )
                if len(sorted_planets) > 1:
                    target_planet = sorted_planets[1][0]
        
        planet = target_planet
        send_count = strategy.aggressive_morty_count(planet, current_trip, morties_remaining)
        if schedule_rate >= 70 and planet == schedule_planet:
            send_count = min(3, morties_remaining)
        elif schedule_rate <= 45:
            send_count = min(send_count, 2)
        
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        mission_log.append(
            {
                "trip_number": result["steps_taken"],
                "planet": planet,
                "morty_count": send_count,
                "survived": survived,
                "schedule_planet": schedule_planet,
                "schedule_rate": schedule_rate,
            }
        )
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 150 == 0:
            print(
                f"\nTrip {current_trip}: Planet {planet}, Count {send_count}, "
                f"{'Survived' if survived else 'Lost'}, "
                f"{morties_remaining} remaining"
            )
            if schedule_planet is not None:
                print(f"  Schedule suggested Planet {schedule_planet} at ~{schedule_rate:.1f}%")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status["morties_on_planet_jessica"] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_hybrid_schedule_phase_strategy() -> Dict:
    """
    Hybrid control variant that executes schedule-aligned phases while
    periodically probing alternates and reacting to live decay.
    """
    print("="*60)
    print("MORTY EXPRESS - HYBRID + SCHEDULE PHASES")
    print("="*60)
    print("Strategy: Follow schedule blocks, exit early if block underperforms, blend with hybrid ranking")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    current_block_planet: Optional[int] = None
    block_end_trip = 0
    block_attempts = 0
    block_successes = 0
    probe_interval = 35
    
    while morties_remaining > 0:
        step_number = current_trip + 1
        schedule_range = find_schedule_range(step_number)
        if schedule_range and (current_block_planet is None or step_number > block_end_trip):
            current_block_planet = schedule_range["planet"]
            block_end_trip = schedule_range["end"]
            block_attempts = 0
            block_successes = 0
        
        target_planet = current_block_planet
        if schedule_range and current_block_planet is not None:
            avg_rate = schedule_range.get("avg_rate", 50)
            recent = strategy.get_recent_success_rate(current_block_planet, 25)
            if recent and avg_rate - recent > 10:
                target_planet = None
        else:
            target_planet = None
        
        if target_planet is None:
            scores = strategy.compute_hybrid_scores(current_trip)
            for idx, (planet_candidate, rate) in enumerate(get_schedule_ranked_planets(step_number)):
                scores[planet_candidate] = scores.get(planet_candidate, 0) + (rate - 50) / 14.0 - idx * 0.4
            planet = max(scores.items(), key=lambda kv: kv[1])[0]
        else:
            planet = target_planet
        
        if probe_interval and step_number % probe_interval == 0:
            ranked = get_schedule_ranked_planets(step_number)
            if ranked:
                for candidate, _ in ranked:
                    if candidate != planet:
                        planet = candidate
                        break
        
        send_count = strategy.aggressive_morty_count(planet, current_trip, morties_remaining)
        if schedule_range:
            avg_rate = schedule_range.get("avg_rate", 50)
            if avg_rate >= 65 and planet == schedule_range["planet"]:
                send_count = min(3, morties_remaining)
            elif avg_rate <= 48:
                send_count = min(send_count, 2)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        mission_log.append(
            {
                "trip_number": result["steps_taken"],
                "planet": planet,
                "morty_count": send_count,
                "survived": survived,
                "schedule_block_planet": current_block_planet,
                "schedule_block_end": block_end_trip,
            }
        )
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if planet == current_block_planet:
            block_attempts += 1
            if survived:
                block_successes += 1
            if block_attempts >= 5:
                block_rate = (block_successes / block_attempts) * 100
                if schedule_range and block_rate + 8 < schedule_range.get("avg_rate", 50):
                    current_block_planet = None
        else:
            block_attempts = max(0, block_attempts - 1)
        
        if current_trip % 150 == 0:
            print(
                f"\nTrip {current_trip}: Planet {planet}, Count {send_count}, "
                f"{'Survived' if survived else 'Lost'}, "
                f"{morties_remaining} remaining"
            )
            if schedule_range:
                print(
                    f"  Active schedule block: Planet {schedule_range['planet']} "
                    f"({schedule_range['start']}-{schedule_range['end']}, "
                    f"{schedule_range.get('avg_rate', 0):.1f}%)"
                )
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status["morties_on_planet_jessica"] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_performance_based_strategy() -> Dict:
    """
    Run solution using performance-based strategy that adapts to observed results.
    
    Returns:
        Final game state dictionary
    """
    print("="*60)
    print("MORTY EXPRESS - PERFORMANCE-BASED STRATEGY")
    print("="*60)
    print("Strategy: Adapts planet selection based on observed performance")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    
    while morties_remaining > 0:
        send_count = min(strategy.morty_count, morties_remaining)
        planet = strategy.performance_based_strategy(current_trip)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        # Log this mission
        mission_log.append({
            "trip_number": result["steps_taken"],
            "planet": planet,
            "morty_count": send_count,
            "survived": survived,
        })
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 150 == 0:
            print(f"\nTrip {current_trip}: Planet {planet}, "
                  f"{'Survived' if survived else 'Lost'}, "
                  f"{morties_remaining} remaining")
            stats_str = ", ".join([f"P{p}: {strategy.planet_stats[p]['survival_rate']:.1f}%" for p in [0, 1, 2]])
            print(f"  Planet stats: {stats_str}")
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status['morties_on_planet_jessica'] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


def run_windowed_performance_strategy() -> Dict:
    """
    Run solution using the pure sliding-window performance strategy.
    """
    print("="*60)
    print("MORTY EXPRESS - WINDOWED PERFORMANCE STRATEGY")
    print("="*60)
    print("Strategy: Sliding-window stats + enforced exploration")
    
    strategy = AdaptiveStrategy(morty_count=3)
    initial_state = start_episode()
    print(f"Episode started: {initial_state}")
    
    morties_remaining = initial_state["morties_in_citadel"]
    current_trip = 0
    mission_log = []
    
    while morties_remaining > 0:
        send_count = min(strategy.morty_count, morties_remaining)
        planet = strategy.windowed_performance_strategy(current_trip)
        result = send_morties(planet=planet, morty_count=send_count)
        
        survived = result["survived"]
        strategy.update_stats(planet, survived)
        
        mission_log.append(
            {
                "trip_number": result["steps_taken"],
                "planet": planet,
                "morty_count": send_count,
                "survived": survived,
            }
        )
        
        morties_remaining = result["morties_in_citadel"]
        current_trip = result["steps_taken"]
        
        if current_trip % 150 == 0:
            print(
                f"\nTrip {current_trip}: Planet {planet}, "
                f"{'Survived' if survived else 'Lost'}, "
                f"{morties_remaining} remaining"
            )
        
        time.sleep(0.1)
    
    final_status = get_status()
    final_status["mission_log"] = mission_log
    print("\n" + "="*60)
    print("SOLUTION COMPLETE")
    print("="*60)
    print("Final Stats:")
    print(f"  Total trips: {current_trip}")
    print(f"  Morties saved: {final_status['morties_on_planet_jessica']}")
    survival_rate = (final_status["morties_on_planet_jessica"] / 1000) * 100
    print(f"  Survival rate: {survival_rate:.2f}%")
    
    return final_status


if __name__ == "__main__":
    # Run data-driven solution based on analysis
    # Strategy: Use Planet 2 early (0-120), then Planet 0 (120+)
    print("Running data-driven adaptive solution...")
    result = run_adaptive_solution()
    
    # Alternative strategies:
    # print("\nRunning time-based strategy with optimal switch points...")
    # result = run_time_based_strategy()
    
    # print("\nRunning optimal data-driven strategy (loads from experiment data)...")
    # result = run_optimal_data_strategy()


"""
Analyze benchmark results to understand strategy patterns and identify improvements.
Enhanced with detailed temporal and transition analysis.
"""
import json
import statistics
from typing import Dict, List
from collections import defaultdict


def load_benchmark(filename: str) -> Dict:
    """Load benchmark JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)


def analyze_temporal_performance(mission_log: List[Dict], segments: int = 3) -> Dict:
    """
    Analyze planet performance across different time segments (early/mid/late game).
    
    Args:
        mission_log: List of mission dictionaries
        segments: Number of time segments to divide into
    
    Returns:
        Dictionary with performance by segment
    """
    if not mission_log:
        return {}
    
    total_trips = len(mission_log)
    segment_size = total_trips // segments
    
    segment_performance = {}
    for seg in range(segments):
        start_idx = seg * segment_size
        end_idx = (seg + 1) * segment_size if seg < segments - 1 else total_trips
        
        segment_missions = mission_log[start_idx:end_idx]
        planet_stats = defaultdict(lambda: {'total': 0, 'successes': 0})
        
        for mission in segment_missions:
            planet = mission.get('planet', 0)
            planet_stats[planet]['total'] += 1
            if mission.get('survived', False):
                planet_stats[planet]['successes'] += 1
        
        segment_rates = {}
        for planet, stats in planet_stats.items():
            if stats['total'] > 0:
                segment_rates[planet] = {
                    'survival_rate': (stats['successes'] / stats['total']) * 100,
                    'trips': stats['total'],
                    'successes': stats['successes'],
                }
        
        segment_performance[f'segment_{seg + 1}'] = {
            'trip_range': (start_idx + 1, end_idx),
            'planet_performance': segment_rates,
        }
    
    return segment_performance


def analyze_transition_effectiveness(mission_log: List[Dict], window: int = 10) -> Dict:
    """
    Analyze whether planet transitions improve or degrade performance.
    
    Args:
        mission_log: List of mission dictionaries
        window: Number of trips before/after transition to analyze
    
    Returns:
        Dictionary with transition analysis
    """
    if not mission_log or len(mission_log) < window * 2:
        return {}
    
    transitions = []
    prev_planet = None
    
    for i, mission in enumerate(mission_log):
        planet = mission.get('planet', 0)
        if prev_planet is not None and planet != prev_planet:
            # Calculate performance before and after transition
            before_start = max(0, i - window)
            before_end = i
            after_start = i
            after_end = min(len(mission_log), i + window)
            
            before_missions = mission_log[before_start:before_end]
            after_missions = mission_log[after_start:after_end]
            
            before_successes = sum(1 for m in before_missions if m.get('survived', False))
            before_total = len(before_missions)
            after_successes = sum(1 for m in after_missions if m.get('survived', False))
            after_total = len(after_missions)
            
            before_rate = (before_successes / before_total * 100) if before_total > 0 else 0
            after_rate = (after_successes / after_total * 100) if after_total > 0 else 0
            
            transitions.append({
                'trip': mission.get('trip_number', i + 1),
                'from': prev_planet,
                'to': planet,
                'before_rate': before_rate,
                'after_rate': after_rate,
                'improvement': after_rate - before_rate,
            })
        
        prev_planet = planet
    
    if not transitions:
        return {'num_transitions': 0}
    
    avg_improvement = statistics.mean([t['improvement'] for t in transitions])
    positive_transitions = sum(1 for t in transitions if t['improvement'] > 0)
    
    return {
        'num_transitions': len(transitions),
        'avg_improvement': avg_improvement,
        'positive_transitions': positive_transitions,
        'positive_transition_rate': (positive_transitions / len(transitions) * 100) if transitions else 0,
        'transitions': transitions[:20],  # Keep first 20 for detail
    }


def analyze_planet_decay(mission_log: List[Dict], window: int = 20) -> Dict:
    """
    Analyze how planet performance degrades over time when used continuously.
    
    Args:
        mission_log: List of mission dictionaries
        window: Window size for calculating rolling performance
    
    Returns:
        Dictionary with decay analysis
    """
    if not mission_log:
        return {}
    
    # Group missions by planet and analyze performance over time
    planet_sequences = defaultdict(list)
    current_planet = None
    sequence_start = 0
    
    for i, mission in enumerate(mission_log):
        planet = mission.get('planet', 0)
        if planet != current_planet:
            if current_planet is not None:
                planet_sequences[current_planet].append({
                    'start': sequence_start,
                    'end': i - 1,
                    'missions': mission_log[sequence_start:i],
                })
            current_planet = planet
            sequence_start = i
    
    # Add final sequence
    if current_planet is not None:
        planet_sequences[current_planet].append({
            'start': sequence_start,
            'end': len(mission_log) - 1,
            'missions': mission_log[sequence_start:],
        })
    
    decay_analysis = {}
    for planet, sequences in planet_sequences.items():
        if not sequences:
            continue
        
        # Analyze each sequence for decay
        sequence_decays = []
        for seq in sequences:
            missions = seq['missions']
            if len(missions) < window * 2:
                continue
            
            # Calculate early vs late performance
            early = missions[:window]
            late = missions[-window:]
            
            early_rate = sum(1 for m in early if m.get('survived', False)) / len(early) * 100
            late_rate = sum(1 for m in late if m.get('survived', False)) / len(late) * 100
            
            sequence_decays.append({
                'length': len(missions),
                'early_rate': early_rate,
                'late_rate': late_rate,
                'decay': early_rate - late_rate,
            })
        
        if sequence_decays:
            decay_analysis[planet] = {
                'avg_decay': statistics.mean([s['decay'] for s in sequence_decays]),
                'sequences': len(sequence_decays),
                'avg_sequence_length': statistics.mean([s['length'] for s in sequence_decays]),
            }
    
    return decay_analysis


def analyze_morty_count_patterns(mission_log: List[Dict]) -> Dict:
    """
    Analyze morty count usage patterns across trips, planets, and phases.
    
    Returns:
        Dictionary with morty count analysis
    """
    if not mission_log:
        return {}
    
    morty_counts = [m.get('morty_count', 0) for m in mission_log if m.get('morty_count', 0) > 0]
    if not morty_counts:
        return {}
    
    # Overall distribution
    count_distribution = defaultdict(int)
    for count in morty_counts:
        count_distribution[count] += 1
    
    # By planet
    morty_by_planet = defaultdict(lambda: {'counts': [], 'total_trips': 0, 'total_morties': 0})
    for mission in mission_log:
        planet = mission.get('planet', 0)
        count = mission.get('morty_count', 0)
        if count > 0:
            morty_by_planet[planet]['counts'].append(count)
            morty_by_planet[planet]['total_trips'] += 1
            morty_by_planet[planet]['total_morties'] += count
    
    planet_stats = {}
    for planet, data in morty_by_planet.items():
        if data['counts']:
            planet_stats[planet] = {
                'avg_morty_count': statistics.mean(data['counts']),
                'median_morty_count': statistics.median(data['counts']),
                'total_trips': data['total_trips'],
                'total_morties_sent': data['total_morties'],
                'distribution': {c: data['counts'].count(c) for c in set(data['counts'])},
            }
    
    # By temporal phase (early/mid/late)
    total_trips = len(mission_log)
    segment_size = total_trips // 3
    phase_stats = {}
    
    for phase_idx, phase_name in enumerate(['early', 'mid', 'late']):
        start_idx = phase_idx * segment_size
        end_idx = (phase_idx + 1) * segment_size if phase_idx < 2 else total_trips
        
        phase_missions = mission_log[start_idx:end_idx]
        phase_counts = [m.get('morty_count', 0) for m in phase_missions if m.get('morty_count', 0) > 0]
        
        if phase_counts:
            phase_stats[phase_name] = {
                'avg_morty_count': statistics.mean(phase_counts),
                'median_morty_count': statistics.median(phase_counts),
                'distribution': {c: phase_counts.count(c) for c in set(phase_counts)},
                'trip_range': (start_idx + 1, end_idx),
            }
    
    # Success rate by morty count
    success_by_count = defaultdict(lambda: {'total': 0, 'successes': 0})
    for mission in mission_log:
        count = mission.get('morty_count', 0)
        if count > 0:
            success_by_count[count]['total'] += 1
            if mission.get('survived', False):
                success_by_count[count]['successes'] += 1
    
    success_rates = {}
    for count, stats in success_by_count.items():
        if stats['total'] > 0:
            success_rates[count] = {
                'survival_rate': (stats['successes'] / stats['total']) * 100,
                'trips': stats['total'],
                'successes': stats['successes'],
            }
    
    return {
        'overall': {
            'avg_morty_count': statistics.mean(morty_counts),
            'median_morty_count': statistics.median(morty_counts),
            'distribution': dict(count_distribution),
            'total_trips': len(morty_counts),
        },
        'by_planet': planet_stats,
        'by_phase': phase_stats,
        'success_by_count': success_rates,
    }


def analyze_streak_patterns(mission_log: List[Dict]) -> Dict:
    """
    Analyze success/failure streaks and planet switching patterns.
    
    Returns:
        Dictionary with streak analysis
    """
    if not mission_log:
        return {}
    
    # Analyze planet streaks
    planet_streaks = []
    current_planet = None
    streak_length = 0
    
    for mission in mission_log:
        planet = mission.get('planet', 0)
        if planet == current_planet:
            streak_length += 1
        else:
            if current_planet is not None:
                planet_streaks.append({
                    'planet': current_planet,
                    'length': streak_length,
                })
            current_planet = planet
            streak_length = 1
    
    # Add final streak
    if current_planet is not None:
        planet_streaks.append({
            'planet': current_planet,
            'length': streak_length,
        })
    
    # Analyze success streaks
    success_streaks = []
    current_success = None
    streak_length = 0
    
    for mission in mission_log:
        survived = mission.get('survived', False)
        if survived == current_success:
            streak_length += 1
        else:
            if current_success is not None:
                success_streaks.append({
                    'success': current_success,
                    'length': streak_length,
                })
            current_success = survived
            streak_length = 1
    
    if current_success is not None:
        success_streaks.append({
            'success': current_success,
            'length': streak_length,
        })
    
    return {
        'planet_streaks': {
            'avg_length': statistics.mean([s['length'] for s in planet_streaks]) if planet_streaks else 0,
            'max_length': max([s['length'] for s in planet_streaks]) if planet_streaks else 0,
            'total_streaks': len(planet_streaks),
        },
        'success_streaks': {
            'avg_success_streak': statistics.mean([s['length'] for s in success_streaks if s['success']]) if any(s['success'] for s in success_streaks) else 0,
            'avg_failure_streak': statistics.mean([s['length'] for s in success_streaks if not s['success']]) if any(not s['success'] for s in success_streaks) else 0,
            'max_success_streak': max([s['length'] for s in success_streaks if s['success']], default=0),
            'max_failure_streak': max([s['length'] for s in success_streaks if not s['success']], default=0),
        },
    }


def analyze_mission_patterns(mission_log: List[Dict]) -> Dict:
    """
    Analyze patterns in mission log to understand planet usage.
    
    Returns:
        Dictionary with analysis results
    """
    if not mission_log:
        return {}
    
    # Track planet usage by trip ranges
    planet_by_trip = {}
    transitions = []
    prev_planet = None
    
    for mission in mission_log:
        trip_num = mission.get('trip_number', 0)
        planet = mission.get('planet', 0)
        survived = mission.get('survived', False)
        
        planet_by_trip[trip_num] = {
            'planet': planet,
            'survived': survived,
            'morty_count': mission.get('morty_count', 0),
        }
        
        if prev_planet is not None and planet != prev_planet:
            transitions.append({
                'trip': trip_num,
                'from': prev_planet,
                'to': planet,
            })
        
        prev_planet = planet
    
    # Calculate planet usage by ranges
    planet_ranges = []
    if planet_by_trip:
        current_planet = planet_by_trip[min(planet_by_trip.keys())]['planet']
        range_start = min(planet_by_trip.keys())
        
        for trip_num in sorted(planet_by_trip.keys()):
            planet = planet_by_trip[trip_num]['planet']
            if planet != current_planet:
                planet_ranges.append({
                    'start': range_start,
                    'end': trip_num - 1,
                    'planet': current_planet,
                    'length': trip_num - range_start,
                })
                range_start = trip_num
                current_planet = planet
        
        # Add final range
        planet_ranges.append({
            'start': range_start,
            'end': max(planet_by_trip.keys()),
            'planet': current_planet,
            'length': max(planet_by_trip.keys()) - range_start + 1,
        })
    
    # Calculate survival rates by planet
    planet_stats = defaultdict(lambda: {'total': 0, 'successes': 0})
    for mission in mission_log:
        planet = mission.get('planet', 0)
        planet_stats[planet]['total'] += 1
        if mission.get('survived', False):
            planet_stats[planet]['successes'] += 1
    
    survival_rates = {}
    for planet, stats in planet_stats.items():
        survival_rates[planet] = (stats['successes'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    # Enhanced analysis
    temporal = analyze_temporal_performance(mission_log)
    transition_effectiveness = analyze_transition_effectiveness(mission_log)
    decay = analyze_planet_decay(mission_log)
    streaks = analyze_streak_patterns(mission_log)
    morty_analysis = analyze_morty_count_patterns(mission_log)
    
    return {
        'total_trips': len(mission_log),
        'planet_ranges': planet_ranges,
        'transitions': transitions,
        'num_transitions': len(transitions),
        'survival_rates': survival_rates,
        'planet_stats': dict(planet_stats),
        'temporal_performance': temporal,
        'transition_effectiveness': transition_effectiveness,
        'planet_decay': decay,
        'streak_patterns': streaks,
        'morty_count_analysis': morty_analysis,
    }


def analyze_strategy_performance(results: List[Dict]) -> Dict:
    """
    Analyze performance patterns across multiple runs of a strategy.
    
    Args:
        results: List of result dictionaries from benchmark
    
    Returns:
        Analysis dictionary
    """
    if not results:
        return {}
    
    valid_results = [r for r in results if 'error' not in r]
    if not valid_results:
        return {'error': 'No valid results'}
    
    # Aggregate mission patterns
    all_mission_logs = []
    for result in valid_results:
        mission_log = result.get('mission_log', [])
        all_mission_logs.extend(mission_log)
    
    # Analyze combined patterns
    combined_patterns = analyze_mission_patterns(all_mission_logs)
    
    # Calculate statistics
    survival_rates = [r['survival_rate'] for r in valid_results]
    
    # Calculate confidence interval (95%)
    if len(survival_rates) > 1:
        mean_rate = statistics.mean(survival_rates)
        stdev = statistics.stdev(survival_rates) if len(survival_rates) > 1 else 0
        # Simple approximation for small samples
        margin = 1.96 * stdev / (len(survival_rates) ** 0.5) if len(survival_rates) > 1 else 0
        ci_lower = mean_rate - margin
        ci_upper = mean_rate + margin
    else:
        mean_rate = survival_rates[0] if survival_rates else 0
        ci_lower = ci_upper = mean_rate
    
    return {
        'num_runs': len(valid_results),
        'avg_survival_rate': statistics.mean(survival_rates),
        'median_survival_rate': statistics.median(survival_rates),
        'stdev_survival_rate': statistics.stdev(survival_rates) if len(survival_rates) > 1 else 0,
        'min_survival_rate': min(survival_rates),
        'max_survival_rate': max(survival_rates),
        'variance': statistics.variance(survival_rates) if len(survival_rates) > 1 else 0,
        'ci_95_lower': ci_lower,
        'ci_95_upper': ci_upper,
        'combined_patterns': combined_patterns,
    }


def print_benchmark_analysis(benchmark_data: Dict):
    """
    Print detailed analysis of benchmark results.
    Analyzes all strategies in the benchmark file, including:
    - Dynamic Adaptive Strategy
    - Performance-Based Strategy
    - Windowed Performance Strategy
    - Any other strategies present in the benchmark data
    """
    print("="*60)
    print("BENCHMARK ANALYSIS")
    print("="*60)
    print(f"Timestamp: {benchmark_data['metadata']['timestamp']}")
    print(f"Strategies tested: {', '.join(benchmark_data['metadata']['strategies_tested'])}")
    print()
    
    # Analyze all strategies in the benchmark file
    for strategy_name, results in benchmark_data['results'].items():
        print("="*60)
        print(f"STRATEGY: {strategy_name}")
        print("="*60)
        
        analysis = analyze_strategy_performance(results)
        
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            continue
        
        print("\nPerformance Statistics:")
        print(f"  Number of runs: {analysis['num_runs']}")
        print(f"  Average survival rate: {analysis['avg_survival_rate']:.2f}%")
        print(f"  Median survival rate: {analysis['median_survival_rate']:.2f}%")
        print(f"  Standard deviation: {analysis['stdev_survival_rate']:.2f}%")
        print(f"  Range: {analysis['min_survival_rate']:.2f}% - {analysis['max_survival_rate']:.2f}%")
        print(f"  95% Confidence Interval: [{analysis['ci_95_lower']:.2f}%, {analysis['ci_95_upper']:.2f}%]")
        print(f"  Variance: {analysis['variance']:.2f}")
        
        patterns = analysis['combined_patterns']
        if patterns:
            print("\nPlanet Usage Patterns:")
            print(f"  Total trips analyzed: {patterns['total_trips']}")
            print(f"  Number of planet transitions: {patterns['num_transitions']}")
            
            print("\n  Survival rates by planet:")
            for planet in sorted(patterns['survival_rates'].keys()):
                rate = patterns['survival_rates'][planet]
                stats = patterns['planet_stats'][planet]
                print(f"    Planet {planet}: {rate:.2f}% ({stats['successes']}/{stats['total']} trips)")
            
            # Temporal performance
            if patterns.get('temporal_performance'):
                print("\n  Temporal Performance (Early/Mid/Late Game):")
                for seg_name, seg_data in patterns['temporal_performance'].items():
                    trip_range = seg_data['trip_range']
                    print(f"    {seg_name.replace('_', ' ').title()} (Trips {trip_range[0]}-{trip_range[1]}):")
                    for planet, perf in sorted(seg_data['planet_performance'].items()):
                        print(f"      Planet {planet}: {perf['survival_rate']:.2f}% ({perf['successes']}/{perf['trips']} trips)")
            
            # Transition effectiveness
            if patterns.get('transition_effectiveness', {}).get('num_transitions', 0) > 0:
                trans = patterns['transition_effectiveness']
                print("\n  Transition Effectiveness:")
                print(f"    Total transitions: {trans['num_transitions']}")
                print(f"    Average improvement per transition: {trans['avg_improvement']:.2f}%")
                print(f"    Positive transitions: {trans['positive_transitions']}/{trans['num_transitions']} ({trans['positive_transition_rate']:.1f}%)")
            
            # Planet decay
            if patterns.get('planet_decay'):
                print("\n  Planet Performance Decay:")
                for planet, decay_data in sorted(patterns['planet_decay'].items()):
                    print(f"    Planet {planet}:")
                    print(f"      Average decay: {decay_data['avg_decay']:.2f}%")
                    print(f"      Sequences analyzed: {decay_data['sequences']}")
                    print(f"      Average sequence length: {decay_data['avg_sequence_length']:.1f} trips")
            
            # Streak patterns
            if patterns.get('streak_patterns'):
                streaks = patterns['streak_patterns']
                print("\n  Streak Patterns:")
                if streaks.get('planet_streaks'):
                    ps = streaks['planet_streaks']
                    print("    Planet streaks:")
                    print(f"      Average length: {ps['avg_length']:.1f} trips")
                    print(f"      Maximum length: {ps['max_length']} trips")
                    print(f"      Total streaks: {ps['total_streaks']}")
                if streaks.get('success_streaks'):
                    ss = streaks['success_streaks']
                    print("    Success streaks:")
                    print(f"      Average success streak: {ss['avg_success_streak']:.1f} trips")
                    print(f"      Average failure streak: {ss['avg_failure_streak']:.1f} trips")
                    print(f"      Max success streak: {ss['max_success_streak']} trips")
                    print(f"      Max failure streak: {ss['max_failure_streak']} trips")
            
            # Morty count analysis
            if patterns.get('morty_count_analysis'):
                morty = patterns['morty_count_analysis']
                print("\n  Morty Count Analysis:")
                if morty.get('overall'):
                    overall = morty['overall']
                    print(f"    Overall average: {overall['avg_morty_count']:.2f} Morties per trip")
                    print(f"    Overall median: {overall['median_morty_count']:.1f} Morties per trip")
                    if overall.get('distribution'):
                        dist_str = ", ".join([f"{count} Morties: {freq} trips" for count, freq in sorted(overall['distribution'].items())])
                        print(f"    Distribution: {dist_str}")
                
                if morty.get('by_planet'):
                    print("\n    By Planet:")
                    for planet in sorted(morty['by_planet'].keys()):
                        pdata = morty['by_planet'][planet]
                        print(f"      Planet {planet}:")
                        print(f"        Average: {pdata['avg_morty_count']:.2f} Morties per trip")
                        print(f"        Median: {pdata['median_morty_count']:.1f} Morties per trip")
                        print(f"        Total Morties sent: {pdata['total_morties_sent']}")
                        if pdata.get('distribution'):
                            dist_str = ", ".join([f"{count}: {freq}" for count, freq in sorted(pdata['distribution'].items())])
                            print(f"        Distribution: {dist_str}")
                
                if morty.get('by_phase'):
                    print("\n    By Phase:")
                    for phase in ['early', 'mid', 'late']:
                        if phase in morty['by_phase']:
                            pdata = morty['by_phase'][phase]
                            trip_range = pdata.get('trip_range', (0, 0))
                            print(f"      {phase.title()} (Trips {trip_range[0]}-{trip_range[1]}):")
                            print(f"        Average: {pdata['avg_morty_count']:.2f} Morties per trip")
                            print(f"        Median: {pdata['median_morty_count']:.1f} Morties per trip")
                
                if morty.get('success_by_count'):
                    print("\n    Success Rate by Morty Count:")
                    for count in sorted(morty['success_by_count'].keys()):
                        sdata = morty['success_by_count'][count]
                        print(f"      {count} Morties: {sdata['survival_rate']:.2f}% "
                              f"({sdata['successes']}/{sdata['trips']} trips)")
            
            print("\n  Planet usage ranges:")
            for range_info in patterns['planet_ranges'][:10]:  # Show first 10 ranges
                print(f"    Trips {range_info['start']}-{range_info['end']}: "
                      f"Planet {range_info['planet']} ({range_info['length']} trips)")
            
            if len(patterns['planet_ranges']) > 10:
                print(f"    ... and {len(patterns['planet_ranges']) - 10} more ranges")
        
        # Analyze individual runs
        print("\n  Individual run details:")
        for result in results:
            if 'error' not in result:
                mission_log = result.get('mission_log', [])
                if mission_log:
                    run_patterns = analyze_mission_patterns(mission_log)
                    print(f"    Run {result['run_number']}: "
                          f"{result['survival_rate']:.2f}% survival, "
                          f"{run_patterns['num_transitions']} transitions, "
                          f"{len(run_patterns['planet_ranges'])} planet ranges")
        
        print()


def suggest_improvements(benchmark_data: Dict) -> Dict:
    """
    Suggest strategy improvements based on analysis.
    
    Returns:
        Dictionary with suggestions
    """
    suggestions = {}
    
    for strategy_name, results in benchmark_data['results'].items():
        analysis = analyze_strategy_performance(results)
        
        if 'error' in analysis:
            continue
        
        patterns = analysis['combined_patterns']
        if not patterns:
            continue
        
        strategy_suggestions = []
        
        # Check if strategy switches planets enough
        num_transitions = patterns.get('num_transitions', 0)
        total_trips = patterns.get('total_trips', 0)
        
        if num_transitions < total_trips * 0.01:  # Less than 1% transitions
            strategy_suggestions.append(
                f"Very few planet transitions ({num_transitions} transitions in {total_trips} trips). "
                f"Consider switching planets more frequently to adapt to changing conditions."
            )
        
        # Check transition effectiveness
        trans_eff = patterns.get('transition_effectiveness', {})
        if trans_eff.get('num_transitions', 0) > 0:
            if trans_eff.get('avg_improvement', 0) < -2:
                strategy_suggestions.append(
                    f"Transitions are degrading performance (avg {trans_eff['avg_improvement']:.2f}%). "
                    f"Consider being more selective about when to switch."
                )
            elif trans_eff.get('positive_transition_rate', 0) < 40:
                strategy_suggestions.append(
                    f"Only {trans_eff['positive_transition_rate']:.1f}% of transitions improve performance. "
                    f"Review transition logic."
                )
        
        # Check planet decay
        decay = patterns.get('planet_decay', {})
        for planet, decay_data in decay.items():
            if decay_data.get('avg_decay', 0) > 10:
                strategy_suggestions.append(
                    f"Planet {planet} shows significant decay ({decay_data['avg_decay']:.2f}%) over long sequences. "
                    f"Consider switching more frequently when using this planet."
                )
        
        # Check streak patterns
        streaks = patterns.get('streak_patterns', {})
        if streaks.get('planet_streaks', {}).get('max_length', 0) > 200:
            strategy_suggestions.append(
                f"Very long planet streak detected ({streaks['planet_streaks']['max_length']} trips). "
                f"Consider enforcing more frequent switches."
            )
        
        # Check if survival rates vary significantly by planet
        survival_rates = patterns.get('survival_rates', {})
        if len(survival_rates) >= 2:
            rates = list(survival_rates.values())
            rate_variance = statistics.variance(rates) if len(rates) > 1 else 0
            
            if rate_variance > 100:  # High variance
                best_planet = max(survival_rates.items(), key=lambda x: x[1])
                worst_planet = min(survival_rates.items(), key=lambda x: x[1])
                strategy_suggestions.append(
                    f"Significant difference in planet performance: "
                    f"Planet {best_planet[0]} ({best_planet[1]:.2f}%) vs "
                    f"Planet {worst_planet[0]} ({worst_planet[1]:.2f}%). "
                    f"Consider using Planet {best_planet[0]} more often."
                )
        
        # Check variance in results
        if analysis.get('variance', 0) > 100:
            strategy_suggestions.append(
                f"High variance in results ({analysis['variance']:.2f}). "
                f"Strategy may be too sensitive to randomness. Consider more consistent approach."
            )
        
        suggestions[strategy_name] = strategy_suggestions
    
    return suggestions


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_benchmark.py <benchmark_file.json>")
        sys.exit(1)
    
    filename = sys.argv[1]
    filehandle = filename.replace(".json", "")
    benchmark_data = load_benchmark(filename)
    
    analysis_file_path = f"data/analysis_{filehandle}.txt"
    print_benchmark_analysis(benchmark_data)
    
    print("\n" + "="*60)
    print("SUGGESTIONS FOR IMPROVEMENT")
    print("="*60)
    
    suggestions = suggest_improvements(benchmark_data)
    for strategy_name, strategy_suggestions in suggestions.items():
        if strategy_suggestions:
            print(f"\n{strategy_name}:")
            for suggestion in strategy_suggestions:
                print(f"  - {suggestion}")
        else:
            print(f"\n{strategy_name}: No specific suggestions (strategy looks good)")

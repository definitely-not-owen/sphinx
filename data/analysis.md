============================================================
BENCHMARK ANALYSIS
============================================================
Timestamp: 2025-11-16T00:48:32.778065
Strategies tested: Hybrid Control (Aggressive Payloads), Hybrid + Transition Enforcer, Hybrid + Planet 2 Priority, Hybrid + Schedule Guided

============================================================
STRATEGY: Hybrid Control (Aggressive Payloads)
============================================================

Performance Statistics:
  Number of runs: 3
  Average survival rate: 56.33%
  Median survival rate: 57.40%
  Standard deviation: 2.57%
  Range: 53.40% - 58.20%
  95% Confidence Interval: [53.42%, 59.24%]
  Variance: 6.61

Planet Usage Patterns:
  Total trips analyzed: 1150
  Number of planet transitions: 73

  Survival rates by planet:
    Planet 0: 50.84% (303/596 trips)
    Planet 1: 0.00% (0/2 trips)
    Planet 2: 60.14% (332/552 trips)

  Temporal Performance (Early/Mid/Late Game):
    Segment 1 (Trips 1-383):
      Planet 0: 50.00% (92/184 trips)
      Planet 1: 0.00% (0/2 trips)
      Planet 2: 51.78% (102/197 trips)
    Segment 2 (Trips 384-766):
      Planet 0: 53.74% (115/214 trips)
      Planet 2: 63.31% (107/169 trips)
    Segment 3 (Trips 767-1150):
      Planet 0: 48.48% (96/198 trips)
      Planet 2: 66.13% (123/186 trips)

  Transition Effectiveness:
    Total transitions: 73
    Average improvement per transition: 2.74%
    Positive transitions: 32/73 (43.8%)

  Planet Performance Decay:
    Planet 0:
      Average decay: -0.45%
      Sequences analyzed: 11
      Average sequence length: 40.0 trips
    Planet 2:
      Average decay: 4.50%
      Sequences analyzed: 10
      Average sequence length: 40.0 trips

  Streak Patterns:
    Planet streaks:
      Average length: 15.5 trips
      Maximum length: 40 trips
      Total streaks: 74
    Success streaks:
      Average success streak: 3.7 trips
      Average failure streak: 3.0 trips
      Max success streak: 34 trips
      Max failure streak: 36 trips

  Morty Count Analysis:
    Overall average: 2.61 Morties per trip
    Overall median: 3.0 Morties per trip
    Distribution: 1 Morties: 91 trips, 2 Morties: 268 trips, 3 Morties: 791 trips

    By Planet:
      Planet 0:
        Average: 2.75 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 1640
        Distribution: 1: 19, 2: 110, 3: 467
      Planet 1:
        Average: 3.00 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 6
        Distribution: 3: 2
      Planet 2:
        Average: 2.45 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 1354
        Distribution: 1: 72, 2: 158, 3: 322

    By Phase:
      Early (Trips 1-383):
        Average: 2.60 Morties per trip
        Median: 3.0 Morties per trip
      Mid (Trips 384-766):
        Average: 2.77 Morties per trip
        Median: 3.0 Morties per trip
      Late (Trips 767-1150):
        Average: 2.46 Morties per trip
        Median: 3.0 Morties per trip

    Success Rate by Morty Count:
      1 Morties: 37.36% (34/91 trips)
      2 Morties: 54.85% (147/268 trips)
      3 Morties: 57.40% (454/791 trips)

  Planet usage ranges:
    Trips 1-40: Planet 2 (40 trips)
    Trips 41-47: Planet 0 (7 trips)
    Trips 48-87: Planet 2 (40 trips)
    Trips 88-88: Planet 0 (1 trips)
    Trips 89-128: Planet 2 (40 trips)
    Trips 129-129: Planet 0 (1 trips)
    Trips 130-136: Planet 2 (7 trips)
    Trips 137-139: Planet 0 (3 trips)
    Trips 140-141: Planet 2 (2 trips)
    Trips 142-152: Planet 0 (11 trips)
    ... and 20 more ranges

  Individual run details:
    Run 1: 53.40% survival, 17 transitions, 18 planet ranges
    Run 2: 58.20% survival, 25 transitions, 26 planet ranges
    Run 3: 57.40% survival, 29 transitions, 30 planet ranges

============================================================
STRATEGY: Hybrid + Transition Enforcer
============================================================

Performance Statistics:
  Number of runs: 3
  Average survival rate: 50.53%
  Median survival rate: 50.60%
  Standard deviation: 3.50%
  Range: 47.00% - 54.00%
  95% Confidence Interval: [46.57%, 54.49%]
  Variance: 12.25

Planet Usage Patterns:
  Total trips analyzed: 1135
  Number of planet transitions: 117

  Survival rates by planet:
    Planet 0: 48.10% (165/343 trips)
    Planet 1: 52.35% (290/554 trips)
    Planet 2: 46.64% (111/238 trips)

  Temporal Performance (Early/Mid/Late Game):
    Segment 1 (Trips 1-378):
      Planet 0: 48.77% (159/326 trips)
      Planet 2: 48.08% (25/52 trips)
    Segment 2 (Trips 379-756):
      Planet 0: 35.71% (5/14 trips)
      Planet 1: 49.21% (124/252 trips)
      Planet 2: 44.64% (50/112 trips)
    Segment 3 (Trips 757-1135):
      Planet 0: 33.33% (1/3 trips)
      Planet 1: 54.97% (166/302 trips)
      Planet 2: 48.65% (36/74 trips)

  Transition Effectiveness:
    Total transitions: 117
    Average improvement per transition: -0.09%
    Positive transitions: 53/117 (45.3%)

  Streak Patterns:
    Planet streaks:
      Average length: 9.6 trips
      Maximum length: 20 trips
      Total streaks: 118
    Success streaks:
      Average success streak: 3.5 trips
      Average failure streak: 3.4 trips
      Max success streak: 22 trips
      Max failure streak: 44 trips

  Morty Count Analysis:
    Overall average: 2.64 Morties per trip
    Overall median: 3.0 Morties per trip
    Distribution: 1 Morties: 116 trips, 2 Morties: 173 trips, 3 Morties: 846 trips

    By Planet:
      Planet 0:
        Average: 2.73 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 937
        Distribution: 1: 13, 2: 66, 3: 264
      Planet 1:
        Average: 2.54 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 1406
        Distribution: 1: 78, 2: 100, 3: 376
      Planet 2:
        Average: 2.76 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 657
        Distribution: 1: 25, 2: 7, 3: 206

    By Phase:
      Early (Trips 1-378):
        Average: 2.71 Morties per trip
        Median: 3.0 Morties per trip
      Mid (Trips 379-756):
        Average: 2.54 Morties per trip
        Median: 3.0 Morties per trip
      Late (Trips 757-1135):
        Average: 2.68 Morties per trip
        Median: 3.0 Morties per trip

    Success Rate by Morty Count:
      1 Morties: 42.24% (49/116 trips)
      2 Morties: 48.55% (84/173 trips)
      3 Morties: 51.18% (433/846 trips)

  Planet usage ranges:
    Trips 1-20: Planet 2 (20 trips)
    Trips 21-21: Planet 0 (1 trips)
    Trips 22-41: Planet 2 (20 trips)
    Trips 42-42: Planet 0 (1 trips)
    Trips 43-62: Planet 2 (20 trips)
    Trips 63-82: Planet 1 (20 trips)
    Trips 83-83: Planet 2 (1 trips)
    Trips 84-103: Planet 1 (20 trips)
    Trips 104-104: Planet 2 (1 trips)
    Trips 105-124: Planet 1 (20 trips)
    ... and 28 more ranges

  Individual run details:
    Run 1: 47.00% survival, 39 transitions, 40 planet ranges
    Run 2: 50.60% survival, 43 transitions, 44 planet ranges
    Run 3: 54.00% survival, 33 transitions, 34 planet ranges

============================================================
STRATEGY: Hybrid + Planet 2 Priority
============================================================

Performance Statistics:
  Number of runs: 3
  Average survival rate: 48.67%
  Median survival rate: 49.30%
  Standard deviation: 1.27%
  Range: 47.20% - 49.50%
  95% Confidence Interval: [47.22%, 50.11%]
  Variance: 1.62

Planet Usage Patterns:
  Total trips analyzed: 1081
  Number of planet transitions: 7

  Survival rates by planet:
    Planet 0: 49.77% (531/1067 trips)
    Planet 2: 0.00% (0/14 trips)

  Temporal Performance (Early/Mid/Late Game):
    Segment 1 (Trips 1-360):
      Planet 0: 48.85% (170/348 trips)
      Planet 2: 0.00% (0/12 trips)
    Segment 2 (Trips 361-720):
      Planet 0: 49.86% (179/359 trips)
      Planet 2: 0.00% (0/1 trips)
    Segment 3 (Trips 721-1081):
      Planet 0: 50.56% (182/360 trips)
      Planet 2: 0.00% (0/1 trips)

  Transition Effectiveness:
    Total transitions: 7
    Average improvement per transition: 7.14%
    Positive transitions: 2/7 (28.6%)

  Planet Performance Decay:
    Planet 0:
      Average decay: -8.33%
      Sequences analyzed: 3
      Average sequence length: 355.3 trips

  Streak Patterns:
    Planet streaks:
      Average length: 135.1 trips
      Maximum length: 357 trips
      Total streaks: 8
    Success streaks:
      Average success streak: 3.3 trips
      Average failure streak: 3.5 trips
      Max success streak: 8 trips
      Max failure streak: 13 trips

  Morty Count Analysis:
    Overall average: 2.78 Morties per trip
    Overall median: 3.0 Morties per trip
    Distribution: 1 Morties: 54 trips, 2 Morties: 135 trips, 3 Morties: 892 trips

    By Planet:
      Planet 0:
        Average: 2.77 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 2958
        Distribution: 1: 54, 2: 135, 3: 878
      Planet 2:
        Average: 3.00 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 42
        Distribution: 3: 14

    By Phase:
      Early (Trips 1-360):
        Average: 2.71 Morties per trip
        Median: 3.0 Morties per trip
      Mid (Trips 361-720):
        Average: 2.80 Morties per trip
        Median: 3.0 Morties per trip
      Late (Trips 721-1081):
        Average: 2.81 Morties per trip
        Median: 3.0 Morties per trip

    Success Rate by Morty Count:
      1 Morties: 53.70% (29/54 trips)
      2 Morties: 55.56% (75/135 trips)
      3 Morties: 47.87% (427/892 trips)

  Planet usage ranges:
    Trips 1-1: Planet 2 (1 trips)
    Trips 2-368: Planet 0 (367 trips)

  Individual run details:
    Run 1: 47.20% survival, 3 transitions, 4 planet ranges
    Run 2: 49.50% survival, 1 transitions, 2 planet ranges
    Run 3: 49.30% survival, 1 transitions, 2 planet ranges

============================================================
STRATEGY: Hybrid + Schedule Guided
============================================================

Performance Statistics:
  Number of runs: 3
  Average survival rate: 52.63%
  Median survival rate: 52.40%
  Standard deviation: 0.68%
  Range: 52.10% - 53.40%
  95% Confidence Interval: [51.86%, 53.40%]
  Variance: 0.46

Planet Usage Patterns:
  Total trips analyzed: 1151
  Number of planet transitions: 161

  Survival rates by planet:
    Planet 0: 53.01% (299/564 trips)
    Planet 1: 46.67% (154/330 trips)
    Planet 2: 61.48% (158/257 trips)

  Temporal Performance (Early/Mid/Late Game):
    Segment 1 (Trips 1-383):
      Planet 0: 12.50% (1/8 trips)
      Planet 1: 48.59% (121/249 trips)
      Planet 2: 70.63% (89/126 trips)
    Segment 2 (Trips 384-766):
      Planet 0: 50.71% (107/211 trips)
      Planet 1: 40.68% (24/59 trips)
      Planet 2: 55.75% (63/113 trips)
    Segment 3 (Trips 767-1151):
      Planet 0: 55.36% (191/345 trips)
      Planet 1: 40.91% (9/22 trips)
      Planet 2: 33.33% (6/18 trips)

  Transition Effectiveness:
    Total transitions: 161
    Average improvement per transition: 8.28%
    Positive transitions: 82/161 (50.9%)

  Planet Performance Decay:
    Planet 0:
      Average decay: 1.43%
      Sequences analyzed: 7
      Average sequence length: 40.0 trips
    Planet 1:
      Average decay: -5.00%
      Sequences analyzed: 3
      Average sequence length: 41.0 trips
    Planet 2:
      Average decay: 15.00%
      Sequences analyzed: 1
      Average sequence length: 40.0 trips

  Streak Patterns:
    Planet streaks:
      Average length: 7.1 trips
      Maximum length: 42 trips
      Total streaks: 162
    Success streaks:
      Average success streak: 3.3 trips
      Average failure streak: 3.0 trips
      Max success streak: 28 trips
      Max failure streak: 16 trips

  Morty Count Analysis:
    Overall average: 2.61 Morties per trip
    Overall median: 3.0 Morties per trip
    Distribution: 1 Morties: 97 trips, 2 Morties: 259 trips, 3 Morties: 795 trips

    By Planet:
      Planet 0:
        Average: 2.82 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 1589
        Distribution: 1: 14, 2: 75, 3: 475
      Planet 1:
        Average: 2.66 Morties per trip
        Median: 3.0 Morties per trip
        Total Morties sent: 878
        Distribution: 1: 37, 2: 38, 3: 255
      Planet 2:
        Average: 2.07 Morties per trip
        Median: 2.0 Morties per trip
        Total Morties sent: 533
        Distribution: 1: 46, 2: 146, 3: 65

    By Phase:
      Early (Trips 1-383):
        Average: 2.40 Morties per trip
        Median: 3.0 Morties per trip
      Mid (Trips 384-766):
        Average: 2.66 Morties per trip
        Median: 3.0 Morties per trip
      Late (Trips 767-1151):
        Average: 2.76 Morties per trip
        Median: 3.0 Morties per trip

    Success Rate by Morty Count:
      1 Morties: 47.42% (46/97 trips)
      2 Morties: 62.55% (162/259 trips)
      3 Morties: 50.69% (403/795 trips)

  Planet usage ranges:
    Trips 1-4: Planet 0 (4 trips)
    Trips 5-6: Planet 1 (2 trips)
    Trips 7-7: Planet 2 (1 trips)
    Trips 8-10: Planet 1 (3 trips)
    Trips 11-12: Planet 0 (2 trips)
    Trips 13-13: Planet 1 (1 trips)
    Trips 14-20: Planet 0 (7 trips)
    Trips 21-21: Planet 2 (1 trips)
    Trips 22-23: Planet 0 (2 trips)
    Trips 24-24: Planet 2 (1 trips)
    ... and 36 more ranges

  Individual run details:
    Run 1: 52.10% survival, 45 transitions, 46 planet ranges
    Run 2: 52.40% survival, 78 transitions, 79 planet ranges
    Run 3: 53.40% survival, 36 transitions, 37 planet ranges


============================================================
SUGGESTIONS FOR IMPROVEMENT
============================================================

Hybrid Control (Aggressive Payloads):
  - Significant difference in planet performance: Planet 2 (60.14%) vs Planet 1 (0.00%). Consider using Planet 2 more often.

Hybrid + Transition Enforcer: No specific suggestions (strategy looks good)

Hybrid + Planet 2 Priority:
  - Very few planet transitions (7 transitions in 1081 trips). Consider switching planets more frequently to adapt to changing conditions.
  - Only 28.6% of transitions improve performance. Review transition logic.
  - Very long planet streak detected (357 trips). Consider enforcing more frequent switches.
  - Significant difference in planet performance: Planet 0 (49.77%) vs Planet 2 (0.00%). Consider using Planet 0 more often.

Hybrid + Schedule Guided:
  - Planet 2 shows significant decay (15.00%) over long sequences. Consider switching more frequently when using this planet.

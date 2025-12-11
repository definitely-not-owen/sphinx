# Morty Express Challenge Solution

A data-driven solution for the Morty Express coding challenge. This project implements an adaptive algorithm to maximize Morty survival rates by analyzing how planet probabilities change over time.

## Project Structure

- `main.py` - Core API functions for interacting with the challenge API
- `explore.py` - Data collection script to run exploration experiments
- `analyze.py` - Data analysis and visualization script
- `solve.py` - Adaptive solution algorithm
- `data/` - Directory for storing experiment results and visualizations

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```
AUTH_TOKEN=your_bearer_token_here
```

## Usage

### Phase 1: Data Collection

Run exploration experiments to collect data on how each planet's survival probability changes over time:

```bash
python explore.py
```

This will:
- Run 3 full episodes (one per planet)
- Send all 1000 Morties through each planet
- Save experiment data to `data/` directory
- Track survival rates at each trip

### Phase 2: Data Analysis

Analyze the collected data to identify patterns:

```bash
python analyze.py
```

This will:
- Load the latest experiment data for each planet
- Calculate survival rate trends and rates of change
- Generate comparison visualizations
- Identify which planets change fastest/slowest

### Phase 3: Run Solution

Run the adaptive solution algorithm:

```bash
python solve.py
```

The solution uses:
- **Exploration phase**: Tests all planets to gather data
- **Adaptive selection**: Chooses best planet based on observed survival rates
- **Time-based switching**: Can switch planets at optimal trip numbers

## Strategy

Based on Rick's hint:
> "although the average survival rate is the same, the probabilities of the 3 planets are changing with time. Time being the number of trips. Some change faster than others."

The solution:
1. **Collects data** by running full episodes for each planet
2. **Analyzes patterns** to understand how probabilities change
3. **Adapts strategy** to use the best planet at each point in time

## Customization

After running analysis, you can customize the solution in `solve.py`:

- Adjust `exploration_trips` parameter to change exploration duration
- Modify `adaptive_get_best_planet()` based on discovered patterns
- Use `run_time_based_strategy()` with custom switch points from analysis

## Goal

Maximize survival rate (aim for 93%+ to compete with top leaderboard scores).


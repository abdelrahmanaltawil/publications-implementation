# Steady State Analysis Module

After running a simulation, we need to identify when the flow has **reached steady state** — when statistical properties stop changing in time. This module handles that analysis.

---

## Why Do We Need This?

Simulations start from random initial conditions. Early on, the flow is in a **transient phase** — it's still evolving toward its natural state. We only want to analyze data from the **steady state** where the flow has settled.

```
                    ┌─────────────────────────
                    │   Steady State
        Energy      │   (analyze this!)
          │    ─────┘
          │   ╱
          │  ╱
          │ ╱
          └──────────────────────────────── time
             ↑_____↑
             Transient
            (discard this)
```

---

## What This Module Does

1. **Downloads** simulation data from Neptune.ai
2. **Identifies** when steady state begins (using energy metrics)
3. **Selects** appropriate snapshots for further analysis
4. **Creates** diagnostic plots to verify stationarity

---

## Workflow Diagram

```mermaid
flowchart TB
    subgraph pre[Preprocessing]
        parse[Load configuration]
        fetch[Connect to Neptune.ai]
        download[Download simulation metadata]
        load[Load monitoring table & snapshots]
    end
    
    subgraph analysis[Analysis]
        check[Check E(k=1) convergence]
        select[Select steady-state snapshots]
    end
    
    subgraph post[Postprocessing]
        upload[Upload results to Neptune]
        plots[Generate diagnostic plots]
    end
    
    pre --> analysis --> post
```

---

## How Steady State is Detected

We look at the energy at wavenumber k=1, called **E(k=1)**. This large-scale energy is sensitive to whether the system has equilibrated.

**Criteria for steady state:**
- E(k=1) has stopped growing
- Fluctuations are around a stable mean
- At least ~50,000 iterations have passed (for default parameters)

---

## Configuration

Edit `parameters/steady_state_analysis.yml`:

```yaml
preprocessing:
  experiment_ID: AC-123    # Neptune run ID from simulation
  download_path: ./data/steady_state_analysis

postprocessing:
  save_path: ./data/steady_state_analysis
```

---

## Running the Analysis

```bash
cd src/steady_state_analysis
python workflow.py
```

---

## Output Plots

### 1. Snapshot Locations

Shows which time points were selected as steady-state:

```
 Iteration
    │  ●  ●  ●  ●  ●  ●  ●  ●  ← Selected snapshots
    │
    │  ○  ○  ○  ○  ← Transient (excluded)
    └────────────────────────── time
```

### 2. Field Visualizations

For each selected snapshot:
- **Vorticity field** ω(x, y) — the spinning
- **Velocity magnitude** |u|(x, y) — how fast
- **Stream function** ψ(x, y) — flow lines

### 3. Energy Spectra

E(k) at different times to confirm stationarity:

```
 E(k)
   │ ╲
   │  ╲
   │   ╲────────────
   │                ╲ 
   └─────────────────── k

   All curves should overlap in steady state!
```

---

## Tips

- **Check the convergence plot first**: If E(k=1) is still rising, run the simulation longer
- **Use multiple snapshots**: Averaging over ~10-20 snapshots improves statistics
- **Keep the run ID**: You'll need it for the next stage (Extrema Search)

---

## Related Documentation

- [Simulation Module](simulation.md) — How to generate the data
- [Extrema Search](extrema_search.md) — Next step in the pipeline

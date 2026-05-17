# Decoupled Day-Ahead Operational Models: Water and Energy

Two independent MILP formulations for day-ahead operational management, staying close to the constraint sets of the source papers. Both run over horizon $t = 1, \dots, T$ with $T = 24$ and $\Delta t = 1$ h. All physical asset capacities and topology are **fixed inputs**; only operational variables are optimized.

- **Water model:** Thomas & Sela (2024), *MILPNet* — including tanks, pumps, gate valves, PRVs, tank-link status checks, event-based and time-based control rules.
- **Energy model:** Morvaj et al. (2016) — energy-hub formulation with linearized AC power flow constraints on the distribution grid.

Big-$M$ values and small $\varepsilon$ are tightly chosen per constraint group as in MILPNet. The papers' subscripts and naming conventions are preserved where possible.

---

## 1. Water Distribution System (MILPNet)

### 1.1 Sets

| Symbol | Description |
|---|---|
| $\mathcal{N}$ | All nodes |
| $\mathcal{J} \subset \mathcal{N}$ | Demand junctions, indexed $i$ |
| $\mathcal{K} \subset \mathcal{N}$ | Tanks, indexed $tk$ |
| $\mathcal{R} \subset \mathcal{N}$ | Reservoirs |
| $\mathcal{L}$ | Pipes, indexed $l$ |
| $\mathcal{P}$ | Pumps, indexed $p$ |
| $\mathcal{G}$ | Gate valves, indexed $g$ |
| $\mathcal{V}$ | Pressure-reducing valves, indexed $v$ |
| $\mathcal{TL}$ | Tank-links (links incident to tanks), indexed $tl$ |
| $\mathcal{CL}$ | Control-links (links subject to control rules), indexed $cl$ |
| $\mathcal{T}$ | Time steps |

### 1.2 Parameters

| Symbol | Description |
|---|---|
| $d_i^t$ | Demand at junction $i$ in hour $t$ |
| $H_r^t$ | Reservoir head at $r$ in hour $t$ |
| $K_l, e_1$ | Hazen-Williams coefficient and exponent ($e_1 = 1.852$) |
| $A, B$ | Pump head-curve constants ($\Delta H = A - B Q^2$) |
| $A_{tk}$ | Cross-sectional area of tank $tk$ |
| $H_{tk}^{\max}, H_{tk}^{\min}$ | Tank capacity bounds |
| $H_{tk}^{0}$ | Initial tank head |
| $H_{set}$ | PRV head setting |
| $H_{ul}, H_{ll}$ | Upper and lower control levels (event-based rules) |
| $T_1, T_2, T_3, \dots$ | Time-based control switch times |
| $c_k^t$ | Pump operating cost coefficient at $t$ under tariff $k$ |
| $\bar{p}$ | Switching penalty coefficient |
| $M_1, M_2, M_3, M_4, M_5, M_6$ | Tightly chosen big-$M$ values per device group |
| $\varepsilon$ | Small positive constant for strict-inequality handling |
| $n_p$ | Number of PWL segments for pipe head loss |
| $n_{pu}$ | Number of PWL segments for pump curves |

### 1.3 Decision Variables (Table 1 of MILPNet)

| Symbol | Type | Description |
|---|---|---|
| $Q_{\{l,p,g,v,tl,cl\}}^t$ | continuous | Flow in the corresponding link |
| $H_{\{i,tk\}}^t$ | continuous | Head at junction $i$ or tank $tk$ |
| $\Delta H_{\{l,p,g,v,tl,cl\}}^t$ | continuous | Head loss / gain across the link |
| $u_{\{p,g,v,tl,cl\}}^t$ | continuous | Slack on energy balance to permit link closure |
| $w_v^t$ | continuous $\geq 0$ | Slack for additional head loss when PRV is *active* |
| $y_{\{p,g,tl,cl\}}^t$ | binary | ON/OFF (open/closed) status |
| $v_1^t, v_2^t, v_3^t$ | binary | PRV state (active / open / closed) |
| $x_1^t, x_2^t$ | binary | Auxiliary, tank-link status check |
| $z_1^t, z_2^t, z_3^t$ | binary | Auxiliary, event-based control rule |
| $y_{sw}^t$ | binary | Pump switching indicator (objective only) |

### 1.4 System Hydraulics

**(W1) Mass balance at every node** (Eq. 1):

$$
\sum_{j=1}^{N} Q_l^t = d_i^t, \qquad \forall i \in \mathcal{J}, \; \forall t \in \mathcal{T}
$$

where the sum is over links $l$ adjacent to node $i$ (sign convention: outflow positive).

**(W2) Energy conservation along pipes** (Eq. 2):

$$
H_i^t - H_j^t - \Delta H_l^t = 0, \qquad \forall l = (i,j) \in \mathcal{L}, \; \forall t
$$

**(W3) Hazen–Williams head loss, piecewise-linearized** (Eq. 3):

$$
\Delta H_l^t = \mathrm{sgn}(Q_l^t) \, K_l \, |Q_l^t|^{e_1}, \qquad K_l = \frac{\alpha L_l}{C_l^{e_1} D_l^{e_2}}
$$

Approximated with $n_p$ piecewise-linear segments. Bidirectional flow is handled by the sign function within the PWL representation.

### 1.5 Tanks (Eq. 4)

**(W4) Tank mass balance:**

$$
H_{tk}^t = H_{tk}^{t-1} + \frac{Q_{tl}^{t-1}}{A_{tk}} \Delta t, \qquad \forall tk \in \mathcal{K}, \; \forall t \geq 1
$$

with $H_{tk}^0$ given.

### 1.6 Pumps (Eqs. 5–7 and Eq. 10 in Figure 2)

**(W5) Energy balance over pump $p = (i, j)$** with closure slack:

$$
\Delta H_p^t - H_j^t + H_i^t - u_p^t = 0
$$

**(W6) Pump head-flow curve** (PWL approximation of $A - B(Q_p^t)^2$ with $n_{pu}$ segments), active only when ON:

$$
\Delta H_p^t = \mathrm{PWL}\big(A - B (Q_p^t)^2\big) \quad \text{when } y_p^t = 0
$$

**(W7) Big-$M$ disjunction for pump state** (Eq. 10):

$$
\begin{aligned}
-M_1\, y_p^t \;\leq\; u_p^t &\;\leq\; M_1\, y_p^t \\
0 \;\leq\; Q_p^t &\;\leq\; M_1\, (1 - y_p^t)
\end{aligned}
$$

Reading: $y_p^t = 0$ means *open* — $u_p^t = 0$ and pump head gain governs the head difference; $y_p^t = 1$ means *closed* — $Q_p^t = 0$ and $u_p^t$ floats freely to disconnect the two nodes. The lower bound $Q_p^t \geq 0$ implicitly prevents back-flow.

### 1.7 Gate Valves (Eqs. 8 and 11 in Figure 2)

**(W8) Energy balance over GV $g = (i, j)$:**

$$
\Delta H_g^t - H_i^t + H_j^t - u_g^t = 0
$$

with head loss following the Hazen-Williams form when *open*:

$$
\Delta H_g^t = \mathrm{sgn}(Q_g^t) K_g |Q_g^t|^{e_1} \quad \text{when } y_g^t = 0
$$

**(W9) Big-$M$ disjunction for GV state** (Eq. 11):

$$
\begin{aligned}
-M_2\, y_g^t \;\leq\; u_g^t &\;\leq\; M_2\, y_g^t \\
-M_2(1 - y_g^t) \;\leq\; Q_g^t &\;\leq\; M_2(1 - y_g^t)
\end{aligned}
$$

Unlike pumps, gate valves allow flow in both directions when open.

### 1.8 Pressure-Reducing Valves (Eqs. 9 and 12 in Figure 2)

**(W10) Modified energy balance over PRV $v = (i, j)$:**

$$
\Delta H_v^t - H_i^t + H_j^t - u_v^t + w_v^t = 0
$$

**(W11) PRV state assignment** — exactly one state per time step:

$$
v_1^t + v_2^t + v_3^t = 1
$$

with $v_1^t = 1$ → *active*, $v_2^t = 1$ → *open*, $v_3^t = 1$ → *closed*.

**(W12) PRV state logic** (Eq. 12, full big-$M$ formulation):

$$
\begin{aligned}
H_{set}\, v_1^t - M_3(v_2^t + v_3^t) &\leq H_j^t \\
H_{set}\, v_1^t + M_3(v_2^t + v_3^t) &\geq H_j^t \\
-M_3(1 - v_2^t + v_1^t) + \varepsilon v_2^t &\leq H_{set} - H_i^t \\
M_3(1 - v_1^t + v_2^t) &\geq H_{set} - H_i^t \\
-M_3 v_3^t &\leq H_i^t - H_j^t \\
M_3(1 - v_3^t) - \varepsilon v_3^t &\geq H_i^t - H_j^t
\end{aligned}
$$

Flow and slack consistency:

$$
\begin{aligned}
0 \;\leq\; w_v^t &\;\leq\; M_3\, v_1^t \\
-M_3(1 - v_1^t) \;\leq\; u_v^t &\;\leq\; M_3(1 - v_1^t) \\
-M_3(1 - v_2^t) \;\leq\; u_v^t &\;\leq\; M_3(1 - v_2^t) \\
-M_3 v_3^t \;\leq\; u_v^t &\;\leq\; M_3 v_3^t \\
-M_3(1 - v_1^t) &\;<\; Q_v^t \\
-M_3(1 - v_2^t) &\;<\; Q_v^t \\
-M_3(1 - v_3^t) \;\leq\; Q_v^t &\;\leq\; M_3(1 - v_3^t)
\end{aligned}
$$

Logic summary:
- $H_i^t > H_{set} > H_j^t$: PRV *active*, additional head loss $w_v^t > 0$ enforces $H_j^t = H_{set}$, $Q_v^t > 0$.
- $H_{set} > H_i^t > H_j^t$: PRV *open*, $H_j^t = H_i^t$, $Q_v^t > 0$, no extra loss.
- $H_j^t > H_i^t$: PRV *closed*, $Q_v^t = 0$, nodes disconnected.

### 1.9 Tank-Link Status Check (Eq. 13 in Figure 5)

For each tank-link $tl$ with associated tank $tk$:

**(W13) Energy balance:**

$$
\Delta H_{tl}^t = H_i^t - H_j^t + u_{tl}^t, \qquad \Delta H_{tl}^t = \mathrm{sgn}(Q_{tl}^t) K_{tl} |Q_{tl}^t|^{e_1}
$$

**(W14) Tank-level region detection:**

$$
\begin{aligned}
H_{tk}^{\max} - M_4(1 - x_1^t) &\leq H_{tk}^{t-1} \\
H_{tk}^{\max} + M_4\, x_1^t &> H_{tk}^{t-1} \\
H_{tk}^{\min} - M_4(1 - x_2^t) &< H_{tk}^{t-1} \\
H_{tk}^{\min} + M_4\, x_2^t &\geq H_{tk}^{t-1}
\end{aligned}
$$

Reading: $x_1^t = 1$ iff tank is at or above max; $x_2^t = 1$ iff tank is above min.

**(W15) Tank-link status:**

$$
x_1^t - x_2^t + 1 = y_{tl}^t
$$

So $y_{tl}^t = 1$ (link closed) iff the tank is full ($x_1 = 1, x_2 = 1$) OR empty ($x_1 = 0, x_2 = 0$); $y_{tl}^t = 0$ (link open) iff strictly between bounds.

**(W16) Big-$M$ disjunction on tank-link:**

$$
\begin{aligned}
-M_2\, y_{tl}^t \;\leq\; u_{tl}^t &\;\leq\; M_2\, y_{tl}^t \\
-M_2(1 - y_{tl}^t) \;\leq\; Q_{tl}^t &\;\leq\; M_2(1 - y_{tl}^t)
\end{aligned}
$$

### 1.10 Event-Based Control Rules (Eq. 14 in Figure 5)

For each control-link $cl$ paired with a tank $tk$ via levels $H_{ul}$ and $H_{ll}$:

**(W17) Energy balance:**

$$
\Delta H_{cl}^t = H_i^t - H_j^t + u_{cl}^t, \qquad \Delta H_{cl}^t = \mathrm{sgn}(Q_{cl}^t) K_{cl} |Q_{cl}^t|^{e_1}
$$

**(W18) Threshold-crossing detection:**

$$
\begin{aligned}
H_{ul} - M_5(1 - z_1^t) &\leq H_{tk}^{t-1} \\
H_{ul} + M_5\, z_1^t &> H_{tk}^{t-1} \\
H_{ll} - M_5(1 - z_2^t) &< H_{tk}^{t-1} \\
H_{ll} + M_5\, z_2^t &\geq H_{tk}^{t-1}
\end{aligned}
$$

**(W19) Rule-state propagation:**

$$
z_2^t - z_1^t = z_3^t
$$

**(W20) Control-link status update** (depends on previous-step status $y_{cl}^{t-1}$ — this is what makes the rule *latching*):

$$
\begin{aligned}
y_{cl}^{t-1} + 2 z_1^t + z_3^t - 2 &\geq M_6(y_{cl}^t - 1) \\
y_{cl}^{t-1} + 2 z_1^t + z_3^t - 2 &< M_6\, y_{cl}^t
\end{aligned}
$$

**(W21) Big-$M$ disjunction on control-link:**

$$
\begin{aligned}
-M_2\, y_{cl}^t \;\leq\; u_{cl}^t &\;\leq\; M_2\, y_{cl}^t \\
-M_2(1 - y_{cl}^t) \;\leq\; Q_{cl}^t &\;\leq\; M_2(1 - y_{cl}^t)
\end{aligned}
$$

Reading: link closes once $H_{tk} \geq H_{ul}$; stays closed until $H_{tk} \leq H_{ll}$; then re-opens.

### 1.11 Time-Based Control Rules (Eq. 15 in Figure 5)

For a control-link $cl$ with prescribed switch times $T_1 < T_2 < T_3 < \dots$:

**(W22) Energy balance** — same form as (W17).

**(W23) Hard schedule on status:**

$$
y_{cl}^t = \begin{cases}
0 & t = 1, \dots, T_1 \\
1 & t = T_1, \dots, T_2 \\
0 & t = T_2, \dots, T_3 \\
1 & t = T_3, \dots \\
\vdots
\end{cases}
$$

**(W24) Big-$M$ disjunction** — same form as (W21).

### 1.12 Objective: Day-Ahead Pump Scheduling (Eq. 16)

Minimize energy cost plus pump-switching penalty:

$$
\boxed{
\min \; f = \sum_{t=1}^{T} \sum_{p \in \mathcal{P}} c_k^t \big(1 - y_p^t\big) \;+\; \bar{p} \sum_{t=1}^{T-1} \sum_{p \in \mathcal{P}} y_{sw}^{p,t}
}
$$

with switch-counting linearization:

$$
y_{sw}^{p,t} \geq y_p^{t+1} - y_p^t, \qquad y_{sw}^{p,t} \geq y_p^t - y_p^{t+1}
$$

Note the paper's convention: $y_p^t = 0$ means pump *open* (operating), $y_p^t = 1$ means *closed*; hence the factor $(1 - y_p^t)$ on the cost.

### 1.13 Complete Day-Ahead Water Problem

$$
\begin{aligned}
\min \; & f \quad \text{(Eq. 16)} \\
\text{s.t.} \quad & \text{(W1)–(W4)} && \text{hydraulics} \\
& \text{(W5)–(W12)} && \text{hydraulic devices: pumps, GVs, PRVs} \\
& \text{(W13)–(W16)} && \text{tank-link status checks} \\
& \text{(W17)–(W24)} && \text{event- and time-based control rules}
\end{aligned}
$$

---

## 2. Distributed Energy System with Grid Constraints (Morvaj et al., 2016)

The model has two coupled layers:

1. **Energy hub layer** — per-building dispatch of conversion and storage technologies meeting electricity and heat demand.
2. **Distribution grid layer** — linearized AC power flow over the LV feeder connecting the buildings, including bus voltages, line currents, and active/reactive flows.

### 2.1 Sets

| Symbol | Description |
|---|---|
| $\mathcal{B}$ | Buildings / energy-hub nodes, indexed $i$ |
| $\mathcal{C}$ | Conversion technologies (CHP, gas boiler, PV, heat pump, …), indexed $c$ |
| $\mathcal{S}$ | Energy storages (electric, thermal), indexed $s$ |
| $\mathcal{T}$ | Time steps |
| $\mathcal{N}$ | Electrical buses |
| $\mathcal{E} \subseteq \mathcal{N} \times \mathcal{N}$ | Distribution lines, indexed $(n,m)$ |
| $ota$ | Technologies producing/consuming active power |
| $otr$ | Technologies producing/consuming reactive power |

### 2.2 Parameters

**Energy hub:**

| Symbol | Description |
|---|---|
| $L_{i,t}^{load}$ | Electric (active) demand at building $i$ in $t$ |
| $H_{i,t}^{load}$ | Heat demand at building $i$ in $t$ |
| $QL_{i,t}^{load}$ | Reactive electric demand at $i$ in $t$ |
| $\mathbf{H}_{tech}$ | Conversion-efficiency matrix (inputs → outputs) |
| $\eta_s^{ch}, \eta_s^{dis}$ | Storage charge / discharge efficiency |
| $\overline{P}_c^{cap}$ | Installed capacity of technology $c$ (given input) |
| $\overline{E}_s^{cap}, \overline{Q}_s^{cap}$ | Storage energy capacity and rate cap |
| $E_s^0$ | Initial state of charge |
| $C_k$ | Cost or emission factor for input stream $k$ |
| $r_t^{PV}$ | PV irradiance factor in $t$ |

**Grid:**

| Symbol | Description |
|---|---|
| $G_{nm}, B_{nm}$ | Line conductance and susceptance |
| $R_{nm}, X_{nm}$ | Line resistance and reactance |
| $U_0$ | Linearization point for voltage magnitude (≈ 1.0 p.u.) |
| $\underline{U}, \overline{U}$ | Voltage magnitude bounds (e.g. $\pm 10\%$ of nominal) |
| $\overline{I}_{nm}$ | Nominal current limit of line $(n,m)$ |
| $N^{seg}$ | Number of PWL segments for current magnitude approximation |

### 2.3 Decision Variables

**Energy hub** (per building $i$, hour $t$):

| Symbol | Type | Description |
|---|---|---|
| $\mathbf{P}_{tech}(i, t)$ | continuous $\geq 0$ | Dispatch vector of conversion technologies |
| $Q_{stor}^{ch}(i, t), Q_{stor}^{dis}(i, t)$ | continuous $\geq 0$ | Storage charge / discharge |
| $E_{stor}^{SOC}(i, t)$ | continuous $\geq 0$ | State of charge |
| $P_{grid}^{import}(i, t)$ | continuous $\geq 0$ | Electricity import from grid |
| $P_{grid}^{export}(i, t)$ | continuous $\geq 0$ | Electricity export to grid |
| $P_k^{input}(i, t)$ | continuous $\geq 0$ | Primary input stream $k$ (gas, etc.) |

**Grid** (per line, bus, hour):

| Symbol | Type | Description |
|---|---|---|
| $P\big((n,m), t\big), Q\big((n,m), t\big)$ | continuous, free | Active / reactive flow on line |
| $\Delta U_{nm, t}, \Delta \theta_{nm, t}$ | continuous, free | Voltage and angle differences |
| $U_n^t, \theta_n^t$ | continuous | Voltage magnitude and angle at bus $n$ |
| $\mathrm{Re}(I_{nm,t}), \mathrm{Im}(I_{nm,t})$ | continuous, free | Real / imaginary parts of line current |
| $\phi_{nm,t}, \chi_{nm,t}$ | continuous $\geq 0$ | Absolute values of the above |
| $\lambda^n_{nm,t}$ | continuous $\geq 0$ | PWL convex weights for current magnitude |

### 2.4 Energy Hub Balances (Eqs. 1–3)

**(E1) Electricity balance at each building $i$** (Eq. 1):

$$
L_{i,t}^{load} = P_{grid}^{import}(i,t) + \mathbf{H}_{tech} \cdot \mathbf{P}_{tech}(i,t) - P_{grid}^{export}(i,t) + \eta_s^{dis} Q_{stor}^{dis}(i,t) - \eta_s^{ch} Q_{stor}^{ch}(i,t)
$$

The matrix product picks out electricity-producing/consuming technologies (e.g. CHP electrical output, PV, heat pump).

**(E2) Heat balance at each building $i$** (Eq. 2):

$$
H_{i,t}^{load} = \mathbf{H}_{tech} \cdot \mathbf{P}_{tech}(i,t) + \eta_s^{dis} Q_{stor}^{dis}(i,t) - \eta_s^{ch} Q_{stor}^{ch}(i,t)
$$

(applied to heat-producing technologies and thermal storages).

**(E3) Storage continuity** (Eq. 3, paper's form):

$$
E_{stor}^{SOC}(i, t+1) = E_{stor}^{SOC}(i, t) + \eta_s^{dis} Q_{stor}^{dis}(i,t) - \eta_s^{ch} Q_{stor}^{ch}(i,t)
$$

> **Convention note:** as written in the paper. Standard physical convention has charging *increase* SoC and discharging decrease it; double-check sign consistency against your chosen convention for (E1)–(E2) when implementing.

**(E4) Operational constraints — capacity, exclusivity, PV cap:**

$$
\begin{aligned}
0 \leq P_{tech}(i,t) &\leq \overline{P}_c^{cap}, \quad \forall c, \forall i, \forall t \\
P_{PV}(i,t) &\leq r_t^{PV} \cdot \overline{P}_{PV}^{cap} \\
0 \leq E_{stor}^{SOC}(i,t) &\leq \overline{E}_s^{cap} \\
0 \leq Q_{stor}^{ch}(i,t), Q_{stor}^{dis}(i,t) &\leq \overline{Q}_s^{cap}
\end{aligned}
$$

Charge/discharge and import/export exclusivity follow the standard binary-pair big-$M$ form (omitted; see §2.2 of Morvaj et al.).

**(E5) End-of-horizon storage closure:**

$$
E_{stor}^{SOC}(i, T) \geq E_{stor}^{SOC}(i, 0)
$$

### 2.5 Linearized AC Power Flow

Following Koster & Lemkens as adopted in Morvaj et al. (Eqs. 10–13).

**(E6) Linearized line flows:**

$$
P\big((n,m), t\big) = U_0 \cdot G_{nm} \cdot \Delta U_{nm,t} - U_0^2 \cdot B_{nm} \cdot \Delta \theta_{nm,t}, \qquad \forall (n,m), \forall t
$$

$$
Q\big((n,m), t\big) = -U_0 \cdot B_{nm} \cdot \Delta U_{nm,t} - U_0^2 \cdot G_{nm} \cdot \Delta \theta_{nm,t}, \qquad \forall (n,m), \forall t
$$

with $\Delta U_{nm,t} = U_n^t - U_m^t$ and $\Delta \theta_{nm,t} = \theta_n^t - \theta_m^t$.

**(E7) Nodal active power balance** (Eqs. 12, 14) — links the grid to the hub:

$$
\sum_{m: (n,m) \in \mathcal{E}} P\big((n,m), t\big) = L_{i,t}^{load} - \sum_{c \in ota} P_{tech}^{gen}(i,t) + \sum_{c \in ota} P_{tech}^{con}(i,t)
$$

where building $i$ sits at bus $n$.

**(E8) Nodal reactive power balance** (Eqs. 13, 15):

$$
\sum_{m: (n,m) \in \mathcal{E}} Q\big((n,m), t\big) = QL_{i,t}^{load} - \sum_{c \in otr} P_{tech}^{gen}(i,t) + \sum_{c \in otr} P_{tech}^{con}(i,t)
$$

**(E9) Bus voltage magnitude bounds:**

$$
\underline{U} \leq U_n^t \leq \overline{U}, \qquad \forall n \in \mathcal{N}, \, \forall t
$$

(e.g. $0.9 \leq U_n^t \leq 1.1$ p.u.)

### 2.6 Linearized Branch Current Magnitude (Eqs. 16–31)

This is the contribution unique to Morvaj et al. — getting branch currents inside a MILP. The full derivation goes through several approximation steps; the final constraint set is:

**(E10) Real and imaginary parts of the linearized current** (Eq. 25):

$$
\mathrm{Re}\big(I_{nm,t}\big) = \frac{R_{nm}(U_n^t - U_m^t) + X_{nm}(\theta_n^t - \theta_m^t)}{R_{nm}^2 + X_{nm}^2}
$$

$$
\mathrm{Im}\big(I_{nm,t}\big) = \frac{-X_{nm}(U_n^t - U_m^t) + R_{nm}(\theta_n^t - \theta_m^t)}{R_{nm}^2 + X_{nm}^2}
$$

(obtained after a first-order Taylor expansion around $U_n \approx 1, \theta_n \approx 0$, and a separable substitution $\alpha = (U + \theta)/2, \beta = (U - \theta)/2$.)

**(E11) Absolute value linearization** (Eqs. 26–27):

$$
\phi_{nm,t} \geq \mathrm{Re}(I_{nm,t}), \quad \phi_{nm,t} \geq -\mathrm{Re}(I_{nm,t})
$$

$$
\chi_{nm,t} \geq \mathrm{Im}(I_{nm,t}), \quad \chi_{nm,t} \geq -\mathrm{Im}(I_{nm,t})
$$

A small positive coefficient on $\phi$ and $\chi$ is added to the objective so the lower-bounding inequalities tighten without distorting the cost.

**(E12) Piecewise-linear approximation of squared absolute parts** (Eqs. 28–30), using the $\lambda$-formulation with $N^{seg}$ breakpoints $\{\phi^{(n)}\}$ and corresponding squared values $\{(\phi^{(n)})^2\}$:

$$
\sum_{n=1}^{N^{seg}} \lambda^n_{nm,t} \phi^{(n)} = \phi_{nm,t}, \qquad
\sum_{n=1}^{N^{seg}} \lambda^n_{nm,t} (\phi^{(n)})^2 = \widehat{\phi^2}_{nm,t}
$$

$$
\sum_{n=1}^{N^{seg}} \lambda^n_{nm,t} = 1, \qquad \lambda^n_{nm,t} \geq 0
$$

(analogous set for $\chi$ giving $\widehat{\chi^2}_{nm,t}$). Because the objective minimizes a separable convex function, the SOS2 adjacency condition on $\lambda$ is not needed.

**(E13) Current-magnitude limit** (Eq. 31):

$$
\widehat{\phi^2}_{nm,t} + \widehat{\chi^2}_{nm,t} \leq \overline{I}_{nm}^{\,2}, \qquad \forall (n,m), \, \forall t
$$

### 2.7 Objective (Eq. 4)

General form — minimize a weighted sum of input streams:

$$
\boxed{
\min \; f = \sum_{k} \sum_{i \in \mathcal{B}} \sum_{t \in \mathcal{T}} C_k \cdot P_k^{input}(i, t)
}
$$

With $C_k$ representing prices ⇒ operational cost; representing emission factors ⇒ CO₂ emissions. Subtract the exported-electricity term (and any PV carbon credit) as in the paper.

For multi-objective cost-vs-emissions, use $\varepsilon$-constraint (Eq. 5):

$$
\min \; F_1(x) \quad \text{s.t.} \quad F_2(x) \leq \varepsilon_a, \; a = 1, \dots, n_a
$$

### 2.8 Complete Day-Ahead Energy Problem

$$
\begin{aligned}
\min \; & f \quad \text{(Eq. 4)} \\
\text{s.t.} \quad & \text{(E1)–(E5)} && \text{energy-hub balances and storage} \\
& \text{(E6)–(E9)} && \text{linearized AC power flow + voltage limits} \\
& \text{(E10)–(E13)} && \text{branch current magnitude + thermal limits}
\end{aligned}
$$

---

## 3. How the Two Stay Decoupled (for now)

| Decoupling point | Water model | Energy model |
|---|---|---|
| Pump electrical demand | Embedded in cost $c_k^t$; not a load on the electrical grid | $L_{i,t}^{load}$ is exogenous (no pump term) |
| Tariff $c_k^t$ / $C_k$ | Parameter | Parameter |
| Time resolution | Hourly | Hourly |
| State variable | Tank head $H_{tk}^t$ | SoC $E_{stor}^{SOC}(i,t)$ |
| Solver | MILP | MILP |

When you couple the two later, the natural bridge is: replace the pump-cost term in (Eq. 16) of the water side with an actual electrical-load term that enters $L_{i,t}^{load}$ in (E1) and propagates through (E6)–(E13). The joint problem stays MILP — no fundamental structural change needed.

---

## References

- Thomas, M., & Sela, L. (2024). *A Mixed-Integer Linear Programming Framework for Optimization of Water Network Operations Problems.* Water Resources Research, 60, e2023WR034526.
- Morvaj, B., Evins, R., & Carmeliet, J. (2016). *Optimization framework for distributed energy systems with integrated electrical grid constraints.* Applied Energy, 171, 296–313.
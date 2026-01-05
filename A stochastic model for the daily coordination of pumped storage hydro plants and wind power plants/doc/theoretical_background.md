# Theoretical Framework: Integrated Decentralized Water-Energy Network Optimization

## 1. Introduction
This work proposes a mathematical framework for the optimal operation of a decentralized, bi-directional water and energy system. To address the complexities of time-dependent supply (e.g., rainfall, solar generation) and the interdependence of resources (energy required for pumping, water treatment), the system is modeled as a **Time-Expanded, Multi-Layer Network Flow Problem**.

This approach allows for the simultaneous optimization of economic and environmental performance by solving a **Minimum Cost Flow problem** over a dynamic graph structure. The methodology relies on linear programming techniques described in **Ahuja et al., *Network Flows: Theory, Algorithms, and Applications***, specifically leveraging **Dynamic Flows (Chapter 19)** and **Generalized Flows (Chapter 15)**.

## 2. Network Topology

### 2.1 The Time-Expanded Network
Traditional static network models are insufficient for systems where storage and timing are critical. To model the daily operation of reservoirs, batteries, and shifting demand, we employ a **Time-Expanded Network** architecture.

* **Temporal Discretization:** The planning horizon $T$ (e.g., 24 hours) is discretized into time steps $t = 1, \dots, T$.
* **Node Duplication:** Every physical location $i$ (e.g., Home, Treatment Plant) is replicated for each time step $t$, creating a set of dynamic nodes $(i, t)$.
* **Flow over Time:** Movement of resources is represented by directed arcs between time-indexed nodes.

### 2.2 The Layered Commodity Structure
To integrate distinct resources without severing their operational coupling, the network is divided into three logical **Layers** at each node:
1.  **Potable Layer ($P$):** High-quality water (Utility imports, treated water).
2.  **Waste/Raw Layer ($W$):** Low-quality water (Rainwater harvesting, wastewater).
3.  **Energy Layer ($E$):** The driver of the system (Grid, Solar, Wind).

This unified structure prevents the sub-optimal solutions that arise from separating water and power networks, a limitation noted in recent literature on joint operation optimization.

## 3. Mathematical Formulation

The system is formulated as a linear programming model. The objective is to minimize the total operational cost subject to mass balance and capacity constraints.

### 3.1 Sets and Indices
* $T$: Set of time steps $\{1, \dots, 24\}$.
* $N$: Set of physical nodes (Homes, Reservoirs, Plants).
* $L$: Set of layers/commodities $\{P, W, E\}$.

### 3.2 Decision Variables
The model controls the system via two primary types of non-negative continuous variables:

1.  **Flow Variables ($x_{ij,t}^{L}$):** Represents the quantity of resource $L$ moving from node $i$ to node $j$ at time $t$. This covers:
    * *Spatial Transport:* Water in pipes or electricity on wires.
    * *Bi-directional Flow:* Explicitly handled by separate variables $x_{ij}$ and $x_{ji}$.
2.  **Storage/Holdover Variables ($h_{i,t}^{L}$):** Represents the quantity of resource $L$ held at node $i$ from time $t$ to $t+1$.
    * *Physical Meaning:* Water volume in a tank or energy state of charge in a battery.

### 3.3 Parameters
* $C_{ij,t}^{L}$: Unit cost of flow (e.g., electricity price, pumping cost, treatment cost).
* $U_{ij}^{L}$: Capacity limit of the arc (e.g., max pipe flow, inverter rating).
* $S_{i}^{L}$: Maximum storage capacity at node $i$.
* $D_{i,t}^{L}$: Net Demand at node $i$, time $t$.
    * $D > 0$: External Supply (e.g., Rainfall, Solar Generation).
    * $D < 0$: Consumption Demand (e.g., Household water use).

### 3.4 Constraints

#### **A. Mass Balance Constraint (Kirchhoff's Law)**
For every node, layer, and time step, the total inflow (from transport, storage, and external supply) must equal the total outflow (to transport, storage, and consumption). This linear constraint ensures physical continuity.

$$
\sum_{j \in N} x_{ji,t}^{L} + h_{i,t-1}^{L} + D_{i,t}^{L} = \sum_{k \in N} x_{ik,t}^{L} + h_{i,t}^{L} \quad \forall i \in N, t \in T, L \in \{P,W,E\}
$$

#### **B. Capacity Constraints**
Flows and storage levels cannot exceed physical infrastructure limits.

$$
0 \leq x_{ij,t}^{L} \leq U_{ij}^{L}
$$
$$
0 \leq h_{i,t}^{L} \leq S_{i}^{L}
$$

#### **C. Inter-Layer Coupling Constraints (Generalized Arcs)**
To model the interdependence of water and energy, we introduce linear coupling constraints based on **Generalized Network Flow** theory. These constraints apply to every node $i$, but the coefficients ($k$, $\gamma$, etc.) are set to **zero** for nodes lacking the specific technology.

1.  **Treatment Efficiency (Waste $\to$ Potable):**
    Transformation of wastewater to potable water incurs a loss factor $\eta$ (efficiency).
    $$
    x_{\text{output}, i, t}^{P} = \eta_{treat, i} \cdot x_{\text{input}, i, t}^{W} \quad \forall i \in N
    $$

2.  **Energy Intensity (Energy $\to$ Transport):**
    Movement of water (pumping) requires a proportional consumption of energy at the source node $i$. The constraint sums all outgoing water arcs.
    $$
    x_{\text{pump}, i, t}^{E} \geq k_{pump, i} \cdot \sum_{j \in N} (x_{ij, t}^{P} + x_{ij, t}^{W}) \quad \forall i \in N
    $$
    *Where $k_{pump, i}$ is the specific energy intensity (kWh/$m^3$) of the pump at node $i$.*

3.  **Pressure Reducing Station (PRS) (Water $\to$ Energy):**
    At gateway nodes, water entering from high-pressure external sources (Utility) releases energy.
    $$
    x_{\text{recover}, i, t}^{E} \leq \gamma_{prs, i} \cdot x_{\text{utility\_in}, i, t}^{P} \quad \forall i \in N
    $$
    *Where $\gamma_{prs, i}$ is the energy recovery factor (kWh/$m^3$) at node $i$.*

4.  **Pumped Hydro Storage (PHS) Dynamics:**
    PHS is modeled as flows between a Lower Reservoir Node ($i$) and an Upper Reservoir Node ($j$).
    * **Charging (Pumping Up $i \to j$):** Consumes Energy at node $i$.
        $$x_{pump\_up, i, t}^{E} = k_{phs, i} \cdot x_{i \to j, t}^{W}$$
    * **Discharging (Turbining Down $j \to i$):** Generates Energy at node $i$.
        $$x_{gen\_down, i, t}^{E} = \eta_{phs, i} \cdot x_{j \to i, t}^{W}$$

## 4. Optimization Objective
The objective function seeks to minimize the total generalized cost of operation over the planning horizon. This includes direct economic costs (importing water/power) and revenue offsets from generation.

$$
\text{Minimize } Z = \sum_{t \in T} \sum_{(i,j) \in A} \left( C_{ij,t}^{\text{grid}} \cdot x_{ij,t}^{E} + C_{ij,t}^{\text{water}} \cdot x_{ij,t}^{P} + C_{ij,t}^{\text{treat}} \cdot x_{ij,t}^{W} \right) - \sum_{t \in T} \sum_{i \in N} R_{gen, i, t}
$$

*Where $R_{gen}$ represents revenue or cost-offsets achieved through PRS and PHS energy generation at node $i$.*

## 5. Justification of Approach
This framework offers three distinct advantages for the proposed system:
1.  **Linearity:** By using piece-wise linear approximations for constraints where necessary (as validated in joint operation literature), the model remains solvable by standard MILP/LP solvers, ensuring scalability.
2.  **Handling Decentralization:** The node-based mass balance approach allows any node (e.g., a home) to dynamically switch roles between "consumer," "storage," and "supplier" based on the optimal flow configuration.
3.  **Intuitive Dynamics:** The Time-Expanded structure visualizes storage as simply "moving water through time," simplifying the interpretation of battery and reservoir dynamics without complex differential equations.
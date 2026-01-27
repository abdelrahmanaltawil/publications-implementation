**Theoretical Framework: Integrated Decentralized Water-Energy Network Optimization**

## **1\. Introduction**

This work proposes a mathematical framework for the optimal operation of a decentralized, bi-directional water and energy system. To address the complexities of time-dependent supply (e.g., rainfall, solar generation) and the interdependence of resources (energy required for pumping, water treatment), the system is modeled as a **Time-Expanded, Multi-Layer Network Flow Problem**.  
This approach allows for the simultaneous optimization of economic and environmental performance by solving a **Generalized Minimum Cost Flow problem** over a dynamic graph structure. The methodology relies on linear programming techniques described in **Ahuja et al., *Network Flows: Theory, Algorithms, and Applications***, specifically leveraging **Dynamic Flows (Chapter 19)** and **Generalized Flows (Chapter 15)**.

## **2\. Network Topology**

### **2.1 The Time-Expanded Network**

Traditional static network models are insufficient for systems where storage and timing are critical. To model the daily operation of reservoirs, batteries, and shifting demand, we employ a **Time-Expanded Network** architecture.

* **Temporal Discretization:** The planning horizon $T$ (e.g., 24 hours) is discretized into time steps $t = 1, \dots, T$.  
* **Node Duplication:** Every physical location $i$ (e.g., Home, Treatment Plant) is replicated for each time step $t$, creating a set of dynamic nodes $(i, t)$.  
* **Flow over Time:** Movement of resources is represented by directed arcs between time-indexed nodes.

### **2.2 The Layered Commodity Structure**

To integrate distinct resources without severing their operational coupling, the network is divided into three logical **Layers** at each node:

1. **Potable Layer ($P$):** High-quality water (Utility imports, treated water).  
2. **Waste/Raw Layer ($W$):** Low-quality water (Rainwater harvesting, wastewater).  
3. **Energy Layer ($E$):** The driver of the system (Grid, Solar, Wind).

This unified structure prevents the sub-optimal solutions that arise from separating water and power networks, a limitation noted in recent literature on joint operation optimization.

## **3\. Mathematical Formulation**

The system is formulated as a linear programming model. The objective is to minimize the total generalized cost subject to mass balance and capacity constraints.

### **3.1 Sets and Indices**

* $T$: Set of time steps $\{1, \dots, 24\}$.  
* $N$: Set of physical nodes (Homes, Reservoirs, Plants).  
* $L$: Set of layers/commodities $\{P, W, E\}$.  
* **Special Subsets:**  
  * $N_{grid} \subset N$: Nodes representing the external Electric Grid.  
  * $N_{utility} \subset N$: Nodes representing the external Water Utility.  
  * $N_{sewer} \subset N$: Nodes representing the external Wastewater discharge point.

### **3.2 Decision Variables**

The model controls the system via two primary types of non-negative continuous variables:

1. **Flow Variables ($x_{ij,t}^{L}$):** Represents the quantity of resource $L$ moving from node $i$ to node $j$ at time $t$. This covers:  
   * *Spatial Transport:* Water in pipes or electricity on wires.  
   * *Bi-directional Regulation:* Explicitly handles both Import ($x_{Grid \to Home}$) and **Export** ($x_{Home \to Grid}$). Crucially, this now applies to **Water** ($x_{Home \to Utility}$) to model resource sharing/selling.  
2. **Storage/Holdover Variables ($h_{i,t}^{L}$):** Represents the quantity of resource $L$ held at node $i$ from time $t$ to $t+1$.  
   * *Physical Meaning:* Water volume in a tank or energy state of charge in a battery.

### **3.3 Parameters**

* $C_{ij,t}^{L}$: Unit cost or price associated with a flow (used for calculating import costs and export revenues).  
* $U_{ij}^{L}$: Capacity limit of the arc (e.g., max pipe flow, inverter rating).  
* $S_{i}^{L}$: Maximum storage capacity at node $i$.  
* $D_{i,t}^{L}$: Net Demand at node $i$, time $t$.

### **3.4 Constraints**

#### **A. Mass Balance Constraint (Kirchhoff's Law)**

For every node, layer, and time step, the total inflow (from transport, storage, and external supply) must equal the total outflow (to transport, storage, and consumption).

$$\sum_{j \in N} x_{ji,t}^{L} + h_{i,t-1}^{L} + D_{i,t}^{L} = \sum_{k \in N} x_{ik,t}^{L} + h_{i,t}^{L} \quad \forall i \in N, t \in T, L \in \{P,W,E\}$$

#### **B. Capacity Constraints**

Flows and storage levels cannot exceed physical infrastructure limits.

$$0 \leq x_{ij,t}^{L} \leq U_{ij}^{L}$$

$$0 \leq h_{i,t}^{L} \leq S_{i}^{L}$$

#### **C. Inter-Layer Coupling Constraints (Generalized Arcs)**

1. **Treatment Efficiency (Waste $\to$ Potable):**

   $$
    x_{\text{output}, i, t}^{P} = \eta_{treat, i} \cdot x_{\text{input}, i, t}^{W} \quad \forall i \in N 
   $$

2. **Energy Intensity (Energy $\to$ Transport):** 

   $$ x_{\text{pump}, i, t}^{E} \geq k_{pump, i} \cdot \sum_{j \in N} (x_{ij, t}^{P} + x_{ij, t}^{W}) \quad \forall i \in N 
   $$

3. **Pressure Reducing Station (PRS) (Water $\to$ Energy):**  

   $$
    x_{\text{recover}, i, t}^{E} \leq \gamma_{prs, i} \cdot x_{\text{utility in}, i, t}^{P} \quad \forall i \in N 
    $$  

4. **Pumped Hydro Storage (PHS) Dynamics:**  
   * **Charging ($i \to j$):** $ x_{pump_up, i, t}^{E} = k_{phs, i} \cdot x_{i \to j, t}^{W} $  
   * **Discharging ($j \to i$):** $ x_{gen_down, i, t}^{E} = \eta_{phs, i} \cdot x_{j \to i, t}^{W} $

## **4\. Optimization Objective**

The objective function $Z$ minimizes the weighted sum of **Net Economic Cost ($Z_{econ}$)** and **Net Resource Impact ($Z_{res}$)** over the planning horizon $T$. This formulation adopts the **N-NWEE-D2N** approach, utilizing bi-directional regulation to value surplus water as a shareable resource rather than waste.

$$
\text{Minimize } Z = \alpha \cdot Z_{econ} + \beta \cdot Z_{res}
$$  

*Where $\alpha$ and $\beta$ are scalar weights prioritizing Economic vs. Environmental performance.*

#### **4.1 Net Economic Cost ($Z_{econ}$)**

This component captures the direct financial transactions (External Expenditures minus Revenues). Operational costs are excluded to focus on the arbitrage of external resources.

$$
Z_{econ} = \sum_{t \in T} \sum_{i \in N} \left[ \underbrace{P_{elec, t}^{buy} \cdot x_{grid \to i, t}^{E}}_{\text{Grid Import Cost}} + \underbrace{P_{water, t}^{buy} \cdot x_{utility \to i, t}^{P}}_{\text{Water Import Cost}} \right] - \sum_{t \in T} \sum_{i \in N} \left[ \underbrace{P_{elec, t}^{sell} \cdot x_{i \to grid, t}^{E}}_{\text{Energy Export Revenue}} + \underbrace{P_{water, t}^{sell} \cdot x_{i \to utility, t}^{P}}_{\text{Water Export Revenue}} \right]
$$

* **$x_{i \to utility, t}^{P}$ (Water Export):** Unlike traditional models, this flow is enabled to represent the "Regulation Down" logic, where surplus water is shared/sold back to the network rather than discharged.

* **$P_{sell}$:** The feed-in tariff or sharing credit for returning resources to the grid/utility.

#### **4.2 Net Resource Impact ($Z_{res}$)**

This component penalizes the depletion of primary resources and the generation of waste. Crucially, **Water Exports are not penalized**, rewarding the system for circularity (sharing surplus) instead of discharging it.

$$
Z_{res} = \sum_{t \in T} \sum_{i \in N} \left[ \underbrace{\omega_{carbon, t} \cdot x_{grid \to i, t}^{E}}_{\text{Carbon Footprint}} + \underbrace{\omega_{scarcity} \cdot x_{utility \to i, t}^{P}}_{\text{Freshwater Withdrawal}} + \underbrace{\omega_{waste} \cdot x_{i \to sewer, t}^{W}}_{\text{Wastewater Discharge}} \right]
$$

* **$\omega_{carbon, t}$:** Grid carbon intensity ($kgCO_2/kWh$), penalizing imports during dirty peak hours.  
* **$\omega_{scarcity}$:** Penalty for withdrawing potable water, incentivizing the use of the Waste Layer ($W$) (rainwater/greywater) or stored resources.  
* **$\omega_{waste}$:** Penalty for discharging water to the sewer/environment. The optimizer will minimize this by either reusing water internally or exporting it ($x_{i \to utility}^{P}$) to the network.

## **5\. Justification of Approach**

This framework offers three distinct advantages for the proposed system:

1. **Linearity:** By using piece-wise linear approximations for constraints where necessary (as validated in joint operation literature), the model remains solvable by standard MILP/LP solvers, ensuring scalability.  
2. **Handling Decentralization:** The node-based mass balance approach allows any node (e.g., a home) to dynamically switch roles between "consumer," "storage," and "supplier" based on the optimal flow configuration.  
3. **Intuitive Dynamics:** The Time-Expanded structure visualizes storage as simply "moving water through time," simplifying the interpretation of battery and reservoir dynamics without complex differential equations.
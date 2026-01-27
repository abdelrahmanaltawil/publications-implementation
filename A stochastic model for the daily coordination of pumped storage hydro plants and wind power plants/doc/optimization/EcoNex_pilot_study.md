# Pilot Case Study: The "Eco-Nex" Resilient Micro-District

## 1. Overview
This pilot case study simulates the **"Eco-Nex" Resilient Micro-District**, a decentralized residential cluster designed to validate the **Time-Expanded, Multi-Layer Network Flow** optimization framework. 

The study focuses on three "Smart Nodes" (Prosumers) and one auxiliary storage node operating over a **24-hour planning horizon ($T=24$)**. The primary objective is to demonstrate how bi-directional resource trading and inter-layer coupling (Water-Energy Nexus) can minimize operational costs and maximize local efficiency. 

This updated study specifically incorporates **Pressure Reducing Station (PRS)** technology for energy recovery and **Pumped Hydro Storage (PHS)** for long-duration buffering.

---

## 2. Physical Topology (Nodes & Arcs)

The system is modeled as a directed graph where nodes represent physical locations and arcs represent the infrastructure connecting them.

### 2.1 The Nodes ($N$)
Heterogeneity is introduced among the nodes to create natural incentives for trade and resource exchange.

**Node 1: The "Energy Surplus" Home**
* **Role:** Net Energy Producer.
* **Generation ($D^E > 0$):** Large rooftop solar array.
* **Storage ($S^E$):** High-capacity residential battery (e.g., Tesla Powerwall).
* **Water Profile:** Standard household consumption; limited rainwater harvesting.

**Node 2: The "Water Intensive" Home**
* **Role:** Net Water Supplier / Energy Consumer.
* **Demand ($D^P < 0$):** High water demand due to large garden/irrigation needs.
* **Generation ($D^W > 0$):** Large catchment area for rainwater harvesting.
* **Storage ($S^W$):** Large raw water cisterns.

**Node 3: The Community Hub (Gateway Node)**
* **Role:** Central Coupling, Treatment, and PHS Lower Basin.
* **Infrastructure:** * **Filtration/Treatment Unit:** Converts Waste $W \to$ Potable $P$.
    * **PRS Turbine:** Situated at the municipal water inlet. Recovers energy from pressure drops.
    * **PHS Connection:** Hosts the pump/turbine equipment connecting to Node 4.
    * **Grid Connections:** Main Utility Grid (Energy) and Municipal Water (Potable).

**Node 4: The Upper Reservoir (Auxiliary Node)**
* **Role:** PHS Upper Basin.
* **Infrastructure:** Passive elevated water storage.
* **Connectivity:** Connected exclusively to Node 3 via a Penstock.

### 2.2 The Infrastructure (Arcs)
The nodes are connected via a local micro-network:
* **Smart Micro-Grid:** Direct DC/AC lines allowing Peer-to-Peer (P2P) electricity transfer between Nodes 1, 2, and 3.
* **Smart Piping:** Bidirectional water pipes allowing the transfer of raw and potable water between neighbors.
* **Penstock (Node 3 $\leftrightarrow$ Node 4):** A specialized high-capacity water link. 
    * Flow $3 \to 4$ is **Pumping** (Consumes Energy).
    * Flow $4 \to 3$ is **Turbining** (Generates Energy).

---

## 3. Layer Specifications

The system tracks three distinct commodities using a layered network approach.

### Layer 1: Energy ($E$)
* **Sources:** Solar (Node 1), Grid Import (Node 3), **PRS Generation (Node 3)**, **PHS Turbine (Node 3)**.
* **Sinks:** Household Load, Pumps (Coupling), Treatment (Coupling), **PHS Pumping (Node 3)**.
* **Storage:** Chemical Batteries ($h_{i,t}^E$).

### Layer 2: Potable Water ($P$)
* **Sources:** Municipal Import (Node 3), Treatment Output (Node 3).
* **Sinks:** Potable Demand (Drinking, Showering).
* **Storage:** Potable Tanks/Pressure Vessels ($h_{i,t}^P$).

### Layer 3: Raw/Waste Water ($W$)
* **Sources:** Rainwater Harvesting (Node 2), Greywater Recovery.
* **Sinks:** Irrigation (Node 2), Treatment Input (Node 3).
* **Storage:** Rain Barrels, **Upper Reservoir (Node 4)**.

---

## 4. Coupling Dynamics (The Nexus)

The pilot explicitly models the interdependence of resources using **Generalized Arcs**. Parameters are node-specific ($i$) to reflect the location of technologies.

### A. Energy-for-Water (Transport & Storage)
* **Standard Pumping:** Moving water through pipes requires energy.
    * $x_{pump, i}^E \geq k_{pump} \cdot \sum x_{out, i}^{Water}$
* **PHS Charging (Node 3 $\to$ 4):** Pumping water to the upper reservoir consumes significant energy but stores it as potential energy.
    * *Logic:* $x_{pump\_up, 3, t}^{E} = k_{phs} \cdot x_{3 \to 4, t}^{W}$

### B. Water-for-Energy (Generation & Recovery)
* **PRS Energy Recovery (Node 3 Only):** As potable water is imported from the high-pressure municipal main, the PRS turbine generates electricity.
    * *Logic:* $x_{gen, 3, t}^{E} = \gamma_{prs} \cdot x_{utility\_in, 3, t}^{P}$
    * *Optimization Effect:* The system may choose to import water specifically during peak energy price windows to offset costs using PRS generation.
* **PHS Discharging (Node 4 $\to$ 3):** Releasing water from the upper reservoir drives a turbine to generate electricity.
    * *Logic:* $x_{gen\_down, 3, t}^{E} = \eta_{phs} \cdot x_{4 \to 3, t}^{W}$

### C. Treatment Coupling
* **Virtual Storage:** Treating water remains an energy-intensive process ($x_{output}^P = \eta \cdot x_{input}^W$), utilized to shift loads.

---

## 5. Input Data Parameters

To solve the Minimum Cost Flow problem, the following data profiles are utilized:

| Parameter | Description | Data Source |
| :--- | :--- | :--- |
| **$D_{i,t}^E$** | Solar Generation Profile | Historical irradiance data (Sunny vs. Cloudy days). |
| **$D_{i,t}^P$** | Water Demand Profile | Standard residential usage curves (Morning/Evening peaks). |
| **$C_{grid,t}^E$** | Grid Electricity Price | Time-of-Use (TOU) tariff (e.g., Peak pricing 4 PM - 9 PM). |
| **$\gamma_{prs, 3}$** | PRS Recovery Factor | Calculated based on pressure head $\Delta P$ and turbine efficiency. |
| **$\eta_{phs}$** | PHS Round-trip Efficiency | Combined pump/turbine efficiency (approx 75-80%). |
| **$S_{Node4}^{W}$** | Upper Reservoir Capacity | Volume of elevated storage available for PHS. |

---

## 6. Target Operational Scenarios

The pilot is designed to demonstrate emergent behaviors including new recovery mechanics:

1.  **Load Shifting:** Batteries charge during off-peak hours and discharge during peak demand.
2.  **Rainwater Arbitrage:** Node 2 captures rain, stores it, and transfers it to Node 3 for treatment only when energy costs are optimal.
3.  **Gravity Energy Recovery (PRS):** Node 3 prioritizes municipal water imports during times when the generated energy from the PRS can be immediately consumed or sold at high prices.
4.  **Hydraulic Battery Cycling (PHS):** The system utilizes the Pumped Hydro capacity for long-duration storage, absorbing excess solar from Node 1 during the day (pumping $3 \to 4$) and releasing it via the hydro turbine during the evening peak (turbining $4 \to 3$).
# Pilot Case Study: The "Eco-Nex" Resilient Micro-District

## 1. Overview
This pilot case study simulates the **"Eco-Nex" Resilient Micro-District**, a decentralized residential cluster designed to validate the **Time-Expanded, Multi-Layer Network Flow** optimization framework. 

The study focuses on three "Smart Nodes" (Prosumers) operating over a **24-hour planning horizon ($T=24$)**. The primary objective is to demonstrate how bi-directional resource trading and inter-layer coupling (Water-Energy Nexus) can minimize operational costs and maximize local efficiency.

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
* **Energy Profile:** No solar generation; relies on grid or trade.

**Node 3: The Community Hub**
* **Role:** Central Coupling & Treatment Authority.
* **Infrastructure:** * Filtration/Treatment Unit (converts Waste $W \to$ Potable $P$).
    * Main Utility Grid Connection (Energy Import/Export).
    * Municipal Water Connection (Backup Potable Supply).
    * Community-scale water reservoir.

### 2.2 The Infrastructure (Arcs)
The nodes are connected via a local micro-network:
* **Smart Micro-Grid:** Direct DC/AC lines allowing Peer-to-Peer (P2P) electricity transfer between Node 1, 2, and 3.
* **Smart Piping:** Bidirectional water pipes allowing the transfer of raw and potable water between neighbors and the hub.

---

## 3. Layer Specifications

The system tracks three distinct commodities using a layered network approach.

### Layer 1: Energy ($E$)
* **Sources:** Solar (Node 1), Grid Import (Node 3).
* **Sinks:** Household Load, **Pumps** (Coupling), **Treatment** (Coupling).
* **Storage:** Batteries ($h_{i,t}^E$).
* **Constraint:** Inverter capacity limits ($U_{ij}^E$).

### Layer 2: Potable Water ($P$)
* **Sources:** Municipal Import (Node 3), Treatment Output (Node 3).
* **Sinks:** Potable Demand (Drinking, Showering).
* **Storage:** Potable Tanks/Pressure Vessels ($h_{i,t}^P$).
* **Constraint:** Quality strictness; Potable water cannot degrade to Waste within the network logic (except via end-use consumption).

### Layer 3: Raw/Waste Water ($W$)
* **Sources:** Rainwater Harvesting (Node 2), Greywater Recovery.
* **Sinks:** Irrigation (Node 2), Treatment Input (Node 3).
* **Storage:** Rain Barrels ($h_{i,t}^W$).

---

## 4. Coupling Dynamics (The Nexus)

The pilot explicitly models the interdependence of resources using **Generalized Arcs**.

### A. Energy-for-Water (Transport)
Moving water requires energy. The model enforces that for every unit of water moved, a proportional amount of energy is consumed at the source node.
* **Logic:** $x_{pump, t}^{E} \geq k \cdot x_{pipe, t}^{Water}$
* **Optimization Effect:** Pumping schedules are shifted to align with periods of high solar generation (Node 1) or low grid prices.

### B. Water-for-Energy (Virtual Storage)
Treating water is an energy-intensive process.
* **Logic:** $x_{output, t}^{P} = \eta \cdot x_{input, t}^{W}$
* **Optimization Effect:** The system treats the potable water tank as a "virtual battery." It pre-treats and stores water when energy is cheap, avoiding treatment during peak electricity pricing windows.

---

## 5. Input Data Parameters

To solve the Minimum Cost Flow problem, the following data profiles are utilized:

| Parameter | Description | Data Source |
| :--- | :--- | :--- |
| **$D_{i,t}^E$** | Solar Generation Profile | Historical irradiance data (Sunny vs. Cloudy days). |
| **$D_{i,t}^P$** | Water Demand Profile | Standard residential usage curves (Morning/Evening peaks). |
| **$C_{grid,t}^E$** | Grid Electricity Price | Time-of-Use (TOU) tariff (e.g., Peak pricing 4 PM - 9 PM). |
| **$D_{i,t}^W$** | Rainfall Events | Stochastic precipitation generator. |
| **$\eta$** | Treatment Efficiency | Filtration unit specifications (e.g., 0.95 recovery). |
| **$k$** | Pumping Intensity | Specific energy of pump ($kWh/m^3$). |

---

## 6. Target Operational Scenarios

The pilot is designed to demonstrate three emergent behaviors:

1.  **Load Shifting:** Batteries charge during off-peak hours and discharge during peak demand.
2.  **Rainwater Arbitrage:** Node 2 captures rain, stores it, and transfers it to Node 3 for treatment only when energy costs are optimal.
3.  **Peak Shaving via Coupling:** During extreme electricity price spikes, the system halts all water movement and treatment, relying entirely on static storage ($h_{t}^P$) to ride through the peak.
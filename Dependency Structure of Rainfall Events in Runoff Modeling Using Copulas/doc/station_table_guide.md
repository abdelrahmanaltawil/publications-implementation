Here is a comprehensive research framework ("Ankur") tailored to your study.

This table is designed to capture every parameter required by the analytical probabilistic model derived in Hassini and Guo (2022). I have suggested specific, well-known urban watersheds/subcatchments near each weather station that are frequently used in Canadian hydrological research.

### **Research Anchor Table (The "Ankur")**

The model is valid for **small urban catchments** (typically a few hectares to a few square kilometers). Therefore, for each station, I have suggested a **Major Watershed** (managed by a Conservation Authority) and a specific **Urban Subcatchment** candidate where you can likely define a study area (e.g., a specific residential subdivision or industrial park).

#### **Data Collection & Model Parameters**

You will need to fill in two types of data for each row:

1. **Rainfall Statistics (Blue Columns):** Derived from the station's historical hourly rainfall data.


2. **Physical Parameters (Green Columns):** Measured from GIS maps, soil surveys, or zoning maps for your specific subcatchment.



**Copy the code block below and save it as `research_master_table.csv`:**

```csv
Station_ID,Station_Name,Region_Label,Suggested_Watershed_Authority,Suggested_Urban_Subcatchment,IETD_Used_hr,Vol_Threshold_mm,Avg_Event_Vol_v_bar_mm,Avg_Event_Dur_t_bar_hr,Avg_Annual_Events_theta,Zeta_1_over_v,Lambda_1_over_t,Catchment_Area_ha,Imperviousness_h_fraction,Imp_Depression_Storage_Sdi_mm,Pervious_Init_Loss_Sil_mm,Ult_Infiltration_fc_mm_hr,Max_Infiltration_Sm_mm,Calc_Time_to_Sat_ts_hr
6153301,HAMILTON RBG CS,Hamilton,Hamilton Cons. Authority,Lower Davis Creek (or Chedoke Creek),,,,,,,"105.74 (Ex)",0.447,0.049,5.20,0.36,4.90,13.61
6139525,WINDSOR A,Windsor,Essex Region CA,Turkey Creek (Grand Marais Drain),,,,,,,,,,,,,,
6144475,LONDON A,London,Upper Thames River CA,Pottersburg Creek (Industrial/Res),,,,,,,,,,,,,,
6106000,OTTAWA MACDONALD-CARTIER,Ottawa,Rideau Valley CA,Pinecrest Creek (or Shirley's Brook),,,,,,,,,,,,,,
6117700,BARRIE-ORO,Barrie,Lake Simcoe Region CA,Lovers Creek (or Hewitts Creek),,,,,,,,,,,,,,
6068150,SUDBURY A,Sudbury,Conservation Sudbury,Junction Creek (Downtown Reach),,,,,,,,,,,,,,
6048261,THUNDER BAY A,Thunder Bay,Lakehead Region CA,McIntyre River (Intercity Area),,,,,,,,,,,,,,
6078285,TIMMINS VICTOR POWER A,Timmins,Mattagami Region CA,Town Creek (Urban Centre),,,,,,,,,,,,,,
6075425,MOOSONEE UA,Moosonee,Moose Creek Drainage,Moosonee Township Drainage,,,,,,,,,,,,,,

```

---

### **Detailed Guide to the Parameters**

To fill out this CSV effectively, here is exactly what each column represents based on the Hassini & Guo (2022) methodology.

#### **1. Rainfall Statistics (To be calculated from Station Data)**

You must process the historical rainfall record for each Station ID to get these values.

* **`IETD_Used_hr`**: The Inter-Event Time Definition. The paper recommends **6–12 hours** for small urban catchments.
* **`Vol_Threshold_mm`**: The minimum volume to count as an event. The paper suggests ** mm**.
* **`Avg_Event_Vol_v_bar_mm` ()**: The average volume of all rainfall events in your record.
* **`Avg_Event_Dur_t_bar_hr` ()**: The average duration of all rainfall events in your record.
* **`Avg_Annual_Events_theta` ()**: The average number of rainfall events per year.
* **`Zeta_1_over_v` ()**: Calculated as .
* **`Lambda_1_over_t` ()**: Calculated as .

#### **2. Physical Catchment Parameters (To be measured from GIS/Maps)**

You need to select a specific plot of land (the "subcatchment") within the suggested watersheds above to define these values.

* **`Catchment_Area_ha`**: The total area of your study site in hectares.
* **`Imperviousness_h_fraction` ()**: The fraction of the land covered by concrete/asphalt (0.0 to 1.0).
* **`Imp_Depression_Storage_Sdi_mm` ()**: Puddle depth on pavement. Typically **0.5–2.0 mm** (Note: Table 2 in the paper used a very specific calibrated value of 0.049 mm, but standard design values are higher).
* **`Pervious_Init_Loss_Sil_mm` ()**: Initial water needed to wet the soil before infiltration starts. A standard assumption is **3–5 mm**.
* **`Ult_Infiltration_fc_mm_hr` ()**: The steady infiltration rate of the soil.
* **Clay (Hamilton/Windsor):** 0.5–2.0 mm/h
* **Sand (Barrie/London):** >10 mm/h.

* **`Max_Infiltration_Sm_mm` ()**: The maximum water the soil can hold before it is saturated (the "empty space" in the soil column).


* **`Calc_Time_to_Sat_ts_hr` ()**: **Do not measure this.** Calculate it using the formula: .

# A Framework for Short-Term Forecasting of Extreme Weather Events

This project implements the framework described in the paper: **"A Framework for Short-Term Forecasting of Extreme Weather Events"**.

## Reference
If you use this code, please cite the following paper:
> A. Altawil, S. Hassini and E. Hassini, "A Framework for Short-Term Forecasting of Extreme Weather Events," 2025 IEEE 9th Forum on Research and Technologies for Society and Industry (RTSI), Tunis, Tunisia, 2025, pp. 238-243, doi: 10.1109/RTSI64020.2025.11212227.



## Overview
This framework uses a combination of statistical methods (3-Sigma rule) and Deep Learning (LSTM) to forecast extreme weather events, specifically focusing on rainfall intensity.

### Key Components:
1.  **Data Preprocessing**: Cleaning rainfall data and handling outliers.
2.  **3-Sigma Transformation**: Categorizing rainfall intensity into discrete levels (No-Rainfall, 1 sigma, 2 sigma, 3 sigma).
3.  **Modeling**: Training an LSTM network to predict the categorical rainfall intensity.

## Setup & Usage

### Prerequisites
- Python 3.10+
- Jupyter Notebook

### Installation
1.  Clone the repository.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Ensure you have `tensorflow`, `scikit-learn`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `statsmodels`, and `mlflow` installed.*

### Running the Project
1.  Ensure you have your data in the `./data/inputs` directory.
2.  Launch Jupyter Notebook:
    ```bash
    jupyter notebook
    ```
3.  Open `3sigma-str.ipynb`.
4.  Run all cells to execute the pipeline from data loading to model evaluation.

## Results
The notebook generates visualizations and metrics (Loss, Precision, Recall, Confusion Matrix) which are saved in the `./data/results` directory.

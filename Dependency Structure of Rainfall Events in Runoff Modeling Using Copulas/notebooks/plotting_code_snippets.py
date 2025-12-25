"""
Plotting Code Snippets for Notebooks
=====================================

Copy-paste these plot functions into your Jupyter notebooks.
Each function is self-contained with inline comments.

Usage:
    1. Copy the imports section
    2. Copy the plot function(s) you need
    3. Load your data
    4. Call the function

Author: Generated for Hassini & Guo (2022) copula implementation
Date: 2024-12-24
"""

# =============================================================================
# IMPORTS (copy this to your notebook first cell)
# =============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from pathlib import Path

# Apply custom style (adjust path as needed)
# plt.style.use('../data/inputs/ploting.mplstyle')


# =============================================================================
# NOTEBOOK 1: INPUT DATA PLOTTING
# =============================================================================

def plot_event_scatter_with_marginals(events_df, save_path=None):
    """
    Scatter plot of Volume vs Duration with marginal histograms.
    Shows the dependency structure between event characteristics.
    
    Parameters:
        events_df: DataFrame with 'Volume (mm)' and 'Duration (hrs)' columns
        save_path: Optional path to save figure
    """
    fig = plt.figure(figsize=(8, 8))
    
    # Create grid for main plot and marginals
    gs = fig.add_gridspec(3, 3, width_ratios=[0.2, 1, 0.05], 
                          height_ratios=[0.2, 1, 0.05],
                          hspace=0.05, wspace=0.05)
    
    ax_main = fig.add_subplot(gs[1, 1])
    ax_top = fig.add_subplot(gs[0, 1], sharex=ax_main)
    ax_right = fig.add_subplot(gs[1, 0], sharey=ax_main)
    
    # Main scatter plot
    ax_main.scatter(events_df['Volume (mm)'], events_df['Duration (hrs)'], 
                   alpha=0.5, s=20, c='steelblue')
    ax_main.set_xlabel(r'Volume $v$ (mm)')
    ax_main.set_ylabel(r'Duration $t$ (hours)')
    
    # Top marginal histogram (Volume)
    ax_top.hist(events_df['Volume (mm)'], bins=30, color='steelblue', 
                edgecolor='white', alpha=0.7)
    ax_top.tick_params(labelbottom=False)
    ax_top.set_ylabel('Count')
    
    # Right marginal histogram (Duration) - horizontal
    ax_right.hist(events_df['Duration (hrs)'], bins=30, color='steelblue',
                  edgecolor='white', alpha=0.7, orientation='horizontal')
    ax_right.tick_params(labelleft=False)
    ax_right.set_xlabel('Count')
    ax_right.invert_xaxis()
    
    # Add correlation annotation
    corr = events_df['Volume (mm)'].corr(events_df['Duration (hrs)'])
    ax_main.annotate(f'ρ = {corr:.3f}', xy=(0.95, 0.95), xycoords='axes fraction',
                    ha='right', va='top', fontsize=12,
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_event_statistics_boxplots(events_df, save_path=None):
    """
    Box plots of event statistics: Volume, Duration, Intensity.
    
    Parameters:
        events_df: DataFrame with event statistics columns
        save_path: Optional path to save figure
    """
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    
    columns = ['Volume (mm)', 'Duration (hrs)', 'Intensity (mm/hr)']
    colors = ['#4C72B0', '#55A868', '#C44E52']
    
    for ax, col, color in zip(axes, columns, colors):
        bp = ax.boxplot(events_df[col].dropna(), patch_artist=True)
        bp['boxes'][0].set_facecolor(color)
        bp['boxes'][0].set_alpha(0.7)
        ax.set_ylabel(col)
        ax.set_xticklabels([''])
        
        # Add mean annotation
        mean_val = events_df[col].mean()
        ax.axhline(mean_val, color='red', linestyle='--', alpha=0.5)
        ax.annotate(f'μ = {mean_val:.2f}', xy=(1.15, mean_val), 
                   xycoords=('axes fraction', 'data'), fontsize=10)
    
    fig.suptitle('Rainfall Event Statistics', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_monthly_event_distribution(events_df, time_col='Start Time', save_path=None):
    """
    Bar chart showing number of events per month.
    
    Parameters:
        events_df: DataFrame with datetime column
        time_col: Name of the datetime column
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Extract month from datetime
    events_df = events_df.copy()
    events_df['Month'] = pd.to_datetime(events_df[time_col]).dt.month
    
    monthly_counts = events_df['Month'].value_counts().sort_index()
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Only plot months that have data
    x = monthly_counts.index
    y = monthly_counts.values
    
    bars = ax.bar(x, y, color='steelblue', edgecolor='white', alpha=0.8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(months)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Events')
    ax.set_title('Monthly Distribution of Rainfall Events')
    
    # Highlight max month
    max_idx = np.argmax(y)
    bars[max_idx].set_color('#C44E52')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_inter_event_time_histogram(events_df, iet_col='Inter-Event Time (hrs)', 
                                     save_path=None):
    """
    Histogram of inter-event times (dry periods).
    
    Parameters:
        events_df: DataFrame with inter-event time column
        iet_col: Name of the IET column
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    
    iet_data = events_df[iet_col].dropna()
    
    ax.hist(iet_data, bins=50, color='steelblue', edgecolor='white', alpha=0.8)
    ax.set_xlabel('Inter-Event Time (hours)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of Dry Periods Between Rainfall Events')
    
    # Add statistics
    mean_iet = iet_data.mean()
    ax.axvline(mean_iet, color='red', linestyle='--', linewidth=2, 
               label=f'Mean = {mean_iet:.1f} hrs')
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


# =============================================================================
# NOTEBOOK 2: COPULA FITTING PLOTTING
# =============================================================================

def plot_pseudo_observations(ranks_df, u_col='U', v_col='V', save_path=None):
    """
    Scatter plot of pseudo-observations (ranks) in unit square.
    
    Parameters:
        ranks_df: DataFrame with rank columns
        u_col: Column name for U (volume rank)
        v_col: Column name for V (duration rank)
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    
    ax.scatter(ranks_df[u_col], ranks_df[v_col], alpha=0.4, s=15, c='steelblue')
    
    ax.set_xlabel(r'$u$ (Volume pseudo-observation)')
    ax.set_ylabel(r'$v$ (Duration pseudo-observation)')
    ax.set_title('Pseudo-Observations (Rank-Transformed Data)')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    
    # Add diagonal reference line (independence)
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.3, label='Independence')
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_copula_aic_comparison(metrics_df, save_path=None):
    """
    Horizontal bar chart comparing copula fits by AIC.
    
    Parameters:
        metrics_df: DataFrame with 'Family' and 'AIC' columns
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Sort by AIC (lower is better)
    sorted_df = metrics_df.sort_values('AIC', ascending=True)
    
    # Color gradient
    n = len(sorted_df)
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, n))
    colors[0] = [0.2, 0.7, 0.3, 1]  # Green for best
    
    bars = ax.barh(sorted_df['Family'], sorted_df['AIC'], color=colors)
    
    ax.set_xlabel('AIC (lower is better)')
    ax.set_ylabel('Copula Family')
    ax.set_title('Copula Fit Comparison')
    
    # Add value labels
    for bar, aic in zip(bars, sorted_df['AIC']):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
               f'{aic:.0f}', va='center', fontsize=10)
    
    # Highlight best
    ax.annotate('Best Fit', xy=(sorted_df['AIC'].iloc[0], 0),
               xytext=(sorted_df['AIC'].iloc[0] + 100, 0.5),
               fontsize=10, color='green',
               arrowprops=dict(arrowstyle='->', color='green'))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_cdf_comparison(cdf_df, copula_cols=None, save_path=None):
    """
    Plot CDF curves for all copulas + analytical solution.
    
    Parameters:
        cdf_df: DataFrame with 'v0' and copula/Analytical columns
        copula_cols: List of copula column names (auto-detect if None)
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Auto-detect copula columns
    if copula_cols is None:
        copula_cols = [c for c in cdf_df.columns if c not in ['v0', 'Analytical']]
    
    # Plot copula CDFs
    for copula in copula_cols:
        ax.plot(cdf_df['v0'], cdf_df[copula], linewidth=2, label=copula)
    
    # Plot analytical (dashed)
    if 'Analytical' in cdf_df.columns:
        ax.plot(cdf_df['v0'], cdf_df['Analytical'], 'k--', linewidth=2, 
               label='Analytical (Independent)', alpha=0.7)
    
    ax.set_xlabel(r'Runoff Volume $v_0$ (mm)')
    ax.set_ylabel(r'$F(v_0)$')
    ax.set_title('Runoff Volume CDF Comparison')
    ax.legend(loc='lower right')
    ax.set_xlim(0, cdf_df['v0'].max())
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_return_periods(return_df, period_col='ReturnPeriod', save_path=None):
    """
    Plot return period curves (log-scale x-axis).
    
    Parameters:
        return_df: DataFrame with return periods and volumes per copula
        period_col: Column name for return periods
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    copula_cols = [c for c in return_df.columns if c != period_col]
    
    for copula in copula_cols:
        ax.plot(return_df[period_col], return_df[copula], 'o-', 
               linewidth=2, markersize=6, label=copula)
    
    ax.set_xlabel('Return Period (years)')
    ax.set_ylabel(r'Runoff Volume $v_0$ (mm)')
    ax.set_title('Return Period Analysis')
    ax.legend(loc='upper left')
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3, which='both')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
    ax.set_xticks([2, 5, 10, 25, 50, 100])
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_return_period_error(return_df, period_col='ReturnPeriod', 
                             analytical_col='Analytical', save_path=None):
    """
    Plot error between copula return periods and analytical model.
    Shows percentage difference for each copula family.
    
    Parameters:
        return_df: DataFrame with return periods and volumes per copula
        period_col: Column name for return periods
        analytical_col: Column name for analytical solution
        save_path: Optional path to save figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    copula_cols = [c for c in return_df.columns 
                   if c not in [period_col, analytical_col]]
    
    # --- Left plot: Absolute error ---
    ax1 = axes[0]
    for copula in copula_cols:
        error = return_df[copula] - return_df[analytical_col]
        ax1.plot(return_df[period_col], error, 'o-', 
                linewidth=2, markersize=6, label=copula)
    
    ax1.axhline(0, color='black', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Return Period (years)')
    ax1.set_ylabel(r'$v_0^{copula} - v_0^{analytical}$ (mm)')
    ax1.set_title('Absolute Error: Copula vs Analytical')
    ax1.legend(loc='best')
    ax1.set_xscale('log')
    ax1.xaxis.set_major_formatter(ticker.ScalarFormatter())
    ax1.set_xticks([2, 5, 10, 25, 50, 100])
    ax1.grid(True, alpha=0.3, which='both')
    
    # --- Right plot: Percentage error ---
    ax2 = axes[1]
    for copula in copula_cols:
        pct_error = ((return_df[copula] - return_df[analytical_col]) 
                     / return_df[analytical_col] * 100)
        ax2.plot(return_df[period_col], pct_error, 'o-', 
                linewidth=2, markersize=6, label=copula)
    
    ax2.axhline(0, color='black', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Return Period (years)')
    ax2.set_ylabel('Percentage Error (%)')
    ax2.set_title('Relative Error: Copula vs Analytical')
    ax2.legend(loc='best')
    ax2.set_xscale('log')
    ax2.xaxis.set_major_formatter(ticker.ScalarFormatter())
    ax2.set_xticks([2, 5, 10, 25, 50, 100])
    ax2.grid(True, alpha=0.3, which='both')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


# =============================================================================
# NOTEBOOK 3: SENSITIVITY/UNCERTAINTY ANALYSIS
# =============================================================================

def plot_bootstrap_confidence_intervals(bootstrap_df, v0_col='v0', 
                                         mean_col='mean', 
                                         lower_col='ci_lower',
                                         upper_col='ci_upper',
                                         copula_name='Clayton',
                                         save_path=None):
    """
    CDF with shaded bootstrap confidence intervals.
    
    Parameters:
        bootstrap_df: DataFrame with mean and CI columns
        v0_col: Volume column name
        mean_col: Mean CDF column name
        lower_col: Lower CI bound column name
        upper_col: Upper CI bound column name
        copula_name: Name for legend
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Shaded confidence interval
    ax.fill_between(bootstrap_df[v0_col], 
                   bootstrap_df[lower_col],
                   bootstrap_df[upper_col],
                   alpha=0.3, color='steelblue',
                   label='95% Confidence Interval')
    
    # Mean line
    ax.plot(bootstrap_df[v0_col], bootstrap_df[mean_col],
           linewidth=2, color='steelblue',
           label=f'{copula_name} (Bootstrap Mean)')
    
    ax.set_xlabel(r'Runoff Volume $v_0$ (mm)')
    ax.set_ylabel(r'$F(v_0)$')
    ax.set_title(f'Bootstrap Uncertainty Analysis - {copula_name} Copula')
    ax.legend(loc='lower right')
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_parameter_sensitivity(sensitivity_df, param_values, 
                               v0_col='v0', param_name='θ',
                               save_path=None):
    """
    Multiple CDF curves colored by parameter value.
    
    Parameters:
        sensitivity_df: DataFrame with v0 and CDF columns for each parameter
        param_values: List of parameter values
        v0_col: Volume column name
        param_name: Parameter symbol for legend
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Color gradient from blue to red
    colors = plt.cm.coolwarm(np.linspace(0, 1, len(param_values)))
    
    for param, color in zip(param_values, colors):
        col_name = f'param_{param}' if f'param_{param}' in sensitivity_df.columns else str(param)
        if col_name in sensitivity_df.columns:
            ax.plot(sensitivity_df[v0_col], sensitivity_df[col_name],
                   color=color, linewidth=1.5, 
                   label=f'{param_name} = {param}')
    
    ax.set_xlabel(r'Runoff Volume $v_0$ (mm)')
    ax.set_ylabel(r'$F(v_0)$')
    ax.set_title(f'Effect of Copula Parameter on CDF')
    ax.legend(loc='lower right', ncol=2, fontsize=9)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    
    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap='coolwarm', 
                               norm=plt.Normalize(min(param_values), max(param_values)))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label(f'Parameter {param_name}')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


# =============================================================================
# EXAMPLE USAGE (uncomment to test)
# =============================================================================

if __name__ == "__main__":
    # Load example data
    results_dir = Path("./data/results/MULTI-STATIONS -- 20251222_002304 -- f4c9/THUNDER BAY A-6048261")
    
    events = pd.read_csv(results_dir / "01_input_data/03_rainfall_events_data.csv")
    metrics = pd.read_csv(results_dir / "02_copula_fitting/02_copula_fit_metrics.csv")
    cdf = pd.read_csv(results_dir / "02_copula_fitting/03_cdf_results.csv")
    returns = pd.read_csv(results_dir / "02_copula_fitting/04_return_periods.csv")
    
    # Generate plots
    plot_event_scatter_with_marginals(events)
    plot_copula_aic_comparison(metrics)
    plot_cdf_comparison(cdf)
    plot_return_period_error(returns)
    plot_event_statistics_boxplots(events)
    plot_copula_fitting_results(cdf)
    
    
    plt.show()

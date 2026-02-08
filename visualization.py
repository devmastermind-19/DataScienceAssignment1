import seaborn as sns
import matplotlib.pyplot as plt
import os
import config

def plot_economics(df, output_path):
    """
    Plots Tip % vs Surcharge.
    """
    fig, ax1 = plt.subplots(figsize=(10, 6))

    color = 'tab:blue'
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Avg Surcharge ($)', color=color)
    sns.barplot(x='month', y='avg_surcharge', data=df, ax=ax1, color='skyblue', alpha=0.6)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color = 'tab:red'
    ax2.set_ylabel('Avg Tip %', color=color)  # we already handled the x-label with ax1
    sns.lineplot(x=df.index, y='avg_tip_pct', data=df, sort=False, ax=ax2, color=color, marker='o')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title('2025 Monthly Avg Congestion Surcharge vs Tip Percentage')
    fig.tight_layout()
    plt.savefig(output_path)
    plt.close()


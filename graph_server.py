import pandas as pd
import matplotlib.pyplot as plt
import argparse
import glob
import os
from datetime import datetime

def find_latest_csv():
    """Find the most recent sequence data CSV file"""
    files = glob.glob("sequence_data_*.csv")
    if not files:
        print("No sequence data files found")
        return None
    
    return max(files, key=os.path.getctime)

def format_time_axis(ax, max_time):
    """Format time axis with appropriate time labels"""
    # Set tick intervals based on data range
    if max_time <= 60:  # Less than a minute
        tick_interval = 10  # Every 10 seconds
        ticks = range(0, int(max_time) + tick_interval, tick_interval)
        labels = [f"{t}s" for t in ticks]
    elif max_time <= 300:  # Less than 5 minutes
        tick_interval = 30  # Every 30 seconds
        ticks = range(0, int(max_time) + tick_interval, tick_interval)
        labels = [f"{t}s" for t in ticks]
    else:
        # For longer durations, format as minutes and seconds
        tick_interval = 60  # Every minute
        ticks = range(0, int(max_time) + tick_interval, tick_interval)
        labels = [f"{t//60}m {t%60}s" if t >= 60 else f"{t}s" for t in ticks]
    
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.set_xlabel('Time (seconds)', fontsize=10)
    return ax

def create_stats_text(df):
    """Create statistics text from dataframe"""
    if len(df) == 0:
        return ""
        
    last_row = df.iloc[-1]
    total_packets = last_row['received'] + last_row['missing']
    final_goodput = last_row['goodput']
    
    return (
        f"Final Statistics:\n"
        f"Total Time: {last_row['timestamp']:.2f} seconds\n"
        f"Total Packets: {int(total_packets)}\n"
        f"Received: {int(last_row['received'])} ({last_row['received']/total_packets*100:.2f}%)\n"
        f"Missing: {int(last_row['missing'])} ({last_row['missing']/total_packets*100:.2f}%)\n"
        f"Final Goodput: {final_goodput:.4f}\n"
        f"Final Window Size: {int(last_row['window_size'])}"
    )

def plot_sequence_data(csv_file):
    """Plot the sequence data from the CSV file into separate charts"""
    # Read the CSV file
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} data points from {csv_file}")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Skip processing if no data
    if len(df) == 0:
        print("No data points found in the CSV file")
        return
    
    # Get timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get max time for consistent x-axis formatting across all charts
    max_time = df['timestamp'].max()
    
    # Calculate stats text once to reuse
    stats_text = create_stats_text(df)
    
    # Define a color palette for consistency
    colors = {
        'received': '#1f77b4',  # Blue
        'missing': '#d62728',   # Red
        'goodput': '#2ca02c',   # Green
        'window': '#9467bd'     # Purple
    }
    
    # Common figure size for all charts
    figsize = (10, 6)

    # ---------- Chart 4: Packets Sent Over Time ----------
    fig1, ax1 = plt.subplots(figsize=figsize)
    ax1.plot(df['timestamp'], df['received'], color=colors['window'], linewidth=2)
    ax1.set_ylabel('Packets Sent', fontsize=10)
    ax1.set_title(f'Cumulative Packets Sent Over Time - {os.path.basename(csv_file)}', fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.7)
    format_time_axis(ax1, max_time)
    ax1.set_xlim(0, max_time * 1.02)  # Add 2% padding on the right
    
    # Add stats at bottom of chart
    plt.figtext(0.5, 0.01, stats_text, ha='center', fontsize=9, 
                bbox=dict(facecolor='lightgray', alpha=0.5, boxstyle='round,pad=0.5'))
    
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])  # Leave space for stats
    received_file = f"packets_sent_{timestamp}.png"
    plt.savefig(received_file, dpi=300, bbox_inches='tight')
    print(f"Saved to {received_file}")
    plt.close(fig1)
    
    # ---------- Chart 1: Packets Received Over Time ----------
    fig1, ax1 = plt.subplots(figsize=figsize)
    ax1.plot(df['timestamp'], df['received'], color=colors['received'], linewidth=2)
    ax1.set_ylabel('Packets Received', fontsize=10)
    ax1.set_title(f'Cumulative Packets Received Over Time - {os.path.basename(csv_file)}', fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.7)
    format_time_axis(ax1, max_time)
    ax1.set_xlim(0, max_time * 1.02)  # Add 2% padding on the right
    
    # Add stats at bottom of chart
    plt.figtext(0.5, 0.01, stats_text, ha='center', fontsize=9, 
                bbox=dict(facecolor='lightgray', alpha=0.5, boxstyle='round,pad=0.5'))
    
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])  # Leave space for stats
    received_file = f"packets_received_{timestamp}.png"
    plt.savefig(received_file, dpi=300, bbox_inches='tight')
    print(f"Saved to {received_file}")
    plt.close(fig1)
    
    # ---------- Chart 2: Missing Packets Over Time ----------
    fig2, ax2 = plt.subplots(figsize=figsize)
    ax2.plot(df['timestamp'], df['missing'], color=colors['missing'], linewidth=2)
    ax2.set_ylabel('Missing Packets', fontsize=10)
    ax2.set_title(f'Cumulative Missing Packets Over Time - {os.path.basename(csv_file)}', fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.7)
    format_time_axis(ax2, max_time)
    ax2.set_xlim(0, max_time * 1.02)
    
    # Add stats at bottom of chart
    plt.figtext(0.5, 0.01, stats_text, ha='center', fontsize=9, 
                bbox=dict(facecolor='lightgray', alpha=0.5, boxstyle='round,pad=0.5'))
    
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])
    missing_file = f"missing_packets_{timestamp}.png"
    plt.savefig(missing_file, dpi=300, bbox_inches='tight')
    print(f"Saved to {missing_file}")
    plt.close(fig2)
    
    # ---------- Chart 3: Goodput Over Time ----------
    fig3, ax3 = plt.subplots(figsize=figsize)
    ax3.plot(df['timestamp'], df['goodput'], color=colors['goodput'], linewidth=2)
    ax3.set_ylabel('Goodput Ratio', fontsize=10)
    ax3.set_title(f'Goodput Ratio Over Time - {os.path.basename(csv_file)}', fontsize=12)
    ax3.grid(True, linestyle='--', alpha=0.7)
    ax3.set_ylim(0, 1)  # Goodput is a ratio between 0 and 1
    format_time_axis(ax3, max_time)
    ax3.set_xlim(0, max_time * 1.02)
    
    # Add stats at bottom of chart
    plt.figtext(0.5, 0.01, stats_text, ha='center', fontsize=9, 
                bbox=dict(facecolor='lightgray', alpha=0.5, boxstyle='round,pad=0.5'))
    
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])
    goodput_file = f"goodput_{timestamp}.png"
    plt.savefig(goodput_file, dpi=300, bbox_inches='tight')
    print(f"Saved to {goodput_file}")
    plt.close(fig3)
    
    # ---------- Chart 4: Window Size Over Time ----------
    fig4, ax4 = plt.subplots(figsize=figsize)
    ax4.plot(df['timestamp'], df['window_size'], color=colors['window'], linewidth=2)
    ax4.set_ylabel('Window Size', fontsize=10)
    ax4.set_title(f'TCP Window Size Over Time - {os.path.basename(csv_file)}', fontsize=12)
    ax4.grid(True, linestyle='--', alpha=0.7)
    format_time_axis(ax4, max_time)
    ax4.set_xlim(0, max_time * 1.02)
    
    # Center the window size plot
    window_vals = df['window_size'].unique()
    if len(window_vals) == 1:  # Constant window size
        base_val = window_vals[0]
        # Set a fixed range for better visibility
        y_min = max(0, base_val - 20)  # Prevent negative window sizes
        y_max = base_val + 20
    else:
        y_min = max(0, df['window_size'].min() - 10)  # Prevent negative window sizes
        y_max = df['window_size'].max() + 10
    
    ax4.set_ylim(y_min, y_max)
    
    # Add stats at bottom of chart
    plt.figtext(0.5, 0.01, stats_text, ha='center', fontsize=9, 
                bbox=dict(facecolor='lightgray', alpha=0.5, boxstyle='round,pad=0.5'))
    
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])
    window_file = f"window_size_{timestamp}.png"
    plt.savefig(window_file, dpi=300, bbox_inches='tight')
    print(f"Saved to {window_file}")
    plt.close(fig4)
    
    print("All charts have been saved as separate PNG files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot sequence data from CSV')
    parser.add_argument('--file', help='CSV file to plot (if not provided, uses most recent)')
    args = parser.parse_args()
    
    csv_file = args.file if args.file else find_latest_csv()
    
    if csv_file:
        plot_sequence_data(csv_file)
    else:
        print("No CSV file specified or found")

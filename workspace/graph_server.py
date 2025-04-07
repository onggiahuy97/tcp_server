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

def plot_sequence_data(csv_file):
    """Plot the sequence data from the CSV file"""
    # Read the CSV file
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} data points from {csv_file}")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Create figure with subplots - increase figure height to make room for stats
    fig, axs = plt.subplots(3, 1, figsize=(12, 16), sharex=True)
    fig.suptitle(f'Network Performance Analysis - {os.path.basename(csv_file)}', fontsize=16)
    
    # Plot 1: Packets Received Over Time
    axs[0].plot(df['timestamp'], df['received'], 'b-', linewidth=2)
    axs[0].set_ylabel('Packets Received')
    axs[0].set_title('Cumulative Packets Received Over Time')
    axs[0].grid(True)
    
    # Plot 2: Missing Packets Over Time
    axs[1].plot(df['timestamp'], df['missing'], 'r-', linewidth=2)
    axs[1].set_ylabel('Missing Packets')
    axs[1].set_title('Cumulative Missing Packets Over Time')
    axs[1].grid(True)
    
    # Plot 3: Goodput Over Time
    axs[2].plot(df['timestamp'], df['goodput'], 'g-', linewidth=2)
    axs[2].set_xlabel('Time (seconds)')
    axs[2].set_ylabel('Goodput Ratio')
    axs[2].set_title('Goodput Ratio Over Time')
    axs[2].grid(True)
    axs[2].set_ylim(0, 1)  # Goodput is a ratio between 0 and 1
    
    # Calculate packet loss rate
    last_row = df.iloc[-1]
    total_packets = last_row['received'] + last_row['missing']
    final_goodput = last_row['goodput']
    
    stats_text = (
        f"Final Statistics:\n"
        f"Total Time: {last_row['timestamp']:.2f} seconds\n"
        f"Total Packets: {int(total_packets)}\n"
        f"Received: {int(last_row['received'])} ({last_row['received']/total_packets*100:.2f}%)\n"
        f"Missing: {int(last_row['missing'])} ({last_row['missing']/total_packets*100:.2f}%)\n"
        f"Final Goodput: {final_goodput:.4f}"
    )
    
    # Tighten layout but leave more space at the bottom for stats
    plt.tight_layout(rect=[0, 0.06, 1, 0.97])
    
    # Add text box with statistics - moved lower with negative y position
    plt.figtext(0.5, -0.02, stats_text, ha='center', fontsize=12, 
                bbox=dict(facecolor='lightgray', alpha=0.5))
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"network_analysis_{timestamp}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')  # Added bbox_inches to ensure stats are included
    print(f"Analysis saved to {output_file}")
    
    # Show the plot
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot sequence data from CSV')
    parser.add_argument('--file', help='CSV file to plot (if not provided, uses most recent)')
    args = parser.parse_args()
    
    csv_file = args.file if args.file else find_latest_csv()
    
    if csv_file:
        plot_sequence_data(csv_file)
    else:
        print("No CSV file specified or found")

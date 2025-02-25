import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

def create_visualization():
    """Create visualizations for TCP project performance data"""
    
    # Check if performance data exists
    if not os.path.exists("tcp_performance_data.json"):
        print("Error: Performance data file not found. Run the server first.")
        return
    
    # Load the performance data
    with open("tcp_performance_data.json", "r") as f:
        data = json.load(f)
    
    # Extract data
    times = data["checkpoint_times"]
    goodput = data["goodput_values"]
    missing = data["missing_packet_counts"]
    received = data["received_packet_counts"]
    
    # Calculate additional metrics
    packet_rates = []
    for i in range(1, len(times)):
        time_diff = times[i] - times[i-1]
        packet_diff = received[i] - received[i-1]
        rate = packet_diff / time_diff if time_diff > 0 else 0
        packet_rates.append(rate)
    
    # Create a pandas DataFrame for table output
    metrics_df = pd.DataFrame({
        "Checkpoint": range(1, len(times)+1),
        "Time (s)": [round(t, 2) for t in times],
        "Packets Received": received,
        "Missing Packets": missing,
        "Goodput (%)": [round(g, 2) for g in goodput]
    })
    
    if len(packet_rates) > 0:
        # Add packet rates (skip first checkpoint as we don't have a rate yet)
        metrics_df.loc[1:, "Packet Rate (pkts/s)"] = [round(r, 2) for r in packet_rates]
    
    # Calculate summary statistics
    summary = {
        "Total Execution Time (s)": round(times[-1], 2),
        "Total Packets Received": received[-1],
        "Total Missing Packets": missing[-1],
        "Final Goodput (%)": round(goodput[-1], 2),
        "Average Packet Rate (pkts/s)": round(received[-1] / times[-1], 2) if times[-1] > 0 else 0
    }
    
    summary_df = pd.DataFrame(list(summary.items()), columns=["Metric", "Value"])
    
    # Set up the figure with multiple subplots
    plt.figure(figsize=(15, 18))
    
    # 1. Goodput over time
    plt.subplot(3, 1, 1)
    plt.plot(times, goodput, 'b-', linewidth=2)
    plt.title('Goodput over Time', fontsize=16)
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Goodput (%)', fontsize=12)
    plt.grid(True)
    plt.ylim(min(goodput) - 1 if goodput else 0, 101)
    
    # 2. Missing packets over time
    plt.subplot(3, 1, 2)
    plt.plot(times, missing, 'r-', linewidth=2)
    plt.title('Missing Packets over Time', fontsize=16)
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Number of Missing Packets', fontsize=12)
    plt.grid(True)
    
    # 3. Packet processing rate over time
    if packet_rates:
        plt.subplot(3, 1, 3)
        plt.plot(times[1:], packet_rates, 'g-', linewidth=2)
        plt.title('Packet Processing Rate over Time', fontsize=16)
        plt.xlabel('Time (seconds)', fontsize=12)
        plt.ylabel('Packets per Second', fontsize=12)
        plt.grid(True)
    
    # Save the figures
    plt.tight_layout()
    plt.savefig('tcp_performance_graphs.png', dpi=300)
    print("Performance graphs saved to tcp_performance_graphs.png")
    
    # Save tables to CSV
    metrics_df.to_csv('tcp_performance_metrics.csv', index=False)
    summary_df.to_csv('tcp_performance_summary.csv', index=False)
    print("Performance metrics saved to tcp_performance_metrics.csv")
    print("Performance summary saved to tcp_performance_summary.csv")
    
    # Print summary table
    print("\nPerformance Summary:")
    print("="*50)
    for metric, value in summary.items():
        print(f"{metric}: {value}")
    
    # Print sample of metrics table
    print("\nPerformance Metrics (first 5 checkpoints):")
    print("="*50)
    print(metrics_df.head().to_string(index=False))
    
    # Create HTML report with all the information
    create_html_report(metrics_df, summary_df)

def create_html_report(metrics_df, summary_df):
    """Create an HTML report with all performance data"""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>TCP Sliding Window Performance Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #2c3e50; }
            h2 { color: #3498db; margin-top: 30px; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            img { max-width: 100%; height: auto; margin-top: 20px; }
        </style>
    </head>
    <body>
        <h1>TCP Sliding Window Performance Report</h1>
        
        <h2>Performance Summary</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
    """
    
    # Add summary table
    for _, row in summary_df.iterrows():
        html += f"""
            <tr>
                <td>{row['Metric']}</td>
                <td>{row['Value']}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Performance Graphs</h2>
        <img src="tcp_performance_graphs.png" alt="TCP Performance Graphs">
        
        <h2>Detailed Metrics</h2>
        <table>
            <tr>
    """
    
    # Add metrics table headers
    for col in metrics_df.columns:
        html += f"<th>{col}</th>"
    
    html += "</tr>"
    
    # Add metrics table rows (limit to 20 rows for readability)
    row_limit = min(20, len(metrics_df))
    for i in range(row_limit):
        html += "<tr>"
        for col in metrics_df.columns:
            html += f"<td>{metrics_df.iloc[i][col]}</td>"
        html += "</tr>"
    
    html += """
        </table>
        
        <p><em>Note: Table limited to first 20 checkpoints. See CSV file for complete data.</em></p>
    </body>
    </html>
    """
    
    # Save the HTML report
    with open("tcp_performance_report.html", "w") as f:
        f.write(html)
    
    print("HTML report saved to tcp_performance_report.html")

if __name__ == "__main__":
    create_visualization()

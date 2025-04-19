# TCP Sliding Window Protocol Simulation

## Project Overview

This project implements a basic TCP sliding window protocol simulation between a client and server. It was developed to demonstrate core TCP concepts including sequence numbers, acknowledgments, packet loss, and retransmission.

## Features

- **TCP Sliding Window**: Implementation of sliding window flow control mechanism
- **Packet Loss Simulation**: Client probabilistically drops 1% of packets
- **Retransmission Protocol**: Dropped packets are retransmitted after a time interval
- **Performance Monitoring**: Server tracks goodput (received packets / total sent packets)
- **Network Resilience**: Handles network disruptions and packet loss gracefully

## Components

### Client (`client.py`)
- Initiates connection with server
- Sends sequence numbers in a sliding window fashion
- Simulates packet loss (1% drop probability)
- Handles retransmission of dropped packets
- Maintains window size of 500 packets
- Supports up to 10,000,000 packet transmissions

### Server (`server.py`)
- Listens for incoming connections
- Tracks received and missing sequence numbers
- Sends acknowledgments back to client
- Calculates and logs goodput statistics
- Saves sequence data to CSV for later analysis

## Usage

1. Start the server on the destination machine:
   ```
   python server.py
   ```

2. Start the client on the source machine:
   ```
   python client.py
   ```

3. By default, the client connects to localhost. To connect to a remote server, modify the `host` parameter in the `PacketClient` class initialization.

## Configuration Parameters

- **window_size**: Controls sliding window size (default: 500)
- **drop_prob**: Probability of packet dropping (default: 0.01 or 1%)
- **max_packets**: Maximum number of packets to send (default: 10,000,000)
- **max_seq**: Maximum sequence number (default: 2^16)

## Requirements

- Python 3.6+
- Standard Python libraries (socket, struct, threading, logging)

package main

import (
	"bufio"
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"
)

// Constants for sequence numbering and reporting.
const (
	maxSequenceNumber = 1 << 16 // Maximum sequence number (65536) before wrapping.
	reportInterval    = 1000    // Number of packets to process before printing a progress report.
	targetPackets     = 500_000 // Total number of packets to be received.
)

// SimpleTracker tracks the statistics of received packets.
type SimpleTracker struct {
	lastSeq       int   // Last sequence number received.
	wrapCount     int64 // Count of sequence number wrap-arounds.
	receivedCount int64 // Total number of packets received.
	missingCount  int64 // Count of packets detected as missing.
	lastGap       int   // The gap value of the last packet (used for debugging).
}

// newSimpleTracker creates and returns a new SimpleTracker instance.
func newSimpleTracker() *SimpleTracker {
	return &SimpleTracker{
		lastSeq: -1, // Indicates that no packet has been received yet.
	}
}

// recordPacket processes an incoming packet's sequence number.
// It updates received and missing counts and accounts for wrap-around.
func (st *SimpleTracker) recordPacket(seq int) {
	// If this is the first packet, initialize lastSeq.
	if st.lastSeq == -1 {
		st.lastSeq = seq
		st.receivedCount++
		return
	}

	// Calculate the gap between the current sequence and the last received.
	gap := seq - st.lastSeq

	// Adjust gap if there is a wrap-around.
	// If gap is negative beyond half the maximum, we assume a forward wrap-around.
	if gap < -(maxSequenceNumber / 2) {
		gap += maxSequenceNumber
		st.wrapCount++
	} else if gap > (maxSequenceNumber / 2) {
		// This case handles out-of-order packets from a previous wrap.
		gap -= maxSequenceNumber
	}

	// If gap is positive, some packets are missing.
	if gap > 0 {
		// Increase missing count by gap-1 (the packets in between).
		st.missingCount += int64(gap - 1)
		// Update lastSeq to the current packet's sequence.
		st.lastSeq = seq
	}
	// If gap is negative, the packet is out-of-order and we do not update lastSeq.

	// Increase the received packet count and record the last gap for debugging.
	st.receivedCount++
	st.lastGap = gap
}

// goodput calculates the ratio of successfully received packets over the total expected packets.
func (st *SimpleTracker) goodput() float64 {
	totalPackets := st.receivedCount + st.missingCount
	if totalPackets <= 0 {
		return 0.0
	}
	return float64(st.receivedCount) / float64(totalPackets)
}

// main starts the TCP server and accepts client connections.
func main() {
	// Listen on TCP port 8080.
	listener, err := net.Listen("tcp", ":8081")
	if err != nil {
		fmt.Println("Error starting server:", err)
		return
	}
	defer listener.Close()
	fmt.Println("Server listening on port 8080...")

	// Continuously accept incoming connections.
	for {
		conn, err := listener.Accept()
		if err != nil {
			fmt.Println("Error accepting connection:", err)
			continue
		}
		// Handle each connection concurrently.
		go handleConnection(conn)
	}
}

// handleConnection processes an individual client connection.
func handleConnection(conn net.Conn) {
	defer conn.Close()
	fmt.Println("New client connected:", conn.RemoteAddr().String())

	// Create a scanner to read incoming data from the connection.
	scanner := bufio.NewScanner(conn)
	// Increase the scanner's buffer size to support large messages.
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	// Initialize a new tracker to record packet statistics.
	tracker := newSimpleTracker()

	// Read the initial message from the client.
	if !scanner.Scan() {
		fmt.Println("Error reading initial message (client disconnected?)")
		return
	}
	initialMessage := scanner.Text()
	fmt.Println("Initial message from client:", initialMessage)

	// Send a confirmation message back to the client.
	if _, err := conn.Write([]byte("success\n")); err != nil {
		fmt.Println("Error sending success message:", err)
		return
	}

	// Variables to manage reporting intervals.
	packetsReceivedSinceReport := 0
	startTime := time.Now()
	lastReportTime := startTime

	// Process incoming messages.
	for scanner.Scan() {
		// Stop processing if we've reached the target packet count.
		if tracker.receivedCount >= targetPackets {
			break
		}

		line := scanner.Text()
		if line == "" {
			continue
		}

		// Split the received line into individual packet sequence numbers.
		parts := strings.Split(line, ",")
		for _, p := range parts {
			seq, err := strconv.Atoi(strings.TrimSpace(p))
			if err != nil {
				// Skip any invalid sequence numbers.
				continue
			}

			// Record the packet and update statistics.
			tracker.recordPacket(seq)
			packetsReceivedSinceReport++

			// If we've processed enough packets, print a progress report.
			if packetsReceivedSinceReport >= reportInterval {
				now := time.Now()
				elapsed := now.Sub(lastReportTime)
				lastReportTime = now

				gp := tracker.goodput()
				percent := float64(tracker.receivedCount) * 100.0 / float64(targetPackets)

				fmt.Printf("Progress: %.3f%% | Received: %d | Missing: %d | Goodput: %.4f | Wraps: %d | Rate: %.2f pkts/s | Last Gap: %d\n",
					percent,
					tracker.receivedCount,
					tracker.missingCount,
					gp,
					tracker.wrapCount,
					float64(reportInterval)/elapsed.Seconds(),
					tracker.lastGap,
				)
				packetsReceivedSinceReport = 0
			}
		}

		// Send an acknowledgment (ACK) back to the client for the received line.
		ackMsg := line + "\n"
		if _, err := conn.Write([]byte(ackMsg)); err != nil {
			fmt.Println("Error sending ACK:", err)
			return
		}
	}

	// After processing, calculate the duration and final statistics.
	duration := time.Since(startTime)
	finalGP := tracker.goodput()
	fmt.Printf("\nFinal Stats:\n")
	fmt.Printf("  Total Received : %d\n", tracker.receivedCount)
	fmt.Printf("  Total Missing  : %d\n", tracker.missingCount)
	fmt.Printf("  Final Goodput  : %.4f\n", finalGP)
	fmt.Printf("  Total Wraps    : %d\n", tracker.wrapCount)
	fmt.Printf("  Time Elapsed   : %.2fs\n", duration.Seconds())
	fmt.Printf("  Average Rate   : %.2f pkts/s\n", float64(tracker.receivedCount)/duration.Seconds())

	// Check for any scanning errors.
	if err := scanner.Err(); err != nil {
		fmt.Println("Error reading from connection:", err)
	}
}

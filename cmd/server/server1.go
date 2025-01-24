package abc

import (
	"bufio"
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"
)

const (
	maxSequenceNumber = 1 << 16 // 65536
	reportInterval    = 1000
	targetPackets     = 50_000
)

type SimpleTracker struct {
	lastSeq       int
	wrapCount     int64
	receivedCount int64
	missingCount  int64
	lastGap       int // Track the last gap size for debugging
}

func newSimpleTracker() *SimpleTracker {
	return &SimpleTracker{
		lastSeq: -1, // indicates we haven't received any packet yet
	}
}

func (st *SimpleTracker) recordPacket(seq int) {
	if st.lastSeq == -1 {
		// first packet ever
		st.lastSeq = seq
		st.receivedCount++
		return
	}

	// Calculate the effective gap considering wrap-around
	gap := seq - st.lastSeq
	if gap < -(maxSequenceNumber / 2) {
		// Sequence wrapped around forward
		gap += maxSequenceNumber
		st.wrapCount++
	} else if gap > (maxSequenceNumber / 2) {
		// Out of order packet from previous wrap
		gap -= maxSequenceNumber
	}

	if gap > 0 {
		// We found missing packets
		st.missingCount += int64(gap - 1)
		st.lastSeq = seq
	} else if gap < 0 {
		// Out of order packet, don't update lastSeq
	}

	st.receivedCount++
	st.lastGap = gap // For debugging
}

func (st *SimpleTracker) goodput() float64 {
	// Total packets should be the sum of received and missing
	totalPackets := st.receivedCount + st.missingCount
	if totalPackets <= 0 {
		return 0.0
	}
	return float64(st.receivedCount) / float64(totalPackets)
}

func main() {
	listener, err := net.Listen("tcp", ":8080")
	if err != nil {
		fmt.Println("Error starting server:", err)
		return
	}
	defer listener.Close()
	fmt.Println("Server listening on port 8080...")

	for {
		conn, err := listener.Accept()
		if err != nil {
			fmt.Println("Error accepting connection:", err)
			continue
		}
		go handleConnection(conn)
	}
}

func handleConnection(conn net.Conn) {
	defer conn.Close()
	fmt.Println("New client connected:", conn.RemoteAddr().String())

	scanner := bufio.NewScanner(conn)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	tracker := newSimpleTracker()

	if !scanner.Scan() {
		fmt.Println("Error reading initial message (client disconnected?)")
		return
	}
	initialMessage := scanner.Text()
	fmt.Println("Initial message from client:", initialMessage)

	_, err := conn.Write([]byte("success\n"))
	if err != nil {
		fmt.Println("Error sending success message:", err)
		return
	}

	packetsReceivedSinceReport := 0
	startTime := time.Now()
	lastReportTime := startTime

	for scanner.Scan() {
		if tracker.receivedCount >= targetPackets {
			break
		}

		line := scanner.Text()
		if line == "" {
			continue
		}

		parts := strings.Split(line, ",")
		for _, p := range parts {
			seq, err := strconv.Atoi(strings.TrimSpace(p))
			if err != nil {
				continue
			}

			tracker.recordPacket(seq)
			packetsReceivedSinceReport++

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

		// Send ACK
		ackMsg := line + "\n"
		if _, err := conn.Write([]byte(ackMsg)); err != nil {
			fmt.Println("Error sending ACK:", err)
			return
		}
	}

	duration := time.Since(startTime)
	finalGP := tracker.goodput()
	fmt.Printf("\nFinal Stats:\n")
	fmt.Printf("  Total Received : %d\n", tracker.receivedCount)
	fmt.Printf("  Total Missing  : %d\n", tracker.missingCount)
	fmt.Printf("  Final Goodput  : %.4f\n", finalGP)
	fmt.Printf("  Total Wraps    : %d\n", tracker.wrapCount)
	fmt.Printf("  Time Elapsed   : %.2fs\n", duration.Seconds())
	fmt.Printf("  Average Rate   : %.2f pkts/s\n", float64(tracker.receivedCount)/duration.Seconds())

	if err := scanner.Err(); err != nil {
		fmt.Println("Error reading from connection:", err)
	}
}

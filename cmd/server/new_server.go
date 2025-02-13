package main

import (
	"bufio"
	"fmt"
	"net"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	maxSequenceNumber = 1 << 16   // Maximum sequence number (65536)
	reportInterval    = 1000      // Report stats every 1000 packets
	targetPackets     = 1_000_000 // Total packets to receive
)

type ServerStats struct {
	receivedPackets   int64
	missingPackets    int64
	lastSequence      int
	lastReportTime    time.Time
	packetsInInterval int
	mu                sync.Mutex
}

func NewServerStats() *ServerStats {
	return &ServerStats{
		lastSequence:   -1,
		lastReportTime: time.Now(),
	}
}

type Server struct {
	listener net.Listener
	stats    *ServerStats
}

func NewServer(listener net.Listener) *Server {
	return &Server{
		listener: listener,
		stats:    NewServerStats(),
	}
}

func (s *Server) handleSequence(seq int) {
	s.stats.mu.Lock()
	defer s.stats.mu.Unlock()

	// Update received packets count
	s.stats.receivedPackets++
	s.stats.packetsInInterval++

	// Calculate missing packets if this isn't the first packet
	if s.stats.lastSequence != -1 {
		gap := seq - s.stats.lastSequence - 1
		if gap > 0 {
			s.stats.missingPackets += int64(gap)
		}
	}
	s.stats.lastSequence = seq

	// Check if it's time to report
	if s.stats.packetsInInterval >= reportInterval {
		now := time.Now()
		duration := now.Sub(s.stats.lastReportTime)
		rate := float64(s.stats.packetsInInterval) / duration.Seconds()
		goodput := float64(s.stats.receivedPackets) / float64(s.stats.receivedPackets+s.stats.missingPackets)
		progress := float64(s.stats.receivedPackets) * 100 / float64(targetPackets)

		fmt.Printf("Progress: %.2f%% | Received: %d | Missing: %d | Goodput: %.4f | Rate: %.2f pkts/s\n",
			progress, s.stats.receivedPackets, s.stats.missingPackets, goodput, rate)

		// Reset interval counter and update last report time
		s.stats.packetsInInterval = 0
		s.stats.lastReportTime = now
	}
}

func (s *Server) handleConnection(conn net.Conn) {
	defer conn.Close()
	fmt.Printf("New client connected: %s\n", conn.RemoteAddr().String())

	scanner := bufio.NewScanner(conn)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	// Handle initial message
	if !scanner.Scan() {
		fmt.Println("Error reading initial message")
		return
	}
	initialMsg := scanner.Text()
	fmt.Printf("Initial message: %s\n", initialMsg)

	// Send success response
	if _, err := conn.Write([]byte("success\n")); err != nil {
		fmt.Println("Error sending success message:", err)
		return
	}

	// Process incoming packets
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		// Process received sequence numbers
		sequences := strings.Split(line, ",")
		for _, seqStr := range sequences {
			seq, err := strconv.Atoi(strings.TrimSpace(seqStr))
			if err != nil {
				continue
			}
			s.handleSequence(seq)
		}

		// Send acknowledgments back
		ackMsg := line + "\n"
		if _, err := conn.Write([]byte(ackMsg)); err != nil {
			fmt.Println("Error sending ACK:", err)
			return
		}

		// Check for finish message from client
		if line == "FINISH" {
			s.printFinalStats()
			fmt.Println("\nServer shutting down...")
			return
		}

		// Check if we've reached the target
		if s.stats.receivedPackets >= targetPackets {
			s.printFinalStats()
			fmt.Println("\nServer shutting down...")
			return
		}
	}

	if err := scanner.Err(); err != nil {
		fmt.Println("Error reading from connection:", err)
	}
}

func (s *Server) printFinalStats() {
	s.stats.mu.Lock()
	defer s.stats.mu.Unlock()

	totalTime := time.Since(s.stats.lastReportTime)
	goodput := float64(s.stats.receivedPackets) / float64(s.stats.receivedPackets+s.stats.missingPackets)
	rate := float64(s.stats.receivedPackets) / totalTime.Seconds()

	fmt.Printf("\n========== Final Statistics ==========\n")
	fmt.Printf("Total Running Time: %.2f seconds\n", totalTime.Seconds())
	fmt.Printf("Total Packets Received: %d\n", s.stats.receivedPackets)
	fmt.Printf("Total Missing Packets: %d\n", s.stats.missingPackets)
	fmt.Printf("Final Goodput: %.4f\n", goodput)
	fmt.Printf("Average Rate: %.2f packets/second\n", rate)
	fmt.Printf("Loss Rate: %.4f%%\n", 100*float64(s.stats.missingPackets)/float64(s.stats.receivedPackets+s.stats.missingPackets))
	fmt.Printf("====================================\n")
}

func main() {
	listener, err := net.Listen("tcp", ":8080")
	if err != nil {
		fmt.Println("Error starting server:", err)
		return
	}
	defer listener.Close()

	fmt.Println("Server listening on port 8080...")

	server := NewServer(listener)

	for {
		conn, err := listener.Accept()
		if err != nil {
			fmt.Println("Error accepting connection:", err)
			continue
		}
		go server.handleConnection(conn)
	}
}

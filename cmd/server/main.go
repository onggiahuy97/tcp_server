package main

import (
	"bufio"
	"fmt"
	"log"
	"net"
	"strconv"
	"strings"
	"sync"
)

const (
	MAX_SEQ_NUM     = 65536 // 2^16
	REPORT_INTERVAL = 1000  // Report goodput every 1000 packets
)

type Server struct {
	receivedPackets map[int]bool
	missingPackets  map[int]bool
	totalReceived   int
	totalExpected   int
	mutex           sync.Mutex
	lastReported    int
}

func NewServer() *Server {
	return &Server{
		receivedPackets: make(map[int]bool),
		missingPackets:  make(map[int]bool),
		totalReceived:   0,
		totalExpected:   0,
		lastReported:    0,
	}
}

func (s *Server) handleConnection(conn net.Conn) {
	defer conn.Close()

	// Handle initial connection
	reader := bufio.NewReader(conn)
	initMsg, err := reader.ReadString('\n')
	if err != nil {
		log.Printf("Error reading initial message: %v", err)
		return
	}

	initMsg = strings.TrimSpace(initMsg)
	if initMsg != "network" {
		log.Printf("Invalid initial message: %s", initMsg)
		return
	}

	// Send success message
	conn.Write([]byte("success\n"))

	// Handle sequence numbers
	for {
		seqStr, err := reader.ReadString('\n')
		if err != nil {
			log.Printf("Connection closed: %v", err)
			return
		}

		seqNum, err := strconv.Atoi(strings.TrimSpace(seqStr))
		if err != nil {
			continue
		}

		s.handleSequenceNumber(seqNum, conn)
	}
}

func (s *Server) handleSequenceNumber(seqNum int, conn net.Conn) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	// Record received packet
	s.receivedPackets[seqNum] = true
	s.totalReceived++
	s.totalExpected++

	// Check for missing packets
	for i := s.lastReported; i < seqNum; i++ {
		if !s.receivedPackets[i] {
			s.missingPackets[i] = true
		}
	}

	// Send ACK
	ack := fmt.Sprintf("ACK %d\n", seqNum)
	conn.Write([]byte(ack))

	// Report goodput every REPORT_INTERVAL packets
	if s.totalReceived%REPORT_INTERVAL == 0 {
		goodput := float64(s.totalReceived) / float64(s.totalExpected)
		fmt.Printf("Goodput after %d packets: %.4f\n", s.totalReceived, goodput)
		fmt.Printf("Missing packets: %d\n", len(s.missingPackets))
	}
}

func main() {
	listener, err := net.Listen("tcp", ":8080")
	if err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	defer listener.Close()

	fmt.Println("Server listening on :8080")
	server := NewServer()

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Failed to accept connection: %v", err)
			continue
		}

		go server.handleConnection(conn)
	}
}

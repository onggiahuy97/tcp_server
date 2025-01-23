package main

import (
	"bufio"
	"fmt"
	"log"
	"math/rand"
	"net"
	"strings"
	"time"
)

const (
	WINDOW_SIZE         = 10
	DROP_PROBABILITY    = 0.01 // 1% packet drop rate
	RETRANSMIT_INTERVAL = 100  // Retransmit after 100 sequence numbers
	TOTAL_PACKETS       = 10000
	MAX_SEQ_NUM         = 65536 // 2^16
)

type Client struct {
	conn            net.Conn
	windowStart     int
	windowEnd       int
	nextSeqNum      int
	droppedPackets  map[int]bool
	retransmitQueue []int
}

func NewClient(conn net.Conn) *Client {
	return &Client{
		conn:           conn,
		windowStart:    0,
		windowEnd:      WINDOW_SIZE,
		nextSeqNum:     0,
		droppedPackets: make(map[int]bool),
	}
}

func (c *Client) sendPacket(seqNum int) bool {
	// Simulate packet drop
	if rand.Float64() < DROP_PROBABILITY {
		c.droppedPackets[seqNum] = true
		return false
	}

	// Send sequence number
	_, err := fmt.Fprintf(c.conn, "%d\n", seqNum)
	if err != nil {
		log.Printf("Failed to send packet %d: %v", seqNum, err)
		return false
	}

	return true
}

func (c *Client) handleRetransmission() {
	// Retransmit dropped packets
	for seqNum := range c.droppedPackets {
		if c.sendPacket(seqNum) {
			delete(c.droppedPackets, seqNum)
		}
	}
}

func main() {
	// Connect to server
	conn, err := net.Dial("tcp", "localhost:8080")
	if err != nil {
		log.Fatalf("Failed to connect to server: %v", err)
	}
	defer conn.Close()

	// Send initial message
	fmt.Fprintf(conn, "network\n")

	// Wait for success response
	reader := bufio.NewReader(conn)
	response, err := reader.ReadString('\n')
	if err != nil {
		log.Fatalf("Failed to read server response: %v", err)
	}

	if strings.TrimSpace(response) != "success" {
		log.Fatalf("Invalid server response: %s", response)
	}

	// Initialize client
	client := NewClient(conn)
	rand.Seed(time.Now().UnixNano())

	// Start reading ACKs in a separate goroutine
	go func() {
		for {
			ack, err := reader.ReadString('\n')
			if err != nil {
				log.Printf("Failed to read ACK: %v", err)
				return
			}

			// Process ACK and adjust window
			fmt.Printf("Received: %s", ack)
		}
	}()

	// Main sending loop
	for i := 0; i < TOTAL_PACKETS; i++ {
		seqNum := i % MAX_SEQ_NUM

		// Send packet
		client.sendPacket(seqNum)

		// Handle retransmission every RETRANSMIT_INTERVAL packets
		if i > 0 && i%RETRANSMIT_INTERVAL == 0 {
			client.handleRetransmission()
		}

		// Small delay to prevent overwhelming the network
		time.Sleep(time.Millisecond)
	}

}

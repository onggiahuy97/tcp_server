package main

import (
	"net"
	"sync"
	"time"
)

// Constants defining protocol and simulation parameters.
const (
	maxSequenceNumber = 1 << 16                // Maximum sequence number before wrapping around.
	slidingWindowSize = 1000                   // Number of packets sent per window.
	dropProbability   = 0.01                   // Simulated probability that a packet is dropped.
	retransmitAfter   = 100 * time.Millisecond // Time to wait before retransmitting a dropped packet.
	targetPackets     = 500_000                // Total number of packets to process.
)

// Packet represents a network packet along with metadata used for tracking.
type Packet struct {
	sequenceNumber int       // Unique identifier for the packet.
	sendTime       time.Time // Last time the packet was sent.
	attempts       int       // Number of send attempts.
	wrapped        bool      // Indicates if this packet's sequence number is from a wrapped window.
}

type Client struct {
	conn            net.Conn        // TCP connection to the server
	sentPackets     map[int]*Packet // Packets sent and awaiting ack.
	droppedPackets  map[int]*Packet // Packets that were simulated as dropped.
	totalSent       int
	totalDropped    int
	currentSequence int // Next sequence number to use.
	wrapCount       int // Count of how many time sequence number have wrapped.
	mu              sync.Mutex
}

// NewClient init a new Client instance with a provided TCP connection.
func NewClient(conn net.Conn) *Client {
	return &Client{
		conn:           conn,
		sentPackets:    make(map[int]*Packet),
		droppedPackets: make(map[int]*Packet),
	}
}

// cleanupOldPackets removes packets from previous sequence wraps to free memory.
func (c *Client) cleanupOldPackets() {
	// Remove packets from sentPackets that belong to a previous (non-wrapped) window.
	for seq, packet := range c.sentPackets {
		if !packet.wrapped && c.wrapCount > 0 {
			delete(c.sentPackets, seq)
		}
	}

	// Do the same cleanup for droppedPackets
	for seq, packet := range c.droppedPackets {
		if !packet.wrapped && c.wrapCount > 0 {
			delete(c.droppedPackets, seq)
		}
	}
}

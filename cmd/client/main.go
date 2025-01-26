package main

import (
	"bufio"
	"fmt"
	"math/rand"
	"net"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	maxSequenceNumber = 1 << 16
	slidingWindowSize = 1000
	dropProbability   = 0.01
	retransmitAfter   = 100 * time.Millisecond
	targetPackets     = 500_000
)

type Packet struct {
	sequenceNumber int
	sendTime       time.Time
	attempts       int
	wrapped        bool // Track if this packet is from a wrapped sequence
}

type Client struct {
	conn            net.Conn
	sentPackets     map[int]*Packet
	droppedPackets  map[int]*Packet
	totalSent       int
	totalDropped    int
	currentSequence int
	wrapCount       int
	mu              sync.Mutex
}

func NewClient(conn net.Conn) *Client {
	return &Client{
		conn:           conn,
		sentPackets:    make(map[int]*Packet),
		droppedPackets: make(map[int]*Packet),
	}
}

func (c *Client) cleanupOldPackets() {
	// Cleanup old packets from previous wraps
	for seq, packet := range c.sentPackets {
		if !packet.wrapped && c.wrapCount > 0 {
			delete(c.sentPackets, seq)
		}
	}
	for seq, packet := range c.droppedPackets {
		if !packet.wrapped && c.wrapCount > 0 {
			delete(c.droppedPackets, seq)
		}
	}
}

func (c *Client) handleRetransmissions() {
	c.mu.Lock()
	defer c.mu.Unlock()

	now := time.Now()
	retransmitSeqs := make([]string, 0)

	for seq, packet := range c.droppedPackets {
		if now.Sub(packet.sendTime) >= retransmitAfter {
			if rand.Float64() > dropProbability {
				retransmitSeqs = append(retransmitSeqs, strconv.Itoa(seq))
				delete(c.droppedPackets, seq)
				packet.sendTime = now
				c.sentPackets[seq] = packet
			} else {
				packet.attempts++
				packet.sendTime = now
				c.totalDropped++
			}
		}
	}

	if len(retransmitSeqs) > 0 {
		if _, err := c.conn.Write([]byte(strings.Join(retransmitSeqs, ",") + "\n")); err != nil {
			fmt.Println("Error sending retransmissions:", err)
		}
	}
}

func (c *Client) sendWindow() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	// Check for wrap-around
	if c.currentSequence+slidingWindowSize > maxSequenceNumber {
		c.wrapCount++
		c.cleanupOldPackets()
	}

	windowEnd := c.currentSequence + slidingWindowSize
	if windowEnd > maxSequenceNumber {
		windowEnd = maxSequenceNumber
	}

	sequenceNumbers := make([]string, 0, slidingWindowSize)
	for i := c.currentSequence; i < windowEnd && c.totalSent < targetPackets; i++ {
		seq := i % maxSequenceNumber
		isWrapped := c.wrapCount > 0

		if rand.Float64() > dropProbability {
			sequenceNumbers = append(sequenceNumbers, strconv.Itoa(seq))
			c.sentPackets[seq] = &Packet{
				sequenceNumber: seq,
				sendTime:       time.Now(),
				attempts:       1,
				wrapped:        isWrapped,
			}
		} else {
			c.droppedPackets[seq] = &Packet{
				sequenceNumber: seq,
				sendTime:       time.Now(),
				attempts:       1,
				wrapped:        isWrapped,
			}
			c.totalDropped++
		}
		c.totalSent++
	}

	if len(sequenceNumbers) > 0 {
		if _, err := c.conn.Write([]byte(strings.Join(sequenceNumbers, ",") + "\n")); err != nil {
			return err
		}
	}

	c.currentSequence = windowEnd % maxSequenceNumber
	return nil
}

func main() {
	rand.Seed(time.Now().UnixNano())

	conn, err := net.Dial("tcp", "127.0.0.1:8080")
	if err != nil {
		fmt.Println("Error connecting to server:", err)
		return
	}
	defer conn.Close()

	client := NewClient(conn)
	scanner := bufio.NewScanner(conn)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	// Connection setup
	if _, err := conn.Write([]byte("network\n")); err != nil {
		fmt.Println("Error sending initial message:", err)
		return
	}

	if !scanner.Scan() {
		fmt.Println("Error reading server response")
		return
	}

	ticker := time.NewTicker(50 * time.Millisecond)
	defer ticker.Stop()

	lastReport := time.Now()
	done := make(chan bool)

	// Start ACK processing in separate goroutine
	go func() {
		for scanner.Scan() {
			acks := strings.Split(scanner.Text(), ",")
			client.mu.Lock()
			for _, ackStr := range acks {
				if seq, err := strconv.Atoi(ackStr); err == nil {
					delete(client.sentPackets, seq)
				}
			}
			client.mu.Unlock()
		}
		done <- true
	}()

	for client.totalSent < targetPackets {
		select {
		case <-ticker.C:
			client.handleRetransmissions()
			if err := client.sendWindow(); err != nil {
				fmt.Println("Error sending window:", err)
				return
			}

			if time.Since(lastReport) >= time.Second {
				client.mu.Lock()
				goodput := float64(client.totalSent-client.totalDropped) / float64(client.totalSent)
				fmt.Printf("Progress: %.2f%%, Sent: %d, Dropped: %d, Goodput: %.4f, Wraps: %d\n",
					float64(client.totalSent)*100/targetPackets,
					client.totalSent,
					client.totalDropped,
					goodput,
					client.wrapCount)
				client.mu.Unlock()
				lastReport = time.Now()
			}
		case <-done:
			return
		}
	}

	client.mu.Lock()
	finalGoodput := float64(client.totalSent-client.totalDropped) / float64(client.totalSent)
	fmt.Printf("\nFinal Statistics:\nTotal Sent: %d\nTotal Dropped: %d\nFinal Goodput: %.4f\nTotal Wraps: %d\n",
		client.totalSent, client.totalDropped, finalGoodput, client.wrapCount)
	client.mu.Unlock()
}

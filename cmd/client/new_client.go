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
	minWindowSize     = 10
	maxWindowSize     = 1000
	dropProbability   = 0.01
	retransmitAfter   = 100 * time.Millisecond
	targetPackets     = 500_000
)

type Packet struct {
	sequenceNumber int
	sendTime       time.Time
	attempts       int
}

type Client struct {
	conn         net.Conn
	window       map[int]*Packet // Currently unacked packets
	windowStart  int             // Lowest unacked sequence number
	windowSize   int             // Current window size
	nextSequence int             // Next sequence number to send
	totalSent    int
	totalDropped int
	lastAckTime  time.Time
	mu           sync.Mutex
}

func NewClient(conn net.Conn) *Client {
	return &Client{
		conn:        conn,
		window:      make(map[int]*Packet),
		windowSize:  minWindowSize,
		lastAckTime: time.Now(),
	}
}

func (c *Client) adjustWindow() {
	c.mu.Lock()
	defer c.mu.Unlock()

	// If we're getting regular acks, grow window
	if time.Since(c.lastAckTime) < 100*time.Millisecond {
		if len(c.window) < c.windowSize && c.windowSize < maxWindowSize {
			c.windowSize = min(c.windowSize+1, maxWindowSize)
		}
	} else {
		// If acks are delayed, shrink window
		c.windowSize = max(c.windowSize/2, minWindowSize)
	}
}

func (c *Client) handleRetransmissions() error {
	c.mu.Lock()
	toRetransmit := make([]string, 0)
	now := time.Now()

	for seq, packet := range c.window {
		if now.Sub(packet.sendTime) >= retransmitAfter {
			if rand.Float64() > dropProbability {
				toRetransmit = append(toRetransmit, strconv.Itoa(seq))
				packet.sendTime = now
				packet.attempts++
			} else {
				c.totalDropped++
			}
		}
	}
	c.mu.Unlock()

	if len(toRetransmit) > 0 {
		message := strings.Join(toRetransmit, ",") + "\n"
		if _, err := c.conn.Write([]byte(message)); err != nil {
			return fmt.Errorf("retransmission error: %v", err)
		}
	}

	return nil
}

func (c *Client) sendNewPackets() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	// Don't send if window is full
	if len(c.window) >= c.windowSize {
		return nil
	}

	toSend := make([]string, 0)
	available := c.windowSize - len(c.window)

	for i := 0; i < available && c.totalSent < targetPackets; i++ {
		seq := c.nextSequence % maxSequenceNumber

		if rand.Float64() > dropProbability {
			toSend = append(toSend, strconv.Itoa(seq))
			c.window[seq] = &Packet{
				sequenceNumber: seq,
				sendTime:       time.Now(),
				attempts:       1,
			}
		} else {
			c.totalDropped++
		}

		c.nextSequence++
		c.totalSent++
	}

	if len(toSend) > 0 {
		message := strings.Join(toSend, ",") + "\n"
		if _, err := c.conn.Write([]byte(message)); err != nil {
			return fmt.Errorf("send error: %v", err)
		}
	}

	return nil
}

func (c *Client) processAcks(acks []string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	for _, ackStr := range acks {
		seq, err := strconv.Atoi(ackStr)
		if err != nil {
			continue
		}

		delete(c.window, seq)
		c.lastAckTime = time.Now()

		// Update window start
		for c.windowStart == seq {
			c.windowStart = (c.windowStart + 1) % maxSequenceNumber
			if _, exists := c.window[c.windowStart]; !exists {
				break
			}
		}
	}
}

func main() {
	rand.Seed(time.Now().UnixNano())

	conn, err := net.Dial("tcp", "127.0.0.1:8080")
	if err != nil {
		fmt.Println("Error connecting:", err)
		return
	}
	defer conn.Close()

	client := NewClient(conn)
	scanner := bufio.NewScanner(conn)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	if _, err := conn.Write([]byte("network\n")); err != nil {
		fmt.Println("Error sending initial message:", err)
		return
	}

	if !scanner.Scan() {
		fmt.Println("Error reading server response")
		return
	}

	// Create tickers
	sendTicker := time.NewTicker(5 * time.Millisecond)
	retransmitTicker := time.NewTicker(20 * time.Millisecond)
	adjustTicker := time.NewTicker(50 * time.Millisecond)
	reportTicker := time.NewTicker(1 * time.Second)

	defer func() {
		sendTicker.Stop()
		retransmitTicker.Stop()
		adjustTicker.Stop()
		reportTicker.Stop()
	}()

	// Start ACK processing goroutine
	done := make(chan bool)
	go func() {
		for scanner.Scan() {
			acks := strings.Split(scanner.Text(), ",")
			client.processAcks(acks)
		}
		done <- true
	}()

	lastPrintTime := time.Now()

	for {
		select {
		case <-sendTicker.C:
			if err := client.sendNewPackets(); err != nil {
				fmt.Println("Send error:", err)
				return
			}

		case <-retransmitTicker.C:
			if err := client.handleRetransmissions(); err != nil {
				fmt.Println("Retransmission error:", err)
				return
			}

		case <-adjustTicker.C:
			client.adjustWindow()

		case <-reportTicker.C:
			client.mu.Lock()
			now := time.Now()
			elapsed := now.Sub(lastPrintTime).Seconds()
			packetsPerSec := float64(client.totalSent) / elapsed
			goodput := float64(client.totalSent-client.totalDropped) / float64(client.totalSent)
			progress := float64(client.totalSent) * 100 / float64(targetPackets)

			fmt.Printf("Progress: %.2f%%, Window Size: %d, Sent: %d, Dropped: %d, Goodput: %.4f, Rate: %.2f pkts/s\n",
				progress, client.windowSize, client.totalSent, client.totalDropped, goodput, packetsPerSec)

			if client.totalSent >= targetPackets {
				fmt.Printf("\nTransmission Complete!\nFinal Statistics:\n")
				fmt.Printf("Total Packets Sent: %d\n", client.totalSent)
				fmt.Printf("Total Packets Dropped: %d\n", client.totalDropped)
				fmt.Printf("Final Goodput: %.4f\n", goodput)
				fmt.Printf("Average Rate: %.2f packets/second\n", packetsPerSec)
				fmt.Printf("Final Window Size: %d\n", client.windowSize)

				// Send completion message to server
				if _, err := client.conn.Write([]byte("FINISH\n")); err != nil {
					fmt.Println("Error sending finish message:", err)
				}

				// Wait a bit for the server to process final packets
				time.Sleep(500 * time.Millisecond)
				client.mu.Unlock()
				return
			}
			client.mu.Unlock()
			lastPrintTime = now

		case <-done:
			return
		}
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

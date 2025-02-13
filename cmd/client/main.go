// package main
//
// import (
// 	"bufio"
// 	"fmt"
// 	"math/rand"
// 	"net"
// 	"strconv"
// 	"strings"
// 	"sync"
// 	"time"
// )
//
// // Constants defining protocol and simulation parameters.
// const (
// 	maxSequenceNumber = 1 << 16                // Maximum sequence number before wrapping around.
// 	slidingWindowSize = 1000                   // Number of packets sent per window.
// 	dropProbability   = 0.01                   // Simulated probability that a packet is dropped.
// 	retransmitAfter   = 100 * time.Millisecond // Time to wait before retransmitting a dropped packet.
// 	targetPackets     = 500_000                // Total number of packets to process.
// )
//
// // Packet represents a network packet along with metadata used for tracking.
// type Packet struct {
// 	sequenceNumber int       // Unique identifier for the packet.
// 	sendTime       time.Time // Last time the packet was sent.
// 	attempts       int       // Number of send attempts.
// 	wrapped        bool      // Indicates if this packet's sequence number is from a wrapped window.
// }
//
// // Client encapsulates the connection and state for sending packets.
// type Client struct {
// 	conn            net.Conn        // TCP connection to the server.
// 	sentPackets     map[int]*Packet // Packets sent and awaiting acknowledgment.
// 	droppedPackets  map[int]*Packet // Packets that were simulated as dropped.
// 	totalSent       int             // Total number of packets processed (sent or dropped).
// 	totalDropped    int             // Total number of packets that were dropped.
// 	currentSequence int             // Next sequence number to use.
// 	wrapCount       int             // Count of how many times sequence numbers have wrapped.
// 	mu              sync.Mutex      // Mutex to synchronize access to Client fields.
// }
//
// // NewClient initializes a new Client instance with the provided TCP connection.
// func NewClient(conn net.Conn) *Client {
// 	return &Client{
// 		conn:           conn,
// 		sentPackets:    make(map[int]*Packet),
// 		droppedPackets: make(map[int]*Packet),
// 	}
// }
//
// // cleanupOldPackets removes packets from previous sequence wraps to free memory.
// func (c *Client) cleanupOldPackets() {
// 	// Remove packets from sentPackets that belong to a previous (non-wrapped) window.
// 	for seq, packet := range c.sentPackets {
// 		if !packet.wrapped && c.wrapCount > 0 {
// 			delete(c.sentPackets, seq)
// 		}
// 	}
// 	// Do the same cleanup for droppedPackets.
// 	for seq, packet := range c.droppedPackets {
// 		if !packet.wrapped && c.wrapCount > 0 {
// 			delete(c.droppedPackets, seq)
// 		}
// 	}
// }
//
// // handleRetransmissions scans droppedPackets and retransmits those that are due.
// func (c *Client) handleRetransmissions() {
// 	c.mu.Lock()
// 	defer c.mu.Unlock()
//
// 	now := time.Now()
// 	retransmitSeqs := make([]string, 0)
//
// 	// Iterate over dropped packets to determine if they should be retransmitted.
// 	for seq, packet := range c.droppedPackets {
// 		if now.Sub(packet.sendTime) >= retransmitAfter {
// 			// Simulate retransmission: determine if the packet is dropped again.
// 			if rand.Float64() > dropProbability {
// 				// Packet retransmission is successful.
// 				retransmitSeqs = append(retransmitSeqs, strconv.Itoa(seq))
// 				delete(c.droppedPackets, seq)
// 				packet.sendTime = now
// 				c.sentPackets[seq] = packet
// 			} else {
// 				// Packet is dropped again; update its send time and attempt counter.
// 				packet.attempts++
// 				packet.sendTime = now
// 				c.totalDropped++
// 			}
// 		}
// 	}
//
// 	// If any packets are due for retransmission, send them as a comma-separated list.
// 	if len(retransmitSeqs) > 0 {
// 		message := strings.Join(retransmitSeqs, ",") + "\n"
// 		if _, err := c.conn.Write([]byte(message)); err != nil {
// 			fmt.Println("Error sending retransmissions:", err)
// 		}
// 	}
// }
//
// // sendWindow sends a window of packets. For each packet, it either sends it successfully
// // or simulates a drop based on dropProbability.
// func (c *Client) sendWindow() error {
// 	c.mu.Lock()
// 	defer c.mu.Unlock()
//
// 	// Check if the current window will wrap around the maximum sequence number.
// 	if c.currentSequence+slidingWindowSize > maxSequenceNumber {
// 		c.wrapCount++
// 		c.cleanupOldPackets()
// 	}
//
// 	// Calculate the end of the current window.
// 	windowEnd := c.currentSequence + slidingWindowSize
// 	if windowEnd > maxSequenceNumber {
// 		windowEnd = maxSequenceNumber
// 	}
//
// 	// This slice will hold the sequence numbers of packets that are actually sent.
// 	sequenceNumbers := make([]string, 0, slidingWindowSize)
//
// 	// Iterate over the sequence numbers in the current window.
// 	for i := c.currentSequence; i < windowEnd && c.totalSent < targetPackets; i++ {
// 		seq := i % maxSequenceNumber
// 		isWrapped := c.wrapCount > 0
//
// 		// Simulate packet drop using dropProbability.
// 		if rand.Float64() > dropProbability {
// 			// Packet is successfully sent.
// 			sequenceNumbers = append(sequenceNumbers, strconv.Itoa(seq))
// 			c.sentPackets[seq] = &Packet{
// 				sequenceNumber: seq,
// 				sendTime:       time.Now(),
// 				attempts:       1,
// 				wrapped:        isWrapped,
// 			}
// 		} else {
// 			// Packet is dropped; record it for future retransmission.
// 			c.droppedPackets[seq] = &Packet{
// 				sequenceNumber: seq,
// 				sendTime:       time.Now(),
// 				attempts:       1,
// 				wrapped:        isWrapped,
// 			}
// 			c.totalDropped++
// 		}
// 		c.totalSent++
// 	}
//
// 	// If any packets were actually sent, write them to the connection.
// 	if len(sequenceNumbers) > 0 {
// 		message := strings.Join(sequenceNumbers, ",") + "\n"
// 		if _, err := c.conn.Write([]byte(message)); err != nil {
// 			return err
// 		}
// 	}
//
// 	// Update the current sequence number, wrapping around if needed.
// 	c.currentSequence = windowEnd % maxSequenceNumber
// 	return nil
// }
//
// func main() {
// 	// Seed the random number generator.
// 	rand.Seed(time.Now().UnixNano())
//
// 	// Establish a TCP connection to the server.
// 	conn, err := net.Dial("tcp", "127.0.0.1:8080")
// 	if err != nil {
// 		fmt.Println("Error connecting to server:", err)
// 		return
// 	}
// 	defer conn.Close()
//
// 	// Initialize the client with the established connection.
// 	client := NewClient(conn)
//
// 	// Create a scanner to read incoming data from the server.
// 	scanner := bufio.NewScanner(conn)
// 	// Increase the scanner's buffer size to handle larger messages.
// 	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
//
// 	// Send an initial message to establish connection context.
// 	if _, err := conn.Write([]byte("network\n")); err != nil {
// 		fmt.Println("Error sending initial message:", err)
// 		return
// 	}
//
// 	// Wait for a response from the server.
// 	if !scanner.Scan() {
// 		fmt.Println("Error reading server response")
// 		return
// 	}
//
// 	// Create a ticker that triggers every 50 milliseconds.
// 	ticker := time.NewTicker(50 * time.Millisecond)
// 	defer ticker.Stop()
//
// 	lastReport := time.Now()
// 	done := make(chan bool)
//
// 	// Start a goroutine to process acknowledgments (ACKs) from the server.
// 	go func() {
// 		for scanner.Scan() {
// 			// The server sends ACKs as a comma-separated string of sequence numbers.
// 			acks := strings.Split(scanner.Text(), ",")
// 			client.mu.Lock()
// 			for _, ackStr := range acks {
// 				if seq, err := strconv.Atoi(ackStr); err == nil {
// 					// Remove the acknowledged packet from the sentPackets map.
// 					delete(client.sentPackets, seq)
// 				}
// 			}
// 			client.mu.Unlock()
// 		}
// 		// Signal completion if the scanner stops receiving data.
// 		done <- true
// 	}()
//
// 	// Main loop: send packet windows and handle retransmissions until the target is reached.
// 	for client.totalSent < targetPackets {
// 		select {
// 		case <-ticker.C:
// 			client.handleRetransmissions()
// 			if err := client.sendWindow(); err != nil {
// 				fmt.Println("Error sending window:", err)
// 				return
// 			}
//
// 			// Every second, print progress statistics.
// 			if time.Since(lastReport) >= time.Second {
// 				client.mu.Lock()
// 				goodput := float64(client.totalSent-client.totalDropped) / float64(client.totalSent)
// 				progress := float64(client.totalSent) * 100 / float64(targetPackets)
// 				fmt.Printf("Progress: %.2f%%, Sent: %d, Dropped: %d, Goodput: %.4f, Wraps: %d\n",
// 					progress, client.totalSent, client.totalDropped, goodput, client.wrapCount)
// 				client.mu.Unlock()
// 				lastReport = time.Now()
// 			}
// 		case <-done:
// 			// Exit the loop if the ACK processing goroutine signals done.
// 			return
// 		}
// 	}
//
// 	// After processing, print the final statistics.
// 	client.mu.Lock()
// 	finalGoodput := float64(client.totalSent-client.totalDropped) / float64(client.totalSent)
// 	fmt.Printf("\nFinal Statistics:\n"+
// 		"Total Sent: %d\nTotal Dropped: %d\nFinal Goodput: %.4f\nTotal Wraps: %d\n",
// 		client.totalSent, client.totalDropped, finalGoodput, client.wrapCount)
// 	client.mu.Unlock()
// }

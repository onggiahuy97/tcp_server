package main

import (
	"bufio"
	"fmt"
	"net"
	"strconv"
	"strings"
)

func main() {
	serverAddr := "localhost:8080"
	listener, err := net.Listen("tcp", serverAddr)
	if err != nil {
		fmt.Println("Error starting server:", err)
		return
	}
	defer listener.Close()
	fmt.Printf("Server listening on %s...\n", serverAddr)

	conn, err := listener.Accept()
	if err != nil {
		fmt.Println("Error accepting connection:", err)
		return
	}
	handleConnection(conn)

}

func handleConnection(conn net.Conn) {
	defer conn.Close()
	fmt.Printf("Accepted connection from %s\n", conn.RemoteAddr())

	scanner := bufio.NewScanner(conn)

	// Track received sequence numbers
	receivedPackets := make(map[int]bool)
	lastAck := 0 // Last cumulative ACK sent

	for scanner.Scan() {
		data := strings.TrimSpace(scanner.Text())

		switch {
		case data == "network":
			fmt.Printf("Sending: success\n")
			conn.Write([]byte("success\n"))

		case data == "finish":
			fmt.Printf("Sending: goodbye\n")
			conn.Write([]byte("goodbye\n"))
			return

		case strings.HasPrefix(data, "SEQ"):
			// Parse sequence number
			parts := strings.Split(data, " ")
			if len(parts) < 2 {
				fmt.Printf("Invalid SEQ format: %s\n", data)
				continue
			}

			seqNum, err := strconv.Atoi(parts[1])
			if err != nil {
				fmt.Printf("Error parsing sequence number: %s\n", data)
				continue
			}

			// Store received sequence number
			receivedPackets[seqNum] = true
			fmt.Printf("Received SEQ: %d\n", seqNum)

			// Find the highest contiguous ACK number
			for receivedPackets[lastAck+1] {
				lastAck++
			}

			// Send cumulative ACK
			ackMsg := fmt.Sprintf("ACK %d\n", lastAck)
			conn.Write([]byte(ackMsg))
			fmt.Printf("Sent: %s", ackMsg)

		default:
			fmt.Printf("Received unknown message: %s\n", data)
		}
	}

	if err := scanner.Err(); err != nil {
		fmt.Printf("Connection closed with error: %v\n", err)
	}
}

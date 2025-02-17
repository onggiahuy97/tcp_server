package main

import (
	"fmt"
	"net"
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
	fmt.Printf("Accepted connection from %s\n", conn.RemoteAddr())
	buffer := make([]byte, 1024)
	for {
		n, err := conn.Read(buffer)
		if err != nil {
			if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
				continue
			}
			fmt.Printf("Connection closed by client: %v\n", err)
			return
		}
		data := strings.TrimSpace(string(buffer[:n]))
		fmt.Printf("Received data: %s\n", data)
		switch {
		case data == "network":
			fmt.Printf("Sending: success\n")
			conn.Write([]byte("success\n"))
		case data == "finish":
			fmt.Printf("Sending: goodbye\n")
			conn.Write([]byte("goodbye\n"))
			return
		case strings.HasPrefix(data, "SEQ"):
			// print SEQ message
			fmt.Printf("Received SEQ message: %s\n", data)
		default:
			fmt.Printf("Received unknown message: %s\n", data)
		}
	}
}

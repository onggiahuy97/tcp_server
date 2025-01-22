package main

import (
	"fmt"
	"net"
	"sync"
)

type Server struct {
	listener      net.Listener
	receivedSeqs  map[uint16]bool
	missingSeqs   map[uint16]bool
	totalReceived int64
	totalSent     int64
	mu            sync.Mutex
	goodputCount  int
	totalGoodput  float64
}

func NewServer(port int) (*Server, error) {
	listener, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return nil, err
	}

	return &Server{
		listener:     listener,
		receivedSeqs: make(map[uint16]bool),
		missingSeqs:  make(map[uint16]bool),
	}, nil
}

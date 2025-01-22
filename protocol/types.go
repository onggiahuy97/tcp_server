package protocol

import (
	"encoding/json"
	"math/rand/v2"
)

const (
	MaxSequenceNumber = 65535 // 2^16
	WindowSize        = 100   // Sliding window size
	DropProbability   = 0.01  // 1% packet drop rate
	RetransmitAfter   = 100   // Retransmit after 100 sequence numbers
	TotalPackets      = 10000000
	InitialString     = "network"
)

type Message struct {
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload"`
}

type ConnectRequest struct {
	InitialString string `json:"initial_string"`
}

type ConnectResponse struct {
	Status string `json:"status"`
}

type Packet struct {
	SequenceNumber   uint16 `json:"sequence_number"`
	IsRetransmission bool   `json:"is_retransmission"`
}

type Ack struct {
	AckNumber uint16 `json:"ack_number"`
}

// SlidingWindow manages the TCP sliding window
type SlidingWindow struct {
	Base        uint16          // First unacked sequence number
	NextSeqNum  uint16          // Next sequence number to be used
	Size        int             // Window size
	Outstanding map[uint16]bool // Track unacked packets
}

func NewSlidingWindow(size int) *SlidingWindow {
	return &SlidingWindow{
		Base:        0,
		NextSeqNum:  0,
		Size:        size,
		Outstanding: make(map[uint16]bool),
	}
}

func ShouldDrop() bool {
	return rand.Float64() < DropProbability
}

func IncrementSeq(seq uint16) uint16 {
	return (seq + 1) % MaxSequenceNumber
}

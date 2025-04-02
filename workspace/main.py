import struct

def encode_delta(sequence):
    # Assume sequence is the list of received numbers.
    # The first number is stored in 2 bytes.
    encoded = struct.pack('>H', sequence[0])
    
    # Then for each subsequent number, store the delta as a single byte.
    # (Make sure your deltas always fit in one byte; otherwise, use a larger type or variable-length encoding.)
    for i in range(1, len(sequence)):
        delta = sequence[i] - sequence[i-1]
        encoded += struct.pack('>B', delta)
    return encoded

# Example usage:
sequence = [1, 2, 3, 5, 6, 8]  # corresponds to "1 2 3 dropped 5 6 dropped 7" where 4 and 7 are missing
binary_data = encode_delta(sequence)
print("Encoded data length:", len(binary_data))  # 2 bytes for the start + 5 bytes for deltas = 7 bytes total

import random

def encrypt_payload(flattened_code: str):
    # Quad-layer XOR + Arithmetic scrambling keys
    k1 = random.randint(15, 245)
    k2 = random.randint(15, 245)
    k3 = random.randint(15, 245)
    k4 = random.randint(15, 245)
    k5 = random.randint(1, 7)
    
    encoded_bytes = []
    for char in flattened_code:
        val = ord(char)
        val = (val + k5) % 256
        val = val ^ k1
        val = (val - 3) % 256
        val = val ^ k2
        val = (val + 4) % 256
        val = val ^ k3
        val = (val - 2) % 256
        val = val ^ k4
        encoded_bytes.append(val)
        
    return encoded_bytes, [k1, k2, k3, k4, k5]

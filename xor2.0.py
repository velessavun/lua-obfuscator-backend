import random

def encrypt_payload_v2(flattened_code: str):
    # Advanced Multi-round Block-Cipher-like Scrambling Keys
    keys = [random.randint(10, 250) for _ in range(8)]
    rotation_shift = random.randint(1, 7)
    
    encoded_bytes = []
    for char in flattened_code:
        val = ord(char)
        # Round 1: Bitwise rotation & XOR
        val = ((val << rotation_shift) | (val >> (8 - rotation_shift))) & 0xFF
        val = val ^ keys[0]
        # Round 2: Arithmetic scramble
        val = (val + keys[1]) % 256
        val = val ^ keys[2]
        # Round 3: Subtraction & XOR
        val = (val - keys[3]) % 256
        val = val ^ keys[4]
        # Round 4: Final permutation pass
        val = ((val >> 1) | (val << 7)) & 0xFF
        val = val ^ keys[5]
        val = (val + keys[6]) % 256
        val = val ^ keys[7]
        encoded_bytes.append(val)
        
    return encoded_bytes, keys, rotation_shift

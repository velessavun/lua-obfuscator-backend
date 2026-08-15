import random

def encrypt_payload(flattened_code: str):
    # Quad-layer XOR + arithmetic scrambling keys.
    k1 = random.randint(15, 245)
    k2 = random.randint(15, 245)
    k3 = random.randint(15, 245)
    k4 = random.randint(15, 245)
    k5 = random.randint(1, 7)

    # CBC-style chaining seed, derived deterministically from the keys so the
    # decoder can recompute it without it ever being stored on its own.
    seed = (((k1 ^ k2) ^ k3) ^ k4)
    seed = (seed + k5) % 256

    encoded_bytes = []
    prev = seed
    for i, char in enumerate(flattened_code):
        val = ord(char)
        # 1) position-dependent additive shift (breaks static substitution)
        val = (val + k5 + (i % 251)) % 256
        val = val ^ k1
        val = (val - 3) % 256
        val = val ^ k2
        val = (val + 4) % 256
        val = val ^ k3
        val = (val - 2) % 256
        val = val ^ k4
        # 9) chain with the previous ciphertext byte (avalanche)
        val = val ^ prev
        encoded_bytes.append(val)
        prev = val

    return encoded_bytes, [k1, k2, k3, k4, k5]

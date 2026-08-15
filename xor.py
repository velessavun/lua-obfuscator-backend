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


def decode_payload(encoded_bytes, keys):
    """Reference decoder -- exactly mirrors the Lua runtime decode loop in
    vm.build_vm_wrapper. Used for verification / layered peel tests."""
    k1, k2, k3, k4, k5 = keys
    seed = (((k1 ^ k2) ^ k3) ^ k4)
    seed = (seed + k5) % 256
    out = []
    prev = seed
    for ip in range(1, len(encoded_bytes) + 1):
        cur = encoded_bytes[ip - 1]
        i0 = (ip - 1) % 251
        b = cur ^ prev
        b = b ^ k4
        b = (b + 2) % 256
        b = b ^ k3
        b = (b - 4) % 256
        b = b ^ k2
        b = (b + 3) % 256
        b = b ^ k1
        b = (b - k5 - i0) % 256
        out.append(chr(b))
        prev = cur
    return ''.join(out)

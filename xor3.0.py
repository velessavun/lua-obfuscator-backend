import random
import base64

class XOR3Engine:
    @staticmethod
    def encrypt(data: bytes, key: str) -> tuple[list[int], list[int], int]:
        """
        Performs cascading multi-stage XOR 3.0 encryption with rolling bitwise 
        rotation and cyclical byte dependency.
        """
        key_bytes = [ord(c) for c in key]
        key_len = len(key_bytes)
        rot_shift = random.randint(1, 7)
        
        encoded = []
        keys = []
        
        prev_val = random.randint(0, 255)
        for i, byte in enumerate(data):
            k_char = key_bytes[i % key_len]
            # Cascading dependency: mix previous ciphertext value, rolling rotation offset, and key byte
            dynamic_key = (k_char ^ prev_val ^ ((i * rot_shift) & 0xFF)) & 0xFF
            keys.append(dynamic_key)
            
            # Apply transformation
            encrypted_byte = (byte ^ dynamic_key) & 0xFF
            # Perform rolling bitwise rotation
            encrypted_byte = ((encrypted_byte << rot_shift) | (encrypted_byte >> (8 - rot_shift))) & 0xFF
            
            encoded.append(encrypted_byte)
            prev_val = encrypted_byte
            
        return encoded, keys, rot_shift

    @staticmethod
    def generate_lua_runtime(encoded: list[int], keys: list[int], rot_shift: int) -> str:
        """
        Generates the self-contained Lua runtime stub that reverses XOR 3.0 
        cascading encryption and execution.
        """
        v_enc = f"_0x{random.randint(1000, 9999)}"
        v_keys = f"_0x{random.randint(1000, 9999)}"
        v_rot = f"_0x{random.randint(1000, 9999)}"
        v_res = f"_0x{random.randint(1000, 9999)}"
        v_i = f"_0x{random.randint(1000, 9999)}"
        v_val = f"_0x{random.randint(1000, 9999)}"
        v_unrot = f"_0x{random.randint(1000, 9999)}"
        v_k = f"_0x{random.randint(1000, 9999)}"
        v_orig = f"_0x{random.randint(1000, 9999)}"

        return f"""local {v_enc} = {{{','.join(map(str, encoded))}}};
local {v_keys} = {{{','.join(map(str, keys))}}};
local {v_rot} = {rot_shift};

local function {v_res}()
    local _chunks = {{}};
    for {v_i}, {v_val} in ipairs({v_enc}) do
        local {v_unrot} = (({v_val} >> {v_rot}) | ({v_val} << (8 - {v_rot}))) & 0xFF;
        local {v_k} = {v_keys}[{v_i}];
        local {v_orig} = {v_unrot} ~ {v_k};
        _chunks[#{v_chunks} + 1] = string.char({v_orig});
    end;
    return table.concat(_chunks);
end;

return loadstring({v_res}())();"""

if __name__ == "__main__":
    sample_code = 'print("XOR 3.0 Secured Execution Active");'
    master_key = "aiko_xor3_secure_master"
    
    enc_bytes, enc_keys, shift = XOR3Engine.encrypt(sample_code.encode('utf-8'), master_key)
    lua_stub = XOR3Engine.generate_lua_runtime(enc_bytes, enc_keys, shift)
    
    print("--- Generated XOR 3.0 Lua Runtime ---")
    print(lua_stub)

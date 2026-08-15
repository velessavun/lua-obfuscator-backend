import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScriptRequest(BaseModel):
    script: str

def apply_control_flow_flattening(code: str) -> str:
    # Extract valid lines while ignoring pure comments/empty lines for flattening
    raw_lines = code.split('\n')
    statements = []
    
    for line in raw_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('--'):
            statements.append(line)
            
    if not statements:
        return code
        
    # Assign random unique states to each statement
    states = []
    for stmt in statements:
        states.append({
            "id": random.randint(100000, 999999),
            "content": stmt
        })
        
    # Shuffle states to completely break linear order
    shuffled_states = states.copy()
    random.shuffle(shuffled_states)
    
    # Map out state transitions like a finite state machine graph
    state_map = {}
    for i in range(len(shuffled_states)):
        current = shuffled_states[i]
        if i < len(shuffled_states) - 1:
            next_id = shuffled_states[i + 1]["id"]
        else:
            next_id = -1 # Termination state
            
        state_map[current["id"]] = {
            "content": current["content"],
            "next": next_id
        }
        
    start_state = shuffled_states[0]["id"]
    
    # Construct the flattened state machine control structure in Lua
    flattened = f"local _state = {start_state};\n"
    flattened += "while _state ~= -1 do\n"
    
    first = True
    for s_id, data in state_map.items():
        if first:
            flattened += f"    if _state == {s_id} then\n"
            first = False
        else:
            flattened += f"    elseif _state == {s_id} then\n"
            
        flattened += f"        {data['content']}\n"
        flattened += f"        _state = {data['next']};\n"
        
    flattened += "    end;\n"
    flattened += "end;\n"
    
    return flattened

@app.post("/v1/obfuscate")
def obfuscate_endpoint(payload: ScriptRequest):
    if not payload.script.strip():
        raise HTTPException(status_code=400, detail="Empty script provided")
    
    code = payload.script
    
    # Step 1: Apply Control Flow Flattening
    flattened_code = apply_control_flow_flattening(code)
    
    # Step 2: Generate dynamic multi-layer keys
    k1 = random.randint(10, 240)
    k2 = random.randint(10, 240)
    k3 = random.randint(10, 240)
    
    # Step 3: Multi-layer XOR encryption pass
    encoded_bytes = []
    for char in flattened_code:
        val = ord(char)
        val = val ^ k1
        val = (val + 3) % 256
        val = val ^ k2
        val = (val - 7) % 256
        val = val ^ k3
        encoded_bytes.append(val)
        
    # Step 4: Generate heavy junk variable bloat
    junk_pool = []
    for i in range(20):
        j_name = f"_0x{random.randint(10000, 99999)}"
        j_val = random.randint(1000, 99999)
        junk_pool.append(f"local {j_name} = {j_val} * {random.randint(2, 8)} + {random.randint(1, 90)};")
    
    random.shuffle(junk_pool)
    junk_block = "\n".join(junk_pool)

    # Step 5: Build final heavily locked execution wrapper
    obfuscated_output = f"""--[[
    ================================================================
    Protected by Advanced Cloud Obfuscator with Control Flow Flattening
    Payload Size: {len(encoded_bytes)} bytes
    ================================================================
]]--
local _env = (getgenv and getgenv()) or _G;
{junk_block}
local _payload = {{{','.join(map(str, encoded_bytes))}}};
local _keys = {{{k1}, {k2}, {k3}}};
local function _proc(_d, _k)
    local _res = {{}};
    for _i = 1, #_d do
        local _v = _d[_i];
        _v = bit32.bxor(_v, _k[3]);
        _v = (_v + 7) % 256;
        _v = bit32.bxor(_v, _k[2]);
        _v = (_v - 3) % 256;
        _v = bit32.bxor(_v, _k[1]);
        _res[_i] = string.char(_v);
    end
    return table.concat(_res);
end;
local _x, _err = pcall(function()
    local _decodedCode = _proc(_payload, _keys);
    local _fn = loadstring(_decodedCode);
    if _fn then
        _fn();
    end
end);
if not _x then
    warn("Obfuscation Execution Error: " .. tostring(_err));
end
"""

    return {"success": True, "obfuscatedScript": obfuscated_output}

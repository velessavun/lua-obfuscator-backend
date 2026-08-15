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
    raw_lines = code.split('\n')
    statements = []
    for line in raw_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('--'):
            statements.append(line)
        
    if not statements:
        return code
        
    states = []
    for stmt in statements:
        states.append({
            "id": random.randint(1000000, 9999999),
            "content": stmt
        })
        
    shuffled_states = states.copy()
    random.shuffle(shuffled_states)
    
    state_map = {}
    for i in range(len(shuffled_states)):
        current = shuffled_states[i]
        next_id = shuffled_states[i + 1]["id"] if i < len(shuffled_states) - 1 else -1
        state_map[current["id"]] = {
            "content": current["content"],
            "next": next_id
        }
        
    start_state = shuffled_states[0]["id"]
    state_var = f"_0x{random.randint(1000,9999)}"
    
    flattened = f"local {state_var} = {start_state};\n"
    flattened += f"while {state_var} ~= -1 do\n"
    
    first = True
    for s_id, data in state_map.items():
        if first:
            flattened += f"    if {state_var} == {s_id} then\n"
            first = False
        else:
            flattened += f"    elseif {state_var} == {s_id} then\n"
            
        flattened += f"        {data['content']}\n"
        flattened += f"        {state_var} = {data['next']};\n"
        
    flattened += "    end;\n"
    flattened += "end;\n"
    
    return flattened

@app.post("/v1/obfuscate")
def obfuscate_endpoint(payload: ScriptRequest):
    if not payload.script.strip():
        raise HTTPException(status_code=400, detail="Empty script provided")
    
    code = payload.script
    
    # Step 1: Control Flow Flattening
    flattened_code = apply_control_flow_flattening(code)
    
    # Step 2: Quad-layer XOR + Arithmetic scrambling keys
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
        
    # Step 3: Massive junk variable bloat with randomized names
    junk_pool = []
    for i in range(30):
        j_name = f"_0x{random.randint(100000, 999999)}"
        j_val = random.randint(10000, 999999)
        junk_pool.append(f"local {j_name} = ({j_val} * {random.randint(2, 9)}) % {random.randint(1000, 9999)};")
    
    random.shuffle(junk_pool)
    junk_block = "\n".join(junk_pool)

    # Step 4: Randomized identifier names for the execution wrapper and VM
    v_env = f"_0x{random.randint(1000,9999)}"
    v_payload = f"_0x{random.randint(1000,9999)}"
    v_keys = f"_0x{random.randint(1000,9999)}"
    v_vm = f"_0x{random.randint(1000,9999)}"
    v_d = f"_0x{random.randint(1000,9999)}"
    v_k = f"_0x{random.randint(1000,9999)}"
    v_res = f"_0x{random.randint(1000,9999)}"
    v_i = f"_0x{random.randint(1000,9999)}"
    v_v = f"_0x{random.randint(1000,9999)}"
    v_x = f"_0x{random.randint(1000,9999)}"
    v_err = f"_0x{random.randint(1000,9999)}"
    v_decoded = f"_0x{random.randint(1000,9999)}"
    v_fn = f"_0x{random.randint(1000,9999)}"
    v_check = f"_0x{random.randint(1000,9999)}"
    v_pc = f"_0x{random.randint(1000,9999)}"

    obfuscated_output = f"""-- Obfuscated by aiko v1.0
{junk_block}
local {v_env} = (getgenv and getgenv()) or _G;
local function {v_check}()
    local _s = pcall(function()
        if debug and debug.sethook then
            local _h = debug.gethook();
            if _h ~= nil then error("Debugger hook detected") end;
        end;
        if rawget(_G, "Hydroxide") or rawget(_G, "RemoteSpy") or rawget(_G, "ScriptWareSpy") then
            error("Instrumented environment detected");
        end;
    end);
    return _s;
end;
if not {v_check}() then
    return;
end;
local {v_payload} = {{{','.join(map(str, encoded_bytes))}}};
local {v_keys} = {{{k1}, {k2}, {k3}, {k4}, {k5}}};
local function {v_vm}({v_d}, {v_k})
    local {v_res} = {{}};
    local {v_pc} = 1;
    while {v_pc} <= #{v_d} do
        local {v_v} = {v_d}[{v_pc}];
        {v_v} = bit32.bxor({v_v}, {v_k}[4]);
        {v_v} = ({v_v} + 2) % 256;
        {v_v} = bit32.bxor({v_v}, {v_k}[3]);
        {v_v} = ({v_v} - 4) % 256;
        {v_v} = bit32.bxor({v_v}, {v_k}[2]);
        {v_v} = ({v_v} + 3) % 256;
        {v_v} = bit32.bxor({v_v}, {v_k}[1]);
        {v_v} = ({v_v} - {v_k}[5]) % 256;
        {v_res}[{v_pc}] = string.char({v_v});
        {v_pc} = {v_pc} + 1;
    end;
    return table.concat({v_res});
end;
local {v_x}, {v_err} = pcall(function()
    local {v_decoded} = {v_vm}({v_payload}, {v_keys});
    local {v_fn} = loadstring({v_decoded});
    if {v_fn} then
        setfenv({v_fn}, {v_env});
        {v_fn}();
    end
end);
if not {v_x} then
    warn("VM Execution Error");
end
"""

    return {"success": True, "obfuscatedScript": obfuscated_output}

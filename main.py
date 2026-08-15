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

@app.post("/v1/obfuscate")
def obfuscate_endpoint(payload: ScriptRequest):
    if not payload.script.strip():
        raise HTTPException(status_code=400, detail="Empty script provided")
    
    code = payload.script
    
    # Generate dynamic multi-layer keys
    k1 = random.randint(10, 240)
    k2 = random.randint(10, 240)
    k3 = random.randint(10, 240)
    
    # Multi-layer XOR encryption pass
    encoded_bytes = []
    for char in code:
        val = ord(char)
        val = val ^ k1
        val = (val + 3) % 256
        val = val ^ k2
        val = (val - 7) % 256
        val = val ^ k3
        encoded_bytes.append(val)
        
    # Generate massive junk variable bloat to make even small scripts huge and unreadable
    junk_pool = []
    for i in range(15):
        j_name = f"_0x{random.randint(10000, 99999)}"
        j_val = random.randint(1000, 99999)
        junk_pool.append(f"local {j_name} = {j_val} * {random.randint(2, 8)} + {random.randint(1, 90)};")
    
    random.shuffle(junk_pool)
    junk_block = "\n".join(junk_pool)

    # Build an insanely heavy, obfuscated execution wrapper runner
    obfuscated_output = f"""--[[
    ====================================================
    Protected by Advanced Cloud Multi-Layer Obfuscator
    Size: {len(encoded_bytes)} bytes compiled payload
    ====================================================
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

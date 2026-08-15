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

    key1 = 165
    key2 = 92
    encoded_bytes = [(ord(c) ^ key1) ^ key2 for c in code]

    obfuscated_output = f"""-- [ Backend Powered Obfuscator ] --
local _bytes = {{{','.join(map(str, encoded_bytes))}}}
local _k1, _k2 = {key1}, {key2}
local _decoded = {{}}
for i = 1, #_bytes do
    _decoded[i] = string.char(bit32.bxor(bit32.bxor(_bytes[i], _k1), _k2))
end
loadstring(table.concat(_decoded))()"""

    return {"success": True, "obfuscatedScript": obfuscated_output}

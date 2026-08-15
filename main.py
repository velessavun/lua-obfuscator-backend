from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from xor2_0 import encrypt_payload_v2
from vm2_0 import apply_control_flow_flattening, build_vm_wrapper_v2

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
    
    flattened_code = apply_control_flow_flattening(code)
    encoded_bytes, keys, rot_shift = encrypt_payload_v2(flattened_code)
    obfuscated_output = build_vm_wrapper_v2(encoded_bytes, keys, rot_shift)

    return {"success": True, "obfuscatedScript": obfuscated_output}

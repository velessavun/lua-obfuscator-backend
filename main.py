from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from xor import encrypt_payload
from vm import apply_control_flow_flattening, build_vm_wrapper

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
    
    # Step 1: Flatten control flow
    flattened_code = apply_control_flow_flattening(code)
    
    # Step 2: Quad XOR encrypt payload and generate keys
    encoded_bytes, keys = encrypt_payload(flattened_code)
    
    # Step 3: Build VM, environment checks, and wrap output
    obfuscated_output = build_vm_wrapper(encoded_bytes, keys)

    return {"success": True, "obfuscatedScript": obfuscated_output}

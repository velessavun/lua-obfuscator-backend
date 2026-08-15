"""
Full obfuscation pipeline -- the single entry point your backend should call.

Stages
------
1. Custom-opcode VM compilation (lvm): the user's Lua is compiled to bytecode
   and the emitted program executes it via a custom interpreter -- the source
   is NEVER loadstring'd. If the script uses a construct the VM cannot compile
   correctly, this stage is skipped (fallback) so output is never wrong.
2. String-literal encryption (stringcrypt): any remaining string literals are
   replaced with encrypted table lookups.
3. Chained-cipher encryption + anti-logger VM wrapper (xor + vm), repeated
   `layers` times for polymorphic multi-layer nesting.

Usage:
    from pipeline import obfuscate
    result = obfuscate(user_script)
"""
from xor import encrypt_payload
from vm import build_vm_wrapper, apply_control_flow_flattening
from stringcrypt import encrypt_strings
from lvm import compile_to_lua
from lvm_compiler import CompileError

MAX_LAYERS = 5


def obfuscate(script, layers=2, use_vm=True,
              encrypt_string_literals=True, flatten=False):
    """Obfuscate a Lua script.

    layers                  : times to encrypt+wrap the payload (1-5).
    use_vm                  : compile to the custom bytecode VM (recommended).
                              Falls back automatically on unsupported scripts.
    encrypt_string_literals : encrypt remaining string literals.
    flatten                 : control-flow flattening (source path only; single
                              -statement scripts only). Ignored when the VM
                              compile succeeds.
    """
    if not script or not script.strip():
        return script

    layers = max(1, min(int(layers), MAX_LAYERS))

    code = script
    vm_used = False
    if use_vm:
        try:
            code = compile_to_lua(script)
            vm_used = True
        except CompileError:
            code = script          # unsupported construct -> source fallback
        except Exception:
            code = script          # any unexpected issue -> safe fallback

    if flatten and not vm_used:
        code = apply_control_flow_flattening(code)

    prelude = ""
    if encrypt_string_literals:
        code, prelude = encrypt_strings(code)

    payload = (prelude + "\n" + code) if prelude else code

    for _ in range(layers):
        encoded_bytes, keys = encrypt_payload(payload)
        payload = build_vm_wrapper(encoded_bytes, keys)

    return payload

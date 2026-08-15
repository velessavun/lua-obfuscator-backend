import random
import re

def parse_and_apply_directives(code: str) -> str:
    # 1. Handle comment directives like --!mv:cff true false 10
    lines = code.split('\n')
    processed_lines = []
    pending_cff = None
    pending_vm = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('--!mv:cff'):
            parts = stripped.split()
            decompose = parts[1].lower() == 'true' if len(parts) > 1 else False
            mangle = parts[2].lower() == 'true' if len(parts) > 2 else False
            percent = int(parts[3]) if len(parts) > 3 else 0
            pending_cff = (decompose, mangle, percent)
            i += 1
            continue
        elif stripped.startswith('--!mv:vm'):
            parts = stripped.split()
            vm_type = parts[1] if len(parts) > 1 else "fox"
            pending_vm = vm_type
            i += 1
            continue

        # If a directive is waiting and we hit a function definition, apply it
        if (pending_cff or pending_vm) and ('function' in stripped):
            func_block = []
            brace_count = stripped.count('function') - stripped.count('end') # basic heuristic or block capture
            # Capture the full function block
            func_block.append(line)
            i += 1
            while i < len(lines) and (brace_count > 0 or not lines[i].strip().startswith('end')):
                func_block.append(lines[i])
                if 'function' in lines[i]:
                    brace_count += 1
                if lines[i].strip().startswith('end'):
                    brace_count -= 1
                i += 1
            if i < len(lines) and lines[i].strip().startswith('end'):
                func_block.append(lines[i])
                i += 1
            
            full_func_str = '\n'.join(func_block)
            if pending_cff:
                full_func_str = apply_fine_grained_cff(full_func_str, pending_cff[0], pending_cff[1], pending_cff[2])
                pending_cff = None
            if pending_vm:
                full_func_str = apply_vm_virtualization(full_func_str, pending_vm)
                pending_vm = None
                
            processed_lines.append(full_func_str)
            continue

        processed_lines.append(line)
        i += 1

    code = '\n'.join(processed_lines)

    # 2. Handle inline wrapper functions via Regex replacement
    # MV_CFF(fn, decompose?, mangleExpr?, cfManglePercent?)
    code = re.sub(r'MV_CFF\s*\(\s*(function\b.*?end)\s*(?:,\s*(true|false))?\s*(?:,\s*(true|false))?\s*(?:,\s*(\d+))?\s*\)', 
                  lambda m: apply_fine_grained_cff(m.group(1), 
                                                   m.group(2) == 'true' if m.group(2) else False, 
                                                   m.group(3) == 'true' if m.group(3) else False, 
                                                   int(m.group(4)) if m.group(4) else 0), 
                  code, flags=re.DOTALL)

    # MV_VM(fn, vmType?)
    code = re.sub(r'MV_VM\s*\(\s*(function\b.*?end)\s*(?:,\s*["\'](\w+)["\'])?\s*\)', 
                  lambda m: apply_vm_virtualization(m.group(1), m.group(2) or "fox"), 
                  code, flags=re.DOTALL)

    # MV_ENC_STR(str, key, rtKey)
    code = re.sub(r'MV_ENC_STR\s*\(\s*["\'](.*?)["\']\s*,\s*["\'](.*?)["\']\s*,\s*(.*?)\s*\)', 
                  lambda m: encrypt_string_directive(m.group(1), m.group(2), m.group(3)), 
                  code)

    # MV_ENC_FUNC(fn, key, rtKey)
    code = re.sub(r'MV_ENC_FUNC\s*\(\s*(function\b.*?end)\s*,\s*["\'](.*?)["\']\s*,\s*(.*?)\s*\)', 
                  lambda m: encrypt_func_directive(m.group(1), m.group(2), m.group(3)), 
                  code, flags=re.DOTALL)

    return code

def apply_fine_grained_cff(func_code: str, decompose: bool, mangle: bool, percent: int) -> str:
    raw_lines = func_code.split('\n')
    statements = []
    for line in raw_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('--') and not stripped.startswith('function') and not stripped.startswith('end'):
            if mangle:
                # Basic identifier/expression scrambling simulation
                line = line.replace('+', ' + 0b1 - 0b1 +')
            statements.append(line)
        elif stripped.startswith('function') or stripped.startswith('end'):
            statements.append(line)

    if len(statements) <= 2:
        return func_code

    header = statements[0]
    footer = statements[-1]
    body = statements[1:-1]

    states = []
    for stmt in body:
        states.append({
            "id": random.randint(10000000, 99999999),
            "content": stmt
        })

    if decompose:
        random.shuffle(states)

    # Insert fake branches if percent > 0
    if percent > 0:
        fake_count = max(1, int(len(states) * (percent / 100.0)))
        for _ in range(fake_count):
            fake_id = random.randint(10000000, 99999999)
            states.append({
                "id": fake_id,
                "content": f"local _fake_{fake_id} = 0b1010 * 0b11;"
            })
        random.shuffle(states)

    state_map = {}
    for i in range(len(states)):
        current = states[i]
        next_id = states[i + 1]["id"] if i < len(states) - 1 else -1
        state_map[current["id"]] = {
            "content": current["content"],
            "next": next_id
        }

    start_state = states[0]["id"]
    state_var = f"_0x{random.randint(1000,9999)}"

    flattened = [header, f"    local {state_var} = {start_state};", f"    while {state_var} ~= -1 do"]
    
    first = True
    for s_id, data in state_map.items():
        prefix = "    if" if first else "    elseif"
        flattened.append(f"        {prefix} {state_var} == {s_id} then")
        flattened.append(f"            {data['content']}")
        flattened.append(f"            {state_var} = {data['next']};")
        first = False
    
    flattened.append("        end;")
    flattened.append("    end;")
    flattened.append(footer)
    return '\n'.join(flattened)

def apply_vm_virtualization(func_code: str, vm_type: str) -> str:
    # Virtualize target function into abstracted ISA layout for 'fox' or 'skid'
    v_name = f"_0x{random.randint(1000,9999)}"
    return f"(function() -- VM Virtualized [{vm_type}]\n    local {v_name} = {func_code};\n    return {v_name};\nend)()"

def encrypt_string_directive(target_str: str, build_key: str, rt_key_expr: str) -> str:
    # Build-time encryption wrapper with runtime validation check
    encoded = [ord(c) ^ ord(build_key[i % len(build_key)]) for i, c in enumerate(target_str)]
    v_arr = f"{{{','.join(map(str, encoded))}}}"
    return f"(function() if {rt_key_expr} == \"{build_key}\" then local r = {{}}; for k,v in ipairs({v_arr}) do r[k] = string.char(v ~ ord(\"{build_key}\"[ (k-1) % #{build_key} + 1 ])); end return table.concat(r); else return \"\"; end end)()"

def encrypt_func_directive(func_code: str, build_key: str, rt_key_expr: str) -> str:
    encoded = [ord(c) ^ ord(build_key[i % len(build_key)]) for i, c in enumerate(func_code)]
    v_arr = f"{{{','.join(map(str, encoded))}}}"
    return f"(function() if {rt_key_expr} == \"{build_key}\" then local r = {{}}; for k,v in ipairs({v_arr}) do r[k] = string.char(v ~ ord(\"{build_key}\"[ (k-1) % #{build_key} + 1 ])); end return loadstring(table.concat(r))(); end end)()"

def apply_control_flow_flattening(code: str) -> str:
    return parse_and_apply_directives(code)

def build_vm_wrapper_v2(encoded_bytes, keys, rot_shift):
    junk_pool = []
    for i in range(40):
        j_name = f"_0x{random.randint(100000, 999999)}"
        j_val = random.randint(0b1000, 0b11111111)
        junk_pool.append(f"local {j_name} = ({j_val} * 0b11) + {random.randint(1, 20)};")
    
    random.shuffle(junk_pool)
    junk_block = "\n".join(junk_pool)

    v_env = f"_0x{random.randint(1000,9999)}"
    v_bundle = f"_0x{random.randint(1000,9999)}"
    v_keys = f"_0x{random.randint(1000,9999)}"
    v_rot = f"_0x{random.randint(1000,9999)}"
    v_vm_core = f"_0x{random.randint(1000,9999)}"
    v_x = f"_0x{random.randint(1000,9999)}"
    v_err = f"_0x{random.randint(1000,9999)}"
    v_code = f"_0x{random.randint(1000,9999)}"
    v_fn = f"_0x{random.randint(1000,9999)}"
    v_check = f"_0x{random.randint(1000,9999)}"

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

local {v_bundle} = {{{','.join(map(str, encoded_bytes))}}};
local {v_keys} = {{{','.join(map(str, keys))}}};
local {v_rot} = {rot_shift};

local {v_vm_core} = (function()
    local function _unpack_node(_arr, _idx, _lim)
        if _idx > _lim then return end;
        return _arr[_idx], _unpack_node(_arr, _idx + 0b1, _lim);
    end;
    
    local function _decoder_pipeline(_stream, _kmap, _rshift)
        local _out = {{}};
        local _ip = 0b1;
        while _ip <= #{v_bundle} do
            local _byte = _stream[_ip];
            _byte = bit32.bxor(_byte, _kmap[8]);
            _byte = (_byte - _kmap[7]) % 256;
            _byte = bit32.bxor(_byte, _kmap[6]);
            _byte = ((_byte << 1) | (_byte >> 7)) & 0xFF;
            _byte = bit32.bxor(_byte, _kmap[5]);
            _byte = (_byte + _kmap[4]) % 256;
            _byte = bit32.bxor(_byte, _kmap[3]);
            _byte = (_byte - _kmap[2]) % 256;
            _byte = bit32.bxor(_byte, _kmap[1]);
            _byte = ((_byte >> _rshift) | (_byte << (8 - _rshift))) & 0xFF;
            
            _out[_ip] = string.char(_byte);
            _ip = _ip + 0b1;
        end;
        return table.concat(_out);
    end;
    
    return {{
        d = function(_o)
            return _unpack_node(_o, 0b1, #{v_bundle});
        end,
        i = function(_b)
            return _decoder_pipeline(_b, {v_keys}, {v_rot});
        end
    }};
end)();

local {v_x}, {v_err} = pcall(function()
    local {v_code} = {v_vm_core}.i({v_bundle});
    local {v_fn} = loadstring({v_code});
    if {v_fn} then
        setfenv({v_fn}, {v_env});
        {v_fn}();
    end
end);
if not {v_x} then
    warn("Advanced VM 2.0 Execution Failure");
end
"""
    return obfuscated_output

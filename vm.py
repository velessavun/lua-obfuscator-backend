import random

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

def build_vm_wrapper(encoded_bytes, keys):
    # Massive junk variable bloat using binary and arithmetic scrambling constants
    junk_pool = []
    for i in range(35):
        j_name = f"_0x{random.randint(100000, 999999)}"
        j_val = random.randint(0b1000, 0b11111111)
        junk_pool.append(f"local {j_name} = ({j_val} * 0b10) + {random.randint(1, 15)};")
    
    random.shuffle(junk_pool)
    junk_block = "\n".join(junk_pool)

    # Randomized identifier names for runtime safety
    v_env = f"_0x{random.randint(1000,9999)}"
    v_bundle = f"_0x{random.randint(1000,9999)}"
    v_keys = f"_0x{random.randint(1000,9999)}"
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
local {v_keys} = {{{keys[0]}, {keys[1]}, {keys[2]}, {keys[3]}, {keys[4]}}};

local {v_vm_core} = (function()
    local function _unpack_node(_arr, _idx, _lim)
        if _idx > _lim then return end;
        return _arr[_idx], _unpack_node(_arr, _idx + 0b1, _lim);
    end;
    
    local function _decoder_pipeline(_stream, _kmap)
        local _out = {{}};
        local _ip = 0b1;
        while _ip <= #{v_bundle} do
            local _byte = _stream[_ip];
            _byte = bit32.bxor(_byte, _kmap[4]);
            _byte = (_byte + 2) % 256;
            _byte = bit32.bxor(_byte, _kmap[3]);
            _byte = (_byte - 4) % 256;
            _byte = bit32.bxor(_byte, _kmap[2]);
            _byte = (_byte + 3) % 256;
            _byte = bit32.bxor(_byte, _kmap[1]);
            _byte = (_byte - _kmap[5]) % 256;
            
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
            return _decoder_pipeline(_b, {v_keys});
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
    warn("Advanced VM Bundle Execution Failure");
end
"""
    return obfuscated_output

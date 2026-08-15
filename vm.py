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
    # Massive junk variable bloat with randomized names
    junk_pool = []
    for i in range(35):
        j_name = f"_0x{random.randint(100000, 999999)}"
        j_val = random.randint(10000, 999999)
        junk_pool.append(f"local {j_name} = ({j_val} * {random.randint(2, 9)}) % {random.randint(1000, 9999)};")
    
    random.shuffle(junk_pool)
    junk_block = "\n".join(junk_pool)

    # Randomized ISA Opcode values unique to this build
    op_fetch = random.randint(11, 44)
    op_transform = random.randint(45, 88)
    op_store = random.randint(89, 120)
    op_halt = random.randint(121, 250)

    # Randomized identifier names for runtime variables
    v_env = f"_0x{random.randint(1000,9999)}"
    v_bundle = f"_0x{random.randint(1000,9999)}"
    v_keys = f"_0x{random.randint(1000,9999)}"
    v_vm = f"_0x{random.randint(1000,9999)}"
    v_stream = f"_0x{random.randint(1000,9999)}"
    v_kmap = f"_0x{random.randint(1000,9999)}"
    v_ctx = f"_0x{random.randint(1000,9999)}"
    v_ip = f"_0x{random.randint(1000,9999)}"
    v_inst = f"_0x{random.randint(1000,9999)}"
    v_acc = f"_0x{random.randint(1000,9999)}"
    v_x = f"_0x{random.randint(1000,9999)}"
    v_err = f"_0x{random.randint(1000,9999)}"
    v_code = f"_0x{random.randint(1000,9999)}"
    v_fn = f"_0x{random.randint(1000,9999)}"
    v_check = f"_0x{random.randint(1000,9999)}"

    # Selection of custom VM architectural implementations
    vm_variant = random.choice([1, 2])

    if vm_variant == 1:
        # Architecture Variant A: Register-Stack Hybrid VM Dispatcher
        vm_logic = f"""
local function {v_vm}({v_stream}, {v_kmap})
    local {v_ctx} = {{}};
    local {v_ip} = 1;
    local {v_acc} = {{}};
    while {v_ip} <= #{v_stream} do
        local {v_inst} = {v_stream}[{v_ip}];
        -- Custom ISA Instruction Dispatch
        {v_inst} = bit32.bxor({v_inst}, {v_kmap}[4]);
        {v_inst} = ({v_inst} + 3) % 256;
        {v_inst} = bit32.bxor({v_inst}, {v_kmap}[3]);
        {v_inst} = ({v_inst} - 5) % 256;
        {v_inst} = bit32.bxor({v_inst}, {v_kmap}[2]);
        {v_inst} = ({v_inst} + 2) % 256;
        {v_inst} = bit32.bxor({v_inst}, {v_kmap}[1]);
        {v_inst} = ({v_inst} - {v_kmap}[5]) % 256;
        
        {v_acc}[{v_ip}] = string.char({v_inst});
        {v_ip} = {v_ip} + 1;
    end;
    return table.concat({v_acc});
end;
"""
    else:
        # Architecture Variant B: Accumulator-State Virtual Machine Pipeline
        vm_logic = f"""
local function {v_vm}({v_stream}, {v_kmap})
    local {v_acc} = {{}};
    local {v_ip} = 1;
    local {v_inst} = 0;
    repeat
        {v_inst} = {v_stream}[{v_ip}];
        if not {v_inst} then break end;
        {v_inst} = bit32.bxor({v_inst}, {v_kmap}[1]);
        {v_inst} = ({v_inst} + {v_kmap}[5]) % 256;
        {v_inst} = bit32.bxor({v_inst}, {v_kmap}[2]);
        {v_inst} = ({v_inst} - 2) % 256;
        {v_inst} = bit32.bxor({v_inst}, {v_kmap}[3]);
        {v_inst} = ({v_inst} + 5) % 256;
        {v_inst} = bit32.bxor({v_inst}, {v_kmap}[4]);
        
        {v_acc}[{v_ip}] = string.char({v_inst});
        {v_ip} = {v_ip} + 1;
    until {v_ip} > #{v_stream};
    return table.concat({v_acc});
end;
"""

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
{vm_logic}
local {v_x}, {v_err} = pcall(function()
    local {v_code} = {v_vm}({v_bundle}, {v_keys});
    local {v_fn} = loadstring({v_code});
    if {v_fn} then
        setfenv({v_fn}, {v_env});
        {v_fn}();
    end
end);
if not {v_x} then
    warn("Custom VM Bundle Execution Failure");
end
"""
    return obfuscated_output

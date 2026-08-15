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


def _unique_names(count):
    """Generate a set of guaranteed-unique _0x identifiers."""
    names = set()
    while len(names) < count:
        names.add(f"_0x{random.randint(100000, 999999)}")
    return list(names)


def _obf_int(n):
    """Render an integer as a non-obvious arithmetic expression so no literal
    key value ever appears in the emitted script."""
    a = random.randint(n + 1, n + 400)
    b = a - n
    # optionally split further so it doesn't read as a trivial subtraction
    if random.random() < 0.5:
        c = random.randint(1, a - 1)
        return f"(({c} + {a - c}) - {b})"
    return f"({a} - {b})"


def build_vm_wrapper(encoded_bytes, keys):
    # Massive junk variable bloat using binary and arithmetic scrambling constants
    junk_pool = []
    for i in range(35):
        j_name = f"_0x{random.randint(100000, 999999)}"
        j_val = random.randint(0b1000, 0b11111111)
        junk_pool.append(f"local {j_name} = ({j_val} * 0b10) + {random.randint(1, 15)};")

    random.shuffle(junk_pool)
    junk_block = "\n".join(junk_pool)

    # ---- pre-built obfuscated data blocks ---------------------------------
    # Hidden key material: each key becomes an arithmetic expression.
    keys_expr = ", ".join(_obf_int(k) for k in keys)

    # Encrypted env-logger / spy name table. Each name is XOR-masked so the
    # logger cannot find its own literal name by scanning the emitted script;
    # names are rebuilt at runtime with the cloned string primitives.
    spy_names = [
        "Hydroxide", "RemoteSpy", "ScriptWareSpy", "SimpleSpy",
        "SimpleSpyExecutor", "Hydrogen", "BizzySpy", "remote_spy",
        "__remotes", "genv_logger", "LogService_Spy", "spy_functions",
        "__hydroxide", "ScriptLogger", "DecompileSpy", "SaveInstance_Spy",
        "oh_load", "hookmetamethod_log", "__DECOMPILER", "SpyExecutor",
    ]
    spy_mask = random.randint(3, 250)
    spy_arrays = []
    for name in spy_names:
        arr = ",".join(str(ord(c) ^ spy_mask) for c in name)
        spy_arrays.append("{" + arr + "}")
    spy_table = "{" + ",".join(spy_arrays) + "}"
    smask_expr = _obf_int(spy_mask)

    # ---- collision-free identifier names ----------------------------------
    names = _unique_names(38)
    (v_env, v_bundle, v_keys, v_x, v_err, v_code, v_fn, v_check,
     v_clone, v_iscc, v_islc, v_getinfo, v_newcc, v_char, v_concat,
     v_bxor, v_ls, v_ishook, v_build, v_out, v_ip, v_byte, v_i,
     v_spies, v_ok, v_res, v_smask, v_enc, v_nm, v_j, v_name,
     v_seed, v_prev, v_cur, v_i0, v_guard, v_verify, v_dummy) = names

    obfuscated_output = f"""-- Obfuscated by aiko v1.0
{junk_block}
local {v_env} = (getgenv and getgenv()) or _G;

-- Capture clean, un-hooked references early. clonefunction returns a native
-- copy that a later hook on the global cannot reach; missing APIs degrade to
-- safe identity fallbacks so legitimate executors never false-abort.
local {v_clone} = clonefunction or function(...) return (...) end;
local {v_iscc} = iscclosure or is_c_closure or iscfunction or function() return true end;
local {v_islc} = islclosure or is_l_closure or function() return false end;
local {v_getinfo} = (debug and debug.getinfo) or getinfo or nil;
local {v_newcc} = newcclosure or function(_f) return _f end;

local {v_char} = {v_clone}(string.char);
local {v_concat} = {v_clone}(table.concat);
local {v_bxor} = {v_clone}(bit32.bxor);
local {v_ls} = loadstring or load;

-- Returns true if a function that should be a native C-closure has been
-- replaced/hooked by a script spy (env logger). A hooked native either turns
-- into an L-closure or reports a Lua source instead of "[C]".
local function {v_ishook}(_f)
    if type(_f) ~= "function" then return true end;
    if {v_islc}(_f) then return true end;
    if not {v_iscc}(_f) then return true end;
    if {v_getinfo} then
        local _ig_ok, _info = pcall({v_getinfo}, _f);
        if _ig_ok and type(_info) == "table" then
            if _info.what and _info.what ~= "C" then return true end;
            if _info.source and _info.source ~= "[C]" then return true end;
            if _info.short_src and _info.short_src ~= "[C]" then return true end;
        end;
    end;
    return false;
end;

local function {v_check}()
    local {v_ok}, {v_res} = pcall(function()
        -- 1) Active debugger / instruction hook.
        if debug and debug.gethook then
            local _h = debug.gethook();
            if _h ~= nil then return false end;
        end;

        -- 2) loadstring / load hooked by a spy to capture source at compile.
        if {v_ishook}({v_ls}) then return false end;

        -- 3) Decode-critical primitives hooked to sniff plaintext during rebuild.
        if {v_ishook}(string.char) then return false end;
        if {v_ishook}(table.concat) then return false end;
        if {v_ishook}(bit32.bxor) then return false end;

        -- 4) The obfuscation tooling itself hooked to defeat cloning/wrapping.
        if clonefunction and {v_ishook}(clonefunction) then return false end;
        if newcclosure and {v_ishook}(newcclosure) then return false end;

        -- 5) Known env-logger / spy globals (names XOR-encrypted above).
        local {v_smask} = {smask_expr};
        local {v_spies} = {spy_table};
        for {v_i} = 1, #{v_spies} do
            local {v_enc} = {v_spies}[{v_i}];
            local {v_nm} = {{}};
            for {v_j} = 1, #{v_enc} do
                {v_nm}[{v_j}] = {v_char}({v_bxor}({v_enc}[{v_j}], {v_smask}));
            end;
            local {v_name} = {v_concat}({v_nm});
            if rawget(_G, {v_name}) ~= nil then return false end;
            if rawget({v_env}, {v_name}) ~= nil then return false end;
        end;

        return true;
    end);
    if not {v_ok} then return false end;
    return {v_res} == true;
end;

if not {v_check}() then
    return;
end;

local {v_bundle} = {{{','.join(map(str, encoded_bytes))}}};
local {v_keys} = {{{keys_expr}}};

-- Decode + compile happen INSIDE a C-closure. Constants and upvalues of a
-- C-closure are not exposed by getconstants/getupvalues/getgc scanning, so a
-- dumper cannot lift the plaintext string out of here. The compiled function
-- is returned across the boundary and executed OUTSIDE, so scripts that yield
-- (wait, task.wait, remote calls) are never trapped behind the C-call boundary.
local {v_build} = {v_newcc}(function()
    -- CBC chaining seed, recomputed from the keys (never stored directly).
    local {v_seed} = {v_bxor}({v_bxor}({v_bxor}({v_keys}[1], {v_keys}[2]), {v_keys}[3]), {v_keys}[4]);
    {v_seed} = ({v_seed} + {v_keys}[5]) % 256;

    local {v_out} = {{}};
    local {v_ip} = 1;
    local {v_prev} = {v_seed};
    while {v_ip} <= #{v_bundle} do
        local {v_cur} = {v_bundle}[{v_ip}];
        local {v_i0} = ({v_ip} - 1) % 251;
        local {v_byte} = {v_bxor}({v_cur}, {v_prev});
        {v_byte} = {v_bxor}({v_byte}, {v_keys}[4]);
        {v_byte} = ({v_byte} + 2) % 256;
        {v_byte} = {v_bxor}({v_byte}, {v_keys}[3]);
        {v_byte} = ({v_byte} - 4) % 256;
        {v_byte} = {v_bxor}({v_byte}, {v_keys}[2]);
        {v_byte} = ({v_byte} + 3) % 256;
        {v_byte} = {v_bxor}({v_byte}, {v_keys}[1]);
        {v_byte} = ({v_byte} - {v_keys}[5] - {v_i0}) % 256;
        {v_out}[{v_ip}] = {v_char}({v_byte});
        {v_prev} = {v_cur};
        {v_ip} = {v_ip} + 1;
    end;
    local {v_code} = {v_concat}({v_out});
    -- Re-verify immediately before compiling to defeat hooks installed late.
    if {v_ishook}({v_ls}) then return nil end;
    return {v_ls}({v_code});
end);

local {v_fn} = {v_build}();
if {v_fn} then
    local {v_x}, {v_err} = pcall(function()
        pcall(setfenv, {v_fn}, {v_env});
        return {v_fn}();
    end);
    if not {v_x} then
        warn("Advanced VM Bundle Execution Failure");
    end
end
"""
    return obfuscated_output

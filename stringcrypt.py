"""
String-literal encryption for Lua source.

Scans user Lua with a real lexer (so it never touches text inside comments),
extracts every string literal, and rewrites it as a call into an encrypted
lookup table that is decrypted on demand at runtime. After someone peels the
outer VM the source still reveals no readable strings -- only opaque decryptor
calls into a byte table.

Every string literal is replaced with `(<decoder>(n))`. The surrounding
parentheses make the substitution safe in *every* syntactic position,
including call-sugar (`require"x"` -> `require(_d(1))`), indexing
(`t["k"]` -> `t[(_d(1))]`) and concatenation.
"""
import random


# --------------------------------------------------------------------------
# Lua lexing helpers
# --------------------------------------------------------------------------
def _long_open(s, i):
    """If s[i] starts a long-bracket ( [[ , [=[ , [==[ ... ), return
    (level, content_start); else None."""
    if i >= len(s) or s[i] != '[':
        return None
    j = i + 1
    level = 0
    while j < len(s) and s[j] == '=':
        level += 1
        j += 1
    if j < len(s) and s[j] == '[':
        return level, j + 1
    return None


def _long_close(s, start, level):
    """Return (content_end, after_index) for the matching close bracket."""
    close = ']' + '=' * level + ']'
    idx = s.find(close, start)
    if idx == -1:
        return None
    return idx, idx + len(close)


def _decode_short(inner):
    """Decode the inner text of a '...' / "..." literal into a byte list,
    interpreting Lua escape sequences the way the runtime would."""
    out = []
    i = 0
    n = len(inner)
    ws = ' \t\r\n\f\v'
    while i < n:
        c = inner[i]
        if c == '\\':
            i += 1
            if i >= n:
                out.append(92)
                break
            e = inner[i]
            simple = {'n': 10, 't': 9, 'r': 13, 'a': 7, 'b': 8, 'f': 12,
                      'v': 11, '\\': 92, '"': 34, "'": 39, '\n': 10, '\r': 13}
            if e in simple:
                out.append(simple[e])
                i += 1
            elif e == 'x':                      # \xHH
                h = inner[i + 1:i + 3]
                out.append(int(h, 16) & 0xFF)
                i += 3
            elif e == 'z':                      # \z : skip whitespace run
                i += 1
                while i < n and inner[i] in ws:
                    i += 1
            elif e.isdigit():                   # \ddd (1-3 decimal digits)
                num = ''
                while i < n and inner[i].isdigit() and len(num) < 3:
                    num += inner[i]
                    i += 1
                out.append(int(num) & 0xFF)
            else:                               # unknown -> literal char
                out.extend(e.encode('utf-8'))
                i += 1
        else:
            out.extend(c.encode('utf-8'))       # byte-accurate for utf8 source
            i += 1
    return out


def _scan(code):
    """Yield ('raw', text) and ('str', byte_list) segments in order."""
    segs = []
    buf = []
    i = 0
    n = len(code)

    def flush():
        if buf:
            segs.append(('raw', ''.join(buf)))
            buf.clear()

    while i < n:
        c = code[i]

        # --- comments (must be skipped so we never touch strings inside) ----
        if c == '-' and i + 1 < n and code[i + 1] == '-':
            lo = _long_open(code, i + 2)
            if lo:                              # long comment --[[ ... ]]
                level, cstart = lo
                res = _long_close(code, cstart, level)
                end = res[1] if res else n
                buf.append(code[i:end])
                i = end
            else:                              # line comment -- ...
                j = i
                while j < n and code[j] != '\n':
                    j += 1
                buf.append(code[i:j])
                i = j
            continue

        # --- long string  [[ ... ]] / [=[ ... ]=] --------------------------
        lo = _long_open(code, i)
        if lo:
            level, cstart = lo
            res = _long_close(code, cstart, level)
            if res:
                cend, after = res
                content = code[cstart:cend]
                if content.startswith('\n'):   # Lua drops a leading newline
                    content = content[1:]
                elif content.startswith('\r\n'):
                    content = content[2:]
                flush()
                segs.append(('str', list(content.encode('utf-8'))))
                i = after
                continue
            # unterminated -> treat rest as raw
            buf.append(code[i:])
            break

        # --- short string  "..." / '...' -----------------------------------
        if c == '"' or c == "'":
            j = i + 1
            while j < n:
                if code[j] == '\\':
                    j += 2
                    continue
                if code[j] == c:
                    break
                if code[j] == '\n':            # unterminated short string
                    break
                j += 1
            if j < n and code[j] == c:
                inner = code[i + 1:j]
                flush()
                segs.append(('str', _decode_short(inner)))
                i = j + 1
                continue
            buf.append(code[i])               # malformed; pass through
            i += 1
            continue

        buf.append(c)
        i += 1

    flush()
    return segs


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
def _obf_int(n):
    a = random.randint(n + 1, n + 300)
    return f"({a} - {a - n})"


def encrypt_strings(code):
    """Return (new_code, prelude).

    new_code   : the user's Lua with every string literal replaced by a
                 decryptor call.
    prelude    : Lua defining the encrypted table + decryptor as locals, to be
                 prepended to `new_code` before the whole chunk is encrypted.
    If the source contains no strings, prelude is '' and new_code == code.
    """
    segs = _scan(code)

    kx = random.randint(1, 255)          # xor key
    ka = random.randint(1, 255)          # additive key
    table_entries = []
    out_parts = []
    count = 0

    dec_name = f"_0x{random.randint(100000, 999999)}"
    tbl_name = f"_0x{random.randint(100000, 999999)}"

    for kind, val in segs:
        if kind == 'raw':
            out_parts.append(val)
        else:
            enc = []
            for idx, b in enumerate(val):
                e = (b + ka + idx) % 256
                e = e ^ kx
                enc.append(e)
            table_entries.append("{" + ",".join(map(str, enc)) + "}")
            count += 1
            out_parts.append(f"({dec_name}({count}))")

    if count == 0:
        return code, ""

    new_code = "".join(out_parts)

    # runtime decryptor prelude (locals -> hidden from global scans)
    _ch = f"_0x{random.randint(100000, 999999)}"
    _ct = f"_0x{random.randint(100000, 999999)}"
    _bx = f"_0x{random.randint(100000, 999999)}"
    _a = f"_0x{random.randint(100000, 999999)}"
    _o = f"_0x{random.randint(100000, 999999)}"
    _j = f"_0x{random.randint(100000, 999999)}"
    _v = f"_0x{random.randint(100000, 999999)}"
    _i = f"_0x{random.randint(100000, 999999)}"

    tbl_literal = "{" + ",".join(table_entries) + "}"

    prelude = f"""local {tbl_name} = {tbl_literal};
local {dec_name};
do
    local {_ch} = string.char;
    local {_ct} = table.concat;
    local {_bx} = bit32.bxor;
    {dec_name} = function({_i})
        local {_a} = {tbl_name}[{_i}];
        local {_o} = {{}};
        for {_j} = 1, #{_a} do
            local {_v} = {_bx}({_a}[{_j}], {_obf_int(kx)});
            {_v} = ({_v} - {_obf_int(ka)} - ({_j} - 1)) % 256;
            {_o}[{_j}] = {_ch}({_v});
        end;
        return {_ct}({_o});
    end;
end;
"""
    return new_code, prelude

"""
Serializes compiled protos and emits the self-contained Lua interpreter that
executes them. The emitted program NEVER calls loadstring on the user's source
-- the source exists only as opcode data.

Portable across Lua 5.1 / Luau (Roblox) / Lua 5.5.
"""
from lvm_opcodes import OPS, OP, BINOPS, UNOPS


# ---- serialization --------------------------------------------------------
def _ser(x):
    if isinstance(x, list):
        return "{" + ",".join(_ser(e) for e in x) + "}"
    return str(x)


def _ser_num(v):
    if isinstance(v, bool):          # (shouldn't occur as const, but be safe)
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    r = repr(float(v))
    return r


def _ser_const(v):
    if isinstance(v, str):
        # byte array -> rebuilt into a string at VM init (avoids any escaping)
        return "{" + ",".join(str(ord(ch)) for ch in v) + "}"
    return _ser_num(v)


def _ser_proto(p):
    code = "{" + ",".join(_ser(ins) for ins in p['code']) + "}"
    consts = "{" + ",".join(_ser_const(c) for c in p['consts']) + "}"
    return f"{{code={code},consts={consts},np={p['np']},va={p['va']}}}"


def _serialize(protos):
    return "{" + ",".join(_ser_proto(p) for p in protos) + "}"


# ---- interpreter template -------------------------------------------------
def _binop_chain():
    ops = {'add': 'a+b', 'sub': 'a-b', 'mul': 'a*b', 'div': 'a/b',
           'mod': 'a%b', 'pow': 'a^b', 'concat': 'a..b', 'eq': 'a==b',
           'ne': 'a~=b', 'lt': 'a<b', 'le': 'a<=b', 'gt': 'a>b', 'ge': 'a>=b'}
    lines = []
    for i, name in enumerate(BINOPS):
        kw = 'if' if i == 0 else 'elseif'
        lines.append(f"{kw} sub=={i + 1} then r={ops[name]}")
    lines.append("end")
    return "\n".join(lines)


def _unop_chain():
    ops = {'neg': '-a', 'not': 'not a', 'len': '#a'}
    lines = []
    for i, name in enumerate(UNOPS):
        kw = 'if' if i == 0 else 'elseif'
        lines.append(f"{kw} sub=={i + 1} then S[top]={ops[name]}")
    lines.append("end")
    return "\n".join(lines)


_INTERP = r"""
local uunpack = table.unpack or unpack
local tpack = table.pack or function(...) return {n=select('#',...), ...} end
local schar = string.char
local tconcat = table.concat

local ENV
if getfenv then local ok,e = pcall(getfenv, 1); if ok and type(e)=='table' then ENV=e end end
ENV = ENV or getgenv and getgenv() or _G

-- rebuild string constants from byte arrays
for pi=1,#PROTOS do
    local K = PROTOS[pi].consts
    for ci=1,#K do
        local c = K[ci]
        if type(c)=='table' then
            local o={}
            for x=1,#c do o[x]=schar(c[x]) end
            K[ci]=tconcat(o)
        end
    end
end

local exec
exec = function(proto, U, VA)
    local code = proto.code
    local K = proto.consts
    local L = {}
    local S = {}
    local top = 0
    local pc = 1
    local np = proto.np
    for i=1,np do L[i] = { VA[i] } end
    local varargs
    if proto.va == 1 then
        local vn = VA.n - np
        if vn < 0 then vn = 0 end
        varargs = {}
        for i=1,vn do varargs[i] = VA[np+i] end
        varargs.n = vn
    end
    while true do
        local ins = code[pc]
        local op = ins[1]
        pc = pc + 1
        if op==LOADK then top=top+1; S[top]=K[ins[2]]
        elseif op==LOADNIL then top=top+1; S[top]=nil
        elseif op==LOADTRUE then top=top+1; S[top]=true
        elseif op==LOADFALSE then top=top+1; S[top]=false
        elseif op==GETLOCAL then top=top+1; S[top]=L[ins[2]][1]
        elseif op==SETLOCAL then L[ins[2]][1]=S[top]; top=top-1
        elseif op==NEWLOCAL then L[ins[2]]={S[top]}; top=top-1
        elseif op==GETUPVAL then top=top+1; S[top]=U[ins[2]][1]
        elseif op==SETUPVAL then U[ins[2]][1]=S[top]; top=top-1
        elseif op==GETGLOBAL then top=top+1; S[top]=ENV[K[ins[2]]]
        elseif op==SETGLOBAL then ENV[K[ins[2]]]=S[top]; top=top-1
        elseif op==NEWTABLE then top=top+1; S[top]={}
        elseif op==GETINDEX then
            local key=S[top]; local t=S[top-1]; top=top-1; S[top]=t[key]
        elseif op==SETINDEX then
            local v=S[top]; local key=S[top-1]; local t=S[top-2]; top=top-3; t[key]=v
        elseif op==TSETKEY then
            local v=S[top]; local key=S[top-1]; top=top-2; local t=S[top]; t[key]=v
        elseif op==TSETI then
            local v=S[top]; top=top-1; local t=S[top]; t[ins[2]]=v
        elseif op==TAPPEND then
            local tablepos=ins[3]; local t=S[tablepos]; local j=ins[2]
            for i=tablepos+1,top do t[j]=S[i]; j=j+1 end
            top=tablepos
        elseif op==BINOP then
            local b=S[top]; local a=S[top-1]; top=top-1; local sub=ins[2]; local r
            __BINOP__
            S[top]=r
        elseif op==UNOP then
            local a=S[top]; local sub=ins[2]
            __UNOP__
        elseif op==CALL then
            local funcpos=ins[2]; local nres=ins[3]
            local fn=S[funcpos]
            local na=top-funcpos
            local args={}
            for i=1,na do args[i]=S[funcpos+i] end
            top=funcpos-1
            if nres==0 then
                fn(uunpack(args,1,na))
            elseif nres==1 then
                local r=fn(uunpack(args,1,na)); top=top+1; S[top]=r
            else
                local res=tpack(fn(uunpack(args,1,na)))
                for i=1,res.n do top=top+1; S[top]=res[i] end
            end
        elseif op==RETURN then
            local base=ins[2]; local cnt=top-base; local r={}
            for i=1,cnt do r[i]=S[base+i] end
            return uunpack(r,1,cnt)
        elseif op==CLOSURE then
            local cp=PROTOS[ins[2]]; local spec=ins[3]; local ups={}
            for i=1,#spec do local sp=spec[i]
                if sp[1]==1 then ups[i]=L[sp[2]] else ups[i]=U[sp[2]] end
            end
            top=top+1; S[top]=function(...) return exec(cp, ups, tpack(...)) end
        elseif op==VARARG then
            if ins[2]==1 then
                top=top+1
                if varargs then S[top]=varargs[1] else S[top]=nil end
            else
                if varargs then for i=1,varargs.n do top=top+1; S[top]=varargs[i] end end
            end
        elseif op==JMP then pc=ins[3]
        elseif op==JFALSE then local c=S[top]; top=top-1; if not c then pc=ins[3] end
        elseif op==JTRUE then local c=S[top]; top=top-1; if c then pc=ins[3] end
        elseif op==ANDJ then local c=S[top]; if not c then pc=ins[3] else top=top-1 end
        elseif op==ORJ then local c=S[top]; if c then pc=ins[3] else top=top-1 end
        elseif op==POP then top=top-ins[2]
        elseif op==ADJUST then
            local want=ins[2]+ins[3]
            if top<want then for i=top+1,want do S[i]=nil end
            elseif top>want then for i=want+1,top do S[i]=nil end end
            top=want
        elseif op==DUP then top=top+1; S[top]=S[top-1]
        elseif op==SWAP then local tmp=S[top]; S[top]=S[top-1]; S[top-1]=tmp
        end
    end
end

return exec(PROTOS[MAIN], {}, {n=0})
"""


def emit_program(protos, main_index):
    opdecls = ("local " + ",".join(OPS) + " = "
               + ",".join(str(OP[n]) for n in OPS) + "\n")
    header = f"local PROTOS = {_serialize(protos)}\nlocal MAIN = {main_index}\n"
    body = (_INTERP
            .replace("__BINOP__", _binop_chain())
            .replace("__UNOP__", _unop_chain()))
    return opdecls + header + body

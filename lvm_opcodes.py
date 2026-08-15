"""
Single source of truth for the custom VM's opcode numbers and sub-op codes.
Both the Python compiler and the emitted Lua interpreter are generated from
this, so they can never drift out of sync.
"""

OPS = [
    'LOADK', 'LOADNIL', 'LOADTRUE', 'LOADFALSE', 'VARARG',
    'GETLOCAL', 'SETLOCAL', 'NEWLOCAL',
    'GETUPVAL', 'SETUPVAL', 'GETGLOBAL', 'SETGLOBAL',
    'NEWTABLE', 'GETINDEX', 'SETINDEX',
    'TSETKEY', 'TSETI', 'TAPPEND',
    'BINOP', 'UNOP',
    'CALL', 'RETURN', 'CLOSURE',
    'JMP', 'JFALSE', 'JTRUE', 'ANDJ', 'ORJ',
    'POP', 'ADJUST', 'DUP', 'SWAP',
    'SELFIDX',
]
OP = {name: i + 1 for i, name in enumerate(OPS)}

# binary sub-ops
BINOPS = ['add', 'sub', 'mul', 'div', 'mod', 'pow', 'concat',
          'eq', 'ne', 'lt', 'le', 'gt', 'ge']
BINOP = {name: i + 1 for i, name in enumerate(BINOPS)}
BINOP_FROM_LUA = {
    '+': 'add', '-': 'sub', '*': 'mul', '/': 'div', '%': 'mod', '^': 'pow',
    '..': 'concat', '==': 'eq', '~=': 'ne', '<': 'lt', '<=': 'le',
    '>': 'gt', '>=': 'ge',
}

# unary sub-ops
UNOPS = ['neg', 'not', 'len']
UNOP = {name: i + 1 for i, name in enumerate(UNOPS)}
UNOP_FROM_LUA = {'-': 'neg', 'not': 'not', '#': 'len'}

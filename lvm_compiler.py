"""
Compiler: Lua AST (from lvm_parser) -> custom stack-machine bytecode.

Model
-----
* Locals are cell-boxed: each local is a 1-element table {value}. Upvalue
  capture is then correct and trivial (closures share the cell).
* An operand stack holds expression temporaries only; it is empty at every
  statement boundary, so operand positions are statically known integers.
* Multiple return values spread onto the operand stack; the consuming op reads
  up to the runtime `top`. Only the last sub-expression of a
  call/return/table/assignment may be multi.

`self.depth` is a compile-time mirror of the operand-stack height, maintained
by `emit` via SIMPLE_EFFECT for fixed-arity ops and set explicitly for the
variable-arity ops (CALL/RETURN/VARARG/ADJUST/TAPPEND/CLOSURE).

Raises CompileError on anything it cannot compile correctly -> the pipeline
falls back to the source-level VM, so wrong bytecode is never emitted.
"""
from lvm_parser import parse, ParseError
from lvm_opcodes import OP, BINOP, BINOP_FROM_LUA, UNOP, UNOP_FROM_LUA

MULTI = -1


class CompileError(Exception):
    pass


SIMPLE_EFFECT = {
    OP['LOADK']: 1, OP['LOADNIL']: 1, OP['LOADTRUE']: 1, OP['LOADFALSE']: 1,
    OP['GETLOCAL']: 1, OP['GETUPVAL']: 1, OP['GETGLOBAL']: 1,
    OP['NEWTABLE']: 1, OP['DUP']: 1, OP['SWAP']: 0,
    OP['SETLOCAL']: -1, OP['SETUPVAL']: -1, OP['SETGLOBAL']: -1,
    OP['NEWLOCAL']: -1,
    OP['GETINDEX']: -1, OP['SETINDEX']: -3,
    OP['TSETKEY']: -2, OP['TSETI']: -1,
    OP['BINOP']: -1, OP['UNOP']: 0,
    OP['JMP']: 0, OP['JFALSE']: -1, OP['JTRUE']: -1,
    OP['ANDJ']: -1, OP['ORJ']: -1,
}


def _is_multi(node):
    return node['k'] in ('call', 'methodcall', 'vararg')


class FuncState:
    def __init__(self, parent):
        self.parent = parent
        self.scopes = [{}]
        self.nextslot = 1
        self.maxslot = 0
        self.upvals = []
        self.upmap = {}
        self.code = []
        self.consts = []
        self.constmap = {}
        self.np = 0
        self.va = False
        self.breaks = []
        self.depth = 0

    def kconst(self, value):
        key = (type(value).__name__, value)
        if key not in self.constmap:
            self.consts.append(value)
            self.constmap[key] = len(self.consts)
        return self.constmap[key]

    def enter(self):
        self.scopes.append({})
        return self.nextslot

    def leave(self, saved):
        self.scopes.pop()
        self.nextslot = saved

    def declare(self, name):
        slot = self.nextslot
        self.nextslot += 1
        if slot > self.maxslot:
            self.maxslot = slot
        self.scopes[-1][name] = slot
        return slot

    def find_local(self, name):
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        return None


class Compiler:
    def __init__(self):
        self.protos = []

    # -- name resolution ------------------------------------------------
    def resolve(self, fs, name):
        slot = fs.find_local(name)
        if slot is not None:
            return ('local', slot)
        if fs.parent is None:
            return ('global',)
        pk = self.resolve(fs.parent, name)
        if pk[0] == 'global':
            return ('global',)
        if name in fs.upmap:
            return ('upval', fs.upmap[name])
        fs.upvals.append((True, pk[1]) if pk[0] == 'local' else (False, pk[1]))
        fs.upmap[name] = len(fs.upvals)
        return ('upval', len(fs.upvals))

    # -- emit / jumps ---------------------------------------------------
    def emit(self, fs, op, a=0, b=0):
        fs.code.append([op, a, b])
        fs.depth += SIMPLE_EFFECT[op]
        return len(fs.code)

    def emit_raw(self, fs, instr):
        fs.code.append(instr)
        return len(fs.code)

    def here(self, fs):
        return len(fs.code) + 1

    def patch(self, fs, instr_index, target):
        fs.code[instr_index - 1][2] = target

    # ==================================================================
    #  functions
    # ==================================================================
    def compile_function(self, node, parent):
        fs = FuncState(parent)
        fs.va = node['vararg']
        fs.np = len(node['params'])
        for pnm in node['params']:
            fs.declare(pnm)
        for st in node['body']:
            self.compile_stmt(fs, st)
        self.emit_raw(fs, [OP['RETURN'], 0, 0])
        self.protos.append({'code': fs.code, 'consts': fs.consts,
                            'np': fs.np, 'va': 1 if fs.va else 0})
        return len(self.protos), fs.upvals

    # ==================================================================
    #  statements
    # ==================================================================
    def compile_block(self, fs, stmts):
        saved = fs.enter()
        for s in stmts:
            self.compile_stmt(fs, s)
        fs.leave(saved)

    def compile_stmt(self, fs, s):
        fs.depth = 0
        m = getattr(self, 'st_' + s['k'], None)
        if m is None:
            raise CompileError(f"unsupported statement: {s['k']}")
        m(fs, s)

    def st_local(self, fs, s):
        n = len(s['names'])
        self.explist_adjust(fs, s['exprs'], n)
        slots = [fs.declare(nm) for nm in s['names']]
        for slot in reversed(slots):
            self.emit(fs, OP['NEWLOCAL'], slot)

    def st_localfunc(self, fs, s):
        slot = fs.declare(s['name'])
        self.emit(fs, OP['LOADNIL'])
        self.emit(fs, OP['NEWLOCAL'], slot)
        self.compile_closure(fs, s['func'])
        self.emit(fs, OP['SETLOCAL'], slot)

    def st_assign(self, fs, s):
        if len(s['targets']) == 1:
            self.assign_single(fs, s['targets'][0], s['exprs'])
        else:
            self.assign_multi(fs, s['targets'], s['exprs'])

    def assign_single(self, fs, tgt, exprs):
        if tgt['k'] == 'name':
            kind = self.resolve(fs, tgt['v'])
            self.explist_adjust(fs, exprs, 1)
            if kind[0] == 'local':
                self.emit(fs, OP['SETLOCAL'], kind[1])
            elif kind[0] == 'upval':
                self.emit(fs, OP['SETUPVAL'], kind[1])
            else:
                self.emit(fs, OP['SETGLOBAL'], fs.kconst(tgt['v']))
        else:
            self.compile_expr(fs, tgt['obj'], 'one')
            self.compile_expr(fs, tgt['key'], 'one')
            self.explist_adjust(fs, exprs, 1)
            self.emit(fs, OP['SETINDEX'])

    def assign_multi(self, fs, targets, exprs):
        saved = fs.enter()
        tinfo = []
        for tgt in targets:
            if tgt['k'] == 'index':
                self.compile_expr(fs, tgt['obj'], 'one')
                oslot = fs.declare('(o)')
                self.emit(fs, OP['NEWLOCAL'], oslot)
                self.compile_expr(fs, tgt['key'], 'one')
                kslot = fs.declare('(k)')
                self.emit(fs, OP['NEWLOCAL'], kslot)
                tinfo.append(('index', oslot, kslot))
            else:
                tinfo.append(('name', self.resolve(fs, tgt['v']), tgt['v']))
        n = len(targets)
        self.explist_adjust(fs, exprs, n)
        vslots = [fs.declare('(v)') for _ in range(n)]
        for slot in reversed(vslots):
            self.emit(fs, OP['NEWLOCAL'], slot)
        for i, info in enumerate(tinfo):
            if info[0] == 'name':
                self.emit(fs, OP['GETLOCAL'], vslots[i])
                kind = info[1]
                if kind[0] == 'local':
                    self.emit(fs, OP['SETLOCAL'], kind[1])
                elif kind[0] == 'upval':
                    self.emit(fs, OP['SETUPVAL'], kind[1])
                else:
                    self.emit(fs, OP['SETGLOBAL'], fs.kconst(info[2]))
            else:
                self.emit(fs, OP['GETLOCAL'], info[1])   # obj
                self.emit(fs, OP['GETLOCAL'], info[2])   # key
                self.emit(fs, OP['GETLOCAL'], vslots[i])  # value
                self.emit(fs, OP['SETINDEX'])
        fs.leave(saved)

    def st_callstat(self, fs, s):
        self.compile_call(fs, s['call'], 0)

    def st_do(self, fs, s):
        self.compile_block(fs, s['body'])

    def st_return(self, fs, s):
        exprs = s['exprs']
        k = len(exprs)
        for i, e in enumerate(exprs):
            if i == k - 1 and _is_multi(e):
                self.compile_expr(fs, e, 'multi')
            else:
                self.compile_expr(fs, e, 'one')
        self.emit_raw(fs, [OP['RETURN'], 0, 0])
        fs.depth = 0

    def st_break(self, fs, s):
        if not fs.breaks:
            raise CompileError("break outside loop")
        fs.breaks[-1].append(self.emit(fs, OP['JMP'], 0))

    def st_if(self, fs, s):
        end_jumps = []
        clauses = s['clauses']
        for idx, (cond, block) in enumerate(clauses):
            self.compile_expr(fs, cond, 'one')
            jfalse = self.emit(fs, OP['JFALSE'], 0)
            self.compile_block(fs, block)
            if s['else'] is not None or idx < len(clauses) - 1:
                end_jumps.append(self.emit(fs, OP['JMP'], 0))
            self.patch(fs, jfalse, self.here(fs))
        if s['else'] is not None:
            self.compile_block(fs, s['else'])
        for j in end_jumps:
            self.patch(fs, j, self.here(fs))

    def st_while(self, fs, s):
        start = self.here(fs)
        self.compile_expr(fs, s['cond'], 'one')
        jexit = self.emit(fs, OP['JFALSE'], 0)
        fs.breaks.append([])
        self.compile_block(fs, s['body'])
        self.emit(fs, OP['JMP'], 0, start)
        self.patch(fs, jexit, self.here(fs))
        for j in fs.breaks.pop():
            self.patch(fs, j, self.here(fs))

    def st_repeat(self, fs, s):
        start = self.here(fs)
        fs.breaks.append([])
        saved = fs.enter()
        for st in s['body']:
            self.compile_stmt(fs, st)
        self.compile_expr(fs, s['cond'], 'one')
        self.emit(fs, OP['JFALSE'], 0, start)
        fs.leave(saved)
        for j in fs.breaks.pop():
            self.patch(fs, j, self.here(fs))

    def st_fornum(self, fs, s):
        self.compile_stmt(fs, desugar_fornum(s))

    def st_forin(self, fs, s):
        self.compile_stmt(fs, desugar_forin(s))

    # ==================================================================
    #  expressions
    # ==================================================================
    def explist_adjust(self, fs, exprs, n):
        base = fs.depth
        k = len(exprs)
        if k == 0:
            for _ in range(n):
                self.emit(fs, OP['LOADNIL'])
            return
        for i, e in enumerate(exprs):
            if i == k - 1 and _is_multi(e):
                self.compile_expr(fs, e, 'multi')
                self.emit_raw(fs, [OP['ADJUST'], base, n])
                fs.depth = base + n
                return
            self.compile_expr(fs, e, 'one')
        if k != n:
            self.emit_raw(fs, [OP['ADJUST'], base, n])
            fs.depth = base + n

    def compile_expr(self, fs, node, want):
        k = node['k']
        if k == 'nil':
            self.emit(fs, OP['LOADNIL'])
        elif k == 'true':
            self.emit(fs, OP['LOADTRUE'])
        elif k == 'false':
            self.emit(fs, OP['LOADFALSE'])
        elif k in ('number', 'string'):
            self.emit(fs, OP['LOADK'], fs.kconst(node['v']))
        elif k == 'vararg':
            if not fs.va:
                raise CompileError("'...' outside vararg function")
            if want == 'multi':
                self.emit_raw(fs, [OP['VARARG'], 0, 0])   # spread
            else:
                self.emit_raw(fs, [OP['VARARG'], 1, 0]); fs.depth += 1
        elif k == 'name':
            kind = self.resolve(fs, node['v'])
            if kind[0] == 'local':
                self.emit(fs, OP['GETLOCAL'], kind[1])
            elif kind[0] == 'upval':
                self.emit(fs, OP['GETUPVAL'], kind[1])
            else:
                self.emit(fs, OP['GETGLOBAL'], fs.kconst(node['v']))
        elif k == 'paren':
            self.compile_expr(fs, node['e'], 'one')
        elif k == 'index':
            self.compile_expr(fs, node['obj'], 'one')
            self.compile_expr(fs, node['key'], 'one')
            self.emit(fs, OP['GETINDEX'])
        elif k in ('call', 'methodcall'):
            self.compile_call(fs, node, MULTI if want == 'multi' else 1)
        elif k == 'binop':
            self.compile_binop(fs, node)
        elif k == 'unop':
            self.compile_expr(fs, node['e'], 'one')
            self.emit(fs, OP['UNOP'], UNOP[UNOP_FROM_LUA[node['op']]])
        elif k == 'table':
            self.compile_table(fs, node)
        elif k == 'function':
            self.compile_closure(fs, node)
        else:
            raise CompileError(f"unsupported expression: {k}")

    def compile_binop(self, fs, node):
        op = node['op']
        if op in ('and', 'or'):
            self.compile_expr(fs, node['l'], 'one')
            j = self.emit(fs, OP['ANDJ'] if op == 'and' else OP['ORJ'], 0)
            self.compile_expr(fs, node['r'], 'one')
            self.patch(fs, j, self.here(fs))
        else:
            self.compile_expr(fs, node['l'], 'one')
            self.compile_expr(fs, node['r'], 'one')
            self.emit(fs, OP['BINOP'], BINOP[BINOP_FROM_LUA[op]])

    def compile_call(self, fs, node, nres):
        base = fs.depth
        if node['k'] == 'call':
            self.compile_expr(fs, node['fn'], 'one')       # func @ base+1
            self.compile_args(fs, node['args'])
        else:
            self.compile_expr(fs, node['obj'], 'one')      # obj @ base+1
            self.emit(fs, OP['DUP'])
            self.emit(fs, OP['LOADK'], fs.kconst(node['method']))
            self.emit(fs, OP['GETINDEX'])                  # -> [obj, func]
            self.emit(fs, OP['SWAP'])                      # -> [func, obj]
            self.compile_args(fs, node['args'])
        funcpos = base + 1
        self.emit_raw(fs, [OP['CALL'], funcpos, nres])
        fs.depth = base + (1 if nres == 1 else 0)

    def compile_args(self, fs, args):
        k = len(args)
        for i, a in enumerate(args):
            if i == k - 1 and _is_multi(a):
                self.compile_expr(fs, a, 'multi')
            else:
                self.compile_expr(fs, a, 'one')

    def compile_table(self, fs, node):
        self.emit(fs, OP['NEWTABLE'])
        tablepos = fs.depth
        items = node['items']
        pos_index = 1
        k = len(items)
        for i, item in enumerate(items):
            if item[0] == 'key':
                self.compile_expr(fs, item[1], 'one')
                self.compile_expr(fs, item[2], 'one')
                self.emit(fs, OP['TSETKEY'])
            else:
                val = item[1]
                if i == k - 1 and _is_multi(val):
                    self.compile_expr(fs, val, 'multi')
                    self.emit_raw(fs, [OP['TAPPEND'], pos_index, tablepos])
                    fs.depth = tablepos
                else:
                    self.compile_expr(fs, val, 'one')
                    self.emit(fs, OP['TSETI'], pos_index)
                    pos_index += 1
        fs.depth = tablepos

    def compile_closure(self, fs, node):
        proto_index, upvals = self.compile_function(node, fs)
        spec = [[1 if L else 0, idx] for (L, idx) in upvals]
        self.emit_raw(fs, [OP['CLOSURE'], proto_index, spec])
        fs.depth += 1


# --------------------------------------------------------------------------
#  for-loop desugaring
# --------------------------------------------------------------------------
def _name(n):
    return {'k': 'name', 'v': n}


def _num(v):
    return {'k': 'number', 'v': v}


def _bin(op, l, r):
    return {'k': 'binop', 'op': op, 'l': l, 'r': r}


def desugar_fornum(s):
    fsv, fev, fpv = '(fs)', '(fe)', '(fp)'
    step = s['step'] if s['step'] is not None else _num(1)
    cond = _bin('or',
                _bin('and', _bin('>', _name(fpv), _num(0)),
                     _bin('<=', _name(fsv), _name(fev))),
                _bin('and', _bin('<=', _name(fpv), _num(0)),
                     _bin('>=', _name(fsv), _name(fev))))
    body = [{'k': 'local', 'names': [s['var']], 'exprs': [_name(fsv)]}]
    body += s['body']
    body += [{'k': 'assign', 'targets': [_name(fsv)],
              'exprs': [_bin('+', _name(fsv), _name(fpv))]}]
    return {'k': 'do', 'body': [
        {'k': 'local', 'names': [fsv, fev, fpv],
         'exprs': [s['start'], s['stop'], step]},
        {'k': 'while', 'cond': cond, 'body': body}]}


def desugar_forin(s):
    ff, fst, fc = '(ff)', '(fst)', '(fc)'
    names = s['names']
    body = [
        {'k': 'local', 'names': list(names),
         'exprs': [{'k': 'call', 'fn': _name(ff),
                    'args': [_name(fst), _name(fc)]}]},
        {'k': 'if', 'clauses': [(_bin('==', _name(names[0]), {'k': 'nil'}),
                                 [{'k': 'break'}])], 'else': None},
        {'k': 'assign', 'targets': [_name(fc)], 'exprs': [_name(names[0])]},
    ] + s['body']
    return {'k': 'do', 'body': [
        {'k': 'local', 'names': [ff, fst, fc], 'exprs': s['exprs']},
        {'k': 'while', 'cond': {'k': 'true'}, 'body': body}]}


def compile_source(src):
    """Parse+compile Lua source. Returns (protos, main_index).
    Raises CompileError on unsupported input."""
    try:
        chunk = parse(src)
    except ParseError as e:
        raise CompileError(f"parse: {e}")
    c = Compiler()
    main_index, _ = c.compile_function(
        {'k': 'function', 'params': [], 'vararg': True, 'body': chunk}, None)
    return c.protos, main_index

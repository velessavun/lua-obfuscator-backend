"""
Recursive-descent parser for the compiled Lua subset.
Raises ParseError on anything unsupported -> pipeline falls back to source VM.
AST nodes are plain dicts with key 'k' for kind.
"""
from lvm_lexer import tokenize, LexError


class ParseError(Exception):
    pass


# binary operator priorities (left, right) -- from Lua's lparser.c
_BINPRI = {
    'or': (1, 1), 'and': (2, 2),
    '<': (3, 3), '>': (3, 3), '<=': (3, 3), '>=': (3, 3), '~=': (3, 3), '==': (3, 3),
    '..': (9, 8),
    '+': (10, 10), '-': (10, 10),
    '*': (11, 11), '/': (11, 11), '%': (11, 11),
    '^': (14, 13),
}
_UNARY_PRI = 12
_UNOPS = {'-', 'not', '#'}


class Parser:
    def __init__(self, toks):
        self.toks = toks
        self.p = 0

    # -- token helpers ------------------------------------------------------
    def cur(self):
        return self.toks[self.p]

    def advance(self):
        t = self.toks[self.p]
        self.p += 1
        return t

    def check(self, type, value=None):
        t = self.toks[self.p]
        if t.type != type:
            return False
        return value is None or t.value == value

    def accept(self, type, value=None):
        if self.check(type, value):
            return self.advance()
        return None

    def expect(self, type, value=None):
        if not self.check(type, value):
            t = self.cur()
            raise ParseError(f"expected {type} {value!r}, got {t.type} {t.value!r} @line {t.line}")
        return self.advance()

    def is_op(self, v):
        return self.check('op', v)

    def is_kw(self, v):
        return self.check('keyword', v)

    # -- entry --------------------------------------------------------------
    def parse_chunk(self):
        body = self.block()
        if self.cur().type != 'eof':
            t = self.cur()
            raise ParseError(f"unexpected {t.type} {t.value!r} @line {t.line}")
        return body

    _BLOCK_END = {'end', 'else', 'elseif', 'until'}

    def block(self):
        stats = []
        while True:
            t = self.cur()
            if t.type == 'eof':
                break
            if t.type == 'keyword' and t.value in self._BLOCK_END:
                break
            if t.type == 'keyword' and t.value == 'return':
                stats.append(self.retstat())
                break
            s = self.statement()
            if s is not None:
                stats.append(s)
        return stats

    def retstat(self):
        self.expect('keyword', 'return')
        exprs = []
        t = self.cur()
        if not (t.type == 'eof' or (t.type == 'keyword' and t.value in self._BLOCK_END)
                or self.is_op(';')):
            exprs = self.explist()
        self.accept('op', ';')
        return {'k': 'return', 'exprs': exprs}

    # -- statements ---------------------------------------------------------
    def statement(self):
        t = self.cur()
        if self.is_op(';'):
            self.advance(); return None
        if t.type == 'keyword':
            kw = t.value
            if kw == 'break':
                self.advance(); return {'k': 'break'}
            if kw == 'do':
                self.advance(); b = self.block(); self.expect('keyword', 'end')
                return {'k': 'do', 'body': b}
            if kw == 'while':
                self.advance(); cond = self.expr(); self.expect('keyword', 'do')
                b = self.block(); self.expect('keyword', 'end')
                return {'k': 'while', 'cond': cond, 'body': b}
            if kw == 'repeat':
                self.advance(); b = self.block(); self.expect('keyword', 'until')
                cond = self.expr()
                return {'k': 'repeat', 'body': b, 'cond': cond}
            if kw == 'if':
                return self.if_stat()
            if kw == 'for':
                return self.for_stat()
            if kw == 'function':
                return self.func_stat()
            if kw == 'local':
                return self.local_stat()
            raise ParseError(f"unexpected keyword {kw} @line {t.line}")
        # exprstat: assignment or call
        return self.expr_stat()

    def if_stat(self):
        self.expect('keyword', 'if')
        clauses = []
        cond = self.expr(); self.expect('keyword', 'then')
        clauses.append((cond, self.block()))
        while self.is_kw('elseif'):
            self.advance(); c = self.expr(); self.expect('keyword', 'then')
            clauses.append((c, self.block()))
        els = None
        if self.accept('keyword', 'else'):
            els = self.block()
        self.expect('keyword', 'end')
        return {'k': 'if', 'clauses': clauses, 'else': els}

    def for_stat(self):
        self.expect('keyword', 'for')
        first = self.expect('name').value
        if self.is_op('='):
            self.advance()
            start = self.expr(); self.expect('op', ',')
            stop = self.expr()
            step = None
            if self.accept('op', ','):
                step = self.expr()
            self.expect('keyword', 'do'); b = self.block(); self.expect('keyword', 'end')
            return {'k': 'fornum', 'var': first, 'start': start, 'stop': stop,
                    'step': step, 'body': b}
        names = [first]
        while self.accept('op', ','):
            names.append(self.expect('name').value)
        self.expect('keyword', 'in')
        exprs = self.explist()
        self.expect('keyword', 'do'); b = self.block(); self.expect('keyword', 'end')
        return {'k': 'forin', 'names': names, 'exprs': exprs, 'body': b}

    def func_stat(self):
        self.expect('keyword', 'function')
        # funcname: Name {'.' Name} [':' Name]
        base = {'k': 'name', 'v': self.expect('name').value}
        is_method = False
        while self.is_op('.'):
            self.advance()
            key = self.expect('name').value
            base = {'k': 'index', 'obj': base, 'key': {'k': 'string', 'v': key}}
        if self.accept('op', ':'):
            key = self.expect('name').value
            base = {'k': 'index', 'obj': base, 'key': {'k': 'string', 'v': key}}
            is_method = True
        func = self.func_body(is_method)
        return {'k': 'assign', 'targets': [base], 'exprs': [func]}

    def local_stat(self):
        self.expect('keyword', 'local')
        if self.accept('keyword', 'function'):
            name = self.expect('name').value
            func = self.func_body(False)
            return {'k': 'localfunc', 'name': name, 'func': func}
        names = [self.expect('name').value]
        # ignore Luau type annotations if present:  local x : T
        self._skip_type()
        while self.accept('op', ','):
            names.append(self.expect('name').value)
            self._skip_type()
        exprs = []
        if self.accept('op', '='):
            exprs = self.explist()
        return {'k': 'local', 'names': names, 'exprs': exprs}

    def _skip_type(self):
        # Luau optional type annotation `: Type` -- reject to stay correct
        if self.is_op(':'):
            raise ParseError("Luau type annotations not supported by VM")

    def expr_stat(self):
        e = self.suffixed_expr()
        if self.is_op('=') or self.is_op(','):
            targets = [e]
            while self.accept('op', ','):
                targets.append(self.suffixed_expr())
            self.expect('op', '=')
            exprs = self.explist()
            for tgt in targets:
                if tgt['k'] not in ('name', 'index'):
                    raise ParseError("invalid assignment target")
            return {'k': 'assign', 'targets': targets, 'exprs': exprs}
        if e['k'] not in ('call', 'methodcall'):
            raise ParseError("syntax error: expression statement is not a call")
        return {'k': 'callstat', 'call': e}

    # -- expressions --------------------------------------------------------
    def explist(self):
        exprs = [self.expr()]
        while self.accept('op', ','):
            exprs.append(self.expr())
        return exprs

    def expr(self, limit=0):
        t = self.cur()
        if (t.type == 'op' and t.value in _UNOPS) or (t.type == 'keyword' and t.value == 'not'):
            op = self.advance().value
            operand = self.expr(_UNARY_PRI)
            node = {'k': 'unop', 'op': op, 'e': operand}
        else:
            node = self.simple_expr()
        while True:
            t = self.cur()
            op = t.value if (t.type == 'op' or (t.type == 'keyword' and t.value in ('and', 'or'))) else None
            if op is None or op not in _BINPRI:
                break
            lp, rp = _BINPRI[op]
            if lp <= limit:
                break
            self.advance()
            rhs = self.expr(rp)
            node = {'k': 'binop', 'op': op, 'l': node, 'r': rhs}
        return node

    def simple_expr(self):
        t = self.cur()
        if t.type == 'number':
            self.advance(); return {'k': 'number', 'v': t.value}
        if t.type == 'string':
            self.advance(); return {'k': 'string', 'v': t.value}
        if t.type == 'keyword':
            if t.value == 'nil':
                self.advance(); return {'k': 'nil'}
            if t.value == 'true':
                self.advance(); return {'k': 'true'}
            if t.value == 'false':
                self.advance(); return {'k': 'false'}
            if t.value == 'function':
                self.advance(); return self.func_body(False)
        if self.is_op('...'):
            self.advance(); return {'k': 'vararg'}
        if self.is_op('{'):
            return self.table_constructor()
        return self.suffixed_expr()

    def primary_expr(self):
        if self.is_op('('):
            self.advance(); e = self.expr(); self.expect('op', ')')
            return {'k': 'paren', 'e': e}
        if self.check('name'):
            return {'k': 'name', 'v': self.advance().value}
        t = self.cur()
        raise ParseError(f"unexpected {t.type} {t.value!r} @line {t.line}")

    def suffixed_expr(self):
        e = self.primary_expr()
        while True:
            if self.is_op('.'):
                self.advance()
                key = self.expect('name').value
                e = {'k': 'index', 'obj': e, 'key': {'k': 'string', 'v': key}}
            elif self.is_op('['):
                self.advance(); k = self.expr(); self.expect('op', ']')
                e = {'k': 'index', 'obj': e, 'key': k}
            elif self.is_op(':'):
                self.advance()
                method = self.expect('name').value
                args = self.call_args()
                e = {'k': 'methodcall', 'obj': e, 'method': method, 'args': args}
            elif self.is_op('(') or self.is_op('{') or self.check('string'):
                args = self.call_args()
                e = {'k': 'call', 'fn': e, 'args': args}
            else:
                break
        return e

    def call_args(self):
        if self.check('string'):
            return [{'k': 'string', 'v': self.advance().value}]
        if self.is_op('{'):
            return [self.table_constructor()]
        self.expect('op', '(')
        if self.accept('op', ')'):
            return []
        args = self.explist()
        self.expect('op', ')')
        return args

    def table_constructor(self):
        self.expect('op', '{')
        items = []
        while not self.is_op('}'):
            if self.is_op('['):
                self.advance(); k = self.expr(); self.expect('op', ']')
                self.expect('op', '='); v = self.expr()
                items.append(('key', k, v))
            elif self.check('name') and self.toks[self.p + 1].type == 'op' and self.toks[self.p + 1].value == '=':
                name = self.advance().value
                self.expect('op', '=')
                v = self.expr()
                items.append(('key', {'k': 'string', 'v': name}, v))
            else:
                items.append(('pos', self.expr()))
            if not (self.accept('op', ',') or self.accept('op', ';')):
                break
        self.expect('op', '}')
        return {'k': 'table', 'items': items}

    def func_body(self, is_method):
        self.expect('op', '(')
        params = ['self'] if is_method else []
        vararg = False
        if not self.is_op(')'):
            while True:
                if self.is_op('...'):
                    self.advance(); vararg = True; break
                params.append(self.expect('name').value)
                self._skip_type()
                if not self.accept('op', ','):
                    break
        self.expect('op', ')')
        self._skip_rettype()
        body = self.block()
        self.expect('keyword', 'end')
        return {'k': 'function', 'params': params, 'vararg': vararg, 'body': body}

    def _skip_rettype(self):
        if self.is_op(':'):
            raise ParseError("Luau return type annotations not supported by VM")


def parse(src):
    try:
        toks = tokenize(src)
    except LexError as e:
        raise ParseError(str(e))
    return Parser(toks).parse_chunk()

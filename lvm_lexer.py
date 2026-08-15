"""
Lexer for the Lua subset compiled by the custom-opcode VM.

Produces a flat token list. On anything it does not recognize it raises
LexError, which the pipeline treats as "fall back to the source VM".
"""


class LexError(Exception):
    pass


KEYWORDS = {
    'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function',
    'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then',
    'true', 'until', 'while',
}


class Tok:
    __slots__ = ('type', 'value', 'line')

    def __init__(self, type, value, line):
        self.type = type      # 'name','number','string','keyword','op','eof'
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Tok({self.type},{self.value!r})"


def _long_bracket(s, i):
    """s[i] == '['. Return (level, content_start) for [[ / [=[ ... else None."""
    if s[i] != '[':
        return None
    j = i + 1
    level = 0
    while j < len(s) and s[j] == '=':
        level += 1
        j += 1
    if j < len(s) and s[j] == '[':
        return level, j + 1
    return None


def _decode_short(inner):
    out = []
    i, n = 0, len(inner)
    ws = ' \t\r\n\f\v'
    simple = {'n': 10, 't': 9, 'r': 13, 'a': 7, 'b': 8, 'f': 12, 'v': 11,
              '\\': 92, '"': 34, "'": 39, '\n': 10, '\r': 13}
    while i < n:
        c = inner[i]
        if c == '\\':
            i += 1
            if i >= n:
                break
            e = inner[i]
            if e in simple:
                out.append(simple[e]); i += 1
            elif e == 'x':
                out.append(int(inner[i + 1:i + 3], 16) & 0xFF); i += 3
            elif e == 'z':
                i += 1
                while i < n and inner[i] in ws:
                    i += 1
            elif e.isdigit():
                num = ''
                while i < n and inner[i].isdigit() and len(num) < 3:
                    num += inner[i]; i += 1
                out.append(int(num) & 0xFF)
            else:
                out.extend(e.encode('utf-8')); i += 1
        else:
            out.extend(c.encode('utf-8')); i += 1
    return bytes(out).decode('latin-1')  # keep as byte-preserving str


# 3+char, 2char, 1char operators (longest match first)
_OPS3 = {'...'}
_OPS2 = {'==', '~=', '<=', '>=', '..', '::'}
_OPS1 = set('+-*/%^#<>=(){}[];:,.')


def tokenize(src):
    toks = []
    i, n = 0, len(src)
    line = 1
    while i < n:
        c = src[i]
        # whitespace
        if c in ' \t\r\f\v':
            i += 1; continue
        if c == '\n':
            line += 1; i += 1; continue
        # comments
        if c == '-' and i + 1 < n and src[i + 1] == '-':
            lb = _long_bracket(src, i + 2)
            if lb:
                level, cstart = lb
                close = ']' + '=' * level + ']'
                end = src.find(close, cstart)
                if end == -1:
                    raise LexError("unterminated long comment")
                line += src.count('\n', i, end)
                i = end + len(close)
            else:
                j = i
                while j < n and src[j] != '\n':
                    j += 1
                i = j
            continue
        # long string
        if c == '[':
            lb = _long_bracket(src, i)
            if lb:
                level, cstart = lb
                close = ']' + '=' * level + ']'
                end = src.find(close, cstart)
                if end == -1:
                    raise LexError("unterminated long string")
                content = src[cstart:end]
                if content.startswith('\r\n'):
                    content = content[2:]
                elif content.startswith('\n') or content.startswith('\r'):
                    content = content[1:]
                line += src.count('\n', i, end)
                toks.append(Tok('string', content, line))
                i = end + len(close)
                continue
        # short string
        if c == '"' or c == "'":
            j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2; continue
                if src[j] == c or src[j] == '\n':
                    break
                j += 1
            if j >= n or src[j] != c:
                raise LexError("unterminated string")
            toks.append(Tok('string', _decode_short(src[i + 1:j]), line))
            i = j + 1
            continue
        # number
        if c.isdigit() or (c == '.' and i + 1 < n and src[i + 1].isdigit()):
            j = i
            if c == '0' and i + 1 < n and src[i + 1] in 'xX':
                j = i + 2
                while j < n and (src[j] in '0123456789abcdefABCDEF.pP' or
                                 (src[j] in '+-' and src[j - 1] in 'pP')):
                    j += 1
                text = src[i:j]
                val = float.fromhex(text) if ('.' in text or 'p' in text.lower()) else int(text, 16)
            else:
                while j < n and (src[j].isdigit() or src[j] in '.eE' or
                                 (src[j] in '+-' and src[j - 1] in 'eE')):
                    j += 1
                text = src[i:j]
                val = float(text) if ('.' in text or 'e' in text.lower()) else int(text)
            toks.append(Tok('number', val, line))
            i = j
            continue
        # name / keyword
        if c.isalpha() or c == '_':
            j = i
            while j < n and (src[j].isalnum() or src[j] == '_'):
                j += 1
            word = src[i:j]
            if word in KEYWORDS:
                toks.append(Tok('keyword', word, line))
            else:
                toks.append(Tok('name', word, line))
            i = j
            continue
        # operators (longest first)
        three = src[i:i + 3]
        if three in _OPS3:
            toks.append(Tok('op', three, line)); i += 3; continue
        two = src[i:i + 2]
        if two in _OPS2:
            toks.append(Tok('op', two, line)); i += 2; continue
        if c in _OPS1:
            toks.append(Tok('op', c, line)); i += 1; continue
        # anything else (compound assignment +=, //, &, |, goto ::, etc.)
        raise LexError(f"unsupported character/token near line {line}: {c!r}")

    toks.append(Tok('eof', None, line))
    return toks

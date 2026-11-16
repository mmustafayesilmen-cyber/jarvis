"""Güvenli matematik ifadesi çözümleyicisi (eval/exec kullanılmaz): yalnızca sayı, x/y/t değişkenleri, + - * / ^ ve beyaz listedeki işlevler.
Türkçe konuşma metnini ('x kare eksi beş x artı altı') ifadeye de çevirir. Aynı sözdizimini ui/scene_sci.html'deki çözümleyici de kullanır."""
import math
import re

FUNCS = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos, "atan": math.atan, "sqrt": math.sqrt, "abs": abs,
         "ln": math.log, "log": math.log10, "exp": math.exp, "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh, "floor": math.floor, "ceil": math.ceil}
CONSTS = {"pi": math.pi, "e": math.e}
VARS = ("x", "y")
MAX_LEN = 200
MAX_POW = 1e6


class MathErr(ValueError):
    pass


_TOK = re.compile(r"\s*(?:(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|([a-zA-Z_]+)|(.))")


def tokenize(s: str):
    if len(s) > MAX_LEN:
        raise MathErr("ifade çok uzun")
    out = []
    for m in _TOK.finditer(s):
        num, name, op = m.groups()
        if num is not None:
            out.append(("n", float(num)))
        elif name is not None:
            out.append(("i", name))
        elif op is not None and not op.isspace():
            if op not in "+-*/^()":
                raise MathErr(f"geçersiz karakter: {op}")
            out.append(("o", op))
    return out


def _split_ident(name: str):
    """'xy' -> x*y, '3x' zaten sayı+ad; 'sinx' -> sin x, 'pix' -> pi*x gibi birleşik adları böler."""
    if name in FUNCS or name in CONSTS or name in VARS:
        return [name]
    for f in sorted(FUNCS, key=len, reverse=True):
        if name.startswith(f) and len(name) > len(f):
            return [f] + _split_ident(name[len(f):])
    if name.startswith("pi") and len(name) > 2:
        return ["pi"] + _split_ident(name[2:])
    if len(name) > 1 and all(c in "xye" for c in name):
        return list(name)
    raise MathErr(f"bilinmeyen ad: {name}")


class Parser:
    def __init__(self, s: str):
        raw = tokenize(s)
        toks = []
        for k, v in raw:
            if k == "i":
                for part in _split_ident(v):
                    toks.append(("i", part))
            else:
                toks.append((k, v))
        # örtük çarpma: 2x, 2(x+1), )(, x(, )x, pi x
        fixed = []
        for i, t in enumerate(toks):
            if fixed:
                p = fixed[-1]
                left = p[0] in "ni" and not (p[0] == "i" and p[1] in FUNCS) or p == ("o", ")")
                right = t[0] in "ni" or t == ("o", "(")
                if left and right:
                    fixed.append(("o", "I"))               # örtük çarpma
            fixed.append(t)
        self.t = fixed
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def eat(self, v=None):
        k, x = self.peek()
        if v is not None and x != v:
            raise MathErr(f"{v} bekleniyordu")
        self.i += 1
        return k, x

    def parse(self):
        if not self.t:
            raise MathErr("boş ifade")
        n = self.expr()
        if self.i != len(self.t):
            raise MathErr("ifade tamamlanamadı")
        return n

    def expr(self):
        n = self.term()
        while self.peek()[1] in ("+", "-") and self.peek()[0] == "o":
            op = self.eat()[1]
            n = (op, n, self.term())
        return n

    def term(self):
        n = self.unary()
        while self.peek()[1] in ("*", "/", "I") and self.peek()[0] == "o":
            op = self.eat()[1]
            n = ("*" if op == "I" else op, n, self.unary())
        return n

    def unary(self):
        if self.peek() == ("o", "-"):
            self.eat()
            return ("neg", self.unary())
        if self.peek() == ("o", "+"):
            self.eat()
            return self.unary()
        return self.power()

    def power(self):
        b = self.atom()
        if self.peek() == ("o", "^"):
            self.eat()
            return ("^", b, self.unary())
        return b

    def atom(self):
        k, v = self.eat()
        if k == "n":
            return ("num", v)
        if k == "i":
            if v in FUNCS:
                if self.peek() == ("o", "("):
                    self.eat()
                    a = self.expr()
                    self.eat(")")
                    return ("f", v, a)
                a = self.power()                          # sin x, sqrt 16, sin 2x
                while self.peek() == ("o", "I") and self.i + 1 < len(self.t) and (self.t[self.i + 1][0] == "n" or self.t[self.i + 1][1] in VARS):
                    self.eat()
                    a = ("*", a, self.power())
                return ("f", v, a)
            if v in CONSTS and v not in VARS:
                return ("num", CONSTS[v])
            return ("var", v)
        if (k, v) == ("o", "("):
            n = self.expr()
            self.eat(")")
            return n
        raise MathErr("beklenmeyen simge")


def parse(s: str):
    return Parser(s).parse()


def ev(n, env=None):
    env = env or {}
    k = n[0]
    if k == "num":
        return n[1]
    if k == "var":
        if n[1] not in env:
            raise MathErr(f"{n[1]} değeri yok")
        return env[n[1]]
    if k == "neg":
        return -ev(n[1], env)
    if k == "f":
        return FUNCS[n[1]](ev(n[2], env))
    a, b = ev(n[1], env), ev(n[2], env)
    if k == "+":
        return a + b
    if k == "-":
        return a - b
    if k == "*":
        return a * b
    if k == "/":
        return a / b
    if k == "^":
        if abs(b) > 400 or abs(a) > MAX_POW:
            raise MathErr("üs çok büyük")
        return a ** b
    raise MathErr("bilinmeyen işlem")


def evaluate(s: str, env=None):
    try:
        return ev(parse(s), env)
    except (ZeroDivisionError, OverflowError, ValueError) as e:
        if isinstance(e, MathErr):
            raise
        raise MathErr("hesaplanamadı")


def f_of(s: str):
    """x'in işlevi olarak çağrılabilir; hesaplanamayan noktalarda nan."""
    ast = parse(s)

    def f(x, y=0.0):
        try:
            v = ev(ast, {"x": x, "y": y})
            return v.real if isinstance(v, complex) else float(v)
        except Exception:
            return float("nan")
    return f


# ---------------------------------------------------------------- konuşma -> ifade
_ONES = {"sıfır": 0, "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9}
_TENS = {"on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50, "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90}
_WORDS = [
    (r"\bmutlak değer(?:i)?\b", " abs "), (r"\bkare ?kök(?:ü)?\b", " sqrt "), (r"\bkök\b", " sqrt "), (r"\bdoğal logaritma\b", " ln "),
    (r"\blogaritma\b", " log "), (r"\bsinüs\b", " sin "), (r"\bkosinüs\b", " cos "), (r"\btanjant\b", " tan "),
    (r"\bkare\b", " ^2 "), (r"\bküp\b", " ^3 "), (r"\b(?:üzeri|üssü|üstü)\b", " ^ "),
    (r"\bartı\b", " + "), (r"\beksi\b", " - "), (r"\bçarpı\b", " * "), (r"\bbölü\b", " / "), (r"\bparantez aç\b", " ( "), (r"\bparantez kapa\w*\b", " ) "),
    (r"\b(?:eşittir|eşit)\b", " = "), (r"\bpi sayısı\b", " pi "),
]


def _numwords(t: str) -> str:
    """Yazıyla sayıları rakama çevirir: 'yüz kırk dört' -> 144, 'iki bin beş' -> 2005 (sıfır hariç tek başına 'on' vb. de sayı sayılır)."""
    toks = t.split()
    out, i = [], 0
    while i < len(toks):
        w = toks[i]
        if w in _ONES or w in _TENS or w in ("yüz", "bin"):
            total = cur = 0
            used = False
            while i < len(toks) and (toks[i] in _ONES or toks[i] in _TENS or toks[i] in ("yüz", "bin")):
                w = toks[i]
                if w in _ONES:
                    cur += _ONES[w]
                elif w in _TENS:
                    cur += _TENS[w]
                elif w == "yüz":
                    cur = (cur or 1) * 100 if cur < 100 else cur * 100
                else:
                    total += (cur or 1) * 1000
                    cur = 0
                used = True
                i += 1
            out.append(str(total + cur) if used else "")
            continue
        out.append(w)
        i += 1
    return " ".join(out)


def speech_to_expr(text: str) -> str:
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = t.replace("²", "^2").replace("³", "^3").replace("×", "*").replace("÷", "/").replace("−", "-").replace("√", " sqrt ").replace("π", " pi ")
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    t = _numwords(t)
    for pat, rep in _WORDS:
        t = re.sub(pat, rep, t)
    t = re.sub(r"[a-z]*[çğıöşü][a-zçğıöşü]*", " ", t)          # tanınmayan Türkçe sözcükleri at (kare, kök vb. yukarıda çevrildi)
    t = re.sub(r"[^0-9a-z+\-*/^().= ]", " ", t)
    keep = []
    for tok in t.split():                                      # tanınmayan düz harfli sözcükleri de at (ve, ile, olan ...)
        if re.fullmatch(r"[a-z]+", tok):
            try:
                _split_ident(tok)
            except MathErr:
                continue
        keep.append(tok)
    t = " ".join(keep)
    t = re.sub(r"\s*\^\s*", "^", t)
    return " ".join(t.split())

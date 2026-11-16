"""Satranç kuralları ve basit motor (dış paket yok). Tahta: 64 kare, a1=0 … h8=63; taşlar 'PNBRQK' beyaz, 'pnbrqk' siyah, boş '.'.
Kurallar tam: rok, geçerken alma, terfi, şah çekme, mat, pat, 50 hamle, üç kez tekrar, yetersiz taş. Doğruluk perft sayılarıyla test edilir.
Motor: negamax + alfa-beta + yakalama araması (quiescence), taş-kare tabloları; seviye = arama derinliği + zaman sınırı."""
import random
import time

FILES = "abcdefgh"
VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}
TR = {"P": "Piyon", "N": "At", "B": "Fil", "R": "Kale", "Q": "Vezir", "K": "Şah"}
TR_LETTER = {"P": "", "N": "A", "B": "F", "R": "K", "Q": "V", "K": "Ş"}       # Türkçe cebirsel gösterim (Af3, Vxd5)
START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
N_OFF = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
K_OFF = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
B_DIR = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
R_DIR = [(1, 0), (-1, 0), (0, 1), (0, -1)]
# taş-kare tabloları (beyaz açısından, a1..h8 sırasıyla; siyah için ayna)
_PST_RAW = {
    "P": [0, 0, 0, 0, 0, 0, 0, 0, 5, 10, 10, -20, -20, 10, 10, 5, 5, -5, -10, 0, 0, -10, -5, 5, 0, 0, 0, 20, 20, 0, 0, 0,
          5, 5, 10, 25, 25, 10, 5, 5, 10, 10, 20, 30, 30, 20, 10, 10, 50, 50, 50, 50, 50, 50, 50, 50, 0, 0, 0, 0, 0, 0, 0, 0],
    "N": [-50, -40, -30, -30, -30, -30, -40, -50, -40, -20, 0, 5, 5, 0, -20, -40, -30, 5, 10, 15, 15, 10, 5, -30, -30, 0, 15, 20, 20, 15, 0, -30,
          -30, 5, 15, 20, 20, 15, 5, -30, -30, 0, 10, 15, 15, 10, 0, -30, -40, -20, 0, 0, 0, 0, -20, -40, -50, -40, -30, -30, -30, -30, -40, -50],
    "B": [-20, -10, -10, -10, -10, -10, -10, -20, -10, 5, 0, 0, 0, 0, 5, -10, -10, 10, 10, 10, 10, 10, 10, -10, -10, 0, 10, 10, 10, 10, 0, -10,
          -10, 5, 5, 10, 10, 5, 5, -10, -10, 0, 5, 10, 10, 5, 0, -10, -10, 0, 0, 0, 0, 0, 0, -10, -20, -10, -10, -10, -10, -10, -10, -20],
    "R": [0, 0, 0, 5, 5, 0, 0, 0, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5, -5, 0, 0, 0, 0, 0, 0, -5, 5, 10, 10, 10, 10, 10, 10, 5, 0, 0, 0, 0, 0, 0, 0, 0],
    "Q": [-20, -10, -10, -5, -5, -10, -10, -20, -10, 0, 5, 0, 0, 0, 0, -10, -10, 5, 5, 5, 5, 5, 0, -10, 0, 0, 5, 5, 5, 5, 0, -5,
          -5, 0, 5, 5, 5, 5, 0, -5, -10, 0, 5, 5, 5, 5, 0, -10, -10, 0, 0, 0, 0, 0, 0, -10, -20, -10, -10, -5, -5, -10, -10, -20],
    "K": [20, 30, 10, 0, 0, 10, 30, 20, 20, 20, 0, 0, 0, 0, 20, 20, -10, -20, -20, -20, -20, -20, -20, -10, -20, -30, -30, -40, -40, -30, -30, -20,
          -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30, -30, -40, -40, -50, -50, -40, -40, -30],
    "KE": [-50, -30, -30, -30, -30, -30, -30, -50, -30, -30, 0, 0, 0, 0, -30, -30, -30, -10, 20, 30, 30, 20, -10, -30, -30, -10, 30, 40, 40, 30, -10, -30,
           -30, -10, 30, 40, 40, 30, -10, -30, -30, -10, 20, 30, 30, 20, -10, -30, -30, -20, -10, 0, 0, -10, -20, -30, -50, -40, -30, -20, -20, -30, -40, -50]}


def sq(name: str) -> int:
    return FILES.index(name[0]) + 8 * (int(name[1]) - 1)


def name(s: int) -> str:
    return FILES[s % 8] + str(s // 8 + 1)


def white(p: str) -> bool:
    return p.isupper()


class Board:
    def __init__(self, fen: str = START):
        b, side, cas, ep, hm, fm = (fen.split() + ["0", "1"])[:6]
        self.sq = ["."] * 64
        for r, row in enumerate(b.split("/")):
            f = 0
            for ch in row:
                if ch.isdigit():
                    f += int(ch)
                else:
                    self.sq[(7 - r) * 8 + f] = ch
                    f += 1
        self.white = side == "w"
        self.castle = "" if cas == "-" else cas
        self.ep = None if ep == "-" else sq(ep)
        self.half = int(hm)
        self.full = int(fm)
        self.hist = [self.key()]

    def copy(self):
        b = Board.__new__(Board)
        b.sq, b.white, b.castle, b.ep, b.half, b.full, b.hist = self.sq[:], self.white, self.castle, self.ep, self.half, self.full, self.hist[:]
        return b

    def key(self) -> str:
        return "".join(self.sq) + ("w" if self.white else "b") + self.castle + (str(self.ep) if self.ep is not None else "-")

    def fen(self) -> str:
        rows = []
        for r in range(7, -1, -1):
            row, e = "", 0
            for f in range(8):
                p = self.sq[r * 8 + f]
                if p == ".":
                    e += 1
                else:
                    row += (str(e) if e else "") + p
                    e = 0
            rows.append(row + (str(e) if e else ""))
        return f"{'/'.join(rows)} {'w' if self.white else 'b'} {self.castle or '-'} {name(self.ep) if self.ep is not None else '-'} {self.half} {self.full}"

    # ---------------------------------------------------------------- saldırı ve hamle üretimi
    def attacked(self, s: int, by_white: bool) -> bool:
        f, r = s % 8, s // 8
        pr = r - 1 if by_white else r + 1          # saldıran piyonun bulunduğu sıra
        if 0 <= pr < 8:
            for df in (-1, 1):
                if 0 <= f + df < 8 and self.sq[pr * 8 + f + df] == ("P" if by_white else "p"):
                    return True
        n, k = ("N", "K") if by_white else ("n", "k")
        for df, dr in N_OFF:
            if 0 <= f + df < 8 and 0 <= r + dr < 8 and self.sq[(r + dr) * 8 + f + df] == n:
                return True
        for df, dr in K_OFF:
            if 0 <= f + df < 8 and 0 <= r + dr < 8 and self.sq[(r + dr) * 8 + f + df] == k:
                return True
        bq, rq = (("B", "Q"), ("R", "Q")) if by_white else (("b", "q"), ("r", "q"))
        for dirs, pcs in ((B_DIR, bq), (R_DIR, rq)):
            for df, dr in dirs:
                ff, rr = f + df, r + dr
                while 0 <= ff < 8 and 0 <= rr < 8:
                    p = self.sq[rr * 8 + ff]
                    if p != ".":
                        if p in pcs:
                            return True
                        break
                    ff += df
                    rr += dr
        return False

    def king(self, w: bool) -> int:
        return self.sq.index("K" if w else "k")

    def in_check(self, w=None) -> bool:
        w = self.white if w is None else w
        return self.attacked(self.king(w), not w)

    def pseudo(self):
        out, w, S = [], self.white, self.sq
        for s in range(64):
            p = S[s]
            if p == "." or white(p) != w:
                continue
            f, r, t = s % 8, s // 8, p.upper()
            if t == "P":
                d, start, last = (1, 1, 7) if w else (-1, 6, 0)
                to = s + 8 * d
                if 0 <= to < 64 and S[to] == ".":
                    if to // 8 == last:
                        out += [(s, to, q) for q in "QRBN"]
                    else:
                        out.append((s, to, None))
                        if r == start and S[to + 8 * d] == ".":
                            out.append((s, to + 8 * d, None))
                for df in (-1, 1):
                    if 0 <= f + df < 8:
                        to = s + 8 * d + df
                        if 0 <= to < 64 and ((S[to] != "." and white(S[to]) != w) or to == self.ep):
                            if to // 8 == last:
                                out += [(s, to, q) for q in "QRBN"]
                            else:
                                out.append((s, to, None))
            elif t in "NK":
                for df, dr in (N_OFF if t == "N" else K_OFF):
                    if 0 <= f + df < 8 and 0 <= r + dr < 8:
                        to = (r + dr) * 8 + f + df
                        if S[to] == "." or white(S[to]) != w:
                            out.append((s, to, None))
                if t == "K":
                    rights = ("K", "Q") if w else ("k", "q")
                    home = 4 if w else 60
                    if s == home and not self.attacked(s, not w):
                        if rights[0] in self.castle and S[s + 1] == S[s + 2] == "." and not self.attacked(s + 1, not w) and not self.attacked(s + 2, not w):
                            out.append((s, s + 2, None))
                        if rights[1] in self.castle and S[s - 1] == S[s - 2] == S[s - 3] == "." and not self.attacked(s - 1, not w) and not self.attacked(s - 2, not w):
                            out.append((s, s - 2, None))
            else:
                dirs = B_DIR if t == "B" else R_DIR if t == "R" else B_DIR + R_DIR
                for df, dr in dirs:
                    ff, rr = f + df, r + dr
                    while 0 <= ff < 8 and 0 <= rr < 8:
                        to = rr * 8 + ff
                        if S[to] == ".":
                            out.append((s, to, None))
                        else:
                            if white(S[to]) != w:
                                out.append((s, to, None))
                            break
                        ff += df
                        rr += dr
        return out

    def push(self, m):
        """Hamleyi uygular (yasal olduğu varsayılır)."""
        a, b, promo = m
        S, w = self.sq, self.white
        p = S[a]
        cap = S[b] != "."
        if p.upper() == "P" and b == self.ep and not cap:                     # geçerken alma
            S[b - 8 if w else b + 8] = "."
            cap = True
        if p.upper() == "K" and abs(b - a) == 2:                              # rok: kaleyi de taşı
            if b > a:
                S[a + 1], S[a + 3] = S[a + 3], "."
            else:
                S[a - 1], S[a - 4] = S[a - 4], "."
        S[b] = (promo if w else promo.lower()) if promo else p
        S[a] = "."
        self.ep = (a + b) // 2 if p.upper() == "P" and abs(b - a) == 16 else None
        rm = {4: "KQ", 60: "kq", 0: "Q", 7: "K", 56: "q", 63: "k"}
        for s in (a, b):
            for c in rm.get(s, ""):
                self.castle = self.castle.replace(c, "")
        self.half = 0 if (cap or p.upper() == "P") else self.half + 1
        if not w:
            self.full += 1
        self.white = not w
        self.hist.append(self.key())

    def legal(self):
        out = []
        for m in self.pseudo():
            b = self.copy()
            b.push(m)
            if not b.in_check(self.white):
                out.append(m)
        return out

    # ---------------------------------------------------------------- oyun sonu
    def insufficient(self) -> bool:
        rest = [p for p in self.sq if p not in ".Kk"]
        if not rest:
            return True
        if len(rest) == 1 and rest[0].upper() in "NB":
            return True
        if all(p.upper() == "B" for p in rest):
            colors = {(s % 8 + s // 8) % 2 for s in range(64) if self.sq[s].upper() == "B"}
            return len(colors) == 1
        return False

    def result(self, moves=None):
        """(sonuç, neden) ya da None. sonuç: '1-0', '0-1', '1/2-1/2'."""
        moves = self.legal() if moves is None else moves
        if not moves:
            if self.in_check():
                return ("0-1" if self.white else "1-0"), "mat"
            return "1/2-1/2", "pat"
        if self.half >= 100:
            return "1/2-1/2", "50 hamle kuralı"
        if self.hist.count(self.hist[-1]) >= 3:
            return "1/2-1/2", "üç kez tekrar"
        if self.insufficient():
            return "1/2-1/2", "yetersiz taş"
        return None

    # ---------------------------------------------------------------- gösterim
    def san(self, m, legal=None, tr: bool = True) -> str:
        """Cebirsel gösterim. tr=True: Türkçe harfler (A, F, K, V, Ş)."""
        a, b, promo = m
        p = self.sq[a].upper()
        L = TR_LETTER if tr else {"P": "", "N": "N", "B": "B", "R": "R", "Q": "Q", "K": "K"}
        if p == "K" and abs(b - a) == 2:
            s = "O-O" if b > a else "O-O-O"
        else:
            cap = self.sq[b] != "." or (p == "P" and b == self.ep)
            s = L[p]
            if p != "P":
                legal = legal if legal is not None else self.legal()
                same = [x for x in legal if x[1] == b and x[0] != a and self.sq[x[0]].upper() == p]
                if same:
                    if all(x[0] % 8 != a % 8 for x in same):
                        s += FILES[a % 8]
                    elif all(x[0] // 8 != a // 8 for x in same):
                        s += str(a // 8 + 1)
                    else:
                        s += name(a)
            elif cap:
                s += FILES[a % 8]
            s += ("x" if cap else "") + name(b)
            if promo:
                s += "=" + L[promo]
        nb = self.copy()
        nb.push(m)
        if nb.in_check():
            s += "#" if not nb.legal() else "+"
        return s

    def describe(self, m) -> str:
        """Sesli anlatım: 'At f3', 'Fil c4 alır', 'kısa rok', 'piyon e8, vezir olur'."""
        a, b, promo = m
        p = self.sq[a].upper()
        if p == "K" and abs(b - a) == 2:
            s = "kısa rok" if b > a else "uzun rok"
        else:
            cap = self.sq[b] != "." or (p == "P" and b == self.ep)
            s = f"{TR[p]} {name(b)}" + (f", {TR[self.sq[b].upper()].lower() if self.sq[b] != '.' else 'piyon'} alır" if cap else "")
            if promo:
                s += f", {TR[promo].lower()} olur"
        nb = self.copy()
        nb.push(m)
        if nb.in_check():
            s += ", mat" if not nb.legal() else ", şah"
        return s


# -------------------------------------------------------------------- değerlendirme ve arama
def evaluate(b: Board) -> int:
    """Hamle sırası olan taraf açısından santipiyon."""
    mat_q = sum(1 for p in b.sq if p in "Qq")
    minors = sum(1 for p in b.sq if p.upper() in "NBR")
    endgame = mat_q == 0 or (mat_q <= 2 and minors <= 2)
    sc = 0
    for s, p in enumerate(b.sq):
        if p == ".":
            continue
        t = p.upper()
        tbl = _PST_RAW["KE" if (t == "K" and endgame) else t]
        if white(p):
            sc += VAL[t] + tbl[s]
        else:
            sc -= VAL[t] + tbl[(7 - s // 8) * 8 + s % 8]
    return sc if b.white else -sc


def _order(b: Board, moves):
    def k(m):
        v = b.sq[m[1]]
        return -(VAL[v.upper()] * 10 - VAL[b.sq[m[0]].upper()] if v != "." else 0) - (900 if m[2] == "Q" else 0)
    return sorted(moves, key=k)


class _Timeout(Exception):
    pass


def _qs(b: Board, alpha, beta, ctx, depth=0):
    ctx["n"] += 1
    if ctx["n"] & 1023 == 0 and time.time() > ctx["deadline"]:
        raise _Timeout
    stand = evaluate(b)
    if stand >= beta:
        return beta
    alpha = max(alpha, stand)
    if depth > 4:
        return alpha
    caps = [m for m in b.pseudo() if b.sq[m[1]] != "." or m[2]]
    for m in _order(b, caps):
        nb = b.copy()
        nb.push(m)
        if nb.in_check(b.white):
            continue
        sc = -_qs(nb, -beta, -alpha, ctx, depth + 1)
        if sc >= beta:
            return beta
        alpha = max(alpha, sc)
    return alpha


def _search(b: Board, depth, alpha, beta, ctx, ply=0):
    ctx["n"] += 1
    if ctx["n"] & 1023 == 0 and time.time() > ctx["deadline"]:
        raise _Timeout
    if ply and (b.half >= 100 or b.hist.count(b.hist[-1]) >= 2):
        return 0
    moves = b.legal()
    if not moves:
        return -100000 + ply if b.in_check() else 0
    if depth <= 0:
        return _qs(b, alpha, beta, ctx)
    best = -10 ** 9
    pv = ctx.get("pv") if ply == 0 else None
    ordered = _order(b, moves)
    if pv in ordered:
        ordered.remove(pv)
        ordered.insert(0, pv)
    for m in ordered:
        nb = b.copy()
        nb.push(m)
        sc = -_search(nb, depth - 1, -beta, -alpha, ctx, ply + 1)
        if sc > best:
            best = sc
            if ply == 0:
                ctx["best"] = m
        alpha = max(alpha, sc)
        if alpha >= beta:
            break
    return best


LEVELS = {1: (1, 0.6, 120), 2: (2, 1.5, 50), 3: (3, 3.0, 15), 4: (4, 6.0, 0), 5: (5, 10.0, 0)}   # (derinlik, saniye, rastgelelik cp)


def best_move(b: Board, level: int = 3):
    """(hamle, puan) — puan hamle sırası olan taraf açısından santipiyon. Seviye 1-2 bilerek hata yapabilir."""
    depth, secs, noise = LEVELS.get(level, LEVELS[3])
    moves = b.legal()
    if not moves:
        return None, 0
    ctx = {"n": 0, "deadline": time.time() + secs, "best": None, "pv": None}
    if noise and len(moves) > 1:
        # düşük seviye: her hamle aynı derinlikte puanlanır, en iyiye 'noise' kadar yakın olanlar arasından rastgele seçilir (mat varsa hep mat)
        scored = []
        try:
            for m in _order(b, moves):
                nb = b.copy()
                nb.push(m)
                scored.append((-_search(nb, depth - 1, -10 ** 9, 10 ** 9, ctx, 1), m))
        except _Timeout:
            pass
        if scored:
            top = max(s for s, _ in scored)
            if top > 90000:
                return next(m for s, m in scored if s == top), top
            pool = [(s, m) for s, m in scored if s >= top - noise]
            s, m = random.choice(pool)
            return m, s
    best, score = moves[0], 0
    try:
        for d in range(1, depth + 1):
            sc = _search(b, d, -10 ** 9, 10 ** 9, ctx)
            best, score = ctx["best"], sc
            ctx["pv"] = best
    except _Timeout:
        if ctx["best"]:
            best = ctx["best"]
    return best, score


def analyse(b: Board, depth: int = 3, secs: float = 2.0):
    """Rastgelelik olmadan en iyi hamle ve puan (koç ve ipucu için). Süre dolarsa o ana kadarki en iyi."""
    moves = b.legal()
    if not moves:
        return None, 0
    ctx = {"n": 0, "deadline": time.time() + secs, "best": None, "pv": None}
    best, score = moves[0], evaluate(b)
    try:
        for d in range(1, depth + 1):
            sc = _search(b, d, -10 ** 9, 10 ** 9, ctx)
            best, score = ctx["best"], sc
            ctx["pv"] = best
    except _Timeout:
        pass
    return best, score


def perft(b: Board, depth: int) -> int:
    if depth == 0:
        return 1
    n = 0
    for m in b.legal():
        nb = b.copy()
        nb.push(m)
        n += perft(nb, depth - 1)
    return n

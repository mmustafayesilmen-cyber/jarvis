"""Basit gök mekaniği: Güneş, Ay ve gezegenlerin (Merkür-Satürn) yaklaşık konumları (Schlyter yöntemi, ~0,5° doğruluk), yıldız zamanı, ufuk koordinatları.
Ekranda görsel amaçlıdır; gözlem planlaması için değil. Dışarıya hiçbir şey gönderilmez."""
import datetime as dt
import math

D2R = math.pi / 180.0


def jd(t: dt.datetime) -> float:
    """Julian günü (UTC)."""
    if t.tzinfo is not None:
        t = t.astimezone(dt.timezone.utc).replace(tzinfo=None)
    y, m = t.year, t.month
    d = t.day + (t.hour + (t.minute + t.second / 60) / 60) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def gmst(jdv: float) -> float:
    """Greenwich ortalama yıldız zamanı (derece)."""
    d = jdv - 2451545.0
    return (280.46061837 + 360.98564736629 * d) % 360


def lst(jdv: float, lon: float) -> float:
    return (gmst(jdv) + lon) % 360


def radec_to_altaz(ra_deg: float, dec_deg: float, lat: float, lst_deg: float):
    """(yükseklik, azimut) derece; azimut kuzeyden doğuya doğru ölçülür."""
    h = (lst_deg - ra_deg) * D2R
    dec, la = dec_deg * D2R, lat * D2R
    sa = math.sin(dec) * math.sin(la) + math.cos(dec) * math.cos(la) * math.cos(h)
    alt = math.asin(max(-1, min(1, sa)))
    y = -math.sin(h) * math.cos(dec)
    x = math.sin(dec) * math.cos(la) - math.cos(dec) * math.sin(la) * math.cos(h)
    az = math.atan2(y, x)
    return alt / D2R, (az / D2R) % 360


def _kepler(M: float, e: float) -> float:
    E = M + e * math.sin(M) * (1 + e * math.cos(M))
    for _ in range(30):
        dE = (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-9:
            break
    return E


# gezegen elemanları (d = gün, 2000 Ocak 0): N, i, w, a, e, M  (derece / AB)
_EL = {
    "Merkür": lambda d: (48.3313 + 3.24587e-5 * d, 7.0047 + 5.0e-8 * d, 29.1241 + 1.01444e-5 * d, 0.387098, 0.205635 + 5.59e-10 * d, 168.6562 + 4.0923344368 * d),
    "Venüs": lambda d: (76.6799 + 2.46590e-5 * d, 3.3946 + 2.75e-8 * d, 54.8910 + 1.38374e-5 * d, 0.723330, 0.006773 - 1.302e-9 * d, 48.0052 + 1.6021302244 * d),
    "Mars": lambda d: (49.5574 + 2.11081e-5 * d, 1.8497 - 1.78e-8 * d, 286.5016 + 2.92961e-5 * d, 1.523688, 0.093405 + 2.516e-9 * d, 18.6021 + 0.5240207766 * d),
    "Jüpiter": lambda d: (100.4542 + 2.76854e-5 * d, 1.3030 - 1.557e-7 * d, 273.8777 + 1.64505e-5 * d, 5.20256, 0.048498 + 4.469e-9 * d, 19.8950 + 0.0830853001 * d),
    "Satürn": lambda d: (113.6634 + 2.38980e-5 * d, 2.4886 - 1.081e-7 * d, 339.3939 + 2.97661e-5 * d, 9.55475, 0.055546 - 9.499e-9 * d, 316.9670 + 0.0334442282 * d),
}
MAG = {"Merkür": 0.0, "Venüs": -4.2, "Mars": 0.5, "Jüpiter": -2.2, "Satürn": 0.6}


def _helio(el):
    N, i, w, a, e, M = el
    M = (M % 360) * D2R
    E = _kepler(M, e)
    xv, yv = a * (math.cos(E) - e), a * math.sqrt(1 - e * e) * math.sin(E)
    v = math.atan2(yv, xv)
    r = math.hypot(xv, yv)
    N, i, w = N * D2R, i * D2R, w * D2R
    u = v + w
    return (r * (math.cos(N) * math.cos(u) - math.sin(N) * math.sin(u) * math.cos(i)),
            r * (math.sin(N) * math.cos(u) + math.cos(N) * math.sin(u) * math.cos(i)),
            r * math.sin(u) * math.sin(i))


def sun_ecl(d: float):
    """Güneş'in ekliptik boylamı (rad) ve uzaklığı (AB); Dünya'nın Güneş'e göre konumu bunun tersidir."""
    w = 282.9404 + 4.70935e-5 * d
    e = 0.016709 - 1.151e-9 * d
    M = (356.0470 + 0.9856002585 * d) % 360 * D2R
    E = _kepler(M, e)
    xv, yv = math.cos(E) - e, math.sqrt(1 - e * e) * math.sin(E)
    v = math.atan2(yv, xv)
    r = math.hypot(xv, yv)
    return (v + w * D2R) % (2 * math.pi), r


def _ecl_to_eq(x, y, z, d):
    ecl = (23.4393 - 3.563e-7 * d) * D2R
    xe, ye, ze = x, y * math.cos(ecl) - z * math.sin(ecl), y * math.sin(ecl) + z * math.cos(ecl)
    return (math.atan2(ye, xe) / D2R) % 360, math.atan2(ze, math.hypot(xe, ye)) / D2R


def sun(jdv: float):
    d = jdv - 2451543.5
    lon, r = sun_ecl(d)
    ra, dec = _ecl_to_eq(r * math.cos(lon), r * math.sin(lon), 0.0, d)
    return {"name": "Güneş", "ra": ra, "dec": dec, "mag": -26.7, "r": r}


def planets(jdv: float):
    d = jdv - 2451543.5
    slon, sr = sun_ecl(d)
    xs, ys = sr * math.cos(slon), sr * math.sin(slon)           # Dünya = −Güneş
    out = []
    for name, f in _EL.items():
        x, y, z = _helio(f(d))
        gx, gy, gz = x + xs, y + ys, z
        ra, dec = _ecl_to_eq(gx, gy, gz, d)
        out.append({"name": name, "ra": ra, "dec": dec, "mag": MAG[name], "dist": math.sqrt(gx * gx + gy * gy + gz * gz)})
    return out


def moon(jdv: float):
    """Ay'ın yaklaşık konumu ve evresi (ana düzeltmelerle ~1° doğruluk)."""
    d = jdv - 2451543.5
    N = (125.1228 - 0.0529538083 * d) * D2R
    i = 5.1454 * D2R
    w = (318.0634 + 0.1643573223 * d) * D2R
    a, e = 60.2666, 0.0549
    M = (115.3654 + 13.0649929509 * d) % 360 * D2R
    E = _kepler(M, e)
    xv, yv = a * (math.cos(E) - e), a * math.sqrt(1 - e * e) * math.sin(E)
    v = math.atan2(yv, xv)
    r = math.hypot(xv, yv)
    u = v + w
    xh = r * (math.cos(N) * math.cos(u) - math.sin(N) * math.sin(u) * math.cos(i))
    yh = r * (math.sin(N) * math.cos(u) + math.cos(N) * math.sin(u) * math.cos(i))
    zh = r * math.sin(u) * math.sin(i)
    lon, lat = math.atan2(yh, xh), math.atan2(zh, math.hypot(xh, yh))
    Ms = (356.0470 + 0.9856002585 * d) % 360 * D2R
    Ls = (282.9404 + 4.70935e-5 * d) * D2R + Ms
    Lm = N + w + M
    Dm, F = Lm - Ls, Lm - N
    lon += (-1.274 * math.sin(M - 2 * Dm) + 0.658 * math.sin(2 * Dm) - 0.186 * math.sin(Ms) - 0.059 * math.sin(2 * M - 2 * Dm)
            - 0.057 * math.sin(M - 2 * Dm + Ms) + 0.053 * math.sin(M + 2 * Dm) + 0.046 * math.sin(2 * Dm - Ms) + 0.041 * math.sin(M - Ms)
            - 0.035 * math.sin(Dm) - 0.031 * math.sin(M + Ms)) * D2R
    lat += (-0.173 * math.sin(F - 2 * Dm) - 0.055 * math.sin(M - F - 2 * Dm) - 0.046 * math.sin(M + F - 2 * Dm) + 0.033 * math.sin(F + 2 * Dm)) * D2R
    x, y, z = math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)
    ra, dec = _ecl_to_eq(x, y, z, d)
    slon, _ = sun_ecl(d)
    elong = (lon - slon) % (2 * math.pi)
    phase = (1 - math.cos(elong)) / 2
    return {"name": "Ay", "ra": ra, "dec": dec, "mag": -12.0, "phase": phase, "elong": elong / D2R}


def phase_name(elong_deg: float) -> str:
    e = elong_deg % 360
    names = [(22.5, "Yeni ay"), (67.5, "Hilal (büyüyen)"), (112.5, "İlk dördün"), (157.5, "Şişkin ay (büyüyen)"), (202.5, "Dolunay"),
             (247.5, "Şişkin ay (küçülen)"), (292.5, "Son dördün"), (337.5, "Hilal (küçülen)")]
    for lim, n in names:
        if e < lim:
            return n
    return "Yeni ay"


def snapshot(t: dt.datetime, lat: float, lon: float):
    """Verilen an ve yer için Güneş, Ay ve gezegenlerin ufuk konumları."""
    j = jd(t)
    L = lst(j, lon)
    objs = [sun(j), moon(j)] + planets(j)
    for o in objs:
        o["alt"], o["az"] = radec_to_altaz(o["ra"], o["dec"], lat, L)
    return objs, L, j

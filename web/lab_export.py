"""Jarvis Cep laboratuvar verisini (web/data/lab.json) bilgisayardaki Jarvis'in veri modüllerinden yeniden üretir.
Çalıştırma: python web/lab_export.py   (kaynak modüller değişince tekrar çalıştırın). Yalnızca kaynağı olan alanları günceller;
Cep'e özgü diğer alanlar (el, cats, org, cells, aa, codon, shapes, fizik/astronomi/jeoloji exps) olduğu gibi kalır."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import bio_data as B  # noqa: E402
import chem_data as C  # noqa: E402
import lab_concepts as K  # noqa: E402
import sci_data as D  # noqa: E402
import sci_data2 as D2  # noqa: E402

PATH = os.path.join(HERE, "data", "lab.json")
_META = re.compile(r"[\\()\[\]{}.*+?^$]")


def kavram(items):
    """(başlık, regex, metin) -> Cep biçimi {t, k, x}; Cep anahtarları düz alt dize olarak arar, bu yüzden regex'ten yalnızca düz alternatifler alınır."""
    out = []
    for title, pat, text in items:
        plain = [a.strip() for a in pat.split("|") if a.strip() and not _META.search(a)]
        out.append({"t": title, "k": "|".join(plain) or title.lower(), "x": text})
    return out


def main():
    with open(PATH, encoding="utf-8") as f:
        d = json.load(f)
    k = d["kimya"]
    k["facts"] = {str(z): t for z, t in sorted(C.FACTS.items())}
    k["mol"] = [{**m, "atoms": [list(a) for a in m["atoms"]], "bonds": [list(b) for b in m["bonds"]]} for m in C.MOLECULES]
    k["exps"] = C.EXPERIMENTS
    k["ph"] = [[n, v, t] for n, v, t in C.PH]
    k["safety"] = C.SAFETY
    k["kavram"] = kavram(K.CHEM)
    b = d["biyoloji"]
    b["exps"] = B.EXPERIMENTS
    b["kavram"] = kavram(K.BIO)
    d["fizik"]["kavram"] = kavram(D.FIZ_CONCEPTS)
    d["matematik"]["kavram"] = kavram(D.MATH_CONCEPTS)
    d["astronomi"]["kavram"] = kavram(D2.AST_CONCEPTS)
    d["jeoloji"]["kavram"] = kavram(D2.GEO_CONCEPTS)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    print("lab.json yazıldı:", os.path.getsize(PATH) // 1024, "KB;",
          {n: len(d[n].get("kavram", [])) for n in ("kimya", "biyoloji", "fizik", "matematik", "astronomi", "jeoloji")},
          "kimya deney", len(k["exps"]), "molekül", len(k["mol"]), "biyoloji deney", len(b["exps"]))


if __name__ == "__main__":
    main()

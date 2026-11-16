"""web/ klasöründeki Jarvis Cep'i TEK bir HTML dosyasına birleştirir (dagitim/Jarvis-Cep.html): WhatsApp'tan gönderilip telefonda açılabilir.
Not: tek dosya olarak açıldığında 'uygulama olarak yükle' ve çevrimdışı önbellek çalışmaz (bunlar için https adresi gerekir); veriler yine yalnızca telefondadır.
Kullanım: python web/tek_dosya.py"""
import base64
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "dagitim", "Jarvis-Cep.html")


def oku(ad):
    with open(os.path.join(HERE, ad), encoding="utf-8") as f:
        return f.read()


html = oku("index.html")
for js in ("core.js", "modes1.js", "modes2.js", "modes3.js", "modes4.js", "modes5.js", "modes6.js", "modes7.js", "modes8.js", "modes9.js", "modes10.js", "modes11.js", "modes12.js"):
    html = html.replace(f'<script src="{js}"></script>', "<script>\n" + oku(js).replace("</script>", "<\\/script>") + "\n</script>")
html = html.replace("<script>" + chr(10) + chr(34) + "use strict" + chr(34), "<script>window.__TARIF=" + oku("data/tarif.json") + "</script>" + chr(10) + "<script>" + chr(10) + chr(34) + "use strict" + chr(34), 1)
html = html.replace("<script>window.__TARIF=", "<script>window.__SKY=" + oku("data/sky.json") + ";window.__DIGER=" + oku("data/diger.json") + "</script>" + chr(10) + "<script>window.__LAB=" + oku("data/lab.json") + "</script>" + chr(10) + "<script>window.__TARIF=", 1)
icon = "data:image/png;base64," + base64.b64encode(open(os.path.join(HERE, "icon-192.png"), "rb").read()).decode()
html = re.sub(r'<link rel="(?:icon|apple-touch-icon)" href="icon-192.png">', f'<link rel="icon" href="{icon}">', html)
html = html.replace('<link rel="manifest" href="manifest.webmanifest">', "")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"{OUT} ({len(html) // 1024} KB)")

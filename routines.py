"""Rutinler (routines.json): tek cümleyle birkaç komutu birden çalıştırır. Örn. "film modu" -> ışığı kapat, ses 30, YouTube aç."""
import json, os, threading

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routines.json")
MAX_STEPS = 8
_lock = threading.Lock()


def load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data: dict):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def key(name: str) -> str:
    return " ".join(name.replace("İ", "i").replace("I", "ı").lower().split())


def add(name: str, steps: list) -> None:
    with _lock:
        d = load()
        d[key(name)] = {"steps": steps[:MAX_STEPS]}
        _save(d)


def delete(name: str) -> bool:
    with _lock:
        d = load()
        if key(name) not in d:
            return False
        del d[key(name)]
        _save(d)
        return True


def get(name: str):
    return load().get(key(name))


def names() -> list:
    return list(load())


# ---- Hazır rutinler: kullanıcının eklemesine gerek yok. Aynı adla kendi rutinini oluşturursa onun sürümü geçerli olur.
# "söyle:" ile başlayan adımın sonucu rutin sonunda sesli söylenir. names: "... modu" denince, phrases: tek başına söylenince tetikler.
BUILTIN = {
    "ders çalışma": {
        "names": ["ders çalışma", "ders", "çalışma", "odaklanma", "ders çalışma saati"],
        "phrases": ["ders çalışma saati", "ders çalışma zamanı", "ders çalışacağım", "ders çalışmaya başla", "ders çalışmaya", "ders çalışmaya başlıyorum",
                    "ders saati", "çalışma saati", "odaklanma zamanı"],
        "steps": ["ışığımı aç", "sesi yüzde 5 yap", "ders müziği çal", "25 dakikalık tam ekran zamanlayıcı kur"],
        "say": "Ders çalışma modu başladı efendim. Işığınız açık, ses yüzde 5, ders şarkılarınız sırayla döngüde çalıyor ve 25 dakikalık sayaç ekranınızda. Başarılar.",
    },
    "film": {
        "names": ["film", "sinema"],
        "phrases": ["film izleyeceğim", "film izleyelim", "film zamanı", "film saati", "sinema zamanı"],
        "steps": ["ışığımı kapat", "sesi yüzde 12 yap", "youtube aç"],
        "say": "Film modu hazır efendim. Işığınızı kapattım, sesi yüzde 12 yaptım ve YouTube'u açıyorum. İyi seyirler.",
    },
    "uyku": {
        "names": ["uyku", "gece"],
        "phrases": ["uyuyacağım", "yatıyorum", "yatma zamanı", "uyku vakti", "uyku zamanı"],
        "steps": ["ışığımı kapat", "sesi yüzde 3 yap"],
        "say": "Uyku modu efendim. Işığınızı kapattım ve sesi kıstım. İyi geceler.",
    },
    "sabah": {
        "names": ["sabah", "günaydın"],
        "phrases": ["günaydın", "günaydın jarvis", "sabah özeti", "günün özeti", "bugün neler var", "sabah oldu"],
        "steps": ["ışığımı aç", "sesi yüzde 8 yap", "söyle: saat kaç", "söyle: bugün ayın kaçı", "söyle: hava durumu",
                  "söyle: bugün hangi derslerim var", "söyle: bugün takvimde ne var", "söyle: dolar kaç lira", "söyle: hatırlatmalarım"],
        "say": "Günaydın efendim, ışığınızı açtım.",
    },
    "mola": {
        "names": ["mola", "ara"],
        "phrases": ["mola verelim", "mola veriyorum", "mola zamanı", "ara verelim"],
        "steps": ["sesi yüzde 6 yap", "söyle: mola ver"],          # mola modunu varsayılan süreyle başlatır (süre: 'mola süresi 15 dakika olsun')
        "say": "Mola zamanı efendim, sesi kıstım.",
    },
    "müzik": {
        "names": ["müzik", "şarkı"],
        "phrases": ["müzik zamanı"],
        "steps": ["sesi yüzde 10 yap", "youtube müzik aç"],
        "say": "Müzik modu efendim. Sesi ayarladım ve YouTube Music'i açıyorum.",
    },
    "kodlama": {
        "names": ["kodlama", "kod", "yazılım", "programlama"],
        "phrases": ["kodlamaya başlıyorum", "kodlama zamanı", "yazılım zamanı"],
        "steps": ["ışığımı aç", "sesi yüzde 8 yap", "kod yazma ekranını aç"],
        "say": "Kodlama modu hazır efendim. Işığınız açık, ses yüzde 8 ve kod yazma ekranı önünüzde. İyi kodlamalar.",
    },
    "okuma": {
        "names": ["okuma", "kitap", "kitap okuma"],
        "phrases": ["kitap okuyacağım", "okuma zamanı", "okuma saati", "kitap zamanı"],
        "steps": ["ışığımı aç", "sesi yüzde 3 yap", "45 dakikalık tam ekran zamanlayıcı kur"],
        "say": "Okuma modu başladı efendim. Işığınız açık, ses kısık ve 45 dakikalık sayaç ekranda. Keyifli okumalar.",
    },
    "odak": {
        "names": ["odak", "derin odak", "yoğun çalışma", "sınav", "tekrar"],
        "phrases": ["odaklanmam lazım", "yoğun çalışacağım", "sınava çalışacağım", "tekrar yapacağım", "tekrar zamanı"],
        "steps": ["ışığımı aç", "sesi yüzde 5 yap", "ders müziği çal", "50 dakikalık tam ekran zamanlayıcı kur"],
        "say": "Odak modu başladı efendim. Ders şarkılarınız döngüde, 50 dakikalık sayaç ekranda. Bitince ders modunu kapat demeniz yeterli.",
    },
    "ödev": {
        "names": ["ödev", "ödev saati"],
        "phrases": ["ödev yapacağım", "ödev zamanı", "ödevlere başlıyorum", "ödev saati"],
        "steps": ["ışığımı aç", "sesi yüzde 5 yap", "söyle: bugün takvimde ne var", "40 dakikalık tam ekran zamanlayıcı kur"],
        "say": "Ödev modu başladı efendim. 40 dakikalık sayaç ekranda, başarılar.",
    },
    "okul hazırlığı": {
        "names": ["okul hazırlığı", "hazırlık", "çanta", "yarın"],
        "phrases": ["çantamı hazırlıyorum", "yarına hazırlanıyorum", "okul hazırlığı"],
        "steps": ["söyle: yarın hangi derslerim var", "söyle: yarın hava nasıl", "söyle: yarın ne var"],
        "say": "Yarına hazırlanalım efendim.",
    },
    "oyun": {
        "names": ["oyun", "oyun oynama"],
        "phrases": ["oyun oynayacağım", "oyun zamanı", "oyun saati"],
        "steps": ["ışığımı kapat", "sesi yüzde 20 yap"],
        "say": "Oyun modu efendim. Işığı kapattım, sesi yüzde 20 yaptım. İyi eğlenceler.",
    },
    "akşam": {
        "names": ["akşam", "akşam rahatlama", "dinlenme"],
        "phrases": ["akşam oldu", "dinleneceğim", "dinlenme zamanı"],
        "steps": ["sesi yüzde 10 yap", "youtube müzik aç", "söyle: yarın hangi derslerim var"],
        "say": "Akşam modu efendim. Sesi ayarladım ve YouTube Music'i açıyorum. Dinlenme zamanı.",
    },
    "spor": {
        "names": ["spor", "egzersiz", "antrenman"],
        "phrases": ["spor yapacağım", "spor zamanı", "antrenman zamanı", "egzersiz yapacağım"],
        "steps": ["sesi yüzde 25 yap", "youtube müzik aç", "30 dakikalık tam ekran zamanlayıcı kur"],
        "say": "Spor modu efendim. Müzik açılıyor ve 30 dakikalık sayaç ekranda. Hadi başlayalım.",
    },
    "yemek": {
        "names": ["yemek", "yemek yeme", "öğle", "öğle yemeği"],
        "phrases": ["yemek yiyeceğim", "yemek zamanı", "yemek saati", "yemeğe gidiyorum"],
        "steps": ["sesi yüzde 6 yap", "20 dakikalık tam ekran zamanlayıcı kur"],
        "say": "Afiyet olsun efendim. 20 dakikalık yemek sayacı ekranda.",
    },
    "sessiz": {
        "names": ["sessiz", "toplantı", "sınıf", "sessizlik"],
        "phrases": ["toplantıya giriyorum", "toplantı başlıyor", "sessiz olsun", "sessizlik lazım"],
        "steps": ["sesi yüzde 1 yap"],
        "say": "Sessiz mod efendim. Sesi en aza indirdim.",
    },
    "misafir": {
        "names": ["misafir", "konuk"],
        "phrases": ["misafir geliyor", "misafirim var", "konuk geliyor"],
        "steps": ["ışığımı aç", "sesi yüzde 5 yap"],
        "say": "Misafir modu efendim. Işığı açtım, sesi kıstım.",
    },
    "hafta sonu": {
        "names": ["hafta sonu", "tatil"],
        "phrases": ["hafta sonu oldu", "tatil başladı"],
        "steps": ["ışığımı aç", "sesi yüzde 10 yap", "söyle: hava durumu", "söyle: takvimimde ne var"],
        "say": "Hafta sonu modu efendim, keyfinize bakın.",
    },
    "okul": {
        "names": ["okul", "okula gidiş", "okula çıkış"],
        "phrases": ["okula gidiyorum", "okula çıkıyorum", "okula gidiyorum jarvis", "okula geç kalıyorum"],
        "steps": ["söyle: bugün hangi derslerim var", "söyle: hava durumu", "söyle: bugün takvimde ne var", "söyle: hatırlatmalarım", "ışığımı kapat"],
        "say": "Günaydın efendim, okul için hazırlanalım.",
    },
    "eve dönüş": {
        "names": ["eve dönüş", "eve geldim", "ev"],
        "phrases": ["eve geldim", "eve döndüm", "eve girdim", "okuldan geldim"],
        "steps": ["ışığımı aç", "sesi yüzde 8 yap", "söyle: bugün takvimde ne var", "söyle: hatırlatmalarım", "söyle: yarın hangi derslerim var"],
        "say": "Hoş geldiniz efendim, ışığınızı açtım.",
    },
    "teneffüs": {
        "names": ["teneffüs", "ders arası"],
        "phrases": ["teneffüs zamanı", "teneffüse çıkıyorum", "ders arası verelim"],
        "steps": ["sesi yüzde 6 yap", "10 dakikalık tam ekran zamanlayıcı kur"],
        "say": "Teneffüs efendim. On dakikalık sayaç ekranda, süre dolunca haber vereceğim.",
    },
    "maraton": {
        "names": ["maraton", "uzun çalışma", "uzun ders"],
        "phrases": ["uzun çalışacağım", "uzun süre çalışacağım", "maraton başlasın"],
        "steps": ["ışığımı aç", "sesi yüzde 5 yap", "ders müziği çal", "2 saatlik tam ekran zamanlayıcı kur"],
        "say": "Çalışma maratonu başladı efendim. İki saatlik sayaç ekranda, ders şarkıları döngüde. Aralarda su içmeyi unutmayın.",
    },
    "göz molası": {
        "names": ["göz molası", "göz", "göz dinlendirme"],
        "phrases": ["gözlerim yoruldu", "gözlerimi dinlendireyim", "göz molası zamanı"],
        "steps": ["sesi yüzde 3 yap", "2 dakikalık tam ekran zamanlayıcı kur"],
        "say": "Göz molası efendim. İki dakika boyunca ekrandan uzağa, en az altı metre ötedeki bir noktaya bakın.",
    },
    "su": {
        "names": ["su", "su içme", "su molası"],
        "phrases": ["su içmeyi hatırlat", "su içme zamanı"],
        "steps": ["30 dakika sonra su içmemi hatırlat", "60 dakika sonra su içmemi hatırlat", "90 dakika sonra su içmemi hatırlat"],
        "say": "Su modu efendim. Yarım saat arayla üç kez su içmenizi hatırlatacağım.",
    },
    "ayrılma": {
        "names": ["ayrılma", "kilit", "uzaklaşma", "bilgisayardan ayrılma"],
        "phrases": ["bilgisayardan kalkıyorum", "kısa bir süre uzaklaşıyorum", "bilgisayarı bırakıyorum", "bilgisayardan ayrılıyorum"],
        "steps": ["ders modunu kapat", "ışığımı kapat", "ekranı kilitle"],
        "say": "Ekranı kilitliyorum ve ışığı kapattım efendim. Dönünce eve dönüş ya da ders modu demeniz yeterli.",
    },
    "gece özeti": {
        "names": ["gece özeti", "yatmadan önce", "yatış"],
        "phrases": ["yatmadan önce özet", "gece özeti ver", "yarına hazırlan ve yat"],
        "steps": ["söyle: yarın hangi derslerim var", "söyle: yarın hava nasıl", "söyle: yarın ne var", "ışığımı kapat", "sesi yüzde 3 yap"],
        "say": "İyi geceler efendim, yarın için her şey hazır.",
    },
    "araştırma": {
        "names": ["araştırma", "ödev araştırması", "proje araştırması"],
        "phrases": ["araştırma yapacağım", "araştırma zamanı"],
        "steps": ["ışığımı aç", "sesi yüzde 5 yap", "google aç", "çeviri uygulamasını aç"],
        "say": "Araştırma modu efendim. Google ve çeviri uygulamanız açıldı. Aradığınız konuyu söylerseniz internette ben de araştırabilirim.",
    },
    "çıkış": {
        "names": ["çıkış", "dışarı", "ev dışı"],
        "phrases": ["evden çıkıyorum", "dışarı çıkıyorum", "çıkıyorum evden"],
        "steps": ["ışığımı kapat"],
        "say": "Güle güle efendim, ışığınızı kapattım.",
    },
}

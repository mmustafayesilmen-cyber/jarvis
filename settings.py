"""Kullanıcı ayarları (config.json)."""
import json, os, threading

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULTS = {
    "tts": "edge",           # "edge" = JARVIS'e en yakın doğal ses (metin Microsoft'ta seslendirilir) | "piper" = tamamen yerel
    "jarvis_fx": True,       # filmdeki gibi hafif yapay zekâ tınısı
    "log_max_mb": 5,
    "mola_len": 10,          # mola modunun varsayılan süresi (dakika)
    "uyku_len": 30,          # uyku modunun varsayılan süresi (dakika)
    "odak_len": 45,          # derin odak modunun varsayılan süresi (dakika)
    "uzak_tam_kontrol": False, # True: Tailscale'e bağlı eşleşmiş telefon bilgisayarın ekranını görür ve Jarvis'e serbest komut verir (tünelden asla)
    "uzak_tailscale": False, # True: Jarvis açılınca telefon erişimi bilgisayarın Tailscale adresinde (tünelsiz, sitesiz) dinlenir
    "uzak_otomatik": False,  # True: Jarvis açılınca uzaktan erişim kendiliğinden kurulur ve link WhatsApp'tan gönderilir
    "uzak_wa_no": "",        # linkin gönderileceği KENDİ WhatsApp numaranız (yalnızca buradan okunur)
    "sohbet_think": "auto",  # sohbet modunda düşünme: "auto" (zor sorularda) | "hep" | "hic"
    "sohbet_ctx": 8192,      # sohbet modunun bağlam uzunluğu (normal Jarvis 4096; mod açılıp kapanırken model bir kez yeniden yüklenir)
    "ultron_ogren": True,    # Ultron arka planda kendi seçtiği konuları internette araştırıp not alır (kapatmak için Ultron modunda "öğrenmeyi durdur")
    "ultron_aralik": 12,     # iki araştırma arası dakika
    "ultron_gunluk": 30,     # günde en çok kaç araştırma
    "luna_ogren": True,      # Luna arka planda kendi seçtiği konuları internette araştırıp not alır (kapatmak için Luna modunda "öğrenmeyi durdur")
    "luna_aralik": 12,       # iki araştırma arası dakika
    "luna_gunluk": 30,       # günde en çok kaç araştırma
    "friday_ogren": True,    # Friday arka planda kendi seçtiği pratik konuları araştırıp not alır ("öğrenmeyi durdur" kapatır)
    "friday_aralik": 15,     # iki araştırma arası dakika
    "friday_gunluk": 20,     # günde en çok kaç araştırma
    "brifing_oto": False,    # True: S.H.I.E.L.D. brifing sayfası açıkken yarım saatte bir kendini yeniler (varsayılan kapalı)
    "spor_fav": [],       # spor modunda favori takımlar
    "save_clips": True,      # konuşma tanıma iyileştirmesi için son 40 ses parçasını yalnızca bu bilgisayarda sakla
    "volume_max": 30,        # Jarvis sesi hiçbir komutla bunun üstüne çıkarmaz (kullanıcı normalde en fazla %10 dinliyor)
    "home_url": "",
    "home_default_device": "",     # "ışığımı aç" dendiğinde dokunulacak cihaz
}
_lock = threading.Lock()


def load() -> dict:
    try:
        with open(PATH, encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def get(key):
    return load().get(key, DEFAULTS.get(key))


def set(key, value):
    """Tek bir ayarı yazar. Dosya okunamıyorsa (bozuk/kilitli) YAZMAZ: aksi halde diğer ayarlar varsayılanlarla ezilirdi. Yazma geçici dosya + değiştirme ile yapılır (yarım dosya kalmaz)."""
    with _lock:
        try:
            with open(PATH, encoding="utf-8") as f:
                cur = json.load(f)
        except FileNotFoundError:
            cur = {}
        except (OSError, ValueError):
            print("AYAR: config.json okunamadı, '%s' yazılmadı (mevcut ayarlar korundu)" % key, flush=True)
            return
        data = {**DEFAULTS, **cur}
        data[key] = value
        tmp = PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PATH)

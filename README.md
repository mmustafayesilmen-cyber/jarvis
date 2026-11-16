# Jarvis — yerel, Türkçe öncelikli sesli asistan (Windows)

Bilgisayarınızda çalışan, internete mecbur olmayan bir sesli asistan. Uyandırma kelimesi, konuşma tanıma, yerel yapay zekâ (Ollama), Türkçe/İngilizce konuşma
ve onlarca tam ekran "mod" (laboratuvarlar, odak/pomodoro, e-kitap, ritim stüdyosu, simya atölyesi…) içerir. Asistan size "efendim" diye hitap eder
(Türkçe modda); isterseniz `ui/` ve `router.py` içinden değiştirebilirsiniz.

> **Gizlilik:** Konuşmalarınız ve kayıtlarınız bilgisayarınızda kalır. Yapay zekâ modeli yerel çalışır. Uzaktan erişim, WhatsApp, VPN gibi özellikler
> **varsayılan olarak kapalıdır** ve ayrı ayrı sesle/ayarla açılır. Bu depo hiçbir kişisel veri, anahtar ya da numara içermez.

## Sistem gereksinimleri
Değerler yaklaşıktır; geliştirici makinesindeki kurulumdan ve model boyutlarından çıkarılmıştır, her donanımda ölçülmemiştir.

| | En az | Önerilen |
|---|---|---|
| İşletim sistemi | Windows 10 (64 bit, 2004 ve üstü) | Windows 11 |
| Python | 3.12 | 3.12 |
| Bellek (RAM) | 8 GB (yavaş çalışır) | 16 GB ve üstü |
| Disk | ~12 GB boş (model ~5 GB + bağımlılıklar + ses dosyaları) | SSD, 15 GB boş |
| Ekran kartı | Gerekmez (işlemciyle çalışır, yanıtlar yavaş olur) | NVIDIA RTX, 8 GB VRAM: model ve konuşma tanıma hızlanır |
| Mikrofon / hoparlör | Gerekli | Kulaklıklı mikrofon |
| İnternet | Kurulumda (paketler, ses ve model indirme) | Hava durumu, e-kitap, spor vb. modlar için çalışırken de |

Yazılım: [Ollama](https://ollama.com) (yerel yapay zekâ), Windows 10/11'de WebView2 çalışma zamanı (Edge ile birlikte gelir).
Linux ve macOS desteklenmez (pywinauto, pycaw, winsdk kullanılır). Daha küçük bir model için `brain.py` içindeki `MODEL` değerini değiştirin.

## Kurulum
```bat
kurulum.bat
```
`kurulum.bat` sanal ortamı kurar, bağımlılıkları yükler, Piper ses dosyalarını indirir ve modeli çeker. Sonra `jarvis.bat` (konsollu) ya da `Jarvis.vbs`
(konsolsuz) ile başlatın. Ayarlar `config.json` içindedir (ilk kurulumda `config.ornek.json`'dan kopyalanır).

## İsteğe bağlı ayarlar (`config.json`)
| Ayar | Anlamı |
|---|---|
| `city` | Hava durumu için şehir |
| `tts` | `edge` (internetli, doğal ses) ya da `piper` (tamamen yerel) |
| `elevenlabs_api_key` | İsteğe bağlı ElevenLabs sesi (kendi anahtarınız) |
| `report_phone` | Raporların WhatsApp'tan gideceği numara (boşsa rapor gönderilmez) |
| `home_url`, `home_default_device` | Google Home ışık kontrolü için kendi ev sayfanız |
| `uzak_*` | Telefondan uzaktan erişim (kapalı gelir; Tailscale/tünel gerektirir) |

## Mimari ve geliştirme
`docs/MIMARI.md` dosyasında süreç modeli, komut hattı, sahne (mod) kalıbı ve yeni mod ekleme adımları anlatılır. Test paketi ya da derleme adımı yoktur;
hata ayıklamak için `jarvis.log` dosyasını okuyun.

## Güvenlik notları
- Sunucu yalnızca `127.0.0.1`'e bağlanır ve her açılışta değişen bir belirteçle korunur. Ağa açılan özellikler ayrı küçük sunuculadır ve yalnızca siz açınca çalışır.
- Silme/kapatma gibi tehlikeli araçlar için sözlü onay istenir.
- WhatsApp/telefon/VPN özelliklerini açmadan önce ilgili modülün (`whatsapp.py`, `remote.py`, `vpn*.py`) üstündeki açıklamayı okuyun.

## Katkı
Hata bildirimleri ve çekme istekleri (pull request) memnuniyetle karşılanır. Kişisel veri (numara, adres, anahtar) içeren hiçbir şeyi göndermeyin.

## Lisans
MIT (bkz. `LICENSE`). Üçüncü taraf bileşenler ve veriler için `THIRD_PARTY.md` dosyasına bakın.

---
**English:** Jarvis is a local, Turkish-first (English mode available) voice assistant for Windows with a local LLM (Ollama), wake word, offline-capable speech and
dozens of full-screen modes. Run `kurulum.bat`, then `jarvis.bat`. No personal data, keys or phone numbers are included; remote/WhatsApp/VPN features are off by default.
(Generated from 266 source files.)

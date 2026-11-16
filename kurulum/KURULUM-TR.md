# Zentra-PPPoE — Kurulum ve Kullanım Kılavuzu (Türkçe)

Bu araç, **kendi internet hattınızın** PPPoE kullanıcı adı ve şifresini modemin
WAN portundan kurtarır.

> ⚠️ **Yasal uyarı:** Yalnızca kendi hattınızda veya yazılı olarak
> yetkilendirildiğiniz bir hat üzerinde kullanın. Başkasının hattının kimlik
> bilgilerini izinsiz ele geçirmek yasa dışıdır.

---

## 1. Dosyalar nerede?

Tüm proje masaüstündeki **`Zentra-PPPoE`** klasöründedir:

```
Zentra-PPPoE/
├── zentra_gui.py       → Pencereli uygulama (önerilen)
├── zentra_pppoe.py     → Komut satırı aracı + yakalama motoru
├── requirements.txt    → Gerekli Python paketi (scapy)
├── README.md           → Kısa özet
├── LICENSE             → MIT lisansı
└── kurulum/            → Bu kılavuzlar
    ├── KURULUM-TR.md   → (bu dosya)
    └── SETUP-EN.md     → İngilizce kılavuz
```

---

## 2. İndirme ve kurulum (yazılım)

### 2.1 — Python (3.8 veya üstü)

- **Windows:** <https://www.python.org/downloads/> → "Download Python" → kurulumda
  **"Add Python to PATH"** kutusunu mutlaka işaretle.
- **macOS:** <https://www.python.org/downloads/> ya da Homebrew:
  `brew install python python-tk`
- **Linux:** genelde kuruludur. Değilse: `sudo apt install python3 python3-pip python3-tk`

Kontrol: terminal/PowerShell'de `python --version` (mac/Linux'ta `python3 --version`).

### 2.2 — scapy (yakalama kütüphanesi)

`Zentra-PPPoE` klasöründe bir terminal aç ve çalıştır:

```bash
pip install -r requirements.txt
```

(Alternatif: `pip install scapy`)

### 2.3 — Npcap (SADECE Windows)

Windows'ta paket dinlemek için gerekir:

1. <https://npcap.com/> → **Download**
2. Kurulumu varsayılan ayarlarla tamamla
   (**"Install Npcap in WinPcap API-compatible Mode"** işaretli kalsın).

> macOS ve Linux'ta ek bir şey gerekmez (libpcap hazır gelir).

---

## 3. Cihaza bağlama (fiziksel kurulum)

1. Modemin **WAN** portuna giden Ethernet kablosunu bul.
2. Bu kabloyu modemden **bilgisayarının Ethernet portuna** tak
   (yani modemin WAN portu ↔ bilgisayar).
3. **Ethernet portu yoksa** (çoğu dizüstü ve Mac): bir
   **USB / USB-C / Thunderbolt → Ethernet adaptörü** kullan.
4. Dinleme sırasında karışmaması için **Wi-Fi'yi kapatman** önerilir.

---

## 4. Çalıştırma

### 4.1 — Pencereli uygulama (önerilen)

**Windows** (PowerShell'i **yönetici olarak** aç):

```powershell
python zentra_gui.py
```

**macOS / Linux:**

```bash
sudo python3 zentra_gui.py
```

Sonra arayüzde:

1. **Ağ arayüzü**nü seç (modemin bağlı olduğu; Windows'ta "Ethernet",
   macOS'ta `en0`/`en5` gibi). Emin değilsen **↻ Yenile**'ye bas.
2. **Dinlemeyi başlat**'a tıkla.
3. **Modemi yeniden başlat** (gücünü kes-aç). Yeniden oturum açarken
   kimlik bilgileri yakalanır.
4. Kullanıcı adı ve şifre bir kart olarak görünür → **kopyala** ile panoya al.

### 4.2 — Komut satırı (alternatif)

```bash
# Arayüzleri listele
python zentra_pppoe.py --list

# Dinle (arayüz adını kendine göre yaz)
sudo python3 zentra_pppoe.py -i en0        # macOS/Linux
python zentra_pppoe.py -i "Ethernet"       # Windows (yönetici)
```

Bayraklar: `-t` süre (sn), `-w dosya.pcap` kayıt, `--keep-going` bulununca durma.

---

## 5. Sorun giderme

| Sorun | Çözüm |
|-------|-------|
| `scapy bulunamadı` | `pip install -r requirements.txt` |
| Windows'ta `arayüz açılamadı` | Npcap kurulu mu? PowerShell'i yönetici açtın mı? |
| macOS'ta `tkinter yok` | `brew install python-tk` |
| Kimlik gelmiyor | Doğru arayüz mü? Dinlerken modemi yeniden başlattın mı? |
| Sadece CHAP görünüyor | Modem CHAP kullanıyordur; şifre hash'li gelir, düz metin görünmez |

---

## 6. Kısa özet (hepsi bir arada)

```bash
# 1) scapy kur
pip install -r requirements.txt
# 2) (Windows) Npcap kur: https://npcap.com/
# 3) Modemin WAN portunu bilgisayara bağla
# 4) Uygulamayı yönetici/sudo ile aç
sudo python3 zentra_gui.py
# 5) Arayüzü seç → Başlat → modemi kapat-aç → bilgileri kopyala
```

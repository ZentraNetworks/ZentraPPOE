# Zentra-PPPoE — Setup & Usage Guide (English)

This tool recovers the PPPoE username and password of **your own internet line**
from the modem's WAN port.

> ⚠️ **Legal notice:** Use only on your own line, or on a line you are explicitly
> authorized to work on. Capturing someone else's credentials without permission
> is illegal.

---

## 1. Where are the files?

The whole project lives in the **`Zentra-PPPoE`** folder on your Desktop:

```
Zentra-PPPoE/
├── zentra_gui.py       → Windowed app (recommended)
├── zentra_pppoe.py     → Command-line tool + capture engine
├── requirements.txt    → Required Python package (scapy)
├── README.md           → Short summary
├── LICENSE             → MIT license
└── kurulum/            → These guides
    ├── KURULUM-TR.md   → Turkish guide
    └── SETUP-EN.md     → (this file)
```

---

## 2. Download & install (software)

### 2.1 — Python (3.8 or newer)

- **Windows:** <https://www.python.org/downloads/> → "Download Python" → during
  install, **check "Add Python to PATH"**.
- **macOS:** <https://www.python.org/downloads/> or Homebrew:
  `brew install python python-tk`
- **Linux:** usually preinstalled. Otherwise: `sudo apt install python3 python3-pip python3-tk`

Check: run `python --version` (on macOS/Linux use `python3 --version`).

### 2.2 — scapy (capture library)

Open a terminal **inside the `Zentra-PPPoE` folder** and run:

```bash
pip install -r requirements.txt
```

(Alternatively: `pip install scapy`)

### 2.3 — Npcap (Windows ONLY)

Required for packet capture on Windows:

1. <https://npcap.com/> → **Download**
2. Install with default options
   (keep **"Install Npcap in WinPcap API-compatible Mode"** checked).

> No extra step is needed on macOS or Linux (libpcap is already included).

---

## 3. Connect to the device (physical setup)

1. Find the Ethernet cable going into the modem's **WAN** port.
2. Plug that cable from the modem into **your computer's Ethernet port**
   (modem WAN ↔ computer).
3. **No Ethernet port?** (most laptops and Macs): use a
   **USB / USB-C / Thunderbolt → Ethernet adapter**.
4. Turning **Wi-Fi off** during capture is recommended to avoid interference.

---

## 4. Run it

### 4.1 — Windowed app (recommended)

**Windows** (open PowerShell **as Administrator**):

```powershell
python zentra_gui.py
```

**macOS / Linux:**

```bash
sudo python3 zentra_gui.py
```

Then in the app:

1. Select the **network interface** the modem is connected to
   (e.g. "Ethernet" on Windows, `en0`/`en5` on macOS). Not sure? Click **↻ Refresh**.
2. Click **Start listening**.
3. **Restart the modem** (power it off and on). It re-authenticates and the
   credentials get captured.
4. The username and password appear as a card → click **copy** to grab them.

### 4.2 — Command line (alternative)

```bash
# List interfaces
python zentra_pppoe.py --list

# Capture (use your own interface name)
sudo python3 zentra_pppoe.py -i en0        # macOS/Linux
python zentra_pppoe.py -i "Ethernet"       # Windows (as Administrator)
```

Flags: `-t` timeout (sec), `-w file.pcap` save capture, `--keep-going` don't stop
after the first hit.

---

## 5. Troubleshooting

| Problem | Fix |
|---------|-----|
| `scapy not found` | `pip install -r requirements.txt` |
| Windows: `interface could not be opened` | Is Npcap installed? Did you run PowerShell as Administrator? |
| macOS: `no module named tkinter` | `brew install python-tk` |
| No credentials captured | Right interface? Did you restart the modem while listening? |
| Only CHAP shown | The modem uses CHAP; the password is hashed, so it is not shown in cleartext |

---

## 6. Quick summary (all in one)

```bash
# 1) Install scapy
pip install -r requirements.txt
# 2) (Windows) Install Npcap: https://npcap.com/
# 3) Connect the modem's WAN port to your computer
# 4) Launch the app as Administrator / sudo
sudo python3 zentra_gui.py
# 5) Select interface → Start → power-cycle the modem → copy the credentials
```

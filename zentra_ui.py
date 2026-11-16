#!/usr/bin/env python3
"""
Zentra-PPPoE — terminal teması (hacker tarzı yeşil-siyah arayüz)
ANSI renk kodları, ASCII banner ve çerçeveli kimlik kutusu.
Harici bağımlılık yok.
"""

import os

# ---- ANSI renkler ----
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
DGREEN = "\033[32m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
GRAY = "\033[90m"


def enable_ansi():
    """Windows cmd/terminalde ANSI renklerini aç."""
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            pass


BANNER = r"""
 ███████ ███████ ███    ██ ████████ ██████   █████
    ███  ██      ████   ██    ██    ██   ██ ██   ██
   ███   █████   ██ ██  ██    ██    ██████  ███████
  ███    ██      ██  ██ ██    ██    ██   ██ ██   ██
 ███████ ███████ ██   ████    ██    ██   ██ ██   ██
"""


CLEAR = "\033[2J\033[H"


def banner(color=GREEN):
    sub = "P P P o E   C r e d e n t i a l   H a r v e s t e r"
    line = "─" * 52
    return (f"{color}{BOLD}{BANNER}{RESET}"
            f"{color}        {sub}{RESET}\n"
            f"{GRAY}  {line}{RESET}")


def _bar(title, inner, ch="═"):
    t = f" {title} " if title else ""
    pad = inner - len(t)
    left = pad // 2
    right = pad - left
    return ch * left + t + ch * right


def panel(title, lines, color=GREEN, footer=""):
    inner = max([len(l) for l in lines] + [len(title) + 2, len(footer) + 2, 44]) + 4
    out = [color + "╔" + _bar(title, inner) + "╗" + RESET,
           color + "║" + " " * inner + "║" + RESET]
    for l in lines:
        pad = inner - len(l)
        lft = pad // 2
        out.append(color + "║" + " " * lft + BOLD + l + RESET +
                   color + " " * (pad - lft) + "║" + RESET)
    out.append(color + "║" + " " * inner + "║" + RESET)
    out.append(color + "╚" + _bar(footer, inner) + "╝" + RESET)
    return "\n".join(out)


def ok(m):
    return f"{GREEN}[+]{RESET} {m}"


def info(m):
    return f"{CYAN}[*]{RESET} {m}"


def warn(m):
    return f"{RED}[!]{RESET} {m}"


def arrow(m):
    return f"{DGREEN}  ->{RESET} {m}"


def dim(m):
    return f"{GRAY}{m}{RESET}"


# ---- "aranıyor" (kırmızı) durumu ----
def hunt(m):
    return f"{RED}[*]{RESET} {RED}{m}{RESET}"


def hunt_arrow(m):
    return f"{RED}  ->{RESET} {RED}{m}{RESET}"


def granted():
    return (f"{GREEN}{BOLD}"
            "        ✓  ERİŞİM SAĞLANDI  ·  ACCESS GRANTED  ✓"
            f"{RESET}")


if __name__ == "__main__":
    enable_ansi()
    print(banner())
    print(info("PADI alındı (router: a8:29:48:09:7c:f0)"))
    print(arrow("PADO gönderildi (VLAN 35)"))
    print(ok("Oturum açıldı"))
    print()
    print(panel("PPPoE Credentials",
                ["Username : ornek@ttnet",
                 "Password : ********",
                 "Client MAC : a8:29:48:09:7c:f0",
                 "VLAN : 35"],
                color=GREEN, footer="Zentra"))

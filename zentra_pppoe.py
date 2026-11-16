#!/usr/bin/env python3
"""
Zentra-PPPoE
============
Kendi internet hattınızın PPPoE kimlik bilgilerini modemin WAN portundan kurtaran
pasif bir dinleme aracı.

YALNIZCA kendi hattınızda veya yazılı olarak yetkilendirildiğiniz bir hat üzerinde
kullanın. Sorumluluk kullanıcıya aittir.

Çalışma mantığı: Modem ISP'ye PPPoE oturumu açarken PPP kimlik doğrulama paketleri
gönderir. PAP kullanılıyorsa kullanıcı adı/şifre düz metin gider ve yakalanır; CHAP
kullanılıyorsa kullanıcı adı + challenge/response gösterilir (şifre hash'li olduğu
için düz metin görünmez).
"""

import argparse
import sys
import time

# ---- PPP protokol numaraları (RFC 1661 / RFC 1334) ----
PPP_PROTO_PAP = 0xC023
PPP_PROTO_CHAP = 0xC223

# ---- PAP kodları ----
PAP_AUTH_REQUEST = 1
PAP_AUTH_ACK = 2
PAP_AUTH_NAK = 3

# ---- CHAP kodları ----
CHAP_CHALLENGE = 1
CHAP_RESPONSE = 2
CHAP_SUCCESS = 3
CHAP_FAILURE = 4


def _die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def _import_scapy():
    """Scapy'i geç yükle ki --list/-h scapy olmadan da çalışsın."""
    try:
        from scapy.all import sniff, wrpcap, get_if_list, conf  # noqa: F401
        from scapy.layers.ppp import PPP  # noqa: F401
        import scapy.all as scapy
        return scapy
    except ImportError:
        _die(
            "[!] scapy bulunamadı. Kurmak için:\n"
            "    pip install -r requirements.txt\n"
            "Windows'ta ayrıca Npcap gerekir: https://npcap.com/"
        )


def list_interfaces():
    scapy = _import_scapy()
    print("Mevcut ağ arayüzleri:\n")
    try:
        # Windows'ta okunabilir isimler verir, diğerlerinde arayüz listesi.
        scapy.show_interfaces()
    except Exception:
        for iface in scapy.get_if_list():
            print("  -", iface)
    print(
        "\nModemin WAN portunun bağlı olduğu arayüzün adını -i ile kullanın."
    )


def get_interface_list():
    """GUI için arayüzleri döndür: [{'id': <sniff'e verilecek>, 'label': ...}]."""
    scapy = _import_scapy()
    result = []
    try:
        for iface in scapy.get_working_ifaces():
            label = getattr(iface, "description", None) or iface.name
            result.append({"id": iface.name, "label": label})
    except Exception:
        try:
            for name in scapy.get_if_list():
                result.append({"id": name, "label": name})
        except Exception:
            pass
    return result


class CredentialSniffer:
    """PPPoE/PPP kimlik doğrulama paketlerinden kimlik bilgisi çıkarır.

    on_result(kind, info) ve on_status(mesaj) geri çağırımları verilirse
    (GUI gibi) sonuçlar oraya iletilir; verilmezse ekrana yazdırılır (CLI).
    kind: "pap" | "chap". info: ilgili alanları içeren sözlük.
    """

    def __init__(self, keep_going: bool = False, on_result=None, on_status=None):
        self.keep_going = keep_going
        self._seen = set()
        self.found_pap = False
        self.on_result = on_result
        self.on_status = on_status

    def _emit_status(self, msg: str):
        if self.on_status:
            self.on_status(msg)
        else:
            print(msg)

    def _emit_result(self, kind: str, info: dict):
        if self.on_result:
            self.on_result(kind, info)
        elif kind == "pap":
            print("\n[+] PAP kimlik bilgisi yakalandı!")
            print(f"    Kullanıcı adı : {info['username']}")
            print(f"    Şifre         : {info['password']}\n")
        elif kind == "chap":
            print(f"\n[*] CHAP {info['kind']} yakalandı "
                  "(şifre hash'li, düz metin değil)")
            print(f"    Kullanıcı adı : {info['username']}")
            print(f"    Değer (hex)   : {info['value_hex']}\n")

    # -- PAP: düz metin kullanıcı adı + şifre --
    def _parse_pap(self, data: bytes):
        if len(data) < 4:
            return
        code = data[0]
        if code != PAP_AUTH_REQUEST:
            return  # kimlik bilgisi yalnızca Authenticate-Request'te var
        idx = 4  # code(1) + id(1) + length(2)
        if idx >= len(data):
            return
        ulen = data[idx]
        idx += 1
        username = data[idx:idx + ulen].decode("utf-8", "replace")
        idx += ulen
        if idx >= len(data):
            return
        plen = data[idx]
        idx += 1
        password = data[idx:idx + plen].decode("utf-8", "replace")

        key = ("pap", username, password)
        if key in self._seen:
            return
        self._seen.add(key)
        self.found_pap = True

        self._emit_result("pap", {"username": username, "password": password})

    # -- CHAP: şifre hash'li; kullanıcı adı + challenge/response gösterilir --
    def _parse_chap(self, data: bytes):
        if len(data) < 4:
            return
        code = data[0]
        if code not in (CHAP_CHALLENGE, CHAP_RESPONSE):
            return
        idx = 4  # code(1) + id(1) + length(2)
        if idx >= len(data):
            return
        vsize = data[idx]
        idx += 1
        value = data[idx:idx + vsize]
        idx += vsize
        name = data[idx:].decode("utf-8", "replace")

        kind = "Challenge" if code == CHAP_CHALLENGE else "Response"
        key = ("chap", kind, name, value.hex())
        if key in self._seen:
            return
        self._seen.add(key)

        self._emit_result("chap", {
            "kind": kind, "username": name, "value_hex": value.hex(),
        })

    def handle(self, pkt):
        from scapy.layers.ppp import PPP
        if not pkt.haslayer(PPP):
            return
        ppp = pkt.getlayer(PPP)
        proto = getattr(ppp, "proto", None)
        payload = bytes(ppp.payload)
        if proto == PPP_PROTO_PAP:
            self._parse_pap(payload)
        elif proto == PPP_PROTO_CHAP:
            self._parse_chap(payload)

    def stop_filter(self, pkt):
        self.handle(pkt)
        if self.found_pap and not self.keep_going:
            return True
        return False


def capture(interface: str, timeout: int, write_path: str, keep_going: bool):
    scapy = _import_scapy()
    sniffer = CredentialSniffer(keep_going=keep_going)

    print("Zentra-PPPoE — dinleme başladı.")
    print(f"  Arayüz  : {interface}")
    print(f"  Süre    : {'sınırsız' if timeout == 0 else str(timeout) + ' sn'}")
    print("\n>>> Şimdi modemi yeniden başlatın (gücünü kes-aç) ki yeniden "
          "oturum açarken kimlik bilgilerini yakalayalım.\n")
    print("Durdurmak için Ctrl+C.\n")

    sniff_kwargs = dict(
        iface=interface,
        prn=None,
        store=bool(write_path),
        stop_filter=sniffer.stop_filter,
    )
    if timeout and timeout > 0:
        sniff_kwargs["timeout"] = timeout

    try:
        packets = scapy.sniff(**sniff_kwargs)
    except PermissionError:
        _die("[!] Yetki hatası. Linux/macOS'ta 'sudo' ile çalıştırın, "
             "Windows'ta yönetici olarak açın.")
    except OSError as e:
        _die(f"[!] Arayüz açılamadı ({interface}): {e}\n"
             "Arayüz adını '--list' ile kontrol edin.")
    except KeyboardInterrupt:
        print("\n[*] Durduruldu.")
        packets = None

    if write_path and packets is not None:
        try:
            scapy.wrpcap(write_path, packets)
            print(f"[*] Paketler kaydedildi: {write_path}")
        except Exception as e:
            print(f"[!] pcap kaydedilemedi: {e}", file=sys.stderr)

    if not sniffer.found_pap and not sniffer._seen:
        print("\n[-] Kimlik bilgisi yakalanamadı.")
        print("    - Modemin WAN portu doğru arayüze bağlı mı?")
        print("    - Dinleme sırasında modemi yeniden başlattınız mı?")
        print("    - Bazı modemler CHAP kullanır (şifre düz metin gelmez).")


def build_parser():
    p = argparse.ArgumentParser(
        prog="zentra_pppoe.py",
        description="Zentra-PPPoE — kendi hattınızın PPPoE kimlik bilgilerini "
                    "kurtarın (pasif dinleme).",
        epilog="Yalnızca kendi hattınızda / yetkili olduğunuz hatta kullanın.",
    )
    p.add_argument("-i", "--interface", help="Dinlenecek ağ arayüzü")
    p.add_argument("--list", action="store_true",
                   help="Mevcut arayüzleri listele ve çık")
    p.add_argument("-t", "--timeout", type=int, default=0,
                   help="Dinleme süresi (saniye, 0 = sınırsız)")
    p.add_argument("-w", "--write", metavar="DOSYA.pcap",
                   help="Yakalanan paketleri pcap olarak kaydet")
    p.add_argument("--keep-going", action="store_true",
                   help="Kimlik bulununca durma, dinlemeye devam et")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        list_interfaces()
        return

    if not args.interface:
        parser.error("bir arayüz belirtin (-i) veya --list kullanın")

    capture(args.interface, args.timeout, args.write, args.keep_going)


if __name__ == "__main__":
    main()

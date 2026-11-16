#!/usr/bin/env python3
"""
Zentra-PPPoE — grafik arayüz (Tkinter)
======================================
zentra_pppoe.py'deki yakalama motorunu pencereli bir arayüzle kullanır.

YALNIZCA kendi hattınızda veya yazılı olarak yetkilendirildiğiniz bir hat
üzerinde kullanın. Dinleme için yönetici (Windows) / root (Linux-macOS)
yetkisi ve Npcap (Windows) gerekir.

Çalıştırma:
    python zentra_gui.py
"""

import queue
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from zentra_pppoe import CredentialSniffer, get_interface_list, _import_scapy

# Platforma göre fontlar (her işletim sisteminde düzgün görünsün)
if sys.platform == "darwin":            # macOS
    UI_FONT = "Helvetica Neue"
    MONO_FONT = "Menlo"
elif sys.platform.startswith("win"):    # Windows
    UI_FONT = "Segoe UI"
    MONO_FONT = "Consolas"
else:                                   # Linux / diğer
    UI_FONT = "DejaVu Sans"
    MONO_FONT = "DejaVu Sans Mono"

# Renkler (tema bağımsız, hem motor hem arayüz için)
BG = "#1b1c1e"
CARD = "#242629"
FG = "#e9e9ea"
MUTED = "#9a9b9e"
ACCENT = "#378add"
OK = "#5dcaa5"
BORDER = "#3a3c40"


class ZentraApp:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.sniffer = None
        self.async_sniffer = None
        self.running = False
        self._iface_map = {}

        root.title("Zentra-PPPoE")
        root.configure(bg=BG)
        root.geometry("480x560")
        root.minsize(440, 520)

        self._build_style()
        self._build_ui()
        self._load_interfaces()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(120, self._poll)

    # ---------------- stil ----------------
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=CARD, background=CARD,
                        foreground=FG, arrowcolor=FG, bordercolor=BORDER)
        style.map("TCombobox", fieldbackground=[("readonly", CARD)],
                  foreground=[("readonly", FG)])

    # ---------------- arayüz ----------------
    def _build_ui(self):
        pad = 18
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True, padx=pad, pady=pad)

        # başlık
        head = tk.Frame(wrap, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text="⚡", bg=BG, fg=ACCENT,
                 font=(UI_FONT, 18)).pack(side="left")
        tk.Label(head, text="  PPPoE kimlik kurtarma", bg=BG, fg=FG,
                 font=(UI_FONT, 15, "bold")).pack(side="left")
        tk.Label(wrap, text="Modemin WAN portunu bağla, dinlemeyi başlat.",
                 bg=BG, fg=MUTED, font=(UI_FONT, 10)).pack(anchor="w",
                 pady=(2, 16))

        # arayüz seçici
        tk.Label(wrap, text="Ağ arayüzü", bg=BG, fg=MUTED,
                 font=(UI_FONT, 9)).pack(anchor="w")
        self.iface_var = tk.StringVar()
        self.iface_box = ttk.Combobox(wrap, textvariable=self.iface_var,
                                      state="readonly", font=(UI_FONT, 10))
        self.iface_box.pack(fill="x", pady=(4, 6))

        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x", pady=(0, 14))
        tk.Button(row, text="↻ Yenile", command=self._load_interfaces,
                  bg=CARD, fg=FG, activebackground=BORDER, activeforeground=FG,
                  relief="flat", font=(UI_FONT, 9), cursor="hand2",
                  padx=10, pady=4).pack(side="left")
        self.keepgoing_var = tk.BooleanVar(value=False)
        tk.Checkbutton(row, text="Bulununca durma", variable=self.keepgoing_var,
                       bg=BG, fg=MUTED, selectcolor=CARD, activebackground=BG,
                       activeforeground=FG, font=(UI_FONT, 9)).pack(
                       side="right")

        # başlat/durdur
        self.start_btn = tk.Button(wrap, text="▶  Dinlemeyi başlat",
                                   command=self._toggle, bg=ACCENT, fg="white",
                                   activebackground="#2f78c4",
                                   activeforeground="white", relief="flat",
                                   font=(UI_FONT, 11, "bold"), cursor="hand2",
                                   pady=9)
        self.start_btn.pack(fill="x")

        # durum
        st = tk.Frame(wrap, bg=BG)
        st.pack(fill="x", pady=(14, 8))
        self.status_dot = tk.Label(st, text="●", bg=BG, fg=MUTED,
                                   font=(UI_FONT, 10))
        self.status_dot.pack(side="left")
        self.status_lbl = tk.Label(st, text="  Hazır", bg=BG, fg=MUTED,
                                   font=(UI_FONT, 10))
        self.status_lbl.pack(side="left")

        # sonuç alanı
        self.results = tk.Frame(wrap, bg=BG)
        self.results.pack(fill="both", expand=True, pady=(4, 0))
        self._placeholder = tk.Label(
            self.results,
            text="Henüz kimlik bilgisi yok.\nDinlemeyi başlatıp modemi "
                 "yeniden başlatın.",
            bg=BG, fg=MUTED, font=(UI_FONT, 10), justify="center")
        self._placeholder.pack(expand=True)

        # dipnot
        tk.Label(wrap, text="Yalnızca kendi hattınızda / yetkili olduğunuz "
                 "hatta kullanın.", bg=BG, fg="#6d6e71",
                 font=(UI_FONT, 8)).pack(side="bottom", pady=(10, 0))

    # ---------------- arayüz listesi ----------------
    def _load_interfaces(self):
        try:
            ifaces = get_interface_list()
        except SystemExit:
            ifaces = []
        if not ifaces:
            self.iface_box["values"] = []
            messagebox.showwarning(
                "Zentra-PPPoE",
                "Ağ arayüzü bulunamadı.\n\nscapy kurulu mu? (pip install -r "
                "requirements.txt)\nWindows'ta Npcap gerekir: https://npcap.com/")
            return
        self._iface_map = {i["label"]: i["id"] for i in ifaces}
        labels = list(self._iface_map.keys())
        self.iface_box["values"] = labels
        if labels and not self.iface_var.get():
            self.iface_var.set(labels[0])

    # ---------------- başlat / durdur ----------------
    def _toggle(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        label = self.iface_var.get()
        iface_id = self._iface_map.get(label)
        if not iface_id:
            messagebox.showwarning("Zentra-PPPoE", "Önce bir ağ arayüzü seçin.")
            return
        try:
            scapy = _import_scapy()
        except SystemExit:
            messagebox.showerror("Zentra-PPPoE",
                                 "scapy kurulu değil.\npip install -r "
                                 "requirements.txt")
            return

        self._clear_results()
        self.sniffer = CredentialSniffer(
            keep_going=self.keepgoing_var.get(),
            on_result=self._q_result, on_status=self._q_status)
        try:
            self.async_sniffer = scapy.AsyncSniffer(
                iface=iface_id, prn=self.sniffer.handle, store=False)
            self.async_sniffer.start()
        except Exception as e:
            messagebox.showerror(
                "Zentra-PPPoE",
                f"Dinleme başlatılamadı:\n{e}\n\nYönetici (Windows) / sudo "
                "(Linux-macOS) olarak çalıştırın.")
            return

        self.running = True
        self.start_btn.config(text="■  Durdur", bg="#99353a",
                              activebackground="#7f2b30")
        self._set_status(OK, "Dinleniyor — modemi yeniden başlatın…")

    def _stop(self):
        if self.async_sniffer:
            try:
                self.async_sniffer.stop()
            except Exception:
                pass
        self.async_sniffer = None
        self.running = False
        self.start_btn.config(text="▶  Dinlemeyi başlat", bg=ACCENT,
                              activebackground="#2f78c4")
        self._set_status(MUTED, "Durduruldu")

    # ---------------- thread -> kuyruk ----------------
    def _q_result(self, kind, info):
        self.q.put(("result", kind, info))

    def _q_status(self, msg):
        self.q.put(("status", msg))

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "result":
                    self._show_result(item[1], item[2])
                elif item[0] == "status":
                    self._set_status(MUTED, item[1])
        except queue.Empty:
            pass
        self.root.after(120, self._poll)

    # ---------------- sonuç kartları ----------------
    def _clear_results(self):
        for w in self.results.winfo_children():
            w.destroy()

    def _set_status(self, color, text):
        self.status_dot.config(fg=color)
        self.status_lbl.config(text="  " + text)

    def _show_result(self, kind, info):
        if info is None:
            return
        card = tk.Frame(self.results, bg=CARD, highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(fill="x", pady=6)
        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="x", padx=14, pady=12)

        if kind == "pap":
            tk.Label(inner, text="✓ Kimlik bilgisi yakalandı (PAP)", bg=CARD,
                     fg=OK, font=(UI_FONT, 10, "bold")).pack(anchor="w",
                     pady=(0, 8))
            self._field(inner, "Kullanıcı adı", info["username"])
            self._field(inner, "Şifre", info["password"], copy=True)
            self._set_status(OK, "PAP kimlik bilgisi bulundu")
        else:
            tk.Label(inner, text=f"CHAP {info['kind']} (şifre hash'li)",
                     bg=CARD, fg=MUTED, font=(UI_FONT, 10, "bold")).pack(
                     anchor="w", pady=(0, 8))
            self._field(inner, "Kullanıcı adı", info["username"])
            self._field(inner, "Değer (hex)", info["value_hex"], copy=True)

    def _field(self, parent, label, value, copy=False):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=CARD, fg=MUTED,
                 font=(UI_FONT, 9)).pack(side="left")
        tk.Label(row, text=value, bg=CARD, fg=FG,
                 font=(MONO_FONT, 10)).pack(side="left", padx=(10, 0))
        if copy:
            tk.Button(row, text="kopyala", command=lambda: self._copy(value),
                      bg=CARD, fg=ACCENT, activebackground=BORDER,
                      activeforeground=ACCENT, relief="flat",
                      font=(UI_FONT, 8), cursor="hand2").pack(side="right")

    def _copy(self, value):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self._set_status(OK, "Panoya kopyalandı")

    def _on_close(self):
        if self.running:
            self._stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    ZentraApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

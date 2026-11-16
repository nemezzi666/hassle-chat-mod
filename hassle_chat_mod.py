# -*- coding: utf-8 -*-
"""
Hassle Online — Chat Mod
Собирает pak-мод с настройками чата и ставит его в игру.
"""
import os
import re
import sys
import json
import time
import base64
import ctypes
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk

try:
    import repak
except Exception as exc:  # pragma: no cover
    repak = None
    REPAK_ERROR = exc
else:
    REPAK_ERROR = None

APP_TITLE = "Hassle Online — Chat Mod"
APP_VERSION = "1.0"

DEFAULT_GAME = r"C:\Program Files (x86)\HASSLE GAMES\Hassle Online\HassleOnline"
PAKS_SUB = ("Content", "Paks")
MOD_STEM = "pakchunk999-Windows"
MOUNT_POINT = "../../../HassleOnline/Content/UserInterface/Main/"
PATH_HASH_SEED = 0xCE05F2FB
UI_ENTRY_SUFFIX = "userinterface/main/assets/index.js"

FONT_STEP = 0.15
FONT_BASE = 1.51
LINE_BASE = 2.22

ROWS_MIN, ROWS_MAX, ROWS_DEFAULT = 5, 40, 20
FONT_MIN, FONT_MAX, FONT_DEFAULT = -8, 6, -2

UTOC_B64 = (
    "LT09LS09PS0tPT0tLT09LQgAAACQAAAAAQAAAAEAAAAMAAAAAAAAACAAAAAAAAEAIgAAAAEAAAATInNh"
    "6Q6y6AAAAAAAAAAAAAAAAAAAAAAIAAAAAQAAAP//////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEyJzYekOsugAAAAGAAAAAAAAAAAAQP////8AAAAAAEAAAEAA"
    "AAACAAAALwABAAAA/////////////////////wAAAAAAAAAA3ZMFceQ/T0/Y3zHrvGpJ6DhVpBcAAAAA"
)
UCAS_B64 = (
    "bkNvSQUAAAATInNh6Q6y6AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA8AAAAAAAAAAQAAAAAAAAAAAAA"
    "AA=="
)

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HassleChatMod")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

RESOLUTIONS = [
    ("1920 × 1080", 1920, 1080),
    ("2560 × 1440", 2560, 1440),
    ("3440 × 1440", 3440, 1440),
    ("3840 × 2160", 3840, 2160),
    ("Своё…", 0, 0),
]

PRESETS = [
    ("Оригинал", 10, 0, True),
    ("Компактный", 20, -2, True),
    ("Крупный", 14, 2, True),
]

CHAT_PLAYERS = [
    ("Alexey_Mazuko", "109", "#79d2ff"),
    ("Kirill_Volkov", "47", "#ffd166"),
    ("Daniil_Sokolov", "12", "#c9b6ff"),
    ("Maxim_Orlov", "88", "#8ee6a8"),
    ("Ivan_Romanov", "203", "#ff9e9e"),
    ("Nikita_Belov", "56", "#7fe8f5"),
    ("Egor_Kuznetsov", "31", "#ffe08a"),
    ("Artem_Morozov", "164", "#b7c4ff"),
]
CHAT_MESSAGES = [
    "стрелка у заправки через 10 минут",
    "кто продаёт колёса на гранту?",
    "менты на выезде из города, аккуратнее",
    "подвези до центра, 500 сверху",
    "сходка у клуба в 22:00",
    "тачку на парковке чекни, там вмятина",
    "го на кольцо, ставка 5к",
    "бак пустой, заправь пока я в магазе",
    "принял, выезжаю",
    "+",
]


# ========================  ЛОГИКА  =========================

def paks_dir(game_dir):
    return os.path.join(game_dir, *PAKS_SUB)


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def can_write(folder):
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, ".hcm_write_test")
        with open(probe, "wb") as fh:
            fh.write(b"1")
        os.remove(probe)
        return True
    except Exception:
        return False


def is_game_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq HassleOnline-Win64-Shipping.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout or ""
    except Exception:
        return False
    return "HassleOnline" in out


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def find_ui_pak(paks):
    if repak is None:
        raise RuntimeError("Не установлен модуль repak: %s" % REPAK_ERROR)
    try:
        names = sorted(os.listdir(paks))
    except FileNotFoundError:
        raise RuntimeError("Папка Paks не найдена: %s" % paks)
    errors = []
    for name in names:
        low = name.lower()
        if not low.endswith(".pak") or MOD_STEM in low:
            continue
        full = os.path.join(paks, name)
        try:
            reader = repak.PakBuilder().reader(full)
        except Exception as exc:
            errors.append("%s: %s" % (name, exc))
            continue
        try:
            for entry in reader.files():
                if entry.lower().endswith(UI_ENTRY_SUFFIX):
                    return full, entry
        finally:
            try:
                reader.close()
            except Exception:
                pass
    hint = ""
    if errors:
        hint = "\n\nНе удалось открыть: " + ", ".join(errors[:3])
    raise RuntimeError("В папке Paks не найден UI-пак с assets/index.js." + hint)


def read_ui_js(game_dir):
    paks = paks_dir(game_dir)
    pak_path, entry = find_ui_pak(paks)
    reader = repak.PakBuilder().reader(pak_path)
    try:
        return reader.get(entry)
    finally:
        reader.close()


def parse_chat_settings(js):
    m = re.search(rb"chatPageSize:(-?\d+),chatFontSize:(-?\d+)", js)
    if not m:
        return None
    ts = re.search(rb"chatTimestamps:(!0|!1)", js)
    return {
        "rows": int(m.group(1)),
        "font": int(m.group(2)),
        "timestamps": (ts.group(1) == b"!0") if ts else True,
    }


def patch_ui_js(js, rows, font, timestamps):
    pat = re.compile(rb"chatPageSize:(-?\d+),chatFontSize:(-?\d+)")
    if not pat.search(js):
        raise RuntimeError(
            "В index.js не нашлась строка настроек чата "
            "(chatPageSize:…,chatFontSize:…). Игра, похоже, обновилась."
        )
    new = ("chatPageSize:%d,chatFontSize:%d" % (rows, font)).encode()
    out = pat.sub(new, js, count=1)
    ts_pat = re.compile(rb"chatTimestamps:!0|chatTimestamps:!1")
    ts_new = b"chatTimestamps:!0" if timestamps else b"chatTimestamps:!1"
    if ts_pat.search(out):
        out = ts_pat.sub(ts_new, out, count=1)
    return out


def build_pak(dest_path, js):
    builder = repak.PakBuilder()
    writer = builder.writer(
        dest_path,
        version=repak.Version.V11,
        mount_point=MOUNT_POINT,
        path_hash_seed=PATH_HASH_SEED,
    )
    writer.write_file("assets/index.js", js, compress=False)
    writer.write_index()


def write_mod_files(game_dir, pak_bytes, utoc_bytes, ucas_bytes):
    paks = paks_dir(game_dir)
    os.makedirs(paks, exist_ok=True)
    tmp_dir = os.path.join(paks, ".hcm_tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    def put(name, data):
        tmp = os.path.join(tmp_dir, name)
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, os.path.join(paks, name))

    put(MOD_STEM + ".pak", pak_bytes)
    put(MOD_STEM + ".utoc", utoc_bytes)
    put(MOD_STEM + ".ucas", ucas_bytes)
    try:
        os.rmdir(tmp_dir)
    except Exception:
        pass


def install_mod(game_dir, rows, font, timestamps):
    js = read_ui_js(game_dir)
    patched = patch_ui_js(js, rows, font, timestamps)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp_pak = os.path.join(CONFIG_DIR, "build.pak")
    build_pak(tmp_pak, patched)
    with open(tmp_pak, "rb") as fh:
        pak_bytes = fh.read()
    try:
        os.remove(tmp_pak)
    except Exception:
        pass
    write_mod_files(game_dir, pak_bytes, base64.b64decode(UTOC_B64),
                    base64.b64decode(UCAS_B64))


def uninstall_mod(game_dir):
    removed = []
    paks = paks_dir(game_dir)
    for ext in (".pak", ".utoc", ".ucas"):
        path = os.path.join(paks, MOD_STEM + ext)
        try:
            os.remove(path)
            removed.append(os.path.basename(path))
        except FileNotFoundError:
            pass
    return removed


def installed_settings(game_dir):
    paks = paks_dir(game_dir)
    path = os.path.join(paks, MOD_STEM + ".pak")
    if not os.path.exists(path):
        return None
    reader = repak.PakBuilder().reader(path)
    try:
        entry = None
        for e in reader.files():
            if e.lower().endswith("/assets/index.js"):
                entry = e
                break
        if not entry:
            return None
        return parse_chat_settings(reader.get(entry))
    finally:
        reader.close()



def _hex_rgba(value):
    value = value.lstrip("#")
    if len(value) == 6:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)
    return (255, 255, 255, 255)


def _rounded(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def asset_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# ========================  ИНТЕРФЕЙС  =========================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.game_dir = self.cfg.get("game") or DEFAULT_GAME
        self.rows = int(self.cfg.get("rows", ROWS_DEFAULT))
        self.font = int(self.cfg.get("font", FONT_DEFAULT))
        self.res_index = int(self.cfg.get("res_index", 1))
        self.custom_w = int(self.cfg.get("custom_w", 2560))
        self.custom_h = int(self.cfg.get("custom_h", 1440))
        self.ts = bool(self.cfg.get("ts", True))

        self.title(APP_TITLE)
        try:
            ico = asset_path("icon.ico")
            if os.path.exists(ico):
                self.iconbitmap(default=ico)
        except Exception:
            pass
        self.geometry("1240x900")
        self.minsize(1000, 700)

        self._syncing = False
        self._bg_cache = {}
        self._pil_fonts = {}
        self._preview_key = None
        self._preview_photo = None
        self._font_bold = asset_path(os.path.join("fonts", "HassleOpenSans-Bold.ttf"))
        self._font_reg = asset_path(os.path.join("fonts", "HassleOpenSans-Regular.ttf"))
        self._preview_src = None
        try:
            self._preview_src = Image.open(asset_path("preview.jpg")).convert("RGB")
        except Exception:
            self._preview_src = None

        self.game_var = tk.StringVar(value=self.game_dir)
        self.rows_var = tk.IntVar(value=self.rows)
        self.font_var = tk.IntVar(value=self.font)
        self.ts_var = tk.BooleanVar(value=self.ts)
        self.res_var = tk.StringVar(value=RESOLUTIONS[self.res_index][0])
        self.w_var = tk.StringVar(value=str(self.custom_w))
        self.h_var = tk.StringVar(value=str(self.custom_h))

        self._build()

        self.after(100, self._check_env)
        pending = self.cfg.get("pending")
        if pending:
            self.cfg["pending"] = None
            save_config(self.cfg)
            self.after(250, self.do_install if pending == "install" else self.do_uninstall)

    # ---------- разметка ----------
    def _build(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        game = ttk.LabelFrame(root, text="Папка игры", padding=8)
        game.pack(fill="x")
        ttk.Entry(game, textvariable=self.game_var).pack(side="left", fill="x", expand=True)
        ttk.Button(game, text="Обзор…", width=10, command=self.pick_game).pack(side="left", padx=(6, 0))

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True, pady=(8, 0))

        left = ttk.Frame(body)
        left.pack(side="left", fill="y")

        chat = ttk.LabelFrame(left, text="Чат", padding=10)
        chat.pack(fill="x")

        row1 = ttk.Frame(chat)
        row1.pack(fill="x")
        ttk.Label(row1, text="Строк в чате:").pack(side="left")
        self.rows_spin = ttk.Spinbox(row1, from_=ROWS_MIN, to=ROWS_MAX, width=5,
                                     textvariable=self.rows_var, command=self._rows_spin_changed)
        self.rows_spin.pack(side="right")
        self.rows_scale = ttk.Scale(chat, from_=ROWS_MIN, to=ROWS_MAX, orient="horizontal",
                                    command=self._rows_scale_moved)
        self.rows_scale.pack(fill="x", pady=(3, 10))

        row2 = ttk.Frame(chat)
        row2.pack(fill="x")
        ttk.Label(row2, text="Размер шрифта:").pack(side="left")
        self.font_info = ttk.Label(row2, text="")
        self.font_info.pack(side="right")
        self.font_scale = ttk.Scale(chat, from_=FONT_MIN, to=FONT_MAX, orient="horizontal",
                                    command=self._font_scale_moved)
        self.font_scale.pack(fill="x", pady=(3, 10))

        ttk.Checkbutton(chat, text="Показывать время у сообщений",
                        variable=self.ts_var, command=self._on_change).pack(anchor="w")

        presets = ttk.LabelFrame(left, text="Пресеты", padding=10)
        presets.pack(fill="x", pady=(8, 0))
        for name, rws, fnt, ts in PRESETS:
            ttk.Button(presets, text=name, width=14,
                       command=lambda r=rws, f=fnt, t=ts: self._apply_preset(r, f, t)
                       ).pack(side="left", padx=(0, 6))

        screen = ttk.LabelFrame(left, text="Экран", padding=10)
        screen.pack(fill="x", pady=(8, 0))
        rrow = ttk.Frame(screen)
        rrow.pack(fill="x")
        ttk.Label(rrow, text="Разрешение:").pack(side="left")
        self.res_box = ttk.Combobox(rrow, textvariable=self.res_var, state="readonly",
                                    width=13, values=[r[0] for r in RESOLUTIONS])
        self.res_box.pack(side="right")
        self.res_box.bind("<<ComboboxSelected>>", self._res_changed)

        self.custom_row = ttk.Frame(screen)
        ttk.Label(self.custom_row, text="Ширина:").pack(side="left")
        ttk.Spinbox(self.custom_row, from_=640, to=7680, increment=10, width=6,
                    textvariable=self.w_var).pack(side="left", padx=(4, 10))
        ttk.Label(self.custom_row, text="Высота:").pack(side="left")
        ttk.Spinbox(self.custom_row, from_=480, to=4320, increment=10, width=6,
                    textvariable=self.h_var).pack(side="left", padx=(4, 0))
        if RESOLUTIONS[self.res_index][1] == 0:
            self.custom_row.pack(fill="x", pady=(6, 0))
        self.w_var.trace_add("write", lambda *_: self._on_change())
        self.h_var.trace_add("write", lambda *_: self._on_change())

        preview = ttk.LabelFrame(body, text="Предпросмотр", padding=8)
        preview.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.canvas = tk.Canvas(preview, bg="#f0f0f0", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.draw_preview())

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(8, 0))
        self.status = ttk.Label(bottom, text="", anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        self.btn_uninstall = ttk.Button(bottom, text="Удалить мод", width=14,
                                        command=self.do_uninstall)
        self.btn_uninstall.pack(side="right")
        self.btn_install = ttk.Button(bottom, text="Установить мод", width=17,
                                      command=self.do_install)
        self.btn_install.pack(side="right", padx=(0, 6))

        self._sync_controls()
        self.after(20, self._restore_geometry)
        self.update_idletasks()
        self.draw_preview()

    def _restore_geometry(self):
        geo = self.cfg.get("geometry")
        if geo:
            try:
                m = re.match(r"(\d+)x(\d+)[+-](\d+)[+-](\d+)", geo)
                if m:
                    w, h = int(m.group(1)), int(m.group(2))
                    sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
                    if 800 <= w <= sw - 20 and 500 <= h <= sh - 60:
                        self.geometry(geo)
            except Exception:
                pass
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self._save_cfg()
        self.destroy()

    # ---------- синхронизация ----------
    def _sync_controls(self):
        self._syncing = True
        try:
            self.rows_var.set(self.rows)
            self.rows_scale.set(self.rows)
            self.font_scale.set(self.font)
            self._update_font_label()
        finally:
            self._syncing = False
        self.draw_preview()

    def _update_font_label(self):
        m = self.metrics()
        self.font_info.configure(text="%+d  ·  %.2f vh" % (self.font, m["font_vh"]))

    def _rows_spin_changed(self):
        if self._syncing:
            return
        try:
            value = int(self.rows_var.get())
        except Exception:
            return
        value = max(ROWS_MIN, min(ROWS_MAX, value))
        self.rows = value
        self._syncing = True
        try:
            self.rows_scale.set(value)
        finally:
            self._syncing = False
        self.draw_preview()

    def _rows_scale_moved(self, value):
        if self._syncing:
            return
        value = max(ROWS_MIN, min(ROWS_MAX, int(round(float(value)))))
        if value == self.rows:
            return
        self.rows = value
        self._syncing = True
        try:
            self.rows_var.set(value)
        finally:
            self._syncing = False
        self.draw_preview()

    def _font_scale_moved(self, value):
        if self._syncing:
            return
        value = max(FONT_MIN, min(FONT_MAX, int(round(float(value)))))
        if value == self.font:
            return
        self.font = value
        self._syncing = True
        try:
            self.font_var.set(value)
            self._update_font_label()
        finally:
            self._syncing = False
        self.draw_preview()

    def _on_change(self):
        self.draw_preview()

    def _apply_preset(self, rows, font, ts):
        self.rows = rows
        self.font = font
        self.ts = ts
        self.ts_var.set(ts)
        self._sync_controls()

    def _res_changed(self, _e=None):
        self.res_index = [r[0] for r in RESOLUTIONS].index(self.res_var.get())
        if RESOLUTIONS[self.res_index][1] == 0:
            self.custom_row.pack(fill="x", pady=(6, 0))
        else:
            self.custom_row.pack_forget()
        self.draw_preview()

    # ---------- метрики ----------
    def resolution(self):
        _name, w, h = RESOLUTIONS[self.res_index]
        if w == 0:
            try:
                w = max(320, int(self.w_var.get()))
                h = max(240, int(self.h_var.get()))
            except Exception:
                w, h = 2560, 1440
        return w, h

    def metrics(self):
        font_vh = FONT_BASE + FONT_STEP * self.font
        line_vh = LINE_BASE + FONT_STEP * self.font
        w, h = self.resolution()
        return {
            "font_vh": font_vh, "line_vh": line_vh,
            "font_px": font_vh * h / 100.0, "line_px": line_vh * h / 100.0,
            "box_vh": line_vh * self.rows, "box_px": line_vh * self.rows * h / 100.0,
            "w": w, "h": h,
        }

    # ---------- предпросмотр ----------
    def _pil_font(self, size, bold=True):
        key = (max(6, int(round(size))), bool(bold))
        if key not in self._pil_fonts:
            path = self._font_bold if bold else self._font_reg
            try:
                self._pil_fonts[key] = ImageFont.truetype(path, key[0])
            except Exception:
                self._pil_fonts[key] = ImageFont.load_default()
        return self._pil_fonts[key]

    def _preview_bg(self, w, h):
        key = (w, h)
        if key not in self._bg_cache:
            src = self._preview_src
            sw, sh = src.size
            k = max(w / sw, h / sh)
            cw, ch = int(w / k), int(h / k)
            left, top = (sw - cw) // 2, (sh - ch) // 2
            self._bg_cache[key] = src.crop(
                (left, top, left + cw, top + ch)).resize((w, h), Image.LANCZOS)
            if len(self._bg_cache) > 4:
                self._bg_cache.pop(next(iter(self._bg_cache)))
        return self._bg_cache[key]

    def draw_preview(self):
        c = self.canvas
        try:
            W = c.winfo_width()
            H = c.winfo_height()
        except Exception:
            return
        if W < 40 or H < 40:
            return
        c.delete("all")
        if self._preview_src is None:
            c.create_rectangle(0, 0, W, H, fill="#7d8790", outline="")
            return
        key = (W, H, self.rows, self.font, bool(self.ts_var.get()))
        if key != self._preview_key:
            self._compose_preview(W, H)
            self._preview_key = key
        if self._preview_photo is not None:
            c.create_image(0, 0, image=self._preview_photo, anchor="nw")

    def _compose_preview(self, W, H):
        img = self._preview_bg(W, H).copy().convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        m = self.metrics()

        line = (m["line_vh"] / 100.0) * H
        font_px = line * (m["font_vh"] / m["line_vh"])
        if font_px < 9.0:
            font_px = 9.0
            line = font_px * (m["line_vh"] / m["font_vh"])
        f_msg = self._pil_font(font_px, True)
        f_hint = self._pil_font(font_px * 0.92, False)
        f_small = self._pil_font(8, False)

        text_col = (244, 241, 225, 255)
        num_col = (242, 207, 107, 255)
        level_col = (228, 234, 240, 235)
        stroke = (4, 5, 7, 255)

        x0 = int(W * 0.0166)
        y0 = int(H * 0.035)
        visible = min(self.rows, max(1, int((H - y0 - 10) // line)))

        for i in range(visible):
            nick, level, color = CHAT_PLAYERS[i % len(CHAT_PLAYERS)]
            msg = CHAT_MESSAGES[i % len(CHAT_MESSAGES)]
            y = y0 + line * i
            x = x0
            parts = []
            if self.ts_var.get():
                parts.append(("[%02d:%02d:%02d]" % (21, 56, (19 + i * 5) % 60), text_col))
            parts.append((nick, _hex_rgba(color)))
            parts.append(("[%s]" % level, level_col))
            parts.append((": ", text_col))
            for j, seg in enumerate(re.split(r"(\d+)", msg)):
                if not seg:
                    continue
                parts.append((seg, num_col if j % 2 else text_col))
            for text, col in parts:
                if x > W - 8:
                    break
                d.text((x, y), text, font=f_msg, fill=col,
                       stroke_width=1, stroke_fill=stroke)
                x += f_msg.getlength(text)

        if visible < self.rows:
            note = "показано %d из %d" % (visible, self.rows)
            tw = f_small.getlength(note)
            d.text((W - tw - 10, 8), note, font=f_small,
                   fill=(255, 255, 255, 235), stroke_width=1, stroke_fill=(0, 0, 0, 160))

        info = "%d строк · %.1f%% высоты экрана · %.0f px" % (
            self.rows, m["box_vh"], m["box_px"])
        tw = f_small.getlength(info)
        d.text((W - tw - 10, H - 16), info, font=f_small,
               fill=(255, 255, 255, 235), stroke_width=1, stroke_fill=(0, 0, 0, 160))

        self._preview_photo = ImageTk.PhotoImage(img)

    # ---------- окружение ----------
    def _check_env(self):
        game = self.game_var.get()
        paks = paks_dir(game)
        if not os.path.isdir(paks):
            self.set_status("Папка Content\\Paks не найдена — укажи папку игры.", error=True)
            return
        self.check_state()

    def set_status(self, text, error=False):
        self.status.configure(text=text, foreground="#b00020" if error else "")

    def check_state(self):
        game = self.game_var.get()
        if not os.path.isdir(paks_dir(game)):
            self.set_status("Папка игры не найдена.", error=True)
            return
        try:
            state = installed_settings(game)
        except Exception as exc:
            self.set_status("Не могу прочитать установленный мод: %s" % exc, error=True)
            return
        if state is None:
            self.set_status("Мод не установлен.")
        else:
            self.set_status("Мод установлен: %d строк, шрифт %+d, время %s."
                            % (state["rows"], state["font"],
                               "вкл" if state["timestamps"] else "выкл"))

    # ---------- действия ----------
    def pick_game(self):
        start = self.game_var.get() if os.path.isdir(self.game_var.get()) else DEFAULT_GAME
        chosen = filedialog.askdirectory(title="Выберите папку HassleOnline", initialdir=start)
        if not chosen:
            return
        if os.path.isdir(os.path.join(chosen, *PAKS_SUB)):
            self.game_var.set(chosen)
        elif os.path.isdir(os.path.join(chosen, "HassleOnline", *PAKS_SUB)):
            self.game_var.set(os.path.join(chosen, "HassleOnline"))
        else:
            messagebox.showwarning(
                "Не та папка",
                "Внутри должна быть папка Content\\Paks.\n"
                "Обычно это …\\HASSLE GAMES\\Hassle Online\\HassleOnline")
            return
        self._check_env()

    def _guard_game(self):
        if is_game_running():
            messagebox.showwarning(
                APP_TITLE,
                "Hassle Online сейчас запущен.\n"
                "Полностью закрой игру — pak'и читаются только при старте.")
            return False
        return True

    def _save_cfg(self, pending=None):
        save_config({
            "game": self.game_var.get(),
            "rows": self.rows,
            "font": self.font,
            "ts": bool(self.ts_var.get()),
            "res_index": self.res_index,
            "custom_w": self.resolution()[0],
            "custom_h": self.resolution()[1],
            "geometry": self.geometry() if self.state() == "normal" else "",
            "pending": pending,
        })

    def _relaunch_admin(self, pending):
        self._save_cfg(pending=pending)
        if getattr(sys, "frozen", False):
            exe, params = sys.executable, ""
        else:
            exe, params = sys.executable, '"%s"' % os.path.abspath(__file__)
        try:
            rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params or None, None, 1)
        except Exception as exc:
            self.set_status("Не удалось запросить права администратора: %s" % exc, error=True)
            return
        if rc <= 32:
            self.set_status("Запрос прав администратора отменён.", error=True)
            self._save_cfg(pending=None)
            return
        self.destroy()

    def do_install(self):
        if not self._guard_game():
            return
        if not can_write(paks_dir(self.game_var.get())):
            messagebox.showinfo(
                APP_TITLE,
                "Папка игры защищена (Program Files).\n"
                "Сейчас приложение перезапустится от имени администратора "
                "и сразу поставит мод.")
            self._relaunch_admin("install")
            return
        self.btn_install.configure(state="disabled")
        self.set_status("Собираю pak…")
        self.update_idletasks()
        try:
            t0 = time.time()
            install_mod(self.game_var.get(), self.rows, self.font, self.ts_var.get())
            self._save_cfg()
            self.set_status("Готово за %.1f с: %d строк, шрифт %+d. Запускай игру."
                            % (time.time() - t0, self.rows, self.font))
            self.check_state()
        except Exception as exc:
            self.set_status("Ошибка: %s" % exc, error=True)
            messagebox.showerror(APP_TITLE, "Не удалось установить мод:\n\n%s" % exc)
        finally:
            self.btn_install.configure(state="normal")

    def do_uninstall(self):
        if not self._guard_game():
            return
        if not can_write(paks_dir(self.game_var.get())):
            messagebox.showinfo(APP_TITLE, "Для удаления нужны права администратора.")
            self._relaunch_admin("uninstall")
            return
        try:
            removed = uninstall_mod(self.game_var.get())
        except Exception as exc:
            messagebox.showerror(APP_TITLE, "Не удалось удалить мод:\n\n%s" % exc)
            return
        if removed:
            self.set_status("Удалено: " + ", ".join(removed) + ". Можно запускать игру.")
        else:
            self.set_status("Мод и так не установлен.")


def selftest(report_path):
    lines = []
    ok = True
    try:
        lines.append("repak: %s" % (repak.__file__ if repak else "НЕТ"))
        js = read_ui_js(DEFAULT_GAME)
        lines.append("index.js: %d байт, настройки: %s" % (len(js), parse_chat_settings(js)))
        patched = patch_ui_js(js, 22, -3, False)
        lines.append("патч: %s" % (parse_chat_settings(patched),))
        out = os.path.join(CONFIG_DIR, "selftest.pak")
        os.makedirs(CONFIG_DIR, exist_ok=True)
        build_pak(out, patched)
        lines.append("pak: %d байт" % os.path.getsize(out))
        r = repak.PakBuilder().reader(out)
        back = r.get("HassleOnline/Content/UserInterface/Main/assets/index.js")
        r.close()
        lines.append("обратное чтение: %s" % ("совпало" if back == patched else "РАСХОЖДЕНИЕ"))
        os.remove(out)
    except Exception as exc:
        ok = False
        lines.append("ОШИБКА: %r" % (exc,))
    lines.insert(0, "OK" if ok else "FAIL")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        idx = sys.argv.index("--selftest")
        path = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else os.path.join(CONFIG_DIR, "selftest.txt")
        sys.exit(selftest(path))
    if repak is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_TITLE, "Не найден модуль repak:\n%s" % REPAK_ERROR)
        return
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

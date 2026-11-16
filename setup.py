# -*- coding: utf-8 -*-
"""
Установщик Hassle Chat Mod.
Ставит приложение в профиль пользователя, создаёт ярлыки и запись в
«Установка и удаление программ». Права администратора не нужны.
"""
import os
import sys
import json
import shutil
import ctypes
import winreg
import tempfile
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "Hassle Chat Mod"
APP_ID = "HassleChatMod"
APP_VERSION = "1.0.0"
APP_PUBLISHER = "Hassle Chat Mod"
APP_URL = "https://github.com/nemezzi666/hassle-chat-mod"

INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                           "Programs", APP_ID)
START_MENU = os.path.join(os.environ.get("APPDATA", ""),
                          "Microsoft", "Windows", "Start Menu", "Programs")
DESKTOP = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
UNINST_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\\" + APP_ID
CONFIG_PATH = os.path.join(os.environ.get("APPDATA", ""), APP_ID, "config.json")


def resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def payload(*parts):
    return resource("payload", *parts)


def is_app_running():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq HassleChatMod.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout or ""
    except Exception:
        return False
    return "HassleChatMod" in out


def is_installed():
    return os.path.exists(os.path.join(INSTALL_DIR, "HassleChatMod.exe"))


def make_shortcut(path, target, workdir, icon):
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
        "$s.TargetPath='%s';$s.WorkingDirectory='%s';$s.IconLocation='%s';$s.Save()"
        % (path, target, workdir, icon)
    )
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def remove_shortcuts():
    for p in (os.path.join(DESKTOP, APP_NAME + ".lnk"),
              os.path.join(START_MENU, APP_NAME + ".lnk")):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
        except Exception:
            pass
    folder = os.path.join(START_MENU, APP_NAME)
    if os.path.isdir(folder):
        shutil.rmtree(folder, ignore_errors=True)


def write_uninstall_entry():
    exe = os.path.join(INSTALL_DIR, "HassleChatMod.exe")
    setup = os.path.join(INSTALL_DIR, "Uninstall.exe")
    size = 35 * 1024
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINST_KEY) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, exe)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, INSTALL_DIR)
            winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, APP_URL)
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, size)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                              '"%s" --uninstall' % setup)
    except Exception:
        pass


def delete_uninstall_entry():
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINST_KEY)
    except OSError:
        pass


def game_mod_files():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as fh:
            game = json.load(fh).get("game", "")
    except Exception:
        return []
    if not game:
        return []
    paks = os.path.join(game, "Content", "Paks")
    return [os.path.join(paks, "pakchunk999-Windows" + ext)
            for ext in (".pak", ".utoc", ".ucas")]


class Setup(tk.Tk):
    def __init__(self, uninstall=False, silent=False):
        super().__init__()
        self.uninstall_mode = uninstall
        self.silent = silent
        self.title(("Удаление — " if uninstall else "Установка — ") + APP_NAME)
        self.resizable(False, False)
        try:
            ico = resource("icon.ico")
            if os.path.exists(ico):
                self.iconbitmap(default=ico)
        except Exception:
            pass

        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        head = ttk.Frame(root)
        head.pack(fill="x")
        try:
            self._logo = tk.PhotoImage(file=resource("icon.png")).subsample(6)
            ttk.Label(head, image=self._logo).pack(side="left", padx=(0, 12))
        except Exception:
            self._logo = None

        text = ttk.Frame(head)
        text.pack(side="left", fill="x", expand=True)
        ttk.Label(text, text=APP_NAME, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(text, text="Версия %s — мод настроек чата для Hassle Online" % APP_VERSION,
                  foreground="#555").pack(anchor="w")
        ttk.Label(text, text="Папка установки: " + INSTALL_DIR,
                  foreground="#555", wraplength=460).pack(anchor="w", pady=(6, 0))

        self.info = ttk.Label(root, text="", wraplength=560, foreground="#555")
        self.info.pack(fill="x", pady=(12, 0))

        self.desktop_var = tk.BooleanVar(value=True)
        if not uninstall:
            ttk.Checkbutton(root, text="Создать ярлык на рабочем столе",
                            variable=self.desktop_var).pack(anchor="w", pady=(10, 0))

        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(16, 0))
        self.status = ttk.Label(btns, text="", foreground="#555")
        self.status.pack(side="left")

        if uninstall:
            ttk.Button(btns, text="Удалить", width=14, command=self.do_uninstall).pack(side="right")
        else:
            if is_installed():
                ttk.Button(btns, text="Удалить", width=12,
                           command=self.do_uninstall).pack(side="right")
                ttk.Button(btns, text="Переустановить", width=16,
                           command=self.do_install).pack(side="right", padx=(0, 6))
            else:
                ttk.Button(btns, text="Установить", width=14,
                           command=self.do_install).pack(side="right")
        ttk.Button(btns, text="Закрыть", width=10, command=self.destroy).pack(side="right", padx=(0, 6))

        self.geometry("+%d+%d" % (self.winfo_screenwidth() // 2 - 320,
                                  self.winfo_screenheight() // 3))
        self.after(100, self.refresh)
        if uninstall:
            self.after(250, self.do_uninstall)

    def refresh(self):
        if is_installed():
            self.info.configure(text="Приложение уже установлено. Можно переустановить "
                                     "или удалить.")
        else:
            self.info.configure(text="Будет установлено в папку пользователя — "
                                     "права администратора не требуются.")

    def set_status(self, text):
        self.status.configure(text=text)
        self.update_idletasks()

    def do_install(self):
        if is_app_running():
            if not self.silent:
                messagebox.showwarning(APP_NAME, "Сначала закрой запущенное приложение.")
            return
        self.set_status("Копирую файлы…")
        try:
            os.makedirs(INSTALL_DIR, exist_ok=True)
            for name in ("HassleChatMod.exe", "README.md", "LICENSE"):
                src = payload(name)
                if os.path.exists(src):
                    shutil.copyfile(src, os.path.join(INSTALL_DIR, name))
            icon_src = resource("icon.ico")
            if os.path.exists(icon_src):
                shutil.copyfile(icon_src, os.path.join(INSTALL_DIR, "icon.ico"))
            shutil.copyfile(os.path.abspath(sys.executable),
                            os.path.join(INSTALL_DIR, "Uninstall.exe"))

            exe = os.path.join(INSTALL_DIR, "HassleChatMod.exe")
            icon = os.path.join(INSTALL_DIR, "icon.ico")
            make_shortcut(os.path.join(START_MENU, APP_NAME + ".lnk"), exe, INSTALL_DIR, icon)
            if self.desktop_var.get():
                make_shortcut(os.path.join(DESKTOP, APP_NAME + ".lnk"), exe, INSTALL_DIR, icon)
            write_uninstall_entry()
            self.set_status("Готово.")
            if not self.silent:
                messagebox.showinfo(APP_NAME, "Установлено.\n\nЯрлык: меню «Пуск»"
                                    + (" и рабочий стол." if self.desktop_var.get() else "."))
            self.refresh()
        except Exception as exc:
            self.set_status("Ошибка установки")
            if not self.silent:
                messagebox.showerror(APP_NAME, "Не удалось установить:\n\n%s" % exc)

    def do_uninstall(self):
        if is_app_running():
            if not self.silent:
                messagebox.showwarning(APP_NAME, "Сначала закрой запущенное приложение.")
            return
        if not self.silent and not messagebox.askyesno(APP_NAME, "Удалить %s?" % APP_NAME):
            return
        self.set_status("Удаляю…")
        remove_shortcuts()
        delete_uninstall_entry()

        # предложить убрать мод из игры
        mods = [p for p in game_mod_files() if os.path.exists(p)]
        if mods and not self.silent:
            if messagebox.askyesno(APP_NAME, "Убрать мод чата из установленной игры?"):
                for p in mods:
                    try:
                        os.remove(p)
                    except Exception as exc:
                        messagebox.showwarning(APP_NAME, "Не удалось удалить %s:\n%s" % (p, exc))

        # удалить папку (сам setup может быть запущен из неё)
        self_exe = os.path.abspath(sys.executable)
        tmp = None
        if os.path.dirname(self_exe).lower() == INSTALL_DIR.lower():
            tmp = os.path.join(tempfile.gettempdir(), "hcm_uninstall_%d.exe" % os.getpid())
            try:
                os.replace(self_exe, tmp)
            except Exception:
                tmp = None
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
        if tmp:
            try:
                subprocess.Popen(
                    ["cmd", "/c", "ping", "-n", "3", "127.0.0.1", ">nul", "&",
                     "del", "/f", "/q", tmp],
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                pass
        self.set_status("Удалено.")
        if not self.silent:
            messagebox.showinfo(APP_NAME, "Приложение удалено.")
        self.destroy()


def main():
    uninstall = "--uninstall" in sys.argv
    silent = "--silent" in sys.argv
    app = Setup(uninstall=uninstall, silent=silent)
    if silent:
        app.withdraw()
        app.update()
        if uninstall:
            app.do_uninstall()
        else:
            app.do_install()
        return
    app.mainloop()


if __name__ == "__main__":
    main()

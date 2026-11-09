"""Inicializador do aplicativo gráfico."""

from __future__ import annotations

import ctypes
import os
import tkinter as tk
from tkinter import messagebox

from coletor_datasets.gui import App


def _ativar_dpi_do_windows() -> None:
    """Pede ao Windows renderização nítida em monitores de alta densidade."""
    if os.name != "nt":
        return
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        definir_contexto = user32.SetProcessDpiAwarenessContext
        definir_contexto.argtypes = [ctypes.c_void_p]
        definir_contexto.restype = ctypes.c_bool
        if definir_contexto(ctypes.c_void_p(-4)):  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            return
    except (AttributeError, OSError):
        pass
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        definir_dpi = shcore.SetProcessDpiAwareness
        definir_dpi.argtypes = [ctypes.c_int]
        definir_dpi.restype = ctypes.c_long
        if definir_dpi(2) == 0:  # PROCESS_PER_MONITOR_DPI_AWARE
            return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.WinDLL("user32", use_last_error=True).SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def main() -> int:
    _ativar_dpi_do_windows()
    try:
        root = tk.Tk()
    except tk.TclError as erro:
        print(f"Não foi possível abrir a interface gráfica: {erro}")
        return 1
    try:
        App(root)
        root.mainloop()
    except Exception as erro:  # a GUI apresenta falhas inesperadas sem perder o contexto
        messagebox.showerror("Erro ao abrir", str(erro))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


"""
gui.py — Sazon Desktop Assistant UI
Complete unified GUI module with:
  - Screen-share privacy (WDA_EXCLUDEFROMCAPTURE)
  - Animated docked bot orb + center expandable dialogue
  - Smooth 60fps window geometry morphing
  - Custom titlebar, status card, quick-action chips, input bar, and console log
"""
import os
import sys
import ctypes
import threading
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
from typing import Optional, Callable, List, Tuple

from dotenv import load_dotenv
load_dotenv()

from config import Theme, WDA_EXCLUDEFROMCAPTURE, WDA_MONITOR
from agent import GoalRequest, TaskStatus, SazonExecutor, default_registry

# Quick action chip presets
_QUICK_ACTIONS = [
    ("💻 System Status", "Check system status and hardware diagnostic details"),
    ("🔍 Find Files",    "Search for files in the current workspace"),
    ("📝 Create Report", "Create a summary report of the current environment"),
]

# Model presets for manual selection
_MODEL_PRESETS = [
    {"label": "🤖 Sazon",                  "provider": "sample",  "model": "sazon"},
    {"label": "⚡ Gemini 2.5 Flash",       "provider": "gemini",  "model": "gemini-2.5-flash"},
    {"label": "🧠 Gemini 1.5 Pro",         "provider": "gemini",  "model": "gemini-1.5-pro"},
    {"label": "🚀 GPT-4o Mini",            "provider": "openai",  "model": "gpt-4o-mini"},
    {"label": "🔥 GPT-4o",                 "provider": "openai",  "model": "gpt-4o"},
    {"label": "💻 Local Heuristic",        "provider": "local",   "model": "heuristic"},
]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Screen-Share Privacy Protection
# ─────────────────────────────────────────────────────────────────────────────

def apply_screen_share_privacy(window: tk.Tk) -> bool:
    """
    Excludes the window from screen capture/sharing (Zoom, Teams, Discord, OBS, screenshots).
    """
    if sys.platform != "win32":
        return False
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        ok = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        if not ok:
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
        return True
    except Exception as e:
        print(f"[Sazon] Screen-share privacy notice: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 2. Smooth Animation Primitives
# ─────────────────────────────────────────────────────────────────────────────

def blend_hex(c1: str, c2: str, t: float) -> str:
    """Linearly blend two hex colors: t=0 -> c1, t=1 -> c2."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + t * (r2 - r1))
    g = int(g1 + t * (g2 - g1))
    b = int(b1 + t * (b2 - b1))
    return f"#{r:02x}{g:02x}{b:02x}"


def ease_in_out(t: float) -> float:
    """Smooth cubic ease-in-out curve clamped to [0, 1]."""
    t = max(0.0, min(1.0, t))
    return 3 * t * t - 2 * t * t * t


class HoverEffect:
    """Smooth background color transition on widget hover."""

    def __init__(self, widget: tk.Widget, base_color: str, hover_color: str, steps: int = 5, interval: int = 18):
        self.widget      = widget
        self.base_color  = base_color
        self.hover_color = hover_color
        self.steps       = steps
        self.interval    = interval
        self._after_id: Optional[str] = None
        self._current_step: float = 0.0
        self._direction: int = 0

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _on_enter(self, _=None):
        self._direction = 1
        self._cancel()
        self._animate()

    def _on_leave(self, _=None):
        self._direction = -1
        self._cancel()
        self._animate()

    def _animate(self):
        if self._direction == 0:
            return
        self._current_step = max(0.0, min(float(self.steps), self._current_step + self._direction))
        t = ease_in_out(self._current_step / self.steps)
        color = blend_hex(self.base_color, self.hover_color, t)
        try:
            self.widget["bg"] = color
        except Exception:
            return

        needs_more = (
            (self._direction == 1 and self._current_step < float(self.steps))
            or (self._direction == -1 and self._current_step > 0.0)
        )
        if needs_more:
            self._after_id = self.widget.after(self.interval, self._animate)
        else:
            self._after_id = None
            self._direction = 0


class OrbPulse:
    """Breathing glow animation for canvas rings."""

    def __init__(self, canvas: tk.Canvas, ring_ids: List[int], base_colors: List[str], bright_color: str = Theme.CYAN, interval: int = 50):
        self.canvas       = canvas
        self.ring_ids     = ring_ids
        self.base_colors  = base_colors
        self.bright_color = bright_color
        self.interval     = interval
        self._phase       = 0.0
        self._after_id: Optional[str] = None
        self._running     = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self):
        self._running = False
        if self._after_id:
            try:
                self.canvas.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _tick(self):
        if not self._running:
            return
        import math
        self._phase = (self._phase + 0.10) % (2 * math.pi)
        sine = 0.5 * (1.0 + math.sin(self._phase))

        for item_id, base_col in zip(self.ring_ids, self.base_colors):
            c = blend_hex(base_col, self.bright_color, sine * 0.70)
            try:
                self.canvas.itemconfig(item_id, outline=c)
            except Exception:
                self._running = False
                return

        if self._running:
            self._after_id = self.canvas.after(self.interval, self._tick)


class StatusDotPulse:
    """Pulse indicator for status label."""

    def __init__(self, label: tk.Label, color_dim: str, color_bright: str, interval: int = 700):
        self.label        = label
        self.color_dim    = color_dim
        self.color_bright = color_bright
        self.interval     = interval
        self._state       = False
        self._after_id: Optional[str] = None
        self._running     = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self, final_color: Optional[str] = None):
        self._running = False
        if self._after_id:
            try:
                self.label.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if final_color:
            try:
                self.label.configure(fg=final_color)
            except Exception:
                pass

    def _tick(self):
        if not self._running:
            return
        self._state = not self._state
        color = self.color_bright if self._state else self.color_dim
        try:
            self.label.configure(fg=color)
        except Exception:
            return
        if self._running:
            self._after_id = self.label.after(self.interval, self._tick)


class GeometryMorph:
    """Hardware-synced window geometry animator for ultra-smooth transitions."""

    def __init__(self, root: tk.Tk, steps: int = 10, interval: int = 16):
        self.root     = root
        self.steps    = steps
        self.interval = interval
        self._after_id: Optional[str] = None

    def cancel(self):
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def morph(self, from_geom: tuple, to_geom: tuple, on_complete: Optional[Callable] = None):
        self.cancel()
        self._step(from_geom, to_geom, 1, on_complete)

    def _step(self, from_geom: tuple, to_geom: tuple, step: int, on_complete: Optional[Callable]):
        t = ease_in_out(step / self.steps)
        w = int(from_geom[0] + t * (to_geom[0] - from_geom[0]))
        h = int(from_geom[1] + t * (to_geom[1] - from_geom[1]))
        x = int(from_geom[2] + t * (to_geom[2] - from_geom[2]))
        y = int(from_geom[3] + t * (to_geom[3] - from_geom[3]))

        try:
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.root.update_idletasks()
        except Exception:
            return

        if step < self.steps:
            self._after_id = self.root.after(self.interval, self._step, from_geom, to_geom, step + 1, on_complete)
        else:
            self._after_id = None
            try:
                self.root.geometry(f"{to_geom[0]}x{to_geom[1]}+{to_geom[2]}+{to_geom[3]}")
                self.root.update_idletasks()
            except Exception:
                pass
            if on_complete:
                on_complete()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Widgets
# ─────────────────────────────────────────────────────────────────────────────

class OrbWidget(tk.Frame):
    """Glowing circular bot mascot orb with concentric rings."""

    def __init__(self, parent: tk.Widget, on_click: Callable, **kwargs):
        super().__init__(parent, bg=Theme.BG_DARK, **kwargs)
        self._on_click = on_click
        self._pulse: Optional[OrbPulse] = None
        self._build()

    def _build(self):
        c, r = 38, 27
        self.canvas = tk.Canvas(self, width=76, height=76, bg=Theme.BG_DARK, highlightthickness=0, cursor="hand2")
        self.canvas.pack(expand=True)

        self._ring3 = self.canvas.create_oval(c-r-12, c-r-12, c+r+12, c+r+12, outline=Theme.CYAN_DARK, width=1)
        self._ring2 = self.canvas.create_oval(c-r-7, c-r-7, c+r+7, c+r+7, outline=Theme.CYAN_DIM, width=1)
        self._ring1 = self.canvas.create_oval(c-r-3, c-r-3, c+r+3, c+r+3, outline=Theme.CYAN, width=2)
        self._circle = self.canvas.create_oval(c-r, c-r, c+r, c+r, fill=Theme.BG_CARD, outline=Theme.CYAN, width=2)
        self._emoji = self.canvas.create_text(c, c-3, text="🤖", font=(Theme.FONT_EMOJI, 19))
        self._label = self.canvas.create_text(c, c+20, text="SAZON", fill=Theme.CYAN, font=(Theme.FONT_UI, 7, "bold"))

        for item in (self._circle, self._emoji, self._label, self._ring1):
            self.canvas.tag_bind(item, "<Button-1>", lambda _e: self._on_click())
        self.canvas.bind("<Button-1>", lambda _e: self._on_click())

        self._pulse = OrbPulse(self.canvas, [self._ring1, self._ring2, self._ring3], [Theme.CYAN_DIM, Theme.CYAN_DARK, "#031e2a"], Theme.CYAN)
        self._pulse.start()

    def stop_pulse(self):
        if self._pulse:
            self._pulse.stop()

    def start_pulse(self):
        if self._pulse:
            self._pulse.start()


class TitleBar(tk.Frame):
    """Header bar with animated status, stealth badge, and dock/close controls."""

    def __init__(self, parent: tk.Widget, on_dock: Callable, on_close: Callable, **kwargs):
        super().__init__(parent, bg=Theme.BG_ELEVATED, height=46, **kwargs)
        self.pack_propagate(False)
        self._on_dock = on_dock
        self._on_close = on_close
        self._dot_pulse: Optional[StatusDotPulse] = None
        self._build()

    def _build(self):
        left = tk.Frame(self, bg=Theme.BG_ELEVATED)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(14, 0))

        self._dot = tk.Label(left, text="●", fg=Theme.GREEN, bg=Theme.BG_ELEVATED, font=(Theme.FONT_UI, 11, "bold"))
        self._dot.pack(side=tk.LEFT, padx=(0, 7))

        tk.Label(left, text="SAZON", fg=Theme.TEXT_WHITE, bg=Theme.BG_ELEVATED, font=(Theme.FONT_UI, 11, "bold")).pack(side=tk.LEFT)
        self._status_lbl = tk.Label(left, text="  Ready", fg=Theme.TEXT_MUTED, bg=Theme.BG_ELEVATED, font=(Theme.FONT_UI, 9))
        self._status_lbl.pack(side=tk.LEFT)

        right = tk.Frame(self, bg=Theme.BG_ELEVATED)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6))

        self._stealth_lbl = tk.Label(right, text="🛡 STEALTH", fg=Theme.GREEN, bg=Theme.BG_ELEVATED, font=(Theme.FONT_UI, 8, "bold"), padx=4)
        self._stealth_lbl.pack(side=tk.LEFT, padx=(0, 10))

        tk.Frame(right, bg=Theme.BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y, pady=10, padx=(0, 6))

        dock_btn = tk.Button(right, text="⊟", bg=Theme.BG_ELEVATED, fg=Theme.TEXT_SUBTLE, activebackground=Theme.BG_HOVER, activeforeground=Theme.CYAN, font=(Theme.FONT_UI, 13), bd=0, relief="flat", cursor="hand2", padx=9, command=self._on_dock)
        dock_btn.pack(side=tk.LEFT)
        HoverEffect(dock_btn, Theme.BG_ELEVATED, Theme.BG_HOVER)

        close_btn = tk.Button(right, text="✕", bg=Theme.BG_ELEVATED, fg=Theme.TEXT_SUBTLE, activebackground="#3d1515", activeforeground="#f87171", font=(Theme.FONT_UI, 11, "bold"), bd=0, relief="flat", cursor="hand2", padx=9, command=self._on_close)
        close_btn.pack(side=tk.LEFT)
        HoverEffect(close_btn, Theme.BG_ELEVATED, "#2a1010")

        tk.Frame(self, bg=Theme.BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)
        self._dot_pulse = StatusDotPulse(self._dot, Theme.GREEN_DIM, Theme.GREEN, interval=900)
        self._dot_pulse.start()

    def bind_drag(self, on_start: Callable, on_drag: Callable):
        for w in [self, *self.winfo_children()]:
            w.bind("<Button-1>", on_start, add="+")
            w.bind("<B1-Motion>", on_drag, add="+")

    def set_status(self, status: str, label: str = ""):
        _cfg = {
            "ready":   (Theme.GREEN_DIM, Theme.GREEN, "  Ready"),
            "running": (Theme.AMBER_DIM, Theme.AMBER, f"  {label or 'Running...'}"),
            "done":    (Theme.GREEN_DIM, Theme.GREEN, "  Done ✓"),
            "error":   (Theme.RED_DIM,   Theme.RED,   "  Error ✗"),
        }
        dim, bright, text = _cfg.get(status, (Theme.GREEN_DIM, Theme.GREEN, "  Ready"))
        self._status_lbl.config(text=text)
        if self._dot_pulse:
            self._dot_pulse.stop()
        self._dot_pulse = StatusDotPulse(self._dot, dim, bright)
        self._dot_pulse.start()

    def set_stealth(self, active: bool):
        self._stealth_lbl.config(
            fg=Theme.GREEN if active else Theme.TEXT_MUTED,
            text="🛡 STEALTH" if active else "○ STEALTH"
        )


class StatusCard(tk.Frame):
    """Metadata summary card displaying real-time agent properties and model switcher."""

    def __init__(self, parent: tk.Widget, on_select_model: Optional[Callable[[str, str, str], None]] = None, **kwargs):
        super().__init__(parent, bg=Theme.BG_CARD, padx=14, pady=12, **kwargs)
        self._meta_labels: dict = {}
        self._on_select_model = on_select_model
        has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"))
        if has_api_key:
            self._active_model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            self._active_display = "⚡ Gemini 2.5 Flash"
        else:
            self._active_model_name = "sazon"
            self._active_display = "🤖 Sazon"
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=Theme.BG_CARD)
        top.pack(fill=tk.X)
        tk.Label(top, text="🤖  SAZON AGENT", bg=Theme.BG_CARD, fg=Theme.TEXT_WHITE, font=(Theme.FONT_UI, 11, "bold")).pack(side=tk.LEFT)
        tk.Label(top, text="● LIVE", bg=Theme.BG_CARD, fg=Theme.GREEN, font=(Theme.FONT_UI, 8, "bold"), padx=4).pack(side=tk.RIGHT)

        tk.Frame(self, bg=Theme.BORDER, height=1).pack(fill=tk.X, pady=(8, 8))

        meta_row = tk.Frame(self, bg=Theme.BG_CARD)
        meta_row.pack(fill=tk.X)

        # Interactive Model Switcher
        model_col = tk.Frame(meta_row, bg=Theme.BG_CARD)
        model_col.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(model_col, text="MODEL (CLICK TO SWITCH)", bg=Theme.BG_CARD, fg=Theme.CYAN, font=(Theme.FONT_UI, 7, "bold")).pack(anchor="w")

        self._model_btn = tk.Button(
            model_col, text=f"{self._active_display} ▾",
            bg=Theme.BG_CARD, fg=Theme.TEXT_WHITE, activebackground=Theme.BG_ELEVATED, activeforeground=Theme.CYAN,
            font=(Theme.FONT_UI, 9, "bold"), bd=0, relief="flat", cursor="hand2", padx=2, pady=1,
            command=self._show_model_menu
        )
        self._model_btn.pack(anchor="w")
        HoverEffect(self._model_btn, Theme.BG_CARD, Theme.BG_ELEVATED)
        self._meta_labels["model"] = self._model_btn

        self._meta_labels["privacy"] = self._meta_col(meta_row, "PRIVACY",  "🛡 ON")
        self._meta_labels["memory"]  = self._meta_col(meta_row, "MEMORY",   "—")
        self._meta_labels["last"]    = self._meta_col(meta_row, "LAST RUN", "—")

        tk.Label(
            self, text="Run commands  ·  Search files  ·  Inspect hardware  ·  Automate tasks",
            bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_UI, 8), wraplength=490, justify="left"
        ).pack(anchor="w", pady=(10, 0))

    def _show_model_menu(self):
        menu = tk.Menu(
            self, tearoff=0, bg=Theme.BG_ELEVATED, fg=Theme.TEXT_WHITE,
            activebackground=Theme.INDIGO, activeforeground=Theme.TEXT_WHITE,
            font=(Theme.FONT_UI, 9), bd=1, relief="solid"
        )
        for p in _MODEL_PRESETS:
            label = p["label"]
            prov = p["provider"]
            mdl = p["model"]
            is_active = (mdl == self._active_model_name)
            prefix = "✓ " if is_active else "   "
            menu.add_command(
                label=f"{prefix}{label}",
                command=lambda pr=prov, m=mdl, lb=label: self._set_model(pr, m, lb)
            )
        menu.add_separator()
        menu.add_command(label="   ✏️ Enter Custom Model Name...", command=self._prompt_custom_model)

        try:
            x = self._model_btn.winfo_rootx()
            y = self._model_btn.winfo_rooty() + self._model_btn.winfo_height() + 2
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _prompt_custom_model(self):
        from tkinter import simpledialog
        custom = simpledialog.askstring(
            "Custom Model",
            "Enter custom model identifier (e.g. gemini-2.0-flash, gpt-4o, o3-mini):",
            parent=self.winfo_toplevel()
        )
        if custom and custom.strip():
            c_model = custom.strip()
            p_lower = c_model.lower()
            provider = "openai" if ("gpt" in p_lower or "o1" in p_lower or "o3" in p_lower) else "gemini"
            self._set_model(provider, c_model, f"⚙️ {c_model}")

    def _set_model(self, provider: str, model: str, display: str):
        self._active_model_name = model
        self._active_display = display
        self._model_btn.config(text=f"{display} ▾")
        if self._on_select_model:
            self._on_select_model(provider, model, display)

    def _meta_col(self, parent: tk.Frame, key: str, value: str) -> tk.Label:
        col = tk.Frame(parent, bg=Theme.BG_CARD)
        col.pack(side=tk.LEFT, padx=(0, 24))
        tk.Label(col, text=key, bg=Theme.BG_CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_UI, 7, "bold")).pack(anchor="w")
        val = tk.Label(col, text=value, bg=Theme.BG_CARD, fg=Theme.TEXT_SUBTLE, font=(Theme.FONT_UI, 9))
        val.pack(anchor="w")
        return val

    def update_meta(self, model: Optional[str] = None, memory_count: Optional[int] = None, last_time: Optional[float] = None, stealth: Optional[bool] = None):
        if model is not None:
            self._model_btn.config(text=f"{model} ▾")
        if memory_count is not None:
            self._meta_labels["memory"].config(text=f"{memory_count} items")
        if last_time is not None:
            self._meta_labels["last"].config(text=f"{last_time:.1f}s")
        if stealth is not None:
            self._meta_labels["privacy"].config(text="🛡 ON" if stealth else "✕ OFF", fg=Theme.GREEN if stealth else Theme.RED)


class ChipBar(tk.Frame):
    """Quick-action suggestion buttons."""

    def __init__(self, parent: tk.Widget, chips: List[Tuple[str, str]], on_click: Callable[[str], None], **kwargs):
        super().__init__(parent, bg=Theme.BG_DARK, **kwargs)
        for text, prompt in chips:
            btn = tk.Button(
                self, text=text, bg=Theme.BG_CARD, fg=Theme.CYAN,
                activebackground=Theme.BG_ELEVATED, activeforeground=Theme.TEXT_WHITE,
                font=(Theme.FONT_UI, 9), bd=0, relief="flat", cursor="hand2", padx=12, pady=5,
                command=lambda p=prompt: on_click(p)
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            HoverEffect(btn, Theme.BG_CARD, Theme.BG_ELEVATED)


class InputBar(tk.Frame):
    """Execution input bar with character counter and run button."""

    def __init__(self, parent: tk.Widget, on_execute: Callable[[], None], **kwargs):
        super().__init__(parent, bg=Theme.BG_DARK, **kwargs)
        self._on_execute = on_execute
        self._build()

    def _build(self):
        self._border = tk.Frame(self, bg=Theme.BORDER, padx=1, pady=1)
        self._border.pack(fill=tk.X)

        inner = tk.Frame(self._border, bg=Theme.BG_INPUT)
        inner.pack(fill=tk.X)

        tk.Label(inner, text="⚡", bg=Theme.BG_INPUT, fg=Theme.CYAN, font=(Theme.FONT_UI, 11), padx=8).pack(side=tk.LEFT)

        self.entry = tk.Entry(inner, bg=Theme.BG_INPUT, fg=Theme.TEXT_WHITE, insertbackground=Theme.CYAN, font=(Theme.FONT_UI, 10), bd=0, relief="flat")
        self.entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=9)
        self.entry.bind("<Return>", lambda _e: self._on_execute())
        self.entry.bind("<FocusIn>", lambda _e: self._border.configure(bg=Theme.CYAN_DIM))
        self.entry.bind("<FocusOut>", lambda _e: self._border.configure(bg=Theme.BORDER))

        self.run_btn = tk.Button(
            inner, text="Execute ▶", bg=Theme.INDIGO, fg=Theme.TEXT_WHITE,
            activebackground=Theme.INDIGO_DARK, activeforeground=Theme.TEXT_WHITE,
            font=(Theme.FONT_UI, 9, "bold"), bd=0, relief="flat", cursor="hand2", padx=18, pady=9,
            command=self._on_execute
        )
        self.run_btn.pack(side=tk.RIGHT)
        HoverEffect(self.run_btn, Theme.INDIGO, Theme.INDIGO_LIGHT)

    def get(self) -> str:
        return self.entry.get().strip()

    def set(self, text: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, text)

    def focus(self):
        self.entry.focus_set()

    def set_executing(self, running: bool):
        if running:
            self.run_btn.config(state=tk.DISABLED, bg=Theme.BG_ELEVATED, text="Running…")
            self.entry.config(state=tk.DISABLED)
        else:
            self.run_btn.config(state=tk.NORMAL, bg=Theme.INDIGO, text="Execute ▶")
            self.entry.config(state=tk.NORMAL)


class ConsoleWidget(tk.Frame):
    """Scrolled terminal-style execution log."""

    _SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, bg=Theme.BG_DARK, **kwargs)
        self._spinner_active = False
        self._spinner_idx = 0
        self._spinner_task = ""
        self._spinner_after_id: Optional[str] = None
        self._build()

    def _build(self):
        header = tk.Frame(self, bg=Theme.BG_ELEVATED)
        header.pack(fill=tk.X)
        tk.Label(header, text="── EXECUTION LOG", bg=Theme.BG_ELEVATED, fg=Theme.TEXT_MUTED, font=(Theme.FONT_UI, 8, "bold"), padx=12, pady=6).pack(side=tk.LEFT)
        clear_btn = tk.Button(header, text="Clear", bg=Theme.BG_ELEVATED, fg=Theme.TEXT_MUTED, activebackground=Theme.BG_HOVER, activeforeground=Theme.TEXT_WHITE, font=(Theme.FONT_UI, 8), bd=0, relief="flat", cursor="hand2", padx=10, pady=3, command=self.clear)
        clear_btn.pack(side=tk.RIGHT, padx=6, pady=4)

        self.text = scrolledtext.ScrolledText(self, bg="#020617", fg=Theme.TEXT_WHITE, insertbackground=Theme.TEXT_WHITE, font=(Theme.FONT_MONO, 9), bd=0, relief="flat", wrap=tk.WORD, state=tk.DISABLED)
        self.text.pack(fill=tk.BOTH, expand=True)

        self.text.tag_config("ts",      foreground="#334155",    font=(Theme.FONT_MONO, 8))
        self.text.tag_config("title",   foreground=Theme.CYAN,   font=(Theme.FONT_MONO, 9, "bold"))
        self.text.tag_config("task",    foreground=Theme.VIOLET, font=(Theme.FONT_MONO, 9, "bold"))
        self.text.tag_config("success", foreground=Theme.GREEN,  font=(Theme.FONT_MONO, 9, "bold"))
        self.text.tag_config("error",   foreground=Theme.RED,    font=(Theme.FONT_MONO, 9, "bold"))
        self.text.tag_config("dim",     foreground=Theme.TEXT_MUTED)

        self._spinner_strip = tk.Frame(self, bg=Theme.BG_ELEVATED, padx=12, pady=4)
        self._spinner_lbl = tk.Label(self._spinner_strip, text="", bg=Theme.BG_ELEVATED, fg=Theme.AMBER, font=(Theme.FONT_MONO, 9, "bold"))
        self._spinner_lbl.pack(side=tk.LEFT)

    def append(self, text: str, tag: Optional[str] = None):
        ts = datetime.now().strftime("%H:%M:%S")
        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, f"[{ts}] ", "ts")
        self.text.insert(tk.END, text + "\n", tag) if tag else self.text.insert(tk.END, text + "\n")
        self.text.see(tk.END)
        self.text.config(state=tk.DISABLED)

    def clear(self):
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.config(state=tk.DISABLED)
        self.stop_spinner()

    def start_spinner(self, task_label: str):
        self.stop_spinner()
        self._spinner_active = True
        self._spinner_task = task_label
        self._spinner_idx = 0
        self._spinner_strip.pack(fill=tk.X, before=self.text)
        self._tick_spinner()

    def _tick_spinner(self):
        if not self._spinner_active:
            return
        frame = self._SPINNER[self._spinner_idx % len(self._SPINNER)]
        self._spinner_idx += 1
        try:
            self._spinner_lbl.config(text=f"{frame}  {self._spinner_task}")
            self._spinner_after_id = self.text.after(100, self._tick_spinner)
        except Exception:
            return

    def stop_spinner(self):
        self._spinner_active = False
        if self._spinner_after_id:
            try:
                self.text.after_cancel(self._spinner_after_id)
            except Exception:
                pass
            self._spinner_after_id = None
        try:
            self._spinner_strip.pack_forget()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# 4. Main Window Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class SazonRoundBotWidget:
    """Main desktop widget for Sazon AI Assistant."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sazon — AI Agent")

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()

        self._bs = Theme.BOT_SIZE
        self._dw = Theme.DIALOGUE_W
        self._dh = Theme.DIALOGUE_H

        self._docked_x = sw - self._bs - 20
        self._docked_y = (sh - self._bs) // 2
        self._center_x = (sw - self._dw) // 2
        self._center_y = (sh - self._dh) // 2

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=Theme.BG_DARK)

        self.is_running: bool = False
        self.is_expanded: bool = False
        self._first_show: bool = True
        self._drag_sx: int = 0
        self._drag_sy: int = 0

        # Active Model Selection
        has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY"))
        if has_api_key:
            self.active_provider = os.getenv("DEFAULT_LLM_PROVIDER", "gemini").lower()
            self.active_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            self.active_model_display = "⚡ Gemini 2.5 Flash"
        else:
            self.active_provider = "sample"
            self.active_model = "sazon"
            self.active_model_display = "🤖 Sazon"

        self._morph = GeometryMorph(self.root)
        self._build()
        self.show_docked_bot()

        self.privacy_active = apply_screen_share_privacy(self.root)
        self.titlebar.set_stealth(self.privacy_active)

    def _build(self):
        self.outer = tk.Frame(self.root, bg=Theme.CYAN, bd=1)
        self.outer.pack(fill=tk.BOTH, expand=True)

        # Docked orb
        self.orb_frame = tk.Frame(self.outer, bg=Theme.BG_DARK)
        self.orb = OrbWidget(self.orb_frame, on_click=self.show_center_dialogue)
        self.orb.pack(expand=True)

        self.orb_frame.bind("<Button-1>", self._start_drag)
        self.orb_frame.bind("<B1-Motion>", self._do_drag)
        self.orb.bind("<Button-1>", self._start_drag)
        self.orb.bind("<B1-Motion>", self._do_drag)

        # Expanded dialogue
        self.dialogue = tk.Frame(self.outer, bg=Theme.BG_DARK)
        self.titlebar = TitleBar(self.dialogue, on_dock=self.show_docked_bot, on_close=self.root.destroy)
        self.titlebar.pack(fill=tk.X)
        self.titlebar.bind_drag(self._start_drag, self._do_drag)

        content = tk.Frame(self.dialogue, bg=Theme.BG_DARK, padx=12, pady=10)
        content.pack(fill=tk.BOTH, expand=True)

        self.status_card = StatusCard(content, on_select_model=self._on_model_changed)
        self.status_card.pack(fill=tk.X, pady=(0, 10))

        self.chip_bar = ChipBar(content, _QUICK_ACTIONS, on_click=self._on_chip_click)
        self.chip_bar.pack(fill=tk.X, pady=(0, 10))

        self.input_bar = InputBar(content, on_execute=self.start_execution)
        self.input_bar.pack(fill=tk.X, pady=(0, 10))

        self.console = ConsoleWidget(content)
        self.console.pack(fill=tk.BOTH, expand=True)

        self.console.append("🤖 Sazon initialized — stealth privacy active.", "title")
        self.console.append("Type a goal above or select a quick action below.", "dim")

    def show_docked_bot(self):
        target = (self._bs, self._bs, self._docked_x, self._docked_y)
        if self._first_show:
            self._first_show = False
            self.dialogue.pack_forget()
            self.orb_frame.pack(fill=tk.BOTH, expand=True)
            self.orb.start_pulse()
            self.root.geometry(f"{self._bs}x{self._bs}+{self._docked_x}+{self._docked_y}")
            self.is_expanded = False
            return

        current = (self.root.winfo_width(), self.root.winfo_height(), self.root.winfo_x(), self.root.winfo_y())
        self.dialogue.pack_forget()
        self.orb_frame.pack(fill=tk.BOTH, expand=True)

        def _on_dock_complete():
            self.orb.start_pulse()
            self.is_expanded = False

        self._morph.morph(current, target, on_complete=_on_dock_complete)
        self.is_expanded = False

    def show_center_dialogue(self):
        target = (self._dw, self._dh, self._center_x, self._center_y)
        current = (self.root.winfo_width(), self.root.winfo_height(), self.root.winfo_x(), self.root.winfo_y())

        self.orb.stop_pulse()

        def _on_expand_complete():
            self.orb_frame.pack_forget()
            self.dialogue.pack(fill=tk.BOTH, expand=True)
            self.input_bar.focus()
            self.is_expanded = True

        self._morph.morph(current, target, on_complete=_on_expand_complete)

    def _start_drag(self, event):
        self._drag_sx = event.x
        self._drag_sy = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_sx)
        y = self.root.winfo_y() + (event.y - self._drag_sy)
        self.root.geometry(f"+{x}+{y}")

    def _on_model_changed(self, provider: str, model: str, display: str):
        self.active_provider = provider
        self.active_model = model
        self.active_model_display = display
        self.console.append(f"🔄 Switched Active Model to: {display} [{provider} / {model}]", "task")

    def _on_chip_click(self, prompt: str):
        if not self.is_expanded:
            self.show_center_dialogue()
        self.input_bar.set(prompt)
        self.root.after(200, self.start_execution)

    def start_execution(self):
        goal = self.input_bar.get()
        if not goal or self.is_running:
            return

        self.input_bar.set("")
        self.is_running = True
        self.input_bar.set_executing(True)
        self.titlebar.set_status("running", f"'{goal[:26]}…'")

        self.console.append(f"\nYou: {goal}", "title")
        self.console.start_spinner("Sazon is processing…")

        thread = threading.Thread(target=self._run_agent_thread, args=(goal,), daemon=True)
        thread.start()

    def _run_agent_thread(self, goal: str):
        try:
            req = GoalRequest(
                goal=goal,
                max_iterations=10,
                llm_provider=self.active_provider,
                model=self.active_model
            )
            executor = SazonExecutor(req)
            result = executor.run()
            self.root.after(0, self._on_execution_complete, result, len(executor.memory.working_memory))
        except Exception as e:
            self.root.after(0, self._on_execution_error, str(e))

    def _on_execution_complete(self, result, memory_count: int = 0):
        self.is_running = False
        self.input_bar.set_executing(False)
        self.console.stop_spinner()
        self.titlebar.set_status("done")

        self.status_card.update_meta(memory_count=memory_count, last_time=result.execution_time_seconds)

        # Clean abstracted output: Sazon: <answer>
        self.console.append(f"Sazon: {result.final_answer}", "success")

    def _on_execution_error(self, err_msg: str):
        self.is_running = False
        self.input_bar.set_executing(False)
        self.console.stop_spinner()
        self.titlebar.set_status("error")
        self.console.append(f"Sazon: Encountered an issue — {err_msg}", "error")


def launch_gui():
    """Launch Sazon Desktop Assistant GUI."""
    root = tk.Tk()
    _app = SazonRoundBotWidget(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()

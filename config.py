"""
config.py — Sazon Design System & Application Configuration
All color tokens, font helpers, window dimensions, and privacy constants live here.
"""

# ─── Windows Screen-Share Privacy Constants ──────────────────────────────────
WDA_NONE               = 0x00000000
WDA_MONITOR            = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011   # Windows 10 2004+ / Windows 11


class Theme:
    # ─── Backgrounds ─────────────────────────────────────────────────────────
    BG_VOID     = "#07090f"   # deepest background
    BG_DARK     = "#0a0e1a"   # base dark surface
    BG_CARD     = "#0f1623"   # card / panel surface
    BG_ELEVATED = "#141e30"   # slightly elevated card (title bar etc.)
    BG_INPUT    = "#1a2540"   # input field background
    BG_HOVER    = "#1e2d45"   # hover state

    # ─── Accent Colors ────────────────────────────────────────────────────────
    CYAN        = "#22d3ee"   # neon ice – primary accent
    CYAN_DIM    = "#0e7490"   # dim cyan for glow rings
    CYAN_DARK   = "#083344"   # darkest cyan halo
    INDIGO      = "#6366f1"   # action / execute button
    INDIGO_DARK = "#4338ca"   # button active / pressed
    INDIGO_LIGHT= "#818cf8"   # button hover
    VIOLET      = "#a78bfa"   # secondary accent / task items
    VIOLET_DIM  = "#5b21b6"   # dim violet
    GREEN       = "#4ade80"   # success / ready
    GREEN_DIM   = "#166534"   # dim green for dot animation
    AMBER       = "#fbbf24"   # in-progress / thinking
    AMBER_DIM   = "#78350f"   # dim amber
    RED         = "#f87171"   # error
    RED_DIM     = "#7f1d1d"   # dim red

    # ─── Text ─────────────────────────────────────────────────────────────────
    TEXT_WHITE  = "#f8fafc"   # primary text
    TEXT_SUBTLE = "#94a3b8"   # secondary / labels
    TEXT_MUTED  = "#64748b"   # placeholder / dimmed

    # ─── Borders ──────────────────────────────────────────────────────────────
    BORDER        = "#1e2d45" # default border
    BORDER_ACCENT = "#22d3ee" # accent border (focused input etc.)

    # ─── Fonts ────────────────────────────────────────────────────────────────
    FONT_UI    = "Segoe UI"
    FONT_MONO  = "Consolas"
    FONT_EMOJI = "Segoe UI Emoji"

    # ─── Window Dimensions ────────────────────────────────────────────────────
    BOT_SIZE   = 80    # docked orb window (square)
    DIALOGUE_W = 560   # expanded dialogue width
    DIALOGUE_H = 690   # expanded dialogue height

    # ─── Font shorthand helpers ───────────────────────────────────────────────
    @staticmethod
    def ui(size: int = 10, weight: str = "normal") -> tuple:
        return ("Segoe UI", size, weight)

    @staticmethod
    def mono(size: int = 9) -> tuple:
        return (Theme.FONT_MONO, size)

    @staticmethod
    def display(size: int = 13, weight: str = "bold") -> tuple:
        return ("Segoe UI", size, weight)

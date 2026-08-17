import sys
import os
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from dotenv import load_dotenv

load_dotenv()

from app.models.task import GoalRequest, TaskStatus
from app.agent.executor import SazonExecutor
from app.agent.tools import default_registry

# Windows Display Affinity Constants for Screen Capture Exclusion
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 2004+ / Windows 11


def apply_screen_share_privacy(window):
    """Excludes window from screen capture/sharing (Zoom, Teams, Meet, Discord, OBS, screenshots)."""
    if sys.platform == "win32":
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            if not hwnd:
                hwnd = window.winfo_id()

            res = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            if not res:
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
            return True
        except Exception as e:
            print(f"Screen share privacy warning: {e}")
            return False
    return False


class SazonRoundBotWidget:
    """Round Cute Bot Mascot Widget with Side Docking and Center Screen Expansion."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sazon - Laptop Assistant")

        # Screen Dimensions
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # Window geometry configs
        self.BOT_SIZE = 75
        self.DIALOGUE_W = 540
        self.DIALOGUE_H = 640

        self.docked_x = self.screen_w - self.BOT_SIZE - 20
        self.docked_y = (self.screen_h // 2) - (self.BOT_SIZE // 2)

        self.center_x = (self.screen_w - self.DIALOGUE_W) // 2
        self.center_y = (self.screen_h - self.DIALOGUE_H) // 2

        # Configure Window
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Color Palette
        self.BG_DARK = "#090d16"         # Ultra deep slate
        self.CARD_BG = "#131c2e"         # Card midnight blue
        self.ACCENT_CYAN = "#38bdf8"     # Bright cyan
        self.ACCENT_PURPLE = "#c084fc"   # Cute purple
        self.ACCENT_BLUE = "#3b82f6"     # Royal blue
        self.TEXT_PRIMARY = "#f8fafc"    # White
        self.TEXT_MUTED = "#94a3b8"      # Muted gray
        self.SUCCESS_GREEN = "#4ade80"   # Mint green
        self.INPUT_BG = "#1e293b"        # Input slate

        self.root.configure(bg=self.BG_DARK)

        # State & Drag Variables
        self.is_running = False
        self.is_expanded = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        self._build_ui()

        # Set initial position to docked side orb
        self.show_docked_bot()

        # Apply screen sharing privacy protection
        self.privacy_active = apply_screen_share_privacy(self.root)

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_start_x)
        y = self.root.winfo_y() + (event.y - self._drag_start_y)
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # Master Outer Frame
        self.outer_frame = tk.Frame(self.root, bg=self.ACCENT_CYAN, bd=1)
        self.outer_frame.pack(fill=tk.BOTH, expand=True)

        # ----------------------------------------------------
        # DOCKED ROUND BOT FRAME (Side Mascot Orb)
        # ----------------------------------------------------
        self.bot_frame = tk.Frame(self.outer_frame, bg=self.BG_DARK, cursor="hand2")
        self.bot_frame.bind("<Button-1>", self._start_drag)
        self.bot_frame.bind("<B1-Motion>", self._do_drag)

        # Round Bot Canvas Icon
        self.bot_canvas = tk.Canvas(
            self.bot_frame,
            width=70,
            height=70,
            bg=self.BG_DARK,
            highlightthickness=0,
            cursor="hand2"
        )
        self.bot_canvas.pack(expand=True)

        # Draw cute circular mascot orb
        self.bot_canvas.create_oval(5, 5, 65, 65, fill=self.CARD_BG, outline=self.ACCENT_CYAN, width=3)
        self.bot_canvas.create_text(35, 30, text="🤖", font=("Segoe UI Emoji", 22))
        self.bot_canvas.create_text(35, 52, text="SAZON", fill=self.ACCENT_CYAN, font=("Segoe UI", 8, "bold"))

        # Click event to expand to center dialogue
        self.bot_canvas.bind("<Button-1>", lambda e: self.show_center_dialogue())
        self.bot_frame.bind("<Button-1>", lambda e: self.show_center_dialogue())

        # ----------------------------------------------------
        # EXPANDED CENTER DIALOGUE FRAME
        # ----------------------------------------------------
        self.dialogue_frame = tk.Frame(self.outer_frame, bg=self.BG_DARK, padx=12, pady=10)

        # Custom Draggable Title Bar
        self.title_bar = tk.Frame(self.dialogue_frame, bg=self.CARD_BG, height=36, cursor="fleur")
        self.title_bar.pack(fill=tk.X, pady=(0, 10))
        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._do_drag)

        title_label = tk.Label(
            self.title_bar,
            text="🤖 Sazon Mascot",
            bg=self.CARD_BG,
            fg=self.ACCENT_CYAN,
            font=("Segoe UI", 10, "bold"),
            cursor="fleur"
        )
        title_label.pack(side=tk.LEFT, padx=(10, 4))
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._do_drag)

        stealth_badge = tk.Label(
            self.title_bar,
            text="🛡️ Stealth Active",
            bg=self.CARD_BG,
            fg=self.SUCCESS_GREEN,
            font=("Segoe UI", 8, "bold"),
            cursor="fleur"
        )
        stealth_badge.pack(side=tk.LEFT, padx=2)
        stealth_badge.bind("<Button-1>", self._start_drag)
        stealth_badge.bind("<B1-Motion>", self._do_drag)

        drag_hint = tk.Label(
            self.title_bar,
            text="⤭ Drag anywhere",
            bg=self.CARD_BG,
            fg=self.TEXT_MUTED,
            font=("Segoe UI", 8, "italic"),
            cursor="fleur"
        )
        drag_hint.pack(side=tk.LEFT, padx=5)
        drag_hint.bind("<Button-1>", self._start_drag)
        drag_hint.bind("<B1-Motion>", self._do_drag)

        # Controls (Close & Dock)
        close_btn = tk.Button(
            self.title_bar,
            text="✕",
            bg=self.CARD_BG,
            fg=self.TEXT_MUTED,
            activebackground="#ef4444",
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=8,
            command=self.root.destroy
        )
        close_btn.pack(side=tk.RIGHT)

        dock_btn = tk.Button(
            self.title_bar,
            text="📌 Dock Side",
            bg=self.CARD_BG,
            fg=self.ACCENT_CYAN,
            activebackground=self.INPUT_BG,
            activeforeground=self.TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=8,
            command=self.show_docked_bot
        )
        dock_btn.pack(side=tk.RIGHT, padx=4)

        # Greeting Card
        greeting_card = tk.Frame(self.dialogue_frame, bg=self.CARD_BG, padx=12, pady=10)
        greeting_card.pack(fill=tk.X, pady=(0, 10))

        header_lbl = tk.Label(
            greeting_card,
            text="Hello! Sazon is here, how may I help you today?",
            bg=self.CARD_BG,
            fg=self.TEXT_PRIMARY,
            font=("Segoe UI", 11, "bold"),
            wraplength=480,
            justify="left"
        )
        header_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            greeting_card,
            text="Your cute laptop assistant (🛡️ Invisible during screen share). Ask me to run commands, search files, inspect hardware, or automate tasks.",
            bg=self.CARD_BG,
            fg=self.TEXT_MUTED,
            font=("Segoe UI", 9),
            wraplength=480,
            justify="left"
        )
        sub_lbl.pack(anchor="w", pady=(3, 0))

        # Quick Action Buttons
        chips_frame = tk.Frame(self.dialogue_frame, bg=self.BG_DARK)
        chips_frame.pack(fill=tk.X, pady=(0, 10))

        quick_actions = [
            ("💻 System Status", "Check system status and hardware diagnostic details"),
            ("🔍 Find Files", "Search for files in current workspace"),
            ("📝 Create Report", "Create a summary report of current environment")
        ]

        for text, prompt in quick_actions:
            btn = tk.Button(
                chips_frame,
                text=text,
                bg=self.CARD_BG,
                fg=self.ACCENT_CYAN,
                activebackground=self.INPUT_BG,
                activeforeground=self.TEXT_PRIMARY,
                font=("Segoe UI", 9),
                bd=0,
                relief="flat",
                cursor="hand2",
                padx=6,
                pady=3,
                command=lambda p=prompt: self._set_quick_prompt(p)
            )
            btn.pack(side=tk.LEFT, padx=(0, 5))

        # Input Box & Execute Button
        input_card = tk.Frame(self.dialogue_frame, bg=self.BG_DARK)
        input_card.pack(fill=tk.X, pady=(0, 10))

        self.goal_entry = tk.Entry(
            input_card,
            bg=self.INPUT_BG,
            fg=self.TEXT_PRIMARY,
            insertbackground=self.TEXT_PRIMARY,
            font=("Segoe UI", 10),
            bd=0,
            relief="flat"
        )
        self.goal_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, ipadx=8, padx=(0, 8))
        self.goal_entry.focus_set()
        self.goal_entry.bind("<Return>", lambda event: self.start_execution())

        self.send_btn = tk.Button(
            input_card,
            text="Execute 🚀",
            bg=self.ACCENT_BLUE,
            fg=self.TEXT_PRIMARY,
            activebackground=self.ACCENT_CYAN,
            activeforeground=self.BG_DARK,
            font=("Segoe UI", 9, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            command=self.start_execution
        )
        self.send_btn.pack(side=tk.RIGHT)

        # Status Label
        self.status_label = tk.Label(
            self.dialogue_frame,
            text="Status: Ready (🛡️ Stealth Active)",
            bg=self.BG_DARK,
            fg=self.ACCENT_CYAN,
            font=("Segoe UI", 9, "bold")
        )
        self.status_label.pack(anchor="w", pady=(0, 5))

        # Scrolled Console Log
        self.log_text = scrolledtext.ScrolledText(
            self.dialogue_frame,
            bg="#020617",
            fg=self.TEXT_PRIMARY,
            insertbackground=self.TEXT_PRIMARY,
            font=("Consolas", 9),
            bd=0,
            relief="flat",
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("title", foreground=self.ACCENT_CYAN, font=("Consolas", 9, "bold"))
        self.log_text.tag_config("task", foreground=self.ACCENT_PURPLE, font=("Consolas", 9, "bold"))
        self.log_text.tag_config("success", foreground=self.SUCCESS_GREEN, font=("Consolas", 9, "bold"))
        self.log_text.tag_config("dim", foreground=self.TEXT_MUTED)

        self._append_log("🤖 Sazon Assistant initialized (🛡️ Stealth Active).", "title")
        self._append_log("Type a task above or click a quick command.\n", "dim")

    def show_docked_bot(self):
        """Collapses Sazon into small round bot icon on the side of screen."""
        self.dialogue_frame.pack_forget()
        self.bot_frame.pack(fill=tk.BOTH, expand=True)
        self.root.geometry(f"{self.BOT_SIZE}x{self.BOT_SIZE}+{self.docked_x}+{self.docked_y}")
        self.is_expanded = False

    def show_center_dialogue(self):
        """Expands Sazon into center screen dialogue box."""
        self.bot_frame.pack_forget()
        self.dialogue_frame.pack(fill=tk.BOTH, expand=True)
        self.root.geometry(f"{self.DIALOGUE_W}x{self.DIALOGUE_H}+{self.center_x}+{self.center_y}")
        self.is_expanded = True
        self.goal_entry.focus_set()

    def _set_quick_prompt(self, prompt: str):
        if not self.is_expanded:
            self.show_center_dialogue()
        self.goal_entry.delete(0, tk.END)
        self.goal_entry.insert(0, prompt)
        self.start_execution()

    def _append_log(self, text: str, tag: str = None):
        self.log_text.config(state=tk.NORMAL)
        if tag:
            self.log_text.insert(tk.END, text + "\n", tag)
        else:
            self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_execution(self):
        goal = self.goal_entry.get().strip()
        if not goal:
            return

        if self.is_running:
            return

        self.is_running = True
        self.send_btn.config(state=tk.DISABLED, bg=self.TEXT_MUTED)
        self.status_label.config(text=f"Status: Executing - '{goal[:30]}...'")

        self._append_log("\n" + "─" * 40, "dim")
        self._append_log(f"🎯 Goal: {goal}", "title")

        thread = threading.Thread(target=self._run_agent_thread, args=(goal,), daemon=True)
        thread.start()

    def _run_agent_thread(self, goal: str):
        try:
            req = GoalRequest(goal=goal, max_iterations=10)
            executor = SazonExecutor(req)

            self.root.after(0, self._append_log, "⚡ Planning & executing via Sazon Engine...", "dim")
            result = executor.run()

            self.root.after(0, self._on_execution_complete, result)
        except Exception as e:
            self.root.after(0, self._on_execution_error, str(e))

    def _on_execution_complete(self, result):
        self.is_running = False
        self.send_btn.config(state=tk.NORMAL, bg=self.ACCENT_BLUE)
        self.status_label.config(text="Status: Completed ✅")

        self._append_log("\n📋 Steps Completed:", "title")
        for task in result.tasks:
            status_symbol = "✓" if task.status == TaskStatus.COMPLETED else "✗"
            tool_info = f" ({task.tool_name})" if task.tool_name else ""
            self._append_log(f" [{status_symbol}] {task.title}{tool_info}", "task")

        self._append_log("\n🏆 Final Outcome:", "success")
        self._append_log(result.final_answer)

    def _on_execution_error(self, error_msg: str):
        self.is_running = False
        self.send_btn.config(state=tk.NORMAL, bg=self.ACCENT_BLUE)
        self.status_label.config(text="Status: Error ❌")
        self._append_log(f"\n❌ Error: {error_msg}")


def launch_gui():
    root = tk.Tk()
    app = SazonRoundBotWidget(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()

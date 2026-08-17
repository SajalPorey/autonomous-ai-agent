# 🤖 Sazon - Cute Floating Laptop AI Assistant

**Sazon** is a cute, floating, draggable AI mascot assistant for your laptop. When you launch the application, Sazon pops up on your screen as an always-on-top mascot widget greeting you with:

> **"Hello! Sazon is here, how may I help you today?"**

---

## ✨ Mascot Widget Features

- 🤖 **Cute Floating Widget**: Sleek, frameless dark card overlay that floats above your active applications.
- ⤭ **Click & Drag Anywhere**: Click and drag the widget anywhere across your laptop screen.
- ➖ **Compact Bubble Mode**: Click `—` to collapse Sazon into a cute floating side bubble (`🤖 Sazon`). Click the bubble anytime to expand the full assistant box!
- 💻 **Laptop Task Automation**: Search files, inspect system hardware, run commands, open web apps, and create reports.

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/SajalPorey/autonomous-ai-agent.git
cd autonomous-ai-agent
pip install -r requirements.txt
```

### 2. Configure Environment (Optional API Key)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Add your Gemini or OpenAI API key to `.env` (Sazon includes smart local fallbacks if an API key is not configured):

```env
GEMINI_API_KEY=your_gemini_api_key_here
DEFAULT_LLM_PROVIDER=gemini
```

### 3. Launch the Floating Assistant Widget

Run the launcher script:

```bash
python run.py
```

---

## 🛠️ Laptop Control Tools

- 💻 `system_status`: Inspect CPU, RAM, Disk space, and OS environment.
- 🔍 `file_search`: Search files across folders by wildcard pattern.
- 📁 `create_folder`: Create directories.
- 📄 `file_read` & `file_write`: Read or write local files.
- 🌐 `open_app_or_url`: Launch local applications or web URLs.
- ⚡ `shell_run`: Execute terminal/shell commands on your laptop.

---

## 🧪 Testing

Run pytest suite:

```bash
pytest
```
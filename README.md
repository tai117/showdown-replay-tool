# 🎮 showdown-replay-tool

Async downloader and metagame analyzer for Pokémon Showdown replays, built with modular architecture, type hints, and production-grade error handling.

## ✨ Features

- 🚀 **Async I/O**: Download 1000+ replays in ~15 seconds with `aiohttp` + `asyncio`
- 🔄 **State Management**: Resume downloads from last timestamp without duplicates
- 🧩 **Modular Parser**: Extract structured data (teams, moves, winner) from raw battle logs
- 📊 **Metagame Analyzer**: Generate CSV/JSON reports with usage stats, winrates, and team cores
- 🛡️ **Production Ready**: Rate limiting, exponential backoff, structured logging, and robust error handling
- 💻 **Professional CLI**: Subcommands, flags, and help system via `argparse`

## 📦 Installation

```bash
# Clone and install in editable mode
git clone https://github.com/youruser/showdown-replay-tool.git
cd showdown-replay-tool
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

# Contributing to DailyAI

Thank you for your interest in contributing to DailyAI! 🎉

## Quick Start

```bash
# Clone the repo
git clone https://github.com/shivangsinha/DailyAInews.git
cd DailyAInews

# Set up Python environment
python -m venv venv
source venv/bin/activate      # macOS/Linux
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Add your API keys to .env

# Run the app
python -m uvicorn app:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

## Project Structure

```
DailyAInews/
├── app.py               # FastAPI routes and entrypoint
├── agent.py             # AI news curation pipeline (LLM calls)
├── digest.py            # Email digest generator
├── services/
│   ├── api_keys.py      # Developer API key management
│   ├── config.py        # App configuration
│   ├── database.py      # Supabase cloud sync
│   ├── models.py        # Pydantic request models
│   ├── news_core.py     # News feed logic
│   ├── profiles.py      # Anonymous user profiles
│   ├── security.py      # CSRF, rate limiting, headers
│   └── store.py         # In-memory data store
├── static/              # Frontend JS, CSS, assets
├── templates/           # HTML templates (Jinja2)
└── tests/               # pytest test suite
```

## Code Style

- **Python**: [Black](https://black.readthedocs.io/) + [Ruff](https://docs.astral.sh/ruff/) (line length: 100)
- **JavaScript**: Vanilla JS, no framework. Keep functions small.
- **CSS**: Vanilla CSS with CSS custom properties. No Tailwind.

```bash
# Lint
ruff check .

# Format
black .

# Type check
mypy .
```

## Running Tests

```bash
pytest tests/ -v
```

## Submitting a PR

1. Fork the repo and create your branch from `main`
2. If you've added code, add tests
3. Ensure the test suite passes
4. Make sure your code lints
5. Open a PR with a clear description

## What to Contribute

### Good First Issues
- Add translations (see `I18N` in `static/app.js`)
- Add new RSS sources to `agent.py`
- Improve card UI components
- Add new topic categories

### Feature Ideas
- Browser extension
- Slack/Discord bot integration
- Custom alert rules
- AI model comparison tracker

## Code of Conduct

Be respectful, be constructive, and have fun building the future of AI news intelligence.

## License

MIT License — see [LICENSE](LICENSE) for details.

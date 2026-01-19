# Global Equity Momentum (GEM) Strategy Assistant

AI-powered momentum strategy assistant for iShares ETFs using LangGraph agents and multi-source data aggregation.

## Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 3. Launch dashboard
poetry run momentum dashboard

# Open http://localhost:7860 in your browser
```

## Overview

This application implements a **Global Equity Momentum (GEM) strategy** that:
- Analyzes momentum across 4 iShares ETFs (Emerging Markets, US Tech, US Bonds, Cash)
- Ranks ETFs based on 12-month momentum (excluding current month)
- Generates BUY/HOLD/SELL signals with AI-powered market context
- Provides web dashboard and CLI for analysis and monitoring

## Key Features

- **LangGraph Agent Workflow**: Stateful AI agent with SQLite checkpointing
- **Multi-Source Data**: Stooq.pl (primary) + Yahoo Finance (fallback)
- **Market Research**: Serper + Brave Search with intelligent deduplication
- **Notifications**: SendGrid (email) + Pushover (push notifications)
- **MCP Architecture**: Model Context Protocol servers for modularity
- **Caching**: 24h research cache for cost optimization
- **Database Migrations**: Versioned schema with automatic upgrades

## Technology Stack

- **Agent Framework**: LangGraph with SQLite persistence
- **Data Sources**: Stooq.pl, Yahoo Finance (yfinance)
- **Search APIs**: Serper (Google Search), Brave Search
- **Notifications**: SendGrid, Pushover
- **LLM**: OpenAI GPT-4
- **UI**: Gradio (web), Rich+Click (CLI)
- **Database**: SQLite with migrations
- **MCP**: FastMCP for server implementation

## Installation

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd gem_strategy_assistant
```

2. Install dependencies:
```bash
# Using Poetry (recommended)
poetry install

# Or using pip
pip install -e .
```

3. Configure environment variables (create `.env` file in project root):
```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (for full functionality)
SERPER_API_KEY=...          # Google Search via Serper
BRAVE_SEARCH_API_KEY=...    # Brave Search
SENDGRID_API_KEY=...        # Email notifications
SENDGRID_FROM_EMAIL=...
SENDGRID_TO_EMAIL=...
PUSHOVER_USER_KEY=...       # Push notifications
PUSHOVER_API_TOKEN=...

# Optional (custom paths)
DB_PATH=./data/momentum_signals.db
LOG_LEVEL=INFO
GRADIO_PORT=7860
```

## Usage

### CLI Commands

All commands use `poetry run momentum` (or just `momentum` if using Poetry shell).

#### Run Analysis
```bash
# Full analysis with research and database save
poetry run momentum analyze

# Skip research (faster, no API costs)
poetry run momentum analyze --no-research

# Don't save to database
poetry run momentum analyze --no-save
```

#### View History
```bash
# Last 30 days (default)
poetry run momentum history

# Custom period
poetry run momentum history --days 90
```

#### Research ETF
```bash
# Research specific ETF
poetry run momentum research EIMI
poetry run momentum research CNDX
```

#### Market Outlook
```bash
# Default: emerging markets 2026
poetry run momentum outlook

# Custom asset class and year
poetry run momentum outlook --asset-class "european equities" --year 2026
```

#### Check Status
```bash
# Show configuration and available ETFs
poetry run momentum status
```

#### Launch Dashboard
```bash
# Start Gradio web interface (RECOMMENDED)
poetry run momentum dashboard
```

**Tip**: Activate Poetry shell to skip `poetry run` prefix:
```bash
poetry shell
momentum dashboard
```

### Web Dashboard

Launch the Gradio interface:
```bash
poetry run momentum dashboard
```

Then open http://localhost:7860 in your browser.

Features:
- **Analysis Tab**: Run momentum analysis with configurable options
- **History Tab**: View signal history with interactive date range
- **Research Tab**: Deep-dive research on specific ETFs
- **Info Tab**: Strategy details and configuration

### Python API

```python
from gem_strategy_assistant.application import MomentumAgent

# Initialize agent
agent = MomentumAgent(checkpoint_path="checkpoints.db")

# Run analysis
result = agent.run_analysis(
    include_research=True,
    max_etfs_to_research=3,
    save_to_db=True
)

print(result["signal"])
print(result["ranking"])
print(result["research"])
```

## ETFs in Strategy

| ETF | Ticker | Description | Asset Class | Risk |
|-----|--------|-------------|-------------|------|
| EIMI | EIMI.L | iShares Core MSCI EM IMI | Emerging Markets | High |
| CNDX | CNDX.L | iShares NASDAQ 100 | US Tech | High |
| CBU0 | CBU0.L | iShares Treasury 7-10Y | US Bonds 7-10Y | Medium |
| IB01 | IB01.L | iShares Treasury 0-1Y | Cash Equivalent | Low |

## Momentum Strategy (12M - 1M)

1. **Calculate Momentum**: For each ETF, calculate total return over last 12 months, excluding current month
2. **Rank ETFs**: Sort by momentum (highest first)
3. **Generate Signal**:
   - **BUY**: Top ETF differs from previous recommendation
   - **HOLD**: Top ETF same as previous recommendation
   - **SELL**: Top ETF is a bond (defensive positioning)
4. **Add Context**: AI agent researches top ETFs and generates detailed rationale
5. **Store & Notify**: Save to database and send notifications

## Architecture

The application follows **Clean Architecture** principles:

```
gem_strategy_assistant/
├── domain/              # Business entities and rules
│   ├── entities.py      # ETF, Signal, MomentumRanking
│   └── strategy.py      # MomentumStrategy (12M-1M)
├── application/         # Use cases and orchestration
│   ├── services.py      # AnalysisService, ResearchService
│   ├── use_cases.py     # Use case implementations
│   ├── agent.py         # LangGraph agent workflow
│   └── mcp_client.py    # MCP client adapter
├── infrastructure/      # External integrations
│   ├── data/            # Market data providers
│   ├── search/          # Search providers
│   ├── notifications/   # Notification providers
│   ├── persistence/     # Database and repositories
│   └── mcp_servers/     # MCP server implementations
└── presentation/        # User interfaces
    ├── cli.py           # Command-line interface
    └── gradio_app.py    # Web dashboard
```

### Key Components

- **MomentumAgent**: LangGraph workflow with 6 nodes (initialization → analysis → research → signal → persistence → notification)
- **Composite Providers**: Graceful fallback between multiple data/search sources
- **MCP Servers**: 3 servers (financial, search, notification) for modular tool access
- **Repository Pattern**: Clean separation between business logic and persistence

## Database Schema

### Tables

- **signals**: Trading signals with timestamps and metadata
- **rankings**: ETF rankings for each signal
- **research_cache**: Cached ETF research (24h TTL)
- **schema_version**: Migration tracking

### Migrations

Run migrations manually:
```bash
python -m gem_strategy_assistant.infrastructure.persistence.migrations
```

Or programmatically:
```python
from gem_strategy_assistant.infrastructure.persistence import run_migrations
run_migrations()
```

## Configuration

All settings in `src/gem_strategy_assistant/config.py`:

- **Strategy**: `LOOKBACK_MONTHS=12`, `SKIP_MONTHS=1`
- **Data**: Primary=Stooq, Fallback=Yahoo Finance
- **Search**: Serper + Brave with deduplication
- **LLM**: OpenAI GPT-4 (configurable model)
- **Cache**: 24h TTL for research
- **Database**: SQLite with migrations

## Development

### Project Structure

```
gem_strategy_assistant/
├── src/gem_strategy_assistant/  # Source code
├── tests/                        # Tests (pytest)
├── pyproject.toml                # Project config
├── .env                          # Environment variables
└── README.md                     # This file
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Troubleshooting

### Common Issues

1. **No data from Stooq**: Check ticker symbols, falls back to Yahoo Finance
2. **Search API errors**: Verify API keys in `.env`, works without research flag
3. **Agent checkpoint errors**: Delete checkpoint DB to reset state
4. **Migration failures**: Use `reset_database()` to start fresh (WARNING: loses data)

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
gem-assistant analyze
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: <repository-url>/issues
- Documentation: See ARCHITECTURE.md and API_REFERENCE.md

## Roadmap

- [ ] Additional ETFs (Asia-Pacific, Real Estate)
- [ ] Backtesting framework
- [ ] Portfolio optimization
- [ ] Real-time price monitoring
- [ ] Telegram bot integration
- [ ] Multi-strategy support

## Acknowledgments

- Strategy inspired by Gary Antonacci's Dual Momentum
- Built with LangGraph by LangChain
- Data from Stooq.pl and Yahoo Finance

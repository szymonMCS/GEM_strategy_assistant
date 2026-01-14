import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dataclasses import replace

from gem_strategy_assistant.domain.strategy import MomentumStrategy
from gem_strategy_assistant.config import settings, get_stooq_link
from gem_strategy_assistant.infrastructure import (
    StooqProvider, StooqError,
    YahooFinanceProvider, YahooFinanceError
)
from gem_strategy_assistant.infrastructure.persistence import Database, SignalRepository
from gem_strategy_assistant.infrastructure.llm import ReportGenerator, LLMError

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """   GEM Strategy Assistant - strategia momentum dla 4 ETF-ów."""
    settings.setup_logging()


@cli.command()
@click.option("--no-ai", is_flag=True, help="Pomiń generowanie raportu AI")
@click.option("--no-save", is_flag=True, help="Nie zapisuj do bazy")
def analyze(no_ai: bool, no_save: bool):
    """Uruchom analizę momentum i wygeneruj sygnał."""
    console.print("\n[bold blue]   MOMENTUM ETF ASSISTANT[/bold blue]\n")
    
    db = Database(settings.db_path)
    repo = SignalRepository(db)
    strategy = MomentumStrategy(
        lookback_months=settings.lookback_months,
        skip_months=settings.skip_months
    )
    
    previous = repo.get_latest()
    previous_etf = previous.recommended_etf if previous else None
    
    if previous:
        console.print(
            f"   Poprzedni sygnał: [cyan]{previous.recommended_etf.name}[/cyan] "
            f"({previous.created_at.date()})"
        )
    
    start, end = strategy.get_analysis_period()
    console.print(f"\n   Okres: {start.date()} → {end.date()}")

    console.print("\n   Pobieranie danych...")
    price_data = None
    data_source = None

    # Próba pobrania ze Stooq (główne źródło)
    try:
        with console.status("[bold green]Pobieranie ze Stooq..."):
            stooq_provider = StooqProvider()
            price_data = stooq_provider.get_all_etf_data(start, end)
            data_source = "Stooq"
    except StooqError as e:
        console.print(f"[yellow]   Stooq niedostępny: {e}[/yellow]")
        console.print("[yellow]   Próbuję Yahoo Finance jako fallback...[/yellow]")

    # Fallback do Yahoo Finance
    if price_data is None:
        try:
            with console.status("[bold green]Pobieranie z Yahoo Finance..."):
                yahoo_provider = YahooFinanceProvider()
                price_data = yahoo_provider.get_all_etf_data(start, end)
                data_source = "Yahoo Finance"
        except YahooFinanceError as e:
            console.print(f"[red]   Błąd Yahoo Finance: {e}[/red]")
            console.print("[red]   Nie udało się pobrać danych z żadnego źródła.[/red]")
            return

    console.print(f"   Źródło danych: [cyan]{data_source}[/cyan]")
    
    ranking = strategy.calculate_ranking(price_data)
    
    table = Table(title="Momentum Ranking")
    table.add_column("#", style="dim", width=4)
    table.add_column("ETF", style="cyan")
    table.add_column("Momentum", justify="right")
    table.add_column("Klasa aktywów")
    
    for i, (etf, mom) in enumerate(ranking.rankings, 1):
        marker = "👑 " if i == 1 else "   "
        color = "green" if mom > 0 else "red"
        table.add_row(
            f"{marker}{i}",
            etf.name,
            f"[{color}]{mom*100:+.2f}%[/{color}]",
            etf.asset_class
        )
    
    console.print(table)
    
    signal = strategy.generate_signal(ranking, previous_etf)
    stooq_link = get_stooq_link(start, end)
    
    if not no_ai and ReportGenerator.is_available():
        try:
            with console.status("[bold green]Generowanie raportu AI..."):
                generator = ReportGenerator()
                report = generator.generate(signal, stooq_link)
                signal = replace(signal, report=report, stooq_link=stooq_link)
            console.print(Panel(report, title="🤖 Raport AI", border_style="blue"))
        except LLMError as e:
            console.print(f"[yellow]   Błąd AI: {e}[/yellow]")
    elif not no_ai:
        console.print("[yellow]   Brak OPENAI_API_KEY - pomijam raport AI[/yellow]")
    
    if not no_save:
        signal_id = repo.save(signal)
        console.print(f"\n   Zapisano jako #{signal_id}")
    
    action_color = "yellow" if signal.requires_rebalance else "green"
    console.print(
        f"\n   [bold {action_color}]SYGNAŁ: {signal.action_emoji} {signal.action}"
        f"[/bold {action_color}]"
    )
    console.print(f"\n   Stooq: {stooq_link}")


@cli.command()
@click.option("-n", "--limit", default=12, help="Liczba sygnałów do wyświetlenia")
def history(limit: int):
    """Pokaż historię sygnałów."""
    db = Database(settings.db_path)
    repo = SignalRepository(db)
    
    signals = repo.get_history(limit)
    
    if not signals:
        console.print("[yellow]Brak historii sygnałów[/yellow]")
        return
    
    table = Table(title=f"   Historia sygnałów (ostatnie {len(signals)})")
    table.add_column("Data", style="dim")
    table.add_column("ETF", style="cyan")
    table.add_column("Momentum", justify="right")
    table.add_column("Akcja")
    
    for s in signals:
        color = "green" if s.ranking.winner_momentum > 0 else "red"
        action = "   Rebalance" if s.requires_rebalance else "   Hold"
        table.add_row(
            s.created_at.strftime("%Y-%m-%d %H:%M"),
            s.recommended_etf.name,
            f"[{color}]{s.ranking.winner_momentum*100:+.2f}%[/{color}]",
            action
        )
    
    console.print(table)


@cli.command()
def stooq():
    strategy = MomentumStrategy(
        lookback_months=settings.lookback_months,
        skip_months=settings.skip_months
    )
    start, end = strategy.get_analysis_period()
    link = get_stooq_link(start, end)
    
    console.print(f"\n   Link do porównania ETF-ów na Stooq:")
    console.print(f"   {link}\n")


@cli.command()
def status():
    """Pokaż status konfiguracji."""
    console.print("\n[bold]   Status konfiguracji[/bold]")
    settings.print_status()


@cli.command()
def dashboard():
    """Uruchom web dashboard (Gradio)."""
    from gem_strategy_assistant.presentation.gradio_app import main
    console.print(f"\n🌐 Uruchamiam dashboard na porcie {settings.gradio_port}...")
    main()


if __name__ == "__main__":
    cli()
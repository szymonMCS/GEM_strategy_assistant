import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from gem_strategy_assistant.domain import ETF
from gem_strategy_assistant.config import settings
from gem_strategy_assistant.application import MomentumAgent

console = Console()
_agent = None


def get_agent() -> MomentumAgent:
    """Lazy initialization of agent."""
    global _agent
    if _agent is None:
        _agent = MomentumAgent(checkpoint_path=str(settings.db_path).replace('.db', '_checkpoints.db'))
    return _agent


@click.group()
@click.version_option(version="0.2.0")
def cli():
    """Global Equity Momentum Assistant - AI-powered ETF momentum strategy."""
    settings.setup_logging()


@cli.command()
@click.option("--no-research", is_flag=True, help="Skip market research")
@click.option("--no-save", is_flag=True, help="Don't save to database")
def analyze(no_research: bool, no_save: bool):
    console.print("\n[bold blue]Global Equity Momentum Assistant[/bold blue]")
    console.print("[dim]Powered by LangGraph Agent[/dim]\n")
    
    try:
        with console.status("[bold green]Running analysis..."):
            result = get_agent().run_analysis(
                include_research=not no_research,
                max_etfs_to_research=3,
                save_to_db=not no_save,
            )
        
        signal = result.get("signal", {})
        action = signal.get("action", "UNKNOWN")
        etf_name = signal.get("recommended_etf", "NONE")
        rationale = signal.get("rationale", "")
        
        action_emoji = {"BUY": "🚀", "HOLD": "✋", "SELL": "⚠️"}.get(action, "❓")
        action_color = {"BUY": "green", "HOLD": "yellow", "SELL": "red"}.get(action, "white")
        
        console.print(f"\n[bold {action_color}]{action_emoji} SIGNAL: {action} {etf_name}[/bold {action_color}]")
        console.print(f"\n{rationale}\n")
        
        ranking = result.get("ranking", [])
        if ranking:
            table = Table(title="📊 Momentum Ranking")
            table.add_column("Rank", style="dim", width=6)
            table.add_column("ETF", style="cyan")
            table.add_column("Display Name")
            table.add_column("Score", justify="right")
            
            for item in ranking:
                rank = item.get("rank", 0)
                etf = item.get("etf", "")
                display = item.get("etf_display_name", "")
                score = item.get("score", 0)
                
                marker = "👑 " if rank == 1 else "   "
                color = "green" if score > 0 else "red"
                
                table.add_row(
                    f"{marker}{rank}",
                    etf,
                    display,
                    f"[{color}]{score:+.2f}%[/{color}]"
                )
            
            console.print(table)
        
        if not no_research and "research" in result:
            research = result["research"]
            console.print("\n[bold]📰 Research Context:[/bold]\n")
            
            for etf_name, etf_research in research.items():
                if "error" not in etf_research:
                    context = etf_research.get("context", {})
                    general = context.get("general_info", [])
                    news = context.get("news", [])
                    
                    if general or news:
                        console.print(f"[cyan]{etf_name}:[/cyan]")
                        
                        if general:
                            console.print("  General Info:")
                            for item in general[:2]:
                                title = item.get("title", "")
                                console.print(f"    • {title}")
                        
                        if news:
                            console.print("  Recent News:")
                            for item in news[:2]:
                                title = item.get("title", "")
                                console.print(f"    • {title}")
                        
                        console.print()
        
        metadata = result.get("metadata", {})
        console.print(f"[dim]Analysis Date: {metadata.get('analysis_date', 'Unknown')}[/dim]")
        console.print(f"[dim]ETFs Analyzed: {metadata.get('total_etfs_analyzed', 0)}[/dim]")
        console.print(f"[dim]Research: {'✅ Included' if metadata.get('research_included') else '❌ Disabled'}[/dim]")
        console.print(f"[dim]Saved to DB: {'✅ Yes' if metadata.get('saved_to_db') else '❌ No'}[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@cli.command()
@click.option("-d", "--days", default=30, help="Days to look back (default: 30)")
def history(days: int):
    """Show signal history."""
    console.print(f"\n[bold]📜 Signal History (last {days} days)[/bold]\n")
    
    try:
        result = get_agent().get_history(days=days)
        
        signals = result.get("signals", [])
        if not signals:
            console.print("[yellow]No signal history found[/yellow]")
            return
        
        table = Table(title=f"Last {len(signals)} signals")
        table.add_column("Date", style="dim")
        table.add_column("Action")
        table.add_column("ETF", style="cyan")
        table.add_column("Rationale")
        
        for s in signals:
            date = s.get("date", "")
            action = s.get("action", "")
            etf = s.get("recommended_etf", "NONE")
            rationale = s.get("rationale", "")[:50] + "..."
            
            action_emoji = {"BUY": "🚀", "HOLD": "✋", "SELL": "⚠️"}.get(action, "❓")
            
            table.add_row(
                date[:10],
                f"{action_emoji} {action}",
                etf,
                rationale
            )
        
        console.print(table)
        
        metadata = result.get("metadata", {})
        console.print(f"\n[dim]Total signals: {metadata.get('total_signals', 0)}[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@cli.command()
@click.argument("etf_name")
def research(etf_name: str):
    """Research a specific ETF."""
    console.print(f"\n[bold]🔍 Researching {etf_name.upper()}...[/bold]\n")
    
    try:
        with console.status("[bold green]Gathering research..."):
            result = get_agent().research_etf(etf_name)
        
        etf_info = result.get("etf", {})
        research_data = result.get("research", {})
        
        console.print(f"[bold cyan]{etf_info.get('display_name', etf_name)}[/bold cyan]")
        console.print(f"Ticker (Yahoo): {etf_info.get('ticker_yfinance', 'N/A')}")
        console.print(f"Ticker (Stooq): {etf_info.get('ticker_stooq', 'N/A')}\n")
        
        if "error" not in research_data:
            general = research_data.get("general_info", [])
            if general:
                console.print("[bold]📊 General Information:[/bold]")
                for item in general[:3]:
                    title = item.get("title", "No title")
                    url = item.get("url", "#")
                    snippet = item.get("snippet", "")
                    console.print(f"\n  • [cyan]{title}[/cyan]")
                    console.print(f"    {snippet[:100]}...")
                    console.print(f"    [dim]{url}[/dim]")
            
            news = research_data.get("news", [])
            if news:
                console.print("\n[bold]📰 Recent News:[/bold]")
                for item in news[:3]:
                    title = item.get("title", "No title")
                    url = item.get("url", "#")
                    console.print(f"\n  • [cyan]{title}[/cyan]")
                    console.print(f"    [dim]{url}[/dim]")
        else:
            console.print(f"[yellow]Research failed: {research_data.get('error')}[/yellow]")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@cli.command()
@click.option("--asset-class", default="emerging markets", help="Asset class to research")
@click.option("--year", default=2026, help="Year for outlook")
def outlook(asset_class: str, year: int):
    """Research market outlook for an asset class."""
    console.print(f"\n[bold]🔮 Market Outlook: {asset_class} ({year})[/bold]\n")
    
    try:
        with console.status("[bold green]Gathering market outlook..."):
            result = get_agent().research_market_outlook(asset_class, year)
        
        results = result.get("results", [])
        if results:
            for i, item in enumerate(results[:5], 1):
                title = item.get("title", "No title")
                url = item.get("url", "#")
                snippet = item.get("snippet", "")
                
                console.print(f"{i}. [cyan]{title}[/cyan]")
                if snippet:
                    console.print(f"   {snippet[:150]}...")
                console.print(f"   [dim]{url}[/dim]\n")
        else:
            console.print("[yellow]No results found[/yellow]")
        
        metadata = result.get("metadata", {})
        console.print(f"[dim]Total results: {metadata.get('total_results', 0)}[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@cli.command()
def status():
    """Show configuration status."""
    console.print("\n[bold]⚙️  Configuration Status[/bold]\n")
    settings.print_status()
    
    console.print("\n[bold]📊 Available ETFs:[/bold]")
    table = Table()
    table.add_column("ETF")
    table.add_column("Display Name")
    table.add_column("Asset Class")
    table.add_column("Risk")
    
    for etf in ETF:
        table.add_row(
            etf.name,
            etf.display_name,
            etf.asset_class,
            etf.risk_level
        )
    
    console.print(table)
    console.print()


@cli.command()
def dashboard():
    """Launch web dashboard (Gradio)."""
    from gem_strategy_assistant.presentation.gradio_app import main
    console.print(f"\n🌐 Launching dashboard on port {settings.gradio_port}...")
    main()


if __name__ == "__main__":
    cli()

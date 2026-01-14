import gradio as gr
from dataclasses import replace
from datetime import datetime

from gem_strategy_assistant.domain import ETF
from gem_strategy_assistant.domain.strategy import MomentumStrategy
from gem_strategy_assistant.config import settings, get_stooq_link
from gem_strategy_assistant.infrastructure import YahooFinanceProvider, YahooFinanceError
from gem_strategy_assistant.infrastructure.persistence import Database, SignalRepository
from gem_strategy_assistant.infrastructure.llm import ReportGenerator, LLMError


def run_analysis(use_ai: bool = True) -> tuple[str, str, str, str, str]:
    """
    Run momentum analysis.
    
    Returns:
        (signal_md, ranking_md, report, stooq_link, period_info)
    """
    try:
        db = Database(settings.db_path)
        repo = SignalRepository(db)
        strategy = MomentumStrategy(
            lookback_months=settings.lookback_months,
            skip_months=settings.skip_months
        )
        provider = YahooFinanceProvider()
        
        previous = repo.get_latest()
        previous_etf = previous.recommended_etf if previous else None
        
        start, end = strategy.get_analysis_period()
        price_data = provider.get_all_etf_data(start, end)
        
        ranking = strategy.calculate_ranking(price_data)
        signal = strategy.generate_signal(ranking, previous_etf)
        stooq_link = get_stooq_link(start, end)
        
        report = ""
        if use_ai and ReportGenerator.is_available():
            try:
                generator = ReportGenerator()
                report = generator.generate(signal, stooq_link)
                signal = replace(signal, report=report, stooq_link=stooq_link)
            except LLMError as e:
                report = f"   Błąd generowania raportu: {e}"
        elif use_ai:
            report = "   Brak OPENAI_API_KEY - raport AI niedostępny"
        
        repo.save(signal)
        
        signal_md = f"# {signal.action_emoji} {signal.action}"
        
        ranking_md = "| # | ETF | Momentum | Klasa |\n|---|-----|----------|-------|\n"
        for i, (etf, mom) in enumerate(ranking.rankings, 1):
            marker = "👑" if i == 1 else ""
            ranking_md += f"| {marker}{i} | {etf.name} | {mom*100:+.2f}% | {etf.asset_class} |\n"
        
        stooq_md = f"[   Porównaj na Stooq.pl]({stooq_link})"
        period_md = f"Okres analizy: {start.date()} → {end.date()}"
        
        return signal_md, ranking_md, report or "Raport AI wyłączony", stooq_md, period_md
        
    except Exception as e:
        return f"#   Błąd: {e}", "", "", "", ""


def get_history() -> str:
    """Get signal history as markdown."""
    try:
        db = Database(settings.db_path)
        repo = SignalRepository(db)
        signals = repo.get_history(12)
        
        if not signals:
            return "Brak historii sygnałów"
        
        md = "| Data | ETF | Momentum | Akcja |\n|------|-----|----------|-------|\n"
        for s in signals:
            action = "🔄 Rebalance" if s.requires_rebalance else "✅ Hold"
            md += (f"| {s.created_at.strftime('%Y-%m-%d %H:%M')} | {s.recommended_etf.name} | "
                   f"{s.ranking.winner_momentum*100:+.2f}% | {action} |\n")
        
        return md
    except Exception as e:
        return f"Błąd: {e}"


def create_dashboard() -> gr.Blocks:
    """Create Gradio dashboard."""
    with gr.Blocks(
        title="Momentum ETF Assistant",
        theme=gr.themes.Soft()
    ) as demo:
        gr.Markdown("#   Momentum ETF Assistant")
        gr.Markdown("Strategia momentum (12M-1M) dla 4 ETF-ów iShares")
        
        with gr.Tab("   Analiza"):
            with gr.Row():
                use_ai_checkbox = gr.Checkbox(
                    label="Generuj raport AI (wymaga OPENAI_API_KEY)",
                    value=ReportGenerator.is_available()
                )
                run_btn = gr.Button("   Uruchom analizę", variant="primary")
            
            signal_output = gr.Markdown(label="Sygnał")
            ranking_output = gr.Markdown(label="Ranking")
            report_output = gr.Markdown(label="Raport AI")
            
            with gr.Row():
                stooq_output = gr.Markdown(label="Link")
                period_output = gr.Markdown(label="Okres")
            
            run_btn.click(
                fn=run_analysis,
                inputs=[use_ai_checkbox],
                outputs=[signal_output, ranking_output, report_output, stooq_output, period_output]
            )
        
        with gr.Tab("   Historia"):
            refresh_btn = gr.Button("🔄 Odśwież")
            history_output = gr.Markdown()
            
            refresh_btn.click(fn=get_history, outputs=[history_output])
            demo.load(fn=get_history, outputs=[history_output])
        
        with gr.Tab("   Info"):
            gr.Markdown(f"""
## ETF-y w strategii

| ETF | Ticker | Klasa aktywów | Ryzyko |
|-----|--------|---------------|--------|
| EIMI | {ETF.EIMI.ticker_yfinance} | {ETF.EIMI.asset_class} | {ETF.EIMI.risk_level} |
| CNDX | {ETF.CNDX.ticker_yfinance} | {ETF.CNDX.asset_class} | {ETF.CNDX.risk_level} |
| CBU0 | {ETF.CBU0.ticker_yfinance} | {ETF.CBU0.asset_class} | {ETF.CBU0.risk_level} |
| IB01 | {ETF.IB01.ticker_yfinance} | {ETF.IB01.asset_class} | {ETF.IB01.risk_level} |

## Strategia Momentum (12M - 1M)

1. Oblicz momentum dla każdego ETF za ostatnie 12 miesięcy (pomijając bieżący miesiąc)
2. Uszereguj ETF-y według momentum (od najwyższego)
3. Zainwestuj 100% portfela w ETF z najwyższym momentum
4. Powtórz analizę za miesiąc

## Konfiguracja

- **Model LLM:** {settings.openai_model}
- **Lookback:** {settings.lookback_months} miesięcy
- **Skip:** {settings.skip_months} miesiąc
            """)
    
    return demo

def main():
    """Launch dashboard."""
    settings.setup_logging()
    demo = create_dashboard()
    demo.launch(server_port=settings.gradio_port)


if __name__ == "__main__":
    main()
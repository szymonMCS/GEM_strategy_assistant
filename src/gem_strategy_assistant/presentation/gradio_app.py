import gradio as gr
from datetime import datetime

from gem_strategy_assistant.domain import ETF
from gem_strategy_assistant.config import settings, get_stooq_link
from gem_strategy_assistant.application import (
    MomentumAgent,
    ResearchETFUseCase,
    GetSignalHistoryUseCase,
)

_agent = None


def get_agent() -> MomentumAgent:
    """Lazy initialization of agent."""
    global _agent
    if _agent is None:
        _agent = MomentumAgent(checkpoint_path=str(settings.db_path).replace('.db', '_checkpoints.db'))
    return _agent


def run_analysis(include_research: bool = True, save_to_db: bool = True) -> tuple[str, str, str, str, str]:
    """
    Run momentum analysis using the agent.
    
    Returns:
        (signal_md, ranking_md, research_md, metadata_md, period_info)
    """
    try:
        result = get_agent().run_analysis(
            include_research=include_research,
            max_etfs_to_research=3,
            save_to_db=save_to_db,
        )
        
        signal = result.get("signal", {})
        action = signal.get("action", "UNKNOWN")
        etf_name = signal.get("recommended_etf", "NONE")
        rationale = signal.get("rationale", "")
        
        action_emoji = {"BUY": "🚀", "HOLD": "✋", "SELL": "⚠️"}.get(action, "❓")
        signal_md = f"# {action_emoji} {action}: {etf_name}\n\n{rationale}"
        
        ranking = result.get("ranking", [])
        ranking_md = "| Rank | ETF | Display Name | Score |\n|------|-----|--------------|-------|\n"
        for item in ranking:
            rank = item.get("rank", 0)
            etf = item.get("etf", "")
            display = item.get("etf_display_name", "")
            score = item.get("score", 0)
            marker = "👑" if rank == 1 else ""
            ranking_md += f"| {marker}{rank} | {etf} | {display} | {score:+.2f}% |\n"
        
        research_md = ""
        if include_research and "research" in result:
            research = result["research"]
            research_md = "## 📰 Research Context\n\n"
            for etf_name, etf_research in research.items():
                research_md += f"### {etf_name}\n\n"
                if "error" not in etf_research:
                    context = etf_research.get("context", {})
                    general = context.get("general_info", [])
                    news = context.get("news", [])
                    
                    if general:
                        research_md += "**General Info:**\n"
                        for item in general[:2]:
                            title = item.get("title", "No title")
                            url = item.get("url", "#")
                            research_md += f"- [{title}]({url})\n"
                        research_md += "\n"
                    
                    if news:
                        research_md += "**Recent News:**\n"
                        for item in news[:2]:
                            title = item.get("title", "No title")
                            url = item.get("url", "#")
                            research_md += f"- [{title}]({url})\n"
                        research_md += "\n"
                else:
                    research_md += f"*Research failed: {etf_research.get('error')}*\n\n"
        else:
            research_md = "*Research disabled*"
        
        metadata = result.get("metadata", {})
        analysis_date = metadata.get("analysis_date", "Unknown")
        total_etfs = metadata.get("total_etfs_analyzed", 0)
        research_included = metadata.get("research_included", False)
        saved_to_db = metadata.get("saved_to_db", False)
        
        metadata_md = f"""
**Analysis Date:** {analysis_date}  
**ETFs Analyzed:** {total_etfs}  
**Research:** {"✅ Included" if research_included else "❌ Disabled"}  
**Saved to DB:** {"✅ Yes" if saved_to_db else "❌ No"}
"""
        
        period_md = f"Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return signal_md, ranking_md, research_md, metadata_md, period_md
        
    except Exception as e:
        error_md = f"# ❌ Error\n\n{str(e)}"
        return error_md, "", "", "", ""


def get_history(days: int = 30) -> str:
    """Get signal history via agent."""
    try:
        result = get_agent().get_history(days=days)
        
        signals = result.get("signals", [])
        if not signals:
            return "No signal history found"
        
        md = "| Date | Action | ETF | Rationale |\n|------|--------|-----|----------|\n"
        for s in signals:
            date = s.get("date", "")
            action = s.get("action", "")
            etf = s.get("recommended_etf", "NONE")
            rationale = s.get("rationale", "")[:50] + "..."
            action_emoji = {"BUY": "🚀", "HOLD": "✋", "SELL": "⚠️"}.get(action, "❓")
            md += f"| {date[:10]} | {action_emoji} {action} | {etf} | {rationale} |\n"
        
        metadata = result.get("metadata", {})
        total = metadata.get("total_signals", 0)
        md += f"\n**Total signals:** {total}"
        
        return md
    except Exception as e:
        return f"Error: {e}"


def research_etf_ui(etf_name: str) -> str:
    """Research specific ETF via agent."""
    if not etf_name:
        return "Please enter an ETF name"
    
    try:
        result = get_agent().research_etf(etf_name)
        
        etf_info = result.get("etf", {})
        research = result.get("research", {})
        
        md = f"# {etf_info.get('display_name', etf_name)}\n\n"
        md += f"**Ticker (Yahoo):** {etf_info.get('ticker_yfinance', 'N/A')}  \n"
        md += f"**Ticker (Stooq):** {etf_info.get('ticker_stooq', 'N/A')}  \n\n"
        
        if "error" not in research:
            md += "## 📊 Research Results\n\n"
            
            general = research.get("general_info", [])
            if general:
                md += "### General Information\n\n"
                for item in general[:3]:
                    title = item.get("title", "No title")
                    url = item.get("url", "#")
                    snippet = item.get("snippet", "")
                    md += f"**[{title}]({url})**  \n{snippet}\n\n"
            
            news = research.get("news", [])
            if news:
                md += "### Recent News\n\n"
                for item in news[:3]:
                    title = item.get("title", "No title")
                    url = item.get("url", "#")
                    snippet = item.get("snippet", "")
                    md += f"**[{title}]({url})**  \n{snippet}\n\n"
        else:
            md += f"\n❌ Research failed: {research.get('error')}"
        
        return md
    except Exception as e:
        return f"# ❌ Error\n\n{str(e)}"


def create_dashboard() -> gr.Blocks:
    """Create enhanced Gradio dashboard with agent integration."""
    with gr.Blocks(
        title="Momentum ETF Assistant",
        theme=gr.themes.Soft()
    ) as demo:
        gr.Markdown("# 🚀 Momentum ETF Assistant")
        gr.Markdown("AI-powered momentum strategy for iShares ETFs with LangGraph agent")
        
        with gr.Tab("📊 Analysis"):
            gr.Markdown("## Run Momentum Analysis")
            
            with gr.Row():
                include_research_checkbox = gr.Checkbox(
                    label="Include market research (uses search APIs)",
                    value=True
                )
                save_to_db_checkbox = gr.Checkbox(
                    label="Save signal to database",
                    value=True
                )
                run_btn = gr.Button("🚀 Run Analysis", variant="primary")
            
            signal_output = gr.Markdown(label="Signal")
            ranking_output = gr.Markdown(label="Ranking")
            research_output = gr.Markdown(label="Research")
            
            with gr.Row():
                metadata_output = gr.Markdown(label="Metadata")
                period_output = gr.Markdown(label="Period")
            
            run_btn.click(
                fn=run_analysis,
                inputs=[include_research_checkbox, save_to_db_checkbox],
                outputs=[signal_output, ranking_output, research_output, metadata_output, period_output]
            )
        
        with gr.Tab("📜 History"):
            gr.Markdown("## Signal History")
            
            with gr.Row():
                days_slider = gr.Slider(
                    minimum=7,
                    maximum=90,
                    value=30,
                    step=1,
                    label="Days to look back"
                )
                refresh_btn = gr.Button("🔄 Refresh")
            
            history_output = gr.Markdown()
            
            refresh_btn.click(fn=get_history, inputs=[days_slider], outputs=[history_output])
            demo.load(fn=lambda: get_history(30), outputs=[history_output])
        
        with gr.Tab("🔍 Research ETF"):
            gr.Markdown("## Research Specific ETF")
            
            with gr.Row():
                etf_dropdown = gr.Dropdown(
                    choices=[e.name for e in ETF],
                    label="Select ETF",
                    value="EIMI"
                )
                research_btn = gr.Button("🔍 Research", variant="primary")
            
            etf_research_output = gr.Markdown()
            
            research_btn.click(
                fn=research_etf_ui,
                inputs=[etf_dropdown],
                outputs=[etf_research_output]
            )
        
        with gr.Tab("ℹ️ Info"):
            gr.Markdown(f"""
## ETFs in Strategy

| ETF | Ticker | Asset Class | Risk |
|-----|--------|-------------|------|
| EIMI | {ETF.EIMI.ticker_yfinance} | {ETF.EIMI.asset_class} | {ETF.EIMI.risk_level} |
| CNDX | {ETF.CNDX.ticker_yfinance} | {ETF.CNDX.asset_class} | {ETF.CNDX.risk_level} |
| CBU0 | {ETF.CBU0.ticker_yfinance} | {ETF.CBU0.asset_class} | {ETF.CBU0.risk_level} |
| IB01 | {ETF.IB01.ticker_yfinance} | {ETF.IB01.asset_class} | {ETF.IB01.risk_level} |

## Momentum Strategy (12M - 1M)

1. Calculate momentum for each ETF over last 12 months (skipping current month)
2. Rank ETFs by momentum (highest first)
3. Invest 100% in highest momentum ETF
4. Repeat analysis monthly

## Technology Stack

- **Agent:** LangGraph with SQLite checkpointing
- **Data:** Stooq.pl (primary) + Yahoo Finance (fallback)
- **Search:** Serper + Brave Search
- **Notifications:** SendGrid + Pushover
- **LLM:** {settings.openai_model}

## Configuration

- **Lookback:** {settings.lookback_months} months
- **Skip:** {settings.skip_months} month
- **Port:** {settings.gradio_port}
            """)
    
    return demo


def main():
    """Launch dashboard."""
    settings.setup_logging()
    demo = create_dashboard()
    demo.launch(server_port=settings.gradio_port)


if __name__ == "__main__":
    main()

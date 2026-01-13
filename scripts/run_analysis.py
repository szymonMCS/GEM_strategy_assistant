from datetime import datetime
from momentum_assistant.domain import ETF, PriceData
from momentum_assistant.domain.strategy import MomentumStrategy
from momentum_assistant.config import settings, get_stooq_link


def main():
    print("=" * 60)
    print(" MOMENTUM ETF ASSISTANT - ANALIZA")
    print("=" * 60)
    
    settings.print_status()
    
    strategy = MomentumStrategy(
        lookback_months=settings.lookback_months,
        skip_months=settings.skip_months
    )
    start, end = strategy.get_analysis_period()
    print(f"\n    Okres analizy: {start.date()} → {end.date()}")
    
    stooq_link = get_stooq_link(start, end)
    print(f"\n    Link do porównania na Stooq:")
    print(f"   {stooq_link}")
    
    mock_prices = [
        PriceData(ETF.CNDX, start, end, 800.0, 920.0),
        PriceData(ETF.EIMI, start, end, 25.0, 28.5),
        PriceData(ETF.IB01, start, end, 100.0, 104.5),
        PriceData(ETF.CBU0, start, end, 95.0, 92.0),
    ]
    
    ranking = strategy.calculate_ranking(mock_prices)
    ranking.print_table()
    
    signal = strategy.generate_signal(ranking, previous_etf=ETF.EIMI)
    print(f"\n    SYGNAŁ: {signal.action}")
    
    print("\n    Analiza zakończona!")


if __name__ == "__main__":
    main()
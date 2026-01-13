from datetime import datetime
from momentum_assistant.domain import ETF, PriceData
from momentum_assistant.domain.strategy import MomentumStrategy


def main():
    print("=" * 60)
    print("    MOMENTUM ETF ASSISTANT - ANALIZA")
    print("=" * 60)
    
    strategy = MomentumStrategy(lookback_months=12, skip_months=1)
    
    start, end = strategy.get_analysis_period()
    print(f"\n    Okres analizy: {start.date()} → {end.date()}")
    print(f"   Lookback: {strategy.lookback_months} miesięcy")
    print(f"   Skip: {strategy.skip_months} miesiąc")
    
    print("\n    Symulowane dane cenowe:")
    mock_prices = [
        PriceData(ETF.CNDX, start, end, 800.0, 920.0),
        PriceData(ETF.EIMI, start, end, 25.0, 28.5),
        PriceData(ETF.IB01, start, end, 100.0, 104.5),
        PriceData(ETF.CBU0, start, end, 95.0, 92.0),
    ]
    
    for pd in mock_prices:
        print(f"   {pd.etf.name}: {pd.momentum_pct}")
    
    ranking = strategy.calculate_ranking(mock_prices)
    ranking.print_table()
    
    signal = strategy.generate_signal(ranking, previous_etf=ETF.EIMI)
    
    print(f"\n    SYGNAŁ: {signal.action}")
    
    if signal.requires_rebalance:
        print("        Wymagany rebalancing!")
    else:
        print("       Bez zmian w portfelu")
    
    print("\n" + "=" * 60)
    print(strategy.get_explanation(signal))
    
    print("\n    Analiza zakończona!")


if __name__ == "__main__":
    main()
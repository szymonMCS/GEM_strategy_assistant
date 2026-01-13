from datetime import datetime
from momentum_assistant.domain import ETF, PriceData, MomentumRanking, Signal

def main():
    print("=" * 60)
    print("GEM STRATEGY ASSISTANT - ANALIZA")
    print("=" * 60)

    print("\n Dostępne ETF-y:")
    print(f"  {'ETF':<6} {'yfinance':<10} {'stooq':<10} {'Klasa':<20}")
    print("   " + "-" * 50)
    for etf in ETF:
        print(f"   {etf.name:<6} {etf.ticker_yfinance:<10} {etf.ticker_stooq:<10} "
              f"{etf.asset_class}")
        
    print("\n   test walidacji danych cenowych:")
    try:
        valid_data = PriceData(
            ETF.CNDX,
            datetime(2024, 12, 31),
            datetime(2025, 12, 31),
            800.0,
            920.0
        )
        print(f"      Poprawne dane: {valid_data.etf.name} momentum = {valid_data.momentum_pct}")
    except ValueError as e:
        print(f"   Błąd: {e}")

    print("\n   Test walidacji - ujemna cena:")
    try:
        invalid_data = PriceData(
            ETF.EIMI,
            datetime(2024, 12, 31),
            datetime(2025, 12, 31),
            -10.0,
            25.0
        )
        print(f"   Powinien być błąd!")
    except ValueError as e:
        print(f"   Walidacja działa: {e}")

    print("\n   Symulowany ranking (mock data):")
    mock_prices = [
        PriceData(ETF.CNDX, datetime(2024, 12, 31), datetime(2025, 12, 31), 800.0, 920.0),
        PriceData(ETF.EIMI, datetime(2024, 12, 31), datetime(2025, 12, 31), 25.0, 28.5),
        PriceData(ETF.IB01, datetime(2024, 12, 31), datetime(2025, 12, 31), 100.0, 104.5),
        PriceData(ETF.CBU0, datetime(2024, 12, 31), datetime(2025, 12, 31), 95.0, 92.0),
    ]
    
    sorted_data = sorted(mock_prices, key=lambda x: x.momentum, reverse=True)
    ranking = MomentumRanking(
        rankings=tuple((pd.etf, pd.momentum) for pd in sorted_data),
        period_start=datetime(2024, 12, 31),
        period_end=datetime(2025, 12, 31),
        calculated_at=datetime.now()
    )
    ranking.print_table()
    
    signal = Signal(
        recommended_etf=ranking.winner,
        ranking=ranking,
        previous_etf=ETF.EIMI,
        requires_rebalance=ranking.winner != ETF.EIMI,
        created_at=datetime.now()
    )
    
    print(f"\n SYGNAŁ: {signal.action}")
    print(f"   Winner momentum: {ranking.winner_momentum*100:+.2f}%")
    
    print("\n Test parsowania tickerów:")
    for ticker in ["CNDX", "CNDX.L", "CNDX.UK", "cndx"]:
        etf = ETF.from_any_ticker(ticker)
        print(f"   '{ticker}' → {etf.name}")
    
    print("\n Analiza zakończona pomyślnie!")
    print("=" * 60)

if __name__ == "__main__":
    main()


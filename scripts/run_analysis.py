from momentum_assistant.domain import ETF
from momentum_assistant.domain.strategy import MomentumStrategy
from momentum_assistant.config import settings, get_stooq_link
from momentum_assistant.infrastructure import (
    StooqProvider, StooqError,
    YahooFinanceProvider, YahooFinanceError
)


def main():
    print("=" * 60)
    print("   MOMENTUM ETF ASSISTANT - ANALIZA")
    print("=" * 60)
    
    settings.print_status()
    settings.setup_logging()
    
    strategy = MomentumStrategy(
        lookback_months=settings.lookback_months,
        skip_months=settings.skip_months
    )
    start, end = strategy.get_analysis_period()
    print(f"\n   Okres analizy: {start.date()} → {end.date()}")

    # Try STOOQ first (primary source), fallback to Yahoo Finance
    price_data = None

    print("\n   Pobieranie danych ze STOOQ (główne źródło)...")
    try:
        provider = StooqProvider(max_retries=3)
        price_data = provider.get_all_etf_data(start, end)
        print("   Źródło: STOOQ")
    except StooqError as e:
        print(f"   STOOQ niedostępny: {e}")
        print("\n   Próbuję Yahoo Finance (backup)...")
        try:
            provider = YahooFinanceProvider(max_retries=3)
            price_data = provider.get_all_etf_data(start, end)
            print("   Źródło: Yahoo Finance")
        except YahooFinanceError as e2:
            print(f"\n   Błąd pobierania danych: {e2}")
            print("   Sprawdź połączenie z internetem")
            return
    
    ranking = strategy.calculate_ranking(price_data)
    ranking.print_table()
    
    signal = strategy.generate_signal(ranking, previous_etf=None)
    print(f"\n   SYGNAŁ: {signal.action}")
    print(f"   Winner: {ranking.winner.display_name}")
    print(f"   Momentum: {ranking.winner_momentum*100:+.2f}%")
    
    print(f"\n   Porównaj na Stooq:")
    print(f"   {get_stooq_link(start, end)}")
    
    print("\n   Analiza zakończona!")


if __name__ == "__main__":
    main()
from momentum_assistant.domain import ETF
from momentum_assistant.domain.strategy import MomentumStrategy
from momentum_assistant.config import settings, get_stooq_link
from momentum_assistant.infrastructure import YahooFinanceProvider, YahooFinanceError
from momentum_assistant.infrastructure.persistence import Database, SignalRepository


def main():
    print("=" * 60)
    print("   MOMENTUM ETF ASSISTANT - ANALIZA")
    print("=" * 60)
    
    settings.print_status()
    settings.setup_logging()
    
    db = Database(settings.db_path)
    repo = SignalRepository(db)
    strategy = MomentumStrategy(
        lookback_months=settings.lookback_months,
        skip_months=settings.skip_months
    )
    provider = YahooFinanceProvider()
    
    previous_signal = repo.get_latest()
    previous_etf = previous_signal.recommended_etf if previous_signal else None
    
    if previous_signal:
        print(f"\n   Poprzedni sygnał: {previous_signal.recommended_etf.name}")
        print(f"   z dnia: {previous_signal.created_at.date()}")
    else:
        print("\n   Brak poprzednich sygnałów w bazie")
    
    start, end = strategy.get_analysis_period()
    print(f"\n   Okres analizy: {start.date()} → {end.date()}")
    
    print("\n   Pobieranie danych...")
    try:
        price_data = provider.get_all_etf_data(start, end)
    except YahooFinanceError as e:
        print(f"\n   Błąd: {e}")
        return
    
    ranking = strategy.calculate_ranking(price_data)
    ranking.print_table()
    
    signal = strategy.generate_signal(ranking, previous_etf=previous_etf)
    
    signal_id = repo.save(signal)
    print(f"\n   Zapisano sygnał #{signal_id}")
    
    print(f"\n   SYGNAŁ: {signal.action}")
    
    history = repo.get_history(limit=5)
    if len(history) > 1:
        print(f"\n   Ostatnie {len(history)} sygnałów:")
        for s in history:
            print(f"   {s.created_at.date()}: {s.recommended_etf.name} "
                  f"({s.ranking.winner_momentum*100:+.1f}%)")
    
    print(f"\n   Stooq: {get_stooq_link(start, end)}")
    print("\n   Analiza zakończona!")


if __name__ == "__main__":
    main()
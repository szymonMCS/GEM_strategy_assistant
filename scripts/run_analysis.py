from dataclasses import replace

from momentum_assistant.domain import ETF
from momentum_assistant.domain.strategy import MomentumStrategy
from momentum_assistant.config import settings, get_stooq_link
from momentum_assistant.infrastructure import YahooFinanceProvider, YahooFinanceError
from momentum_assistant.infrastructure.persistence import Database, SignalRepository
from momentum_assistant.infrastructure.llm import ReportGenerator, LLMError


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
    
    start, end = strategy.get_analysis_period()
    print(f"\n   Okres: {start.date()} → {end.date()}")
    
    print("\n   Pobieranie danych...")
    try:
        price_data = provider.get_all_etf_data(start, end)
    except YahooFinanceError as e:
        print(f"\n   Błąd: {e}")
        return
    
    ranking = strategy.calculate_ranking(price_data)
    ranking.print_table()
    
    signal = strategy.generate_signal(ranking, previous_etf=previous_etf)
    stooq_link = get_stooq_link(start, end)
    
    report = None
    if ReportGenerator.is_available():
        print("\n   Generowanie raportu AI...")
        try:
            generator = ReportGenerator()
            report = generator.generate(signal, stooq_link)
            signal = replace(signal, report=report, stooq_link=stooq_link)
            print(f"\n   RAPORT:\n{report}")
        except LLMError as e:
            print(f"      Błąd generowania raportu: {e}")
    else:
        print("\n   Brak OPENAI_API_KEY - pomijam raport AI")
    
    signal_id = repo.save(signal)
    print(f"\n   Zapisano sygnał #{signal_id}")
    
    print(f"\n   SYGNAŁ: {signal.action}")
    print(f"\n   Stooq: {stooq_link}")
    print("\n   Analiza zakończona!")


if __name__ == "__main__":
    main()
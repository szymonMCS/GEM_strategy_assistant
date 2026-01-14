from datetime import datetime, timedelta
from typing import Optional
from dateutil.relativedelta import relativedelta
from .models import ETF, PriceData, MomentumRanking, Signal

class MomentumStrategy:
    """
    Simple Momentum Ranking Strategy (12M - 1M).
    
    Algorithm:
    1. Calculate momentum for period: (12 months ago) to (end of previous month)
    2. Rank ETFs by momentum (highest first)
    3. Recommend the ETF with highest momentum
    """
    
    def __init__(self, lookback_months: int = 12, skip_months: int = 1):
        """
        Initialize strategy.
        
        Args:
            lookback_months: How many months to look back (default 12)
            skip_months: How many recent months to skip (default 1)
            
        Raises:
            ValueError: If parameters are invalid
        """
        if lookback_months < 1:
            raise ValueError(f"lookback_months must be >= 1, got {lookback_months}")
        if skip_months < 0:
            raise ValueError(f"skip_months must be >= 0, got {skip_months}")
        
        self.lookback_months = lookback_months
        self.skip_months = skip_months
    
    def get_analysis_period(self, as_of_date: Optional[datetime] = None) -> tuple[datetime, datetime]:
        """
        Calculate the analysis period.
        
        Args:
            as_of_date: Reference date (default: today)
            
        Returns:
            (start_date, end_date) tuple
            
        Example:
            as_of_date = 2026-01-10, skip_months=1, lookback_months=12
            → end_date = 2025-12-31 (last day of December 2025)
            → start_date = 2024-12-31 (12 months before end_date)
        """
        if as_of_date is None:
            as_of_date = datetime.now()
        
        first_of_current = as_of_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        first_of_target = first_of_current - relativedelta(months=self.skip_months)
        end_date = (first_of_target + relativedelta(months=1)) - timedelta(days=1)
        start_date = end_date - relativedelta(months=self.lookback_months)
        return start_date, end_date
    
    def calculate_ranking(self, price_data: list[PriceData]) -> MomentumRanking:
        """
        Calculate momentum ranking from price data.
        
        Args:
            price_data: List of PriceData for all ETFs
            
        Returns:
            MomentumRanking with ETFs sorted by momentum
            
        Raises:
            ValueError: If data is invalid or inconsistent
        """
        if len(price_data) != len(ETF):
            etfs_present = {pd.etf for pd in price_data}
            etfs_missing = set(ETF) - etfs_present
            raise ValueError(
                f"Missing data for ETFs: {[e.name for e in etfs_missing]}"
            )

        etfs_in_data = [pd.etf for pd in price_data]
        if len(etfs_in_data) != len(set(etfs_in_data)):
            raise ValueError("Duplicate ETF entries in price_data")

        # Allow small date variations (up to 10 days) due to different trading calendars
        start_dates = [pd.start_date.date() for pd in price_data]
        end_dates = [pd.end_date.date() for pd in price_data]
        start_diff = (max(start_dates) - min(start_dates)).days
        end_diff = (max(end_dates) - min(end_dates)).days

        if start_diff > 10 or end_diff > 10:
            raise ValueError(
                f"Inconsistent analysis periods: start dates differ by {start_diff} days, "
                f"end dates differ by {end_diff} days (max allowed: 10)"
            )
        
        momentum_list = [
            (pd.etf, pd.momentum) 
            for pd in price_data
        ]
        momentum_list.sort(key=lambda x: x[1], reverse=True)
        
        return MomentumRanking(
            rankings=tuple(momentum_list),
            period_start=price_data[0].start_date,
            period_end=price_data[0].end_date,
            calculated_at=datetime.now()
        )
    
    def generate_signal(self, ranking: MomentumRanking, previous_etf: Optional[ETF] = None) -> Signal:
        """
        Generate investment signal from ranking.
        
        Args:
            ranking: Calculated momentum ranking
            previous_etf: Currently held ETF (if any)
            
        Returns:
            Signal with recommendation
        """
        winner = ranking.winner
        requires_rebalance = (
            previous_etf is None or 
            winner != previous_etf
        )
        
        return Signal(
            recommended_etf=winner,
            ranking=ranking,
            previous_etf=previous_etf,
            requires_rebalance=requires_rebalance,
            created_at=datetime.now()
        )
    
    def get_explanation(self, signal: Signal) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            signal: Generated signal
            
        Returns:
            Markdown explanation string
        """
        ranking = signal.ranking
        winner = signal.recommended_etf
        
        lines = [
            f"## Analiza Momentum",
            f"**Okres:** {ranking.period_start.strftime('%Y-%m-%d')} → "
            f"{ranking.period_end.strftime('%Y-%m-%d')}",
            "",
            "### Ranking:",
        ]
        
        for i, (etf, mom) in enumerate(ranking.rankings, 1):
            marker = "👑" if i == 1 else f"  "
            lines.append(f"{marker} {i}. **{etf.display_name}**: {mom:+.1%}")
        
        lines.extend([
            "",
            f"### Rekomendacja: **{winner.display_name}**",
            f"- Klasa aktywów: {winner.asset_class}",
            f"- Poziom ryzyka: {winner.risk_level}",
        ])
        
        if signal.requires_rebalance:
            if signal.previous_etf:
                lines.extend([
                    "",
                    f"###     WYMAGANA ZMIANA POZYCJI",
                    f"- Sprzedaj: {signal.previous_etf.display_name}",
                    f"- Kup: {winner.display_name}"
                ])
            else:
                lines.extend([
                    "",
                    f"###     NOWA POZYCJA",
                    f"- Kup: {winner.display_name}"
                ])
        else:
            lines.extend([
                "",
                f"###     BEZ ZMIAN",
                f"- Trzymaj: {winner.display_name}"
            ])
        
        return "\n".join(lines)
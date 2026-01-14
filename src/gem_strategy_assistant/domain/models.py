from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, NamedTuple

class ETFInfo(NamedTuple):
    ticker_yfinance: str
    ticker_stooq: str
    display_name: str
    asset_class: str
    risk_level: str

class ETF(Enum):
    """Tracked ETFs"""
    EIMI = ETFInfo(
        ticker_yfinance="EIMI.L",
        ticker_stooq="EIMI.UK",
        display_name="iShares EM IMI (EIMI)",
        asset_class="Emerging Markets",
        risk_level="High"
    )
    CNDX = ETFInfo(
        ticker_yfinance="CNDX.L",
        ticker_stooq="CNDX.UK",
        display_name="iShares NASDAQ 100 (CNDX)",
        asset_class="US Tech",
        risk_level="High"
    )
    CBU0 = ETFInfo(
        ticker_yfinance="CBU0.L",
        ticker_stooq="CBU0.UK",
        display_name="iShares Treasury 7-10Y (CBU0)",
        asset_class="US Bonds 7-10Y",
        risk_level="Medium"
    )
    IB01 = ETFInfo(
        ticker_yfinance="IB01.L",
        ticker_stooq="IB01.UK",
        display_name="iShares Treasury 0-1Y (IB01)",
        asset_class="Cash Equivalent",
        risk_level="Low"
    )

    @property
    def ticker_yfinance(self) -> str:
        return self.value.ticker_yfinance
    
    @property
    def ticker_stooq(self) -> str:
        return self.value.ticker_stooq
    
    @property
    def display_name(self) -> str:
        return self.value.display_name
    
    @property
    def asset_class(self) -> str:
        return self.value.asset_class
    
    @property
    def risk_level(self) -> str:
        return self.value.risk_level

    @classmethod
    def from_any_ticker(cls, ticker: str) -> "ETF":
        """
        Find ETF by any ticker format:

        Args:
            ticker: Ticker in any format (EIMI, EIMI.L, EIMI.UK)

        Returns:
            Matching ETF enum

        Raises:
            ValueError: If ticker not found
        """
        ticker_upper = ticker.upper().replace(".L", "").replace(".UK", "")
        for etf in cls:
            if etf.name == ticker_upper:
                return etf
        raise ValueError(f"Unknown ETF ticker: {ticker}")
    
@dataclass(frozen=True)
class PriceData:
    """
    Historical price data for ETF
    """
    etf: ETF
    start_date: datetime
    end_date: datetime
    start_price: float
    end_price: float

    def __post_init__(self):
        """Validate proce data after initialization"""
        if self.start_price <= 0:
            raise ValueError(f"start_price must be positive, got {self.start_price}")
        if self.end_price <= 0:
            raise ValueError(f"end_price must be positive, got {self.end_price}")
        if self.start_date >= self.end_date:
            raise ValueError(f"start_date must be before end_date")
        
    @property
    def momentum(self) -> float:
        """Calculate momentum as percentage change"""
        return (self.end_price - self.start_price) / self.start_price
    
    @property
    def momentum_pct(self) -> str:
        "format momentum"
        return f"{self.momentum * 100:+.2f}%"
    

@dataclass(frozen=True)
class MomentumRanking:
    """ETFs momentum ranking"""
    rankings: tuple[tuple[ETF, float], ...]
    period_start: datetime
    period_end: datetime
    calculated_at: datetime

    def __post_init__(self):
        """Validate ranking data"""
        if len(self.rankings) == 0:
            raise ValueError("Rankings cannot be empty")
        if len(self.rankings) != len(ETF):
            raise ValueError(f"Expected {len(ETF)} ETFs in ranking, got {len(self.rankings)}")
        
    @property
    def winner(self) -> ETF:
        """Highest momentum ETF"""
        return self.rankings[0][0]
    
    @property
    def winner_momentum(self) -> float:
        """Wining ETF momentum"""
        return self.rankings[0][1]
    
    def get_rank(self, etf: ETF) -> int:
        """Get rank position for ETF"""
        for i, (e, _) in enumerate(self.rankings, 1):
            if e == etf:
                return i
        raise ValueError(f"ETF {etf} not in ranking")
    
    def get_momentum(self, etf: ETF) -> float:
        """Specific ETF momentum"""
        for e, m in self.rankings:
            if e == etf:
                return m
        raise ValueError(f"ETF {etf} not in ranking")
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "rankings": [(e.name, m) for e, m in self.rankings],
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "calculated_at": self.calculated_at.isoformat(),
            "winner": self.winner.name,
            "winner_momentum": self.winner_momentum
        }
    
    def print_table(self) -> None:
        """Print ranking as formatted table"""
        print(f"\n Momentum Ranking ({self.period_start.date()} -> {self.period_end.date()})")
        print("-" * 55)
        for i, (etf, mom) in enumerate(self.rankings, 1):
            marker = "👑" if i == 1 else "  "
            print(f"{marker} #{i} {etf.ticker_yfinance:8} {mom*100:+7.2f}%  "
                  f"{etf.asset_class}")
        print("-" * 55)

@dataclass(frozen=True)
class Signal:
    "Full context investment signal"
    recommended_etf: ETF
    ranking: MomentumRanking
    previous_etf: Optional[ETF]
    requires_rebalance: bool
    created_at: datetime
    report: Optional[str] = None
    stooq_link: Optional[str] = None

    @property
    def action(self) -> str:
        """Human readable action string"""
        if not self.requires_rebalance:
            return f"HOLD {self.recommended_etf.name}"
        if self.previous_etf:
            return f"SWITCH {self.previous_etf.name} -> {self.recommended_etf.name}"
        return f"BUY {self.recommended_etf.name}"

    @property
    def action_emoji(self) -> str:
        """Get emoji representation of action"""
        if not self.requires_rebalance:
            return "✋"
        if self.previous_etf:
            return "🔄"
        return "💰"
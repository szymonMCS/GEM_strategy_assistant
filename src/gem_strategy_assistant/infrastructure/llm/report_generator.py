import logging
from typing import Optional

from momentum_assistant.domain import Signal, ETF
from .openai_client import OpenAIClient, LLMError

logger = logging.getLogger(__name__)

REPORT_PROMPT_TEMPLATE = """Jesteś asystentem inwestycyjnym analizującym strategię Momentum ETF.

## Dane wejściowe:

**Ranking Momentum (12M - 1M):**
{ranking}

**Zwycięzca:** {winner} ({winner_momentum})
**Poprzedni ETF:** {previous}
**Wymaga rebalancingu:** {rebalance}

**Link do porównania wykresów:** {stooq_link}

## Zadanie:

Wygeneruj zwięzły raport (4-6 zdań) w języku polskim zawierający:
1. Podsumowanie - który ETF wygrał i dlaczego (najwyższe momentum)
2. Czy warto rebalansować (uwzględnij koszty transakcyjne vs różnica momentum)
3. Krótki outlook dla zwycięskiego ETF

Pisz konkretnie i profesjonalnie. Używaj emoji dla czytelności.
NIE używaj nagłówków markdown - tylko płynny tekst."""

class ReportGenerator:
    """
    Generate investment reports using LLM.
    
    Separates prompt construction from LLM interaction.
    """
    def __init__(self, client: Optional[OpenAIClient] = None):
        """
        Initialize generator.
        
        Args:
            client: OpenAI client (creates new if not provided)
        """
        self._client = client
    
    @property
    def client(self) -> OpenAIClient:
        """Lazy-load client."""
        if self._client is None:
            self._client = OpenAIClient()
        return self._client
    
    def generate(self, signal: Signal, stooq_link: Optional[str] = None) -> str:
        """
        Generate investment report for signal.
        
        Args:
            signal: Investment signal with ranking
            stooq_link: Optional Stooq comparison URL
            
        Returns:
            Generated report text
            
        Raises:
            LLMError: If generation fails
        """
        prompt = self._build_prompt(signal, stooq_link)
        
        logger.info(f"Generating report for signal: {signal.recommended_etf.name}")
        
        return self.client.complete(prompt, max_tokens=500, temperature=0.7)
    
    def _build_prompt(self, signal: Signal, stooq_link: Optional[str]) -> str:
        """Build prompt from signal data."""
        ranking_text = "\n".join(
            f"#{i+1} {etf.name}: {mom*100:+.2f}% ({etf.asset_class})"
            for i, (etf, mom) in enumerate(signal.ranking.rankings)
        )
        
        return REPORT_PROMPT_TEMPLATE.format(
            ranking=ranking_text,
            winner=signal.recommended_etf.display_name,
            winner_momentum=f"{signal.ranking.winner_momentum*100:+.2f}%",
            previous=signal.previous_etf.name if signal.previous_etf else "Brak (pierwsza analiza)",
            rebalance="TAK   " if signal.requires_rebalance else "NIE   ",
            stooq_link=stooq_link or "Niedostępny"
        )
    
    @staticmethod
    def is_available() -> bool:
        """Check if report generation is available."""
        return OpenAIClient.is_available()
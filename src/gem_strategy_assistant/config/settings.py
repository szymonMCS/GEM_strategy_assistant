from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import logging

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    polygon_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    notification_email: Optional[str] = None
    pushover_user_key: Optional[str] = None
    pushover_api_token: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    lookback_months: int = 12
    skip_months: int = 1
    db_path: Path = Path("data/momentum.db")
    gradio_port: int = 7860
    log_level: str = "INFO"
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    def setup_logging(self) -> None:
        """Configure logging based on settings."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def print_status(self) -> None:
        """Print configuration status."""
        print("\n     Konfiguracja:")
        
        checks = [
            ("OpenAI API", self.openai_api_key, True),
            ("OpenAI Model", self.openai_model, False),
            ("Polygon API", self.polygon_api_key, False),
            ("Serper API", self.serper_api_key, False),
            ("Brave API", self.brave_api_key, False),
            ("SendGrid", self.sendgrid_api_key, False),
            ("Pushover", self.pushover_user_key, False),
        ]
        
        for name, value, required in checks:
            if isinstance(value, str) and not value.startswith("sk-") and len(value) < 50:
                status = f"    {value}" if value else "    (not set)"
            else:
                status = "    (configured)" if value else ("    REQUIRED!" if required else "    (optional)")
            print(f"   {name}: {status}")
        
        print(f"\n   Strategy: {self.lookback_months}M - {self.skip_months}M")
        print(f"   Database: {self.db_path}")

_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get settings instance (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

settings = get_settings()
import logging
from datetime import datetime, timedelta
from io import StringIO
import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from momentum_assistant.domain import ETF, PriceData
from momentum_assistant.config import get_stooq_ticker

logger = logging.getLogger(__name__)

STOOQ_CSV_URL = "https://stooq.pl/q/d/l/"


class StooqError(Exception):
    pass


class StooqProvider:
    def __init__(self, max_retries: int = 3, timeout: int = 30):
        self.max_retries = max_retries
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _fetch_csv(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch historical data from STOOQ as CSV.

        Args:
            ticker: STOOQ ticker (e.g. EIMI.UK)
            start: Start date YYYYMMDD
            end: End date YYYYMMDD

        Returns:
            DataFrame with historical prices
        """
        params = {
            "s": ticker.lower(),
            "d1": start,
            "d2": end,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(STOOQ_CSV_URL, params=params)
                response.raise_for_status()

            content = response.text
            if "Brak danych" in content or len(content.strip()) < 50:
                raise StooqError(f"No data for {ticker}")

            df = pd.read_csv(StringIO(content))

            if df.empty or len(df) < 2:
                raise StooqError(f"Insufficient data for {ticker}")

            column_map = {
                "Data": "Date",
                "Otwarcie": "Open",
                "Najwyzszy": "High",
                "Najnizszy": "Low",
                "Zamkniecie": "Close",
                "Wolumen": "Volume"
            }
            df = df.rename(columns=column_map)

            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")

            return df

        except httpx.HTTPStatusError as e:
            raise StooqError(f"HTTP error for {ticker}: {e}")
        except pd.errors.EmptyDataError:
            raise StooqError(f"Empty CSV for {ticker}")
        except Exception as e:
            if isinstance(e, StooqError):
                raise
            raise StooqError(f"Failed to fetch {ticker}: {e}")

    def get_price_data(self, etf: ETF, start_date: datetime, end_date: datetime) -> PriceData:
        """
        Fetch historical price data for an ETF.

        Args:
            etf: ETF enum
            start_date: Period start
            end_date: Period end

        Returns:
            PriceData with start and end prices
        """
        ticker = get_stooq_ticker(etf)
        logger.info(f"Fetching data for {etf.name} from STOOQ ({ticker})")

        start_str = start_date.strftime("%Y%m%d")
        end_with_buffer = (end_date + timedelta(days=5)).strftime("%Y%m%d")

        df = self._fetch_csv(ticker, start_str, end_with_buffer)

        start_price = float(df.iloc[0]["Close"])
        end_price = float(df.iloc[-1]["Close"])

        actual_start = df.iloc[0]["Date"].to_pydatetime()
        actual_end = df.iloc[-1]["Date"].to_pydatetime()

        logger.debug(
            f"{etf.name}: {actual_start.date()} ({start_price:.2f}) -> "
            f"{actual_end.date()} ({end_price:.2f})"
        )

        return PriceData(
            etf=etf,
            start_date=actual_start,
            end_date=actual_end,
            start_price=start_price,
            end_price=end_price
        )

    def get_all_etf_data(
        self, start_date: datetime, end_date: datetime, fail_fast: bool = True
    ) -> list[PriceData]:
        """
        Fetch data for all tracked ETFs.

        Args:
            start_date: Period start
            end_date: Period end
            fail_fast: If True, raise on first error

        Returns:
            List of PriceData for all ETFs
        """
        results = []
        errors = []

        for etf in ETF:
            try:
                data = self.get_price_data(etf, start_date, end_date)
                results.append(data)
                print(f"      {etf.name}: {data.momentum_pct}")
            except Exception as e:
                error_msg = f"{etf.name}: {e}"
                logger.error(error_msg)
                print(f"      {error_msg}")

                if fail_fast:
                    raise StooqError(f"Failed to fetch {etf.name}: {e}")
                errors.append(error_msg)

        if errors and not fail_fast:
            logger.warning(f"Failed to fetch {len(errors)} ETFs: {errors}")

        return results

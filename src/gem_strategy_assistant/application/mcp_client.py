import logging
from typing import Optional, Any
import asyncio
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClientAdapter:
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        logger.info("MCPClientAdapter initialized")

    @asynccontextmanager
    async def _connect_to_server(self, server_name: str, command: list[str]):
        """
        Connect to an MCP server.
        
        Args:
            server_name: Name of the server
            command: Command to start the server
            
        Yields:
            ClientSession for the connected server
        """
        server_params = StdioServerParameters(
            command=command[0],
            args=command[1:],
            env=None,
        )
        
        logger.info(f"Connecting to MCP server: {server_name}")
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info(f"✅ Connected to {server_name}")
                yield session

    async def get_momentum_ranking(self) -> dict:
        """
        Get current momentum ranking from financial server.
        
        Returns:
            Dictionary with momentum ranking
        """
        logger.info("Calling financial server: get_momentum_ranking")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.financial_server"]
        
        async with self._connect_to_server("financial", command) as session:
            result = await session.call_tool("get_momentum_ranking", arguments={})
            logger.info("✅ Momentum ranking retrieved")
            return result.content[0].text if result.content else {}

    async def get_etf_price_data(self, etf_name: str, start_date: str, end_date: str) -> dict:
        """
        Get ETF price data from financial server.
        
        Args:
            etf_name: ETF name (e.g., "EIMI")
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            Dictionary with price data
        """
        logger.info(f"Calling financial server: get_etf_price_data for {etf_name}")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.financial_server"]
        
        async with self._connect_to_server("financial", command) as session:
            result = await session.call_tool(
                "get_etf_price_data",
                arguments={
                    "etf_name": etf_name,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
            logger.info(f"✅ Price data retrieved for {etf_name}")
            return result.content[0].text if result.content else {}

    async def search_web(self, query: str, num_results: int = 10) -> dict:
        """
        Search the web using search server.
        
        Args:
            query: Search query
            num_results: Number of results (default: 10)
            
        Returns:
            Dictionary with search results
        """
        logger.info(f"Calling search server: search_web for '{query}'")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.search_server"]
        
        async with self._connect_to_server("search", command) as session:
            result = await session.call_tool(
                "search_web",
                arguments={"query": query, "num_results": num_results}
            )
            logger.info("✅ Web search complete")
            return result.content[0].text if result.content else {}

    async def search_etf_context(self, etf_name: str) -> dict:
        """
        Search for ETF context using search server.
        
        Args:
            etf_name: ETF name (e.g., "EIMI")
            
        Returns:
            Dictionary with ETF context
        """
        logger.info(f"Calling search server: search_etf_context for {etf_name}")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.search_server"]
        
        async with self._connect_to_server("search", command) as session:
            result = await session.call_tool(
                "search_etf_context",
                arguments={"etf_name": etf_name}
            )
            logger.info(f"✅ ETF context retrieved for {etf_name}")
            return result.content[0].text if result.content else {}

    async def search_market_outlook(self, asset_class: str, year: int = 2026) -> dict:
        """
        Search for market outlook using search server.
        
        Args:
            asset_class: Asset class (e.g., "emerging markets")
            year: Year for outlook (default: 2026)
            
        Returns:
            Dictionary with market outlook
        """
        logger.info(f"Calling search server: search_market_outlook for {asset_class}")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.search_server"]
        
        async with self._connect_to_server("search", command) as session:
            result = await session.call_tool(
                "search_market_outlook",
                arguments={"asset_class": asset_class, "year": year}
            )
            logger.info("✅ Market outlook retrieved")
            return result.content[0].text if result.content else {}

    async def send_email(self, to_email: str, subject: str, content: str) -> dict:
        """
        Send email notification.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            content: Email content
            
        Returns:
            Dictionary with send status
        """
        logger.info(f"Calling notification server: send_email to {to_email}")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.notification_server"]
        
        async with self._connect_to_server("notification", command) as session:
            result = await session.call_tool(
                "send_email",
                arguments={
                    "to_email": to_email,
                    "subject": subject,
                    "content": content,
                }
            )
            logger.info("✅ Email sent")
            return result.content[0].text if result.content else {}

    async def send_signal_email(
        self, to_email: str, signal_type: str, etf_name: str, details: str
    ) -> dict:
        """
        Send trading signal email.
        
        Args:
            to_email: Recipient email
            signal_type: Signal type ("BUY", "SELL", "HOLD")
            etf_name: ETF name
            details: Signal details
            
        Returns:
            Dictionary with send status
        """
        logger.info(f"Calling notification server: send_signal_email ({signal_type} {etf_name})")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.notification_server"]
        
        async with self._connect_to_server("notification", command) as session:
            result = await session.call_tool(
                "send_signal_email",
                arguments={
                    "to_email": to_email,
                    "signal_type": signal_type,
                    "etf_name": etf_name,
                    "details": details,
                }
            )
            logger.info("✅ Signal email sent")
            return result.content[0].text if result.content else {}

    async def send_signal_push(
        self, signal_type: str, etf_name: str, details: str, priority: int = 1
    ) -> dict:
        """
        Send trading signal push notification.
        
        Args:
            signal_type: Signal type ("BUY", "SELL", "HOLD")
            etf_name: ETF name
            details: Signal details
            priority: Notification priority (default: 1)
            
        Returns:
            Dictionary with send status
        """
        logger.info(f"Calling notification server: send_signal_push ({signal_type} {etf_name})")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.notification_server"]
        
        async with self._connect_to_server("notification", command) as session:
            result = await session.call_tool(
                "send_signal_push",
                arguments={
                    "signal_type": signal_type,
                    "etf_name": etf_name,
                    "details": details,
                    "priority": priority,
                }
            )
            logger.info("✅ Signal push sent")
            return result.content[0].text if result.content else {}

    async def check_notification_status(self) -> dict:
        """
        Check which notification channels are configured.
        
        Returns:
            Dictionary with notification channel status
        """
        logger.info("Calling notification server: check_notification_status")
        
        command = ["python", "-m", "gem_strategy_assistant.infrastructure.mcp_servers.notification_server"]
        
        async with self._connect_to_server("notification", command) as session:
            result = await session.call_tool("check_notification_status", arguments={})
            logger.info("✅ Notification status retrieved")
            return result.content[0].text if result.content else {}

    def get_momentum_ranking_sync(self) -> dict:
        """Synchronous wrapper for get_momentum_ranking."""
        return asyncio.run(self.get_momentum_ranking())

    def search_web_sync(self, query: str, num_results: int = 10) -> dict:
        """Synchronous wrapper for search_web."""
        return asyncio.run(self.search_web(query, num_results))

    def search_etf_context_sync(self, etf_name: str) -> dict:
        """Synchronous wrapper for search_etf_context."""
        return asyncio.run(self.search_etf_context(etf_name))

    def send_signal_email_sync(
        self, to_email: str, signal_type: str, etf_name: str, details: str
    ) -> dict:
        """Synchronous wrapper for send_signal_email."""
        return asyncio.run(self.send_signal_email(to_email, signal_type, etf_name, details))

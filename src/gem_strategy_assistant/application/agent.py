import logging
import sqlite3
from typing import Annotated, TypedDict, Literal
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from gem_strategy_assistant.application.use_cases import (
    AnalyzeAndRecommendUseCase,
    GetSignalHistoryUseCase,
    ResearchETFUseCase,
    ResearchMarketOutlookUseCase,
)

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    task: str
    
    include_research: bool
    max_etfs_to_research: int
    save_to_db: bool
    
    etf_name: str | None
    asset_class: str | None
    year: int
    days: int
    
    result: dict | None
    error: str | None
    completed: bool


class MomentumAgent:
    def __init__(
        self,
        checkpoint_path: str = "momentum_agent_checkpoints.db",
    ):
        """
        Initialize the momentum agent.

        Args:
            checkpoint_path: Path to SQLite checkpoint database
        """
        self.checkpoint_path = checkpoint_path
        self.checkpoint_conn = sqlite3.connect(checkpoint_path, check_same_thread=False)

        self.analyze_use_case = AnalyzeAndRecommendUseCase()
        self.history_use_case = GetSignalHistoryUseCase()
        self.research_etf_use_case = ResearchETFUseCase()
        self.market_outlook_use_case = ResearchMarketOutlookUseCase()

        self.graph = self._build_graph()

        logger.info(f"MomentumAgent initialized with checkpoints at {checkpoint_path}")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        workflow = StateGraph(AgentState)
        
        workflow.add_node("route_task", self._route_task)
        workflow.add_node("analyze_and_recommend", self._analyze_and_recommend)
        workflow.add_node("get_history", self._get_history)
        workflow.add_node("research_etf", self._research_etf)
        workflow.add_node("market_outlook", self._market_outlook)
        workflow.add_node("finalize", self._finalize)
        
        workflow.set_entry_point("route_task")
        
        workflow.add_conditional_edges(
            "route_task",
            self._route_to_task,
            {
                "analyze": "analyze_and_recommend",
                "history": "get_history",
                "research_etf": "research_etf",
                "market_outlook": "market_outlook",
            }
        )
        
        workflow.add_edge("analyze_and_recommend", "finalize")
        workflow.add_edge("get_history", "finalize")
        workflow.add_edge("research_etf", "finalize")
        workflow.add_edge("market_outlook", "finalize")
        
        workflow.add_edge("finalize", END)

        checkpointer = SqliteSaver(self.checkpoint_conn)
        compiled = workflow.compile(checkpointer=checkpointer)

        logger.info("LangGraph workflow compiled with checkpointing")
        return compiled

    def _route_task(self, state: AgentState) -> AgentState:
        """Route to the appropriate task handler."""
        task = state.get("task", "analyze")
        logger.info(f"Routing to task: {task}")
        return state

    def _route_to_task(self, state: AgentState) -> Literal["analyze", "history", "research_etf", "market_outlook"]:
        """Determine which task to execute."""
        task = state.get("task", "analyze")
        
        valid_tasks = ["analyze", "history", "research_etf", "market_outlook"]
        if task not in valid_tasks:
            logger.warning(f"Invalid task '{task}', defaulting to 'analyze'")
            return "analyze"
        
        return task

    def _analyze_and_recommend(self, state: AgentState) -> AgentState:
        """Execute momentum analysis and generate recommendation."""
        logger.info("Executing AnalyzeAndRecommendUseCase")
        
        try:
            result = self.analyze_use_case.execute(
                include_research=state.get("include_research", True),
                max_etfs_to_research=state.get("max_etfs_to_research", 3),
                save_to_db=state.get("save_to_db", True),
            )
            
            state["result"] = result
            state["error"] = None
            logger.info("✅ Analysis complete")
            
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            state["result"] = None
            state["error"] = str(e)
        
        return state

    def _get_history(self, state: AgentState) -> AgentState:
        """Retrieve signal history."""
        logger.info("Executing GetSignalHistoryUseCase")
        
        try:
            result = self.history_use_case.execute(
                days=state.get("days", 30)
            )
            
            state["result"] = result
            state["error"] = None
            logger.info("✅ History retrieval complete")
            
        except Exception as e:
            logger.error(f"❌ History retrieval failed: {e}")
            state["result"] = None
            state["error"] = str(e)
        
        return state

    def _research_etf(self, state: AgentState) -> AgentState:
        """Research a specific ETF."""
        etf_name = state.get("etf_name")
        
        if not etf_name:
            logger.error("ETF name not provided")
            state["result"] = None
            state["error"] = "ETF name is required for research"
            return state
        
        logger.info(f"Executing ResearchETFUseCase for {etf_name}")
        
        try:
            result = self.research_etf_use_case.execute(
                etf_name=etf_name,
                use_cache=True,
            )
            
            state["result"] = result
            state["error"] = None
            logger.info(f"✅ ETF research complete for {etf_name}")
            
        except Exception as e:
            logger.error(f"❌ ETF research failed: {e}")
            state["result"] = None
            state["error"] = str(e)
        
        return state

    def _market_outlook(self, state: AgentState) -> AgentState:
        """Research market outlook."""
        asset_class = state.get("asset_class")
        
        if not asset_class:
            logger.error("Asset class not provided")
            state["result"] = None
            state["error"] = "Asset class is required for market outlook"
            return state
        
        logger.info(f"Executing ResearchMarketOutlookUseCase for {asset_class}")
        
        try:
            result = self.market_outlook_use_case.execute(
                asset_class=asset_class,
                year=state.get("year", 2026),
            )
            
            state["result"] = result
            state["error"] = None
            logger.info(f"✅ Market outlook research complete")
            
        except Exception as e:
            logger.error(f"❌ Market outlook research failed: {e}")
            state["result"] = None
            state["error"] = str(e)
        
        return state

    def _finalize(self, state: AgentState) -> AgentState:
        """Finalize the workflow and prepare response."""
        logger.info("Finalizing workflow")
        
        state["completed"] = True
        
        if state["result"] and isinstance(state["result"], dict):
            if "metadata" not in state["result"]:
                state["result"]["metadata"] = {}
            
            state["result"]["metadata"]["execution_time"] = datetime.now().isoformat()
            state["result"]["metadata"]["task"] = state.get("task", "unknown")
        
        logger.info("✅ Workflow finalized")
        return state

    def run_analysis(
        self,
        include_research: bool = True,
        max_etfs_to_research: int = 3,
        save_to_db: bool = True,
    ) -> dict:
        """
        Run momentum analysis workflow.
        
        Args:
            include_research: Include market research (default: True)
            max_etfs_to_research: Max ETFs to research (default: 3)
            save_to_db: Save signal to database (default: True)
            
        Returns:
            Dictionary with analysis results
        """
        logger.info("Starting analysis workflow")
        
        initial_state = {
            "task": "analyze",
            "include_research": include_research,
            "max_etfs_to_research": max_etfs_to_research,
            "save_to_db": save_to_db,
            "etf_name": None,
            "asset_class": None,
            "year": 2026,
            "days": 30,
            "result": None,
            "error": None,
            "completed": False,
        }

        config = {"configurable": {"thread_id": "1"}}
        final_state = self.graph.invoke(initial_state, config)
        
        if final_state.get("error"):
            logger.error(f"Workflow failed: {final_state['error']}")
            raise Exception(final_state["error"])
        
        return final_state.get("result", {})

    def get_history(self, days: int = 30) -> dict:
        """
        Get signal history.
        
        Args:
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary with signal history
        """
        logger.info(f"Starting history workflow (last {days} days)")
        
        initial_state = {
            "task": "history",
            "include_research": False,
            "max_etfs_to_research": 0,
            "save_to_db": False,
            "etf_name": None,
            "asset_class": None,
            "year": 2026,
            "days": days,
            "result": None,
            "error": None,
            "completed": False,
        }

        config = {"configurable": {"thread_id": "1"}}
        final_state = self.graph.invoke(initial_state, config)
        
        if final_state.get("error"):
            logger.error(f"Workflow failed: {final_state['error']}")
            raise Exception(final_state["error"])
        
        return final_state.get("result", {})

    def research_etf(self, etf_name: str) -> dict:
        """
        Research a specific ETF.
        
        Args:
            etf_name: ETF name (e.g., "EIMI")
            
        Returns:
            Dictionary with ETF research
        """
        logger.info(f"Starting ETF research workflow for {etf_name}")
        
        initial_state = {
            "task": "research_etf",
            "include_research": False,
            "max_etfs_to_research": 0,
            "save_to_db": False,
            "etf_name": etf_name,
            "asset_class": None,
            "year": 2026,
            "days": 30,
            "result": None,
            "error": None,
            "completed": False,
        }

        config = {"configurable": {"thread_id": "1"}}
        final_state = self.graph.invoke(initial_state, config)
        
        if final_state.get("error"):
            logger.error(f"Workflow failed: {final_state['error']}")
            raise Exception(final_state["error"])
        
        return final_state.get("result", {})

    def research_market_outlook(self, asset_class: str, year: int = 2026) -> dict:
        """
        Research market outlook.
        
        Args:
            asset_class: Asset class (e.g., "emerging markets")
            year: Year for outlook (default: 2026)
            
        Returns:
            Dictionary with market outlook research
        """
        logger.info(f"Starting market outlook workflow for {asset_class}")
        
        initial_state = {
            "task": "market_outlook",
            "include_research": False,
            "max_etfs_to_research": 0,
            "save_to_db": False,
            "etf_name": None,
            "asset_class": asset_class,
            "year": year,
            "days": 30,
            "result": None,
            "error": None,
            "completed": False,
        }

        config = {"configurable": {"thread_id": "1"}}
        final_state = self.graph.invoke(initial_state, config)
        
        if final_state.get("error"):
            logger.error(f"Workflow failed: {final_state['error']}")
            raise Exception(final_state["error"])
        
        return final_state.get("result", {})

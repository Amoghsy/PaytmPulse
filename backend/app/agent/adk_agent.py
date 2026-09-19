"""
Paytm Pulse - Phase 5 Google ADK Pulse Investigation Agent
Autonomous tool-using business intelligence and what-if simulation reasoning agent.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Tuple
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent.schemas import AgentAnalysis, ImpactEstimate, ChatResponse
from app.agent.prompts import (
    AGENT_SYSTEM_INSTRUCTION,
    EVENT_INVESTIGATION_PROMPT,
    MERCHANT_HEALTH_INVESTIGATION_PROMPT,
    CHAT_INVESTIGATION_PROMPT
)
from app.agent.tools.sales_tools import get_sales_analysis
from app.agent.tools.anomaly_tools import detect_anomalies
from app.agent.tools.forecast_tools import forecast_demand
from app.agent.tools.inventory_tools import predict_stockout, get_all_stockout_risks
from app.agent.tools.customer_tools import get_customer_intelligence
from app.agent.tools.opportunity_tools import detect_opportunities
from app.agent.tools.event_tools import get_business_event
from app.agent.tools.memory_tools import get_recent_merchant_context
from app.agent.tools.outcome_tools import get_action_outcome, get_action_history
from app.agent.tools.feedback_tools import get_recommendation_feedback, get_merchant_feedback_summary
from app.agent.tools.financial_tools import get_financial_opportunities
from app.agent.tools.decision_tools import generate_next_best_actions
from app.agent.tools.simulation_tools import simulate_business_action

load_dotenv()
logger = logging.getLogger("paytm_pulse.agent.adk")

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_TOOL_CALLS = int(os.getenv("AGENT_MAX_TOOL_CALLS", "10"))


def build_tool_registry(db: Optional[Session] = None) -> List[Callable]:
    """
    Constructs clean, strongly-typed tool wrappers bound to the active database session.
    All tools are read-only and safe for autonomous ADK agent invocation.
    """
    def tool_get_sales_analysis(merchant_id: str) -> str:
        """
        Get multi-horizon sales performance, trends, top products, and hourly sales for a merchant.
        
        Args:
            merchant_id: Unique merchant identifier.
        """
        try:
            res = get_sales_analysis(merchant_id=merchant_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Failed to retrieve sales analysis: {str(e)}", "merchant_id": merchant_id})

    def tool_detect_anomalies(merchant_id: str, product_id: Optional[str] = None) -> str:
        """
        Detect statistical demand spikes, sales drops, or revenue anomalies for a merchant or specific product.
        
        Args:
            merchant_id: Unique merchant identifier.
            product_id: Optional specific product identifier.
        """
        try:
            res = detect_anomalies(merchant_id=merchant_id, product_id=product_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Anomaly detection failed: {str(e)}", "merchant_id": merchant_id})

    def tool_forecast_demand(merchant_id: str, product_id: str, horizon: str = "next_hour") -> str:
        """
        Generate ML demand forecasts for a product across short and medium horizons ('next_hour', 'next_6h', 'next_day').
        
        Args:
            merchant_id: Unique merchant identifier.
            product_id: Unique product identifier.
            horizon: Forecast time horizon ('next_hour', 'next_6h', 'next_day').
        """
        try:
            res = forecast_demand(merchant_id=merchant_id, product_id=product_id, horizon=horizon, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Demand forecasting failed: {str(e)}", "merchant_id": merchant_id})

    def tool_predict_stockout(merchant_id: str, product_id: str) -> str:
        """
        Evaluate real-time stockout risk, velocity, and estimated runway hours for a specific product.
        
        Args:
            merchant_id: Unique merchant identifier.
            product_id: Unique product identifier.
        """
        try:
            res = predict_stockout(merchant_id=merchant_id, product_id=product_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Stockout prediction failed: {str(e)}", "merchant_id": merchant_id})

    def tool_get_all_stockout_risks(merchant_id: str) -> str:
        """
        Retrieve all at-risk products for a merchant sorted by urgency of stockout.
        
        Args:
            merchant_id: Unique merchant identifier.
        """
        try:
            res = get_all_stockout_risks(merchant_id=merchant_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Stockout risks query failed: {str(e)}", "merchant_id": merchant_id})

    def tool_get_customer_intelligence(merchant_id: str) -> str:
        """
        Retrieve customer RFM segmentation, active/inactive lists, and churn risk summaries for a merchant.
        
        Args:
            merchant_id: Unique merchant identifier.
        """
        try:
            res = get_customer_intelligence(merchant_id=merchant_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Customer intelligence failed: {str(e)}", "merchant_id": merchant_id})

    def tool_detect_opportunities(merchant_id: str) -> str:
        """
        Scan sales trends, stockout risks, customer churn, and cross-sell affinities to discover high-value opportunities.
        
        Args:
            merchant_id: Unique merchant identifier.
        """
        try:
            res = detect_opportunities(merchant_id=merchant_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Opportunity detection failed: {str(e)}", "merchant_id": merchant_id})

    def tool_get_business_event(event_id: str) -> str:
        """
        Retrieve real-time business event payload, severity, source, and metadata.
        
        Args:
            event_id: Unique business event identifier.
        """
        try:
            res = get_business_event(event_id=event_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Event lookup failed: {str(e)}", "event_id": event_id})

    def tool_get_recent_merchant_context(merchant_id: str) -> str:
        """
        Retrieve fast Redis memory snapshot for a merchant including recent transactions, alerts, and state.
        
        Args:
            merchant_id: Unique merchant identifier.
        """
        try:
            res = get_recent_merchant_context(merchant_id=merchant_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Memory context lookup failed: {str(e)}", "merchant_id": merchant_id})

    def tool_get_action_outcome(action_id: str) -> str:
        """
        Retrieve the measured closed-loop business outcome for a specific executed action ID.
        
        Args:
            action_id: Unique action identifier.
        """
        try:
            return get_action_outcome(action_id=action_id, db=db)
        except Exception as e:
            return json.dumps({"error": f"Outcome lookup failed: {str(e)}", "action_id": action_id})

    def tool_get_action_history(merchant_id: str, limit: int = 5) -> str:
        """
        Retrieve historical executed actions and their measured business outcomes for a merchant.
        
        Args:
            merchant_id: Unique merchant identifier.
            limit: Maximum past actions to retrieve.
        """
        try:
            return get_action_history(merchant_id=merchant_id, limit=limit, db=db)
        except Exception as e:
            return json.dumps({"error": f"Action history lookup failed: {str(e)}", "merchant_id": merchant_id})

    def tool_get_recommendation_feedback(recommendation_id: str) -> str:
        """
        Retrieve merchant feedback status, rating, and effectiveness notes for a recommendation.
        
        Args:
            recommendation_id: Unique recommendation identifier.
        """
        try:
            return get_recommendation_feedback(recommendation_id=recommendation_id, db=db)
        except Exception as e:
            return json.dumps({"error": f"Feedback lookup failed: {str(e)}", "recommendation_id": recommendation_id})

    def tool_get_merchant_feedback_summary(merchant_id: str) -> str:
        """
        Retrieve overall merchant feedback summary, approval rate, and decision effectiveness stats.
        
        Args:
            merchant_id: Unique merchant identifier.
        """
        try:
            return get_merchant_feedback_summary(merchant_id=merchant_id, db=db)
        except Exception as e:
            return json.dumps({"error": f"Feedback summary failed: {str(e)}", "merchant_id": merchant_id})

    def tool_get_financial_opportunities(merchant_id: str) -> str:
        """
        Retrieve contextual simulated financial opportunities (e.g. Working Capital) based on merchant growth signals.
        
        Args:
            merchant_id: Unique merchant identifier.
        """
        try:
            return get_financial_opportunities(merchant_id=merchant_id, db=db)
        except Exception as e:
            return json.dumps({"error": f"Financial opportunities lookup failed: {str(e)}", "merchant_id": merchant_id})

    def tool_generate_next_best_actions(merchant_id: str, event_id: Optional[str] = None) -> str:
        """
        Generate and rank candidate actions for a merchant using the Next Best Action decision engine.
        
        Args:
            merchant_id: Unique merchant identifier.
            event_id: Optional business event ID.
        """
        try:
            res = generate_next_best_actions(merchant_id=merchant_id, event_id=event_id, db=db)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Decision generation failed: {str(e)}", "merchant_id": merchant_id})

    def tool_simulate_business_action(
        merchant_id: str,
        action_type: str,
        product_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Simulate the projected impact of a potential action (RESTOCK_PRODUCT, RUN_PROMOTION, CUSTOMER_WINBACK, CREATE_BUNDLE, ADJUST_OFFER, MONITOR_TREND, DO_NOTHING).
        Strictly read-only and sets executed=False.
        
        Args:
            merchant_id: Unique merchant identifier.
            action_type: Action type to simulate ('RESTOCK_PRODUCT', 'RUN_PROMOTION', 'CUSTOMER_WINBACK', 'CREATE_BUNDLE', 'ADJUST_OFFER', 'DO_NOTHING', 'MONITOR_TREND').
            product_id: Optional product identifier for product-specific actions.
            parameters: Optional dictionary of scenario parameters (e.g. quantity, discount_percentage).
        """
        try:
            res = simulate_business_action(
                merchant_id=merchant_id,
                action_type=action_type,
                product_id=product_id,
                parameters=parameters,
                db=db
            )
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"error": f"Simulation failed: {str(e)}", "merchant_id": merchant_id, "action_type": action_type, "executed": False})

    return [
        tool_get_sales_analysis,
        tool_detect_anomalies,
        tool_forecast_demand,
        tool_predict_stockout,
        tool_get_all_stockout_risks,
        tool_get_customer_intelligence,
        tool_detect_opportunities,
        tool_get_business_event,
        tool_get_recent_merchant_context,
        tool_get_action_outcome,
        tool_get_action_history,
        tool_get_recommendation_feedback,
        tool_get_merchant_feedback_summary,
        tool_get_financial_opportunities,
        tool_generate_next_best_actions,
        tool_simulate_business_action
    ]


def _clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extracts and parses JSON from response text, with graceful preservation of natural LLM text."""
    if not raw_text:
        return {}
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # 1. Try direct JSON parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {"response": str(parsed)}
    except Exception:
        pass

    # 2. Try regex extraction of JSON {...}
    import re
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            extracted = json.loads(json_match.group(0))
            if isinstance(extracted, dict):
                return extracted
        except Exception:
            pass

    # 3. Direct preservation of Gemini LLM generative response
    return {
        "response": text,
        "suggested_action": "MONITOR"
    }


class PulseInvestigationAgent:
    """
    Main Google ADK Investigation Agent for Paytm Pulse.
    Manages dynamic tool selection, multi-step business investigation, and what-if simulation.
    """

    def __init__(self, db: Optional[Session] = None, model_name: Optional[str] = None):
        self.db = db
        self.model_name = model_name or DEFAULT_MODEL
        self.tools = build_tool_registry(db=self.db)
        self.session_service = InMemorySessionService()
        self.agent = self._create_adk_agent()
        self.runner = Runner(
            app_name="paytm_pulse",
            agent=self.agent,
            session_service=self.session_service,
            auto_create_session=True
        )

    def _create_adk_agent(self) -> Agent:
        """Instantiates the Google ADK Agent with registered tools and system instructions."""
        return Agent(
            name="Pulse_Investigation_Agent",
            model=self.model_name,
            instruction=AGENT_SYSTEM_INSTRUCTION,
            tools=self.tools
        )

    def run_investigation(
        self,
        prompt: str,
        merchant_id: str,
        user_intent: str = "investigate"
    ) -> Tuple[Optional[Dict[str, Any]], List[str], bool]:
        """
        Executes dynamic ADK tool-calling loop with bounded execution.
        
        Returns:
            Tuple of (parsed_json_output, list_of_tools_called, used_simulation_boolean)
        """
        start_time = time.time()
        tools_called: List[str] = []
        used_simulation = False
        parsed_result = None

        logger.info(f"ADK Agent investigation initiated | merchant_id: {merchant_id} | intent: {user_intent}")

        try:
            # Check API key presence
            api_key = os.getenv("GOOGLE_API_KEY", "").strip()
            if not api_key:
                logger.info("No GOOGLE_API_KEY configured; skipping ADK cloud execution to fallback.")
                return None, [], False

            # We create a user message and run via ADK runner
            content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )

            session_id = f"session_{merchant_id}_{int(time.time())}"
            user_id = f"merchant_{merchant_id}"

            # Run async loop synchronously within runner
            import asyncio
            async def _execute_runner():
                nonlocal used_simulation
                final_text = ""
                call_count = 0

                async for event in self.runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content
                ):
                    # Inspect tool calls and events
                    if hasattr(event, "content") and event.content:
                        for part in getattr(event.content, "parts", []):
                            # Check function call
                            if hasattr(part, "function_call") and part.function_call:
                                fn_name = part.function_call.name
                                tools_called.append(fn_name)
                                call_count += 1
                                if "simulate" in fn_name:
                                    used_simulation = True
                                logger.info(f"ADK Agent dynamically invoked tool [{call_count}]: {fn_name}")
                                if call_count >= MAX_TOOL_CALLS:
                                    logger.warning(f"ADK Agent reached max tool calls limit ({MAX_TOOL_CALLS}). Halting further investigation.")
                                    break
                            # Check text response
                            if hasattr(part, "text") and part.text:
                                final_text += part.text

                    # Also inspect actions/output if present in ADK Event
                    if hasattr(event, "actions") and event.actions:
                        for act in event.actions:
                            if hasattr(act, "name"):
                                tools_called.append(act.name)

                return final_text

            # Execute with safe timeout
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    output_text = pool.submit(asyncio.run, _execute_runner()).result(timeout=15.0)
            else:
                output_text = loop.run_until_complete(asyncio.wait_for(_execute_runner(), timeout=15.0))

            if output_text:
                parsed_result = _clean_json_response(output_text)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"ADK Agent investigation completed in {duration_ms:.2f}ms | "
                    f"tools_called: {len(tools_called)} {tools_called} | simulation_used: {used_simulation}"
                )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(f"ADK Agent investigation encountered exception: {e} after {duration_ms:.2f}ms")
            parsed_result = None

        return parsed_result, tools_called, used_simulation

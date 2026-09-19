"""
Paytm Pulse - n8n Workflow Integration Service
Handles authenticated API communication, webhook triggering, and health checks with n8n.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("paytm_pulse.n8n")

N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678").rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY", "").strip()


def get_n8n_headers() -> Dict[str, str]:
    """Returns standard headers including the n8n API key if configured."""
    headers = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
    return headers


def check_n8n_connection(base_url: Optional[str] = None) -> bool:
    """
    Checks if n8n service is reachable across local or container network addresses.
    """
    candidate_urls = [
        base_url or N8N_BASE_URL,
        "http://n8n:5678",
        "http://localhost:5678",
        "http://127.0.0.1:5678",
        "http://host.docker.internal:5678"
    ]
    seen = set()
    for url in candidate_urls:
        if not url or url in seen:
            continue
        seen.add(url)
        try:
            with httpx.Client(timeout=1.0) as client:
                resp = client.get(f"{url.rstrip('/')}/healthz")
                if resp.status_code == 200:
                    return True
        except Exception:
            continue
    return False


def trigger_n8n_webhook(
    webhook_path: str,
    payload: Dict[str, Any],
    base_url: str = N8N_BASE_URL
) -> Dict[str, Any]:
    """
    Triggers an n8n webhook workflow with payload data.
    
    Args:
        webhook_path: Webhook path (e.g. "webhook/paytm-transaction" or "webhook-test/...")
        payload: JSON payload to pass to n8n workflow
        base_url: Optional n8n base URL override
        
    Returns:
        Dictionary with status and response payload
    """
    url = f"{base_url}/{webhook_path.lstrip('/')}"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, json=payload, headers=get_n8n_headers())
            return {
                "ok": resp.is_success,
                "status_code": resp.status_code,
                "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            }
    except Exception as e:
        logger.warning(f"Failed to trigger n8n webhook at {url}: {str(e)}")
        return {
            "ok": False,
            "status_code": 0,
            "error": str(e)
        }


def list_n8n_workflows(base_url: str = N8N_BASE_URL) -> List[Dict[str, Any]]:
    """
    Retrieves list of active workflows from n8n REST API using N8N_API_KEY.
    """
    if not N8N_API_KEY:
        logger.debug("N8N_API_KEY is not configured; cannot list workflows.")
        return []

    url = f"{base_url}/api/v1/workflows"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url, headers=get_n8n_headers())
            if resp.is_success:
                data = resp.json()
                return data.get("data", [])
            return []
    except Exception as e:
        logger.warning(f"Failed to fetch n8n workflows: {str(e)}")
        return []

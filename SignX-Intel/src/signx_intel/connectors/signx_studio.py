"""Connector for SignX-Studio integration."""
from typing import Dict, Any, Optional
import httpx


class SignXStudioConnector:
    """
    Connector for bidirectional integration with SignX-Studio.
    
    This allows SignX-Intel to:
    - Receive project data from SignX-Studio
    - Send cost predictions back to SignX-Studio
    - Sync cost history for training
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize connector.
        
        Args:
            base_url: SignX-Studio API base URL
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            headers={"X-API-Key": api_key} if api_key else {}
        )
    
    async def fetch_project(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch project data from SignX-Studio.
        
        Args:
            project_id: Project ID in SignX-Studio
        
        Returns:
            Project data dictionary
        """
        response = await self.client.get(
            f"{self.base_url}/api/projects/{project_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def send_cost_prediction(
        self,
        project_id: str,
        prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send cost prediction back to SignX-Studio.
        
        Args:
            project_id: Project ID
            prediction: Prediction result
        
        Returns:
            Response from SignX-Studio
        """
        response = await self.client.post(
            f"{self.base_url}/api/projects/{project_id}/cost-prediction",
            json=prediction
        )
        response.raise_for_status()
        return response.json()
    
    async def sync_cost_history(
        self,
        since: Optional[str] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        Sync completed project costs from SignX-Studio.
        
        Args:
            since: ISO timestamp to sync from
            limit: Max records to fetch
        
        Returns:
            List of cost records
        """
        params = {"limit": limit}
        if since:
            params["since"] = since
        
        response = await self.client.get(
            f"{self.base_url}/api/cost-history",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


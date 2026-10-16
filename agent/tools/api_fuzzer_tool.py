"""This is the API fuzzing tool."""

from __future__ import annotations

from typing import Any
import httpx
from pydantic import BaseModel, Field

from .base import tool
from .http_tool import _get_client

# The parameters the LLM gives for this tool
class APIFuzzerParams(BaseModel):
  endpoint: str = Field(..., description="API endpoint to fuzz")
  method: str = Field(default="GET", description="HTTP method")

@tool(
  name="api_fuzzer",
  description="This fuzzes API endpoints with different inputs to find unexpected behavior.",
  params=APIFuzzerParams,
)
def api_fuzzer(
  endpoint: str,
  method: str = "GET",
) -> dict[str, Any]:
  
  client = _get_client()

  # These are the different payloads to test API behavior
  payloads = [
    {},
    {"id": "1"},
    {"id": "-1"},
    {"id": "9999"},
    {"id": "' OR 1=1 --"},
    {"test": "random"},
    {"admin": "true"},
  ]

  results = []
  findings = []

  for payload in payloads:
    try:
      if method.upper() == "GET":
        response = client.get(endpoint, params=payload)
      else:
        response = client.request(
          method.upper(),
          endpoint,
           json=payload,
        )

      body = response.text[:200]

      unusual = response.status_code in [500, 401, 403]

      if unusual:
        findings.append({
          "type": "API Fuzzing Anomaly",
          "endpoint": endpoint,
          "payload": str(payload),
          "severity": "Low",
          "evidence": f"Status {response.status_code}: {body}",
           "remediation": "Validate inputs and handle unexpected parameters safely.",
        })

      results.append({
        "payload": payload,
        "status": response.status_code,
        "unusual": unusual,
        "evidence": body,
      })

    except httpx.RequestError as e:
      results.append({
        "payload": payload,
        "error": str(e),
      })

  return {
    "endpoint": endpoint,
    "results": results,
    "findings": findings,
  }

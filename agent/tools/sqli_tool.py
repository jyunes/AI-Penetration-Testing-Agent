"""This is the SQL Injection testing tool."""

from __future__ import annotations

from typing import Any
import httpx
from pydantic import BaseModel, Field

from .base import tool
from .http_tool import _get_client

# These are the parameters the LLM must provide when using the tool
class SQLiParams(BaseModel):
  path: str = Field(..., description="Endpoint to test (like login)")
  parameter: str = Field(..., description="Parameter to inject to")
  method: str = Field(default="GET", description="HTTP method")

@tool(
  name="sql_injection_tester",
  description="This tests the endpoints for SQL injection using common payloads.",
  params=SQLiParams,
)
def sql_injection_tester(
  path: str,
  parameter: str,
  method: str = "GET",
) -> dict[str, Any]:
  
  client = _get_client()

  # The common SQL injection payloads
  payloads = [
    "' OR 1=1 --",
    "' OR '1'='1",
    "admin'--",
  ]

  results = []
  findings = []

  for payload in payloads:
    try:
      # Sends the request with injected payload
      if method.upper() == "GET":
        response = client.get(path, params={parameter: payload})
      else:
        response = client.request(
          method.upper(),
          path,
          json={parameter: payload},
        )
      
      body = response.text

      # This checks for suspicious SQL-related errors
      suspicious = any(
        keyword in body.lower()
        for keyword in ["sql", "syntax", "database", "error"]
      )

      if suspicious:
        findings.append({
           "type": "Potential SQL Injection",
           "endpoint": path,
           "payload": payload,
           "severity": "Medium",
           "evidence": body[:200],
        })

      results.append({
        "payload": payload,
        "status": response.status_code,
        "suspicious": suspicious,
        "evidence": body[:200],
      })

    except httpx.RequestError as e:
      results.append({
        "payload": payload,
         "error": str(e),
      })

  return {
    "endpoint": path,
    "parameter": parameter,
    "results": results,
    "findings": findings,
  }
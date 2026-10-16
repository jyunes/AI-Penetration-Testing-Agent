"""This is the XSS tool."""

from __future__ import annotations

from typing import Any
import httpx
from pydantic import BaseModel, Field

from .base import tool
from .http_tool import _get_client

# Parameters the LLM must provide when using the tool
class XSSParams(BaseModel):
  path: str = Field(..., description="Endpoint to test")
  parameter: str = Field(..., description="Parameter to inject into")
  method: str = Field(default="GET", description="HTTP method")

@tool(
  name="xss_tester",
  description="This tests endpoints for reflected XSS using common payloads.",
  params=XSSParams,
)

def xss_tester(
  path: str,
  parameter: str,
  method: str = "GET",
) -> dict[str, Any]:
  
  client = _get_client()

  # The common XSS payloads
  payloads = [
    "<script>alert(1)</script>",
    "\"><script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
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

      # If payload appears in response, it may be reflected XSS
      reflected = payload in body

      if reflected:
        findings.append({
          "type": "Potential Reflected XSS",
          "endpoint": path,
          "payload": payload,
          "severity": "Medium",
          "evidence": body[:200],
          "remediation": "Encode output and sanitize user-controlled input.",
        })

      results.append({
        "payload": payload,
        "status": response.status_code,
        "reflected": reflected,
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
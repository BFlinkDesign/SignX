#!/usr/bin/env python3
"""
KeyedIn MCP Server - bridges Claude MCP to the persistent agent
Exposes fast tools: status, login, navigate, extract_table, search_page, export_data
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterable

# Local import
from keyedin_resilient_agent import AgentConfig, KeyedInAgent  # same folder

# MCP SDK
try:
    from mcp.types import InitializationOptions
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import mcp.types as types
except ImportError:
    raise SystemExit("pip install mcp")

SERVER_NAME = "keyedin-connector"
SERVER_VER = "1.0.0"

def table_to_records(table: List[List[str]]) -> List[Dict[str, str]]:
    if not table:
        return []
    headers = [str(h).strip() for h in (table[0] or [])]
    if not headers:
        return []
    records: List[Dict[str, str]] = []
    for row in table[1:]:
        row = list(row or [])
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
        if len(row) > len(headers):
            row = row[: len(headers)]
        rec = {headers[i]: ("" if row[i] is None else str(row[i]).strip()) for i in range(len(headers))}
        records.append(rec)
    return records

class KeyedInMCPServer:
    def __init__(self):
        self.server = Server(SERVER_NAME)
        self.agent: Optional[KeyedInAgent] = None
        self.server.tool(self.keyedin_status)
        self.server.tool(self.keyedin_login)
        self.server.tool(self.keyedin_navigate)
        self.server.tool(self.keyedin_extract_table)
        self.server.tool(self.keyedin_search_page)
        self.server.tool(self.keyedin_export_data)

    async def _get_agent(self) -> KeyedInAgent:
        if self.agent is None:
            cfg = AgentConfig()
            self.agent = KeyedInAgent(cfg)
            await self.agent.start()
            await self.agent.ensure_logged_in()
        return self.agent

    async def keyedin_status(self) -> str:
        agent = await self._get_agent()
        ok = await agent.ensure_logged_in()
        return " Agent ready" if ok else " Agent not authenticated"

    async def keyedin_login(self) -> str:
        agent = await self._get_agent()
        ok = await agent.ensure_logged_in()
        return " Logged in" if ok else " Login failed"

    async def keyedin_navigate(self, module: str) -> str:
        module = (module or "").strip().lower()
        agent = await self._get_agent()
        if module in ("projects", "project", "proj"):
            await agent.goto_projects()
            return " Navigated to projects"
        return f" Unsupported module: {module}"

    async def keyedin_extract_table(self, selector: str = "table") -> List[List[str]]:
        agent = await self._get_agent()
        page = agent.page
        if not page:
            return []
        await page.wait_for_load_state("domcontentloaded")
        rows = await page.eval_on_selector_all(
            selector,
            """els => {
                if (!els.length) return [];
                const table = els[0];
                return Array.from(table.querySelectorAll("tr")).map(tr =>
                  Array.from(tr.querySelectorAll("th,td")).map(td => td.innerText.trim())
                );
            }"""
        )
        return rows or []

    async def keyedin_search_page(self, query: str) -> Dict[str, Any]:
        agent = await self._get_agent()
        page = agent.page
        if not page:
            return {"found": False}
        text = await page.evaluate("() => document.body.innerText")
        q = (query or "").lower()
        t = text.lower()
        idx = t.find(q)
        if idx == -1:
            return {"found": False}
        start = max(0, idx - 120)
        end = min(len(text), idx + 240)
        return {"found": True, "context": text[start:end]}

    async def keyedin_export_data(self, format_type: str = "json", filename: str = "export.json") -> str:
        try:
            data = await self.keyedin_extract_table()
            if not data:
                return " No table data available"
            fp = Path(filename)
            if format_type == "json":
                records = table_to_records(data)
                fp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
            elif format_type == "csv":
                import csv
                with fp.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerows(data)
            else:
                return f" Unsupported format: {format_type}"
            return f" Exported {len(data)} rows to {fp}"
        except Exception as e:
            return f" Export failed: {e}"

async def main():
    m = KeyedInMCPServer()
    @m.server.list_resources()
    async def list_resources() -> List[types.Resource]:
        return []
    @m.server.read_resource()
    async def read_resource(uri: str) -> str:
        return ""
    async with stdio_server(m.server) as (r, w):
        await m.server.run(r, w, InitializationOptions(
            server_name=SERVER_NAME,
            server_version=SERVER_VER,
            capabilities=m.server.get_capabilities(notification_options=None, experimental_capabilities={})
        ))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

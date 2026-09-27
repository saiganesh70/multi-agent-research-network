"""Custom tools equipped to the CrewAI agents.

- TavilySearchTool: live web search for competitor/market data
- PDFReaderTool: reads an existing PDF (e.g. a prior report) for extra context
- CalculatorTool: safe arithmetic evaluation for market-size / growth-rate math
"""

import ast
import operator
import os

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pypdf import PdfReader
from tavily import TavilyClient


# ---------------------------------------------------------------------------
# Tavily web search tool
# ---------------------------------------------------------------------------
class TavilySearchInput(BaseModel):
    query: str = Field(..., description="The search query to run against the web")


class TavilySearchTool(BaseTool):
    name: str = "tavily_web_search"
    description: str = (
        "Searches the live web for up-to-date company, market, and competitor information. "
        "Use this whenever you need current facts, news, pricing, or funding data."
    )
    args_schema: type[BaseModel] = TavilySearchInput

    def _run(self, query: str) -> str:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "ERROR: TAVILY_API_KEY not set. Cannot perform live web search."
        try:
            client = TavilyClient(api_key=api_key)
            results = client.search(query=query, search_depth="advanced", max_results=5)
            formatted = []
            for r in results.get("results", []):
                formatted.append(
                    f"- {r.get('title', 'Untitled')}\n"
                    f"  URL: {r.get('url', 'N/A')}\n"
                    f"  Snippet: {r.get('content', '')[:400]}"
                )
            return "\n\n".join(formatted) if formatted else "No results found."
        except Exception as exc:  # noqa: BLE001
            return f"ERROR during Tavily search: {exc}"


# ---------------------------------------------------------------------------
# PDF reader tool
# ---------------------------------------------------------------------------
class PDFReaderInput(BaseModel):
    file_path: str = Field(..., description="Local path to a PDF file to read")
    max_pages: int = Field(default=20, description="Maximum number of pages to extract")


class PDFReaderTool(BaseTool):
    name: str = "pdf_reader"
    description: str = (
        "Reads text content from a local PDF file, useful for extracting context from an "
        "existing competitor report or company document."
    )
    args_schema: type[BaseModel] = PDFReaderInput

    def _run(self, file_path: str, max_pages: int = 20) -> str:
        if not os.path.exists(file_path):
            return f"ERROR: file not found at {file_path}"
        try:
            reader = PdfReader(file_path)
            pages_text = []
            for i, page in enumerate(reader.pages[:max_pages]):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"--- Page {i + 1} ---\n{text.strip()}")
            content = "\n\n".join(pages_text)
            return content if content else "No extractable text found in PDF."
        except Exception as exc:  # noqa: BLE001
            return f"ERROR reading PDF: {exc}"


# ---------------------------------------------------------------------------
# Calculator tool (safe eval — no builtins, arithmetic only)
# ---------------------------------------------------------------------------
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


class CalculatorInput(BaseModel):
    expression: str = Field(..., description="Arithmetic expression, e.g. '(120 - 100) / 100 * 100'")


class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = (
        "Evaluates a pure arithmetic expression safely. Use for growth-rate, market-share, "
        "or market-size calculations. Only numbers and + - * / % ** are supported."
    )
    args_schema: type[BaseModel] = CalculatorInput

    def _run(self, expression: str) -> str:
        try:
            tree = ast.parse(expression, mode="eval")
            result = _safe_eval(tree.body)
            return str(result)
        except Exception as exc:  # noqa: BLE001
            return f"ERROR evaluating expression '{expression}': {exc}"

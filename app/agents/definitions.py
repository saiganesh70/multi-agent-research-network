"""Defines the 3-agent crew: Researcher, Analyst, Writer."""

import os

from crewai import Agent, LLM

from app.tools.custom_tools import CalculatorTool, PDFReaderTool, TavilySearchTool

tavily_tool = TavilySearchTool()
pdf_tool = PDFReaderTool()
calc_tool = CalculatorTool()


def get_llm() -> LLM:
    return LLM(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.3,
    )


def build_researcher_agent() -> Agent:
    return Agent(
        role="Market Researcher",
        goal=(
            "Gather accurate, current, and well-sourced information about the target company, "
            "its competitors, and its industry using live web search and any supplied documents."
        ),
        backstory=(
            "You are a meticulous OSINT researcher who has spent years tracking startups and "
            "public companies. You never fabricate facts — if you can't find something, you say so. "
            "You always cite where information came from."
        ),
        tools=[tavily_tool, pdf_tool],
        llm=get_llm(),
        allow_delegation=False,
        verbose=True,
        max_retry_limit=2,
    )


def build_analyst_agent() -> Agent:
    return Agent(
        role="Competitive Analyst",
        goal=(
            "Turn raw research into structured competitive insight: strengths, weaknesses, "
            "market positioning, pricing trends, and growth metrics — using the calculator tool "
            "for any numeric comparisons."
        ),
        backstory=(
            "You are a former strategy consultant who specializes in translating messy research "
            "notes into crisp, decision-ready analysis. You double check every number."
        ),
        tools=[calc_tool],
        llm=get_llm(),
        allow_delegation=False,
        verbose=True,
        max_retry_limit=2,
    )


def build_writer_agent() -> Agent:
    return Agent(
        role="Report Writer",
        goal=(
            "Produce a polished, well-structured markdown competitor analysis report suitable "
            "for a business stakeholder to read in under five minutes."
        ),
        backstory=(
            "You are a business writer known for clear, concise, non-fluffy reports. You always "
            "organize content with headers, bullet points, and a short executive summary at the top."
        ),
        tools=[],
        llm=get_llm(),
        allow_delegation=False,
        verbose=True,
        max_retry_limit=2,
    )

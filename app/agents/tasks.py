"""Task definitions wiring the 3 agents into a sequential pipeline."""

from crewai import Agent, Task


def build_research_task(agent: Agent, company_name: str, industry: str | None, focus_areas: list[str] | None, pdf_path: str | None) -> Task:
    focus_str = ", ".join(focus_areas) if focus_areas else "general competitive landscape, pricing, recent news, funding"
    pdf_note = f"\nAlso read and incorporate context from the local PDF at: {pdf_path}" if pdf_path else ""
    return Task(
        description=(
            f"Research the company '{company_name}'"
            + (f" in the '{industry}' industry" if industry else "")
            + f". Focus specifically on: {focus_str}."
            f"{pdf_note}\n"
            "Use the web search tool multiple times with varied queries to build a well-rounded picture. "
            "Record every source URL you use."
        ),
        expected_output=(
            "A structured research brief with sections: Company Overview, Recent News, "
            "Pricing/Positioning, Funding/Financials (if available), and a Sources list with URLs."
        ),
        agent=agent,
    )


def build_analysis_task(agent: Agent, company_name: str) -> Task:
    return Task(
        description=(
            f"Analyze the research brief on '{company_name}'. Identify strengths, weaknesses, "
            "market positioning, and any notable growth or pricing trends. Where the brief contains "
            "numeric data (e.g. revenue, growth %, pricing), use the calculator tool to verify or "
            "derive comparative metrics (e.g. YoY growth, market share deltas)."
        ),
        expected_output=(
            "A structured analysis with sections: Strengths, Weaknesses, Market Positioning, "
            "Key Metrics (with any calculations shown), and Strategic Implications."
        ),
        agent=agent,
    )


def build_writing_task(agent: Agent, company_name: str) -> Task:
    return Task(
        description=(
            f"Write the final competitor analysis report on '{company_name}' based on the research "
            "brief and analysis. Structure it as a clean markdown document with: a 3-4 sentence "
            "Executive Summary at the top, followed by clearly headed sections, bullet points where "
            "appropriate, and a final 'Sources' section listing all URLs used."
        ),
        expected_output=(
            "A complete, polished markdown report ready to hand to a business stakeholder, "
            "generated in a form suitable for direct display or export."
        ),
        agent=agent,
    )

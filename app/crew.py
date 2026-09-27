"""Orchestrates the 3-agent CrewAI pipeline with resilience: retries, fallback
responses, and validation guards so a single agent hiccup doesn't kill the run.
"""

import logging

from crewai import Crew, Process
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.agents.definitions import build_analyst_agent, build_researcher_agent, build_writer_agent
from app.agents.tasks import build_analysis_task, build_research_task, build_writing_task

logger = logging.getLogger("research_crew")

MIN_REPORT_LENGTH = 200  # chars — a report shorter than this is treated as a failed / low-quality run


class CrewValidationError(Exception):
    """Raised when the crew's output fails basic sanity checks."""


def _validate_report(report_text: str) -> None:
    if not report_text or len(report_text.strip()) < MIN_REPORT_LENGTH:
        raise CrewValidationError(
            f"Generated report is too short ({len(report_text.strip()) if report_text else 0} chars) "
            "to be considered valid output."
        )
    if "ERROR" in report_text[:50]:
        raise CrewValidationError("Report output starts with an error marker.")


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type((CrewValidationError, ConnectionError, TimeoutError)),
)
def run_research_pipeline(
    company_name: str,
    industry: str | None = None,
    focus_areas: list[str] | None = None,
    pdf_path: str | None = None,
) -> str:
    """Runs the Researcher -> Analyst -> Writer crew sequentially.

    Retries up to 3 times (exponential backoff) on validation failures or
    transient network errors. If all retries are exhausted, a fallback
    markdown report is returned instead of raising, so the API caller always
    gets a usable response.
    """
    try:
        researcher = build_researcher_agent()
        analyst = build_analyst_agent()
        writer = build_writer_agent()

        research_task = build_research_task(researcher, company_name, industry, focus_areas, pdf_path)
        analysis_task = build_analysis_task(analyst, company_name)
        writing_task = build_writing_task(writer, company_name)

        # Analysis depends on research output; writing depends on analysis output.
        analysis_task.context = [research_task]
        writing_task.context = [research_task, analysis_task]

        crew = Crew(
            agents=[researcher, analyst, writer],
            tasks=[research_task, analysis_task, writing_task],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()
        report_text = str(result)
        _validate_report(report_text)
        return report_text

    except CrewValidationError:
        raise  # let tenacity retry
    except Exception as exc:  # noqa: BLE001
        logger.exception("Crew run failed with an unexpected error: %s", exc)
        raise ConnectionError(str(exc)) from exc


def run_with_fallback(
    company_name: str,
    industry: str | None = None,
    focus_areas: list[str] | None = None,
    pdf_path: str | None = None,
) -> str:
    """Wraps run_research_pipeline; if all retries are exhausted, returns a
    graceful fallback report rather than propagating an exception.
    """
    try:
        return run_research_pipeline(company_name, industry, focus_areas, pdf_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("All retries exhausted for %s: %s", company_name, exc)
        return (
            f"# Competitor Analysis Report: {company_name}\n\n"
            "## ⚠️ Fallback Report\n\n"
            "The automated research pipeline could not complete successfully after multiple "
            f"retries. Last error: `{exc}`\n\n"
            "**Suggested next steps:**\n"
            "- Verify your `OPENAI_API_KEY` and `TAVILY_API_KEY` are valid and have quota\n"
            "- Retry the request\n"
            "- Run the research manually if the issue persists\n"
        )

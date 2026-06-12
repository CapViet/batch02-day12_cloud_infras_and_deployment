"""Multi-agent orchestrator — law / tax / compliance specialists.

Single-process re-implementation of the Day 09 A2A multi-agent system
(customer_agent → law_agent → {tax_agent, compliance_agent}). Instead of
HTTP delegation through a registry, the specialist analyses run as plain
async functions and are dispatched concurrently with ``asyncio.gather`` —
simpler, stateless, and cheaper to deploy as a single container.
"""
from __future__ import annotations

import asyncio
import logging

from app.agents import mock_responses, prompts
from app.agents.llm_client import chat

logger = logging.getLogger(__name__)


async def _run_law_analysis(question: str) -> str:
    result = await chat(prompts.LAW_SYSTEM_PROMPT, question)
    return result or mock_responses.MOCK_LAW_ANALYSIS


async def _run_tax_analysis(question: str) -> str:
    result = await chat(prompts.TAX_SYSTEM_PROMPT, question)
    return result or mock_responses.MOCK_TAX_ANALYSIS


async def _run_compliance_analysis(question: str) -> str:
    result = await chat(prompts.COMPLIANCE_SYSTEM_PROMPT, question)
    return result or mock_responses.MOCK_COMPLIANCE_ANALYSIS


def _needs_tax(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in prompts.TAX_KEYWORDS)


def _needs_compliance(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in prompts.COMPLIANCE_KEYWORDS)


async def _aggregate(question: str, sections: dict[str, str]) -> str:
    formatted = []
    if "law" in sections:
        formatted.append(f"## Legal Analysis\n{sections['law']}")
    if "tax" in sections:
        formatted.append(f"## Tax Analysis\n{sections['tax']}")
    if "compliance" in sections:
        formatted.append(f"## Regulatory Compliance Analysis\n{sections['compliance']}")

    combined = "\n\n---\n\n".join(formatted)
    result = await chat(prompts.AGGREGATE_SYSTEM_PROMPT, combined)
    return result or mock_responses.mock_aggregate(formatted)


async def run_legal_assistant(question: str) -> dict:
    """Analyse a legal question, routing to tax/compliance specialists as needed.

    Returns a dict with ``answer`` (final synthesised text) and
    ``agents_consulted`` (list of specialist agents that contributed).
    """
    tasks: dict[str, asyncio.Task] = {"law": asyncio.create_task(_run_law_analysis(question))}

    if _needs_tax(question):
        tasks["tax"] = asyncio.create_task(_run_tax_analysis(question))
    if _needs_compliance(question):
        tasks["compliance"] = asyncio.create_task(_run_compliance_analysis(question))

    logger.info("Routing decision: agents=%s", list(tasks.keys()))

    results = await asyncio.gather(*tasks.values())
    sections = dict(zip(tasks.keys(), results))

    answer = await _aggregate(question, sections)
    return {"answer": answer, "agents_consulted": list(tasks.keys())}

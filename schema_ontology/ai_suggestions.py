"""AI-powered suggestions for schema violations using OpenAI API.

Uses OpenAI to generate human-readable suggestions for how to
fix violations and improve schemas.
"""

from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI

from .violations import Violation


def get_violation_suggestion(
    violation: Violation,
    entity_yaml: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Get an AI-powered suggestion for fixing a violation.

    Args:
        violation: The violation to get suggestions for.
        entity_yaml: Optional YAML snippet of the entity that violated.
        api_key: Optional API key (uses OPENAI_API_KEY env var if not provided).

    Returns:
        Human-readable suggestion from OpenAI.
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    # Build context about the violation
    context = f"""
Violation Code: {violation.code}
Entity: {violation.entity_ref}
Rule: {violation.rule}
Message: {violation.message}
"""

    if entity_yaml:
        context += f"\nEntity YAML:\n{entity_yaml}\n"

    # Prompt for a suggestion
    prompt = f"""You are a helpful assistant that explains YAML schema violations and suggests fixes.

{context}

Provide a concise, actionable suggestion (2-3 sentences) to fix this violation.
Be specific about what should be changed and why.
Focus on the practical solution, not the technical details."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=150,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.choices[0].message.content


def get_schema_analysis(
    schema_yaml: str,
    api_key: Optional[str] = None,
) -> str:
    """Get AI analysis and recommendations for a schema.

    Args:
        schema_yaml: The ontology schema YAML.
        api_key: Optional API key (uses OPENAI_API_KEY env var if not provided).

    Returns:
        Analysis and recommendations from OpenAI.
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    prompt = f"""Review this YAML schema ontology and provide brief recommendations for improvement.
Focus on: completeness, clarity, and common validation patterns.

Schema:
{schema_yaml}

Provide 3-5 bullet-point recommendations for improving this schema."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=250,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.choices[0].message.content


def explain_violation_for_team(
    violation: Violation,
    context: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Generate an explanation suitable for sharing with team members.

    Args:
        violation: The violation to explain.
        context: Optional additional context (e.g., team standards).
        api_key: Optional API key (uses OPENAI_API_KEY env var if not provided).

    Returns:
        Team-friendly explanation from OpenAI.
    """
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    prompt = f"""Explain this schema violation in clear, non-technical language suitable
for a team that may not be familiar with schema validation.

Violation Code: {violation.code}
Message: {violation.message}
Entity: {violation.entity_ref}
"""

    if context:
        prompt += f"\nTeam Context: {context}\n"

    prompt += """Explain:
1. What went wrong (simple terms)
2. Why it matters (business impact)
3. How to fix it (actionable steps)"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.choices[0].message.content

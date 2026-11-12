#!/usr/bin/env python3
"""
Example: Using AI-powered suggestions to fix violations

This example shows how to use Claude API to generate suggestions for
schema violations.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schema_ontology import Ontology, validate_entity
from schema_ontology.ai_suggestions import (
    get_violation_suggestion,
    get_schema_analysis,
    explain_violation_for_team,
)


def main():
    """Run AI suggestion examples."""

    print("="*70)
    print("SCHEMA ONTOLOGY VALIDATOR - AI SUGGESTIONS DEMO")
    print("="*70)

    # Load ontology
    ontology = Ontology.from_file("examples/ontology.yaml")
    print("\n✓ Ontology loaded")

    # Example 1: Validate an entity with violations
    print("\n" + "-"*70)
    print("1. VALIDATE ENTITY WITH VIOLATIONS")
    print("-"*70)

    invalid_entity = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "payment-api",
            "annotations": {
                "owner": "team",
                "tier": "gold",  # Invalid: should be tier-1, tier-2, or tier-3
            },
            "labels": {"env": "prod"},
        },
        "spec": {"type": "microservice"},
    }

    violations = validate_entity(invalid_entity, ontology)

    print(f"\nFound {len(violations)} violation(s):")
    for v in violations:
        print(f"  • {v.code}: {v.message}")

    # Example 2: Get AI suggestions
    print("\n" + "-"*70)
    print("2. GET AI-POWERED SUGGESTIONS")
    print("-"*70)

    if violations:
        violation = violations[0]
        print(f"\nViolation: {violation.code}")
        print(f"Entity: {violation.entity_ref}")
        print(f"Issue: {violation.message}")

        try:
            print("\n💡 OpenAI's Suggestion:")
            suggestion = get_violation_suggestion(violation)
            for line in suggestion.split("\n"):
                print(f"   {line}")
        except Exception as e:
            print(f"   Could not generate suggestion: {e}")
            print("   (Make sure OPENAI_API_KEY is set)")

    # Example 3: Explain for team
    print("\n" + "-"*70)
    print("3. EXPLAIN VIOLATION FOR TEAM")
    print("-"*70)

    if violations:
        violation = violations[0]
        try:
            print("\n📢 Team Explanation:")
            explanation = explain_violation_for_team(
                violation, context="Our team uses tier-1 for critical services"
            )
            for line in explanation.split("\n"):
                print(f"   {line}")
        except Exception as e:
            print(f"   Could not generate explanation: {e}")
            print("   (Make sure OPENAI_API_KEY is set)")

    # Example 4: Analyze schema
    print("\n" + "-"*70)
    print("4. ANALYZE SCHEMA FOR IMPROVEMENTS")
    print("-"*70)

    try:
        with open("examples/ontology.yaml") as f:
            schema_text = f.read()

        print("\n📊 Claude's Schema Analysis:")
        analysis = get_schema_analysis(schema_text)
        for line in analysis.split("\n"):
            print(f"   {line}")
    except Exception as e:
        print(f"   Could not analyze schema: {e}")
        print("   (Make sure OPENAI_API_KEY is set)")

    print("\n" + "="*70)
    print("Demo complete!")
    print("="*70)


if __name__ == "__main__":
    main()

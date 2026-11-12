"""Violation types and error taxonomy.

Every violation has a code (DFC001, DFC102, etc.) for deterministic routing
and automation. Severity determines whether a violation blocks ingestion
(ERROR) or just warns (WARNING).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    """Violation severity level."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Violation:
    """A single ontology violation.

    Attributes:
        code: Machine-readable violation code (e.g., "DFC101").
        severity: ERROR (blocks) or WARNING (informs).
        rule: Human-readable rule name (e.g., "annotation declared").
        entity_ref: The entity that violated the rule (e.g., "service:default/payment").
        message: Detailed explanation of the violation.
        file: Optional file path where the entity was found.
        extra: Optional extra structured data (e.g., invalid_values=[...]).
    """

    code: str
    severity: Severity
    rule: str
    entity_ref: str
    message: str
    file: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def format(self) -> str:
        """Format violation as a single-line message."""
        severity_str = self.severity.value.upper()
        return f"{self.code} [{severity_str}] {self.entity_ref}: {self.message}"


# Violation code taxonomy. Maps code to human-readable family name.
CODE_FAMILY = {
    # DFC00x: Kind validation
    "DFC001": "Kind not declared in ontology",
    "DFC003": "apiVersion does not match kind declaration",
    # DFC10x: Annotations
    "DFC101": "Unknown annotation key (not declared in ontology)",
    "DFC102": "Annotation not allowed on this kind (wrong scope)",
    "DFC103": "Annotation value not in declared enum",
    "DFC104": "Annotation key is deprecated",
    "DFC105": "Annotation value is deprecated",
    # DFC20x: Labels
    "DFC201": "Unknown label key (not declared in ontology)",
    "DFC202": "Label not allowed on this kind (wrong scope)",
    "DFC203": "Label value must be 'true' (boolean labels, Kubernetes style)",
    "DFC204": "Label key is deprecated",
    "DFC205": "Label references unknown value (e.g., sub-business slug)",
    # DFC30x: Tags
    "DFC301": "Unknown tag (not declared in ontology)",
    "DFC302": "Tag not allowed on this kind (wrong scope)",
    "DFC303": "Too many tags for this kind (exceeds per-kind ceiling)",
    "DFC304": "Tag duplicates a structured fact (e.g., annotated as spec.type)",
    # DFC40x: Spec fields
    "DFC401": "spec.type value not in declared enum",
    # DFC50x: Semantic constraints
    "DFC501": "Business-root Domain name not in declared_businesses",
    "DFC503": "Sub-business Domain has wrong spec.type (must be product-group)",
    "DFC504": "Sub-business Domain missing required spec.subdomainOf",
}


def get_code_family(code: str) -> str:
    """Get the human-readable family name for a violation code."""
    return CODE_FAMILY.get(code, f"Unknown violation code: {code}")

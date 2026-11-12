"""Schema Ontology Validator.

A production-grade Python tool for validating YAML configuration files
against a declarative ontology schema.
"""

from .loader import Ontology
from .validator import validate_entity, validate_entity_file, validate_entities
from .violations import Violation, Severity

__version__ = "1.0.0"

__all__ = [
    "Ontology",
    "validate_entity",
    "validate_entity_file",
    "validate_entities",
    "Violation",
    "Severity",
]

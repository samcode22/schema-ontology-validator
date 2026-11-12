"""Entity-level rule engine.

Each rule function is deterministic and side-effect-free. The same engine
runs at multiple layers (pre-commit, CLI, Python API) without coordination.

All violations are collected (no short-circuit), so a single validation call
reports everything wrong with an entity.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

import yaml

from .loader import Ontology
from .violations import Severity, Violation


def validate_entity(
    entity: dict,
    ontology: Ontology,
    *,
    file: Optional[str] = None,
) -> list[Violation]:
    """Run every entity-level rule and return all collected violations.

    Args:
        entity: A dict from yaml.safe_load (or REST API response).
        ontology: The loaded Ontology.
        file: Optional file path for violation reporting.

    Returns:
        List of Violation objects. Empty list means entity is valid.
    """
    if not isinstance(entity, dict):
        return [
            Violation(
                code="DFC001",
                severity=Severity.ERROR,
                rule="entity must be a YAML mapping",
                entity_ref="?",
                message=f"entity is {type(entity).__name__}, expected dict",
                file=file,
            )
        ]

    out: list[Violation] = []
    out += _check_kind(entity, ontology, file)
    out += _check_annotations(entity, ontology, file)
    out += _check_labels(entity, ontology, file)
    out += _check_tags(entity, ontology, file)
    out += _check_spec(entity, ontology, file)
    return out


def validate_entity_file(
    path: os.PathLike | str,
    ontology: Ontology,
) -> list[Violation]:
    """Load and validate all entities in a YAML file.

    Supports multi-document YAML files (one entity per document).
    Files with no entities are silently ignored.

    Args:
        path: File or directory path.
        ontology: The loaded Ontology.

    Returns:
        List of all violations found.
    """
    p = Path(path)
    file_str = str(p)

    # Check file exists and is readable
    if not p.exists():
        return [
            Violation(
                code="DFC001",
                severity=Severity.ERROR,
                rule="file exists",
                entity_ref="?",
                message=f"file does not exist: {file_str}",
                file=file_str,
            )
        ]

    if not p.is_file():
        return [
            Violation(
                code="DFC001",
                severity=Severity.ERROR,
                rule="path is file",
                entity_ref="?",
                message=f"path is not a file: {file_str}",
                file=file_str,
            )
        ]

    # Read file
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            Violation(
                code="DFC001",
                severity=Severity.ERROR,
                rule="file readable",
                entity_ref="?",
                message=f"could not read file: {exc}",
                file=file_str,
            )
        ]

    if not text or not text.strip():
        return []  # Empty file is valid

    # Parse YAML
    try:
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError as exc:
        return [
            Violation(
                code="DFC001",
                severity=Severity.ERROR,
                rule="YAML parses",
                entity_ref="?",
                message=f"YAML parse error: {exc}",
                file=file_str,
            )
        ]

    if not docs:
        return []  # Empty YAML is valid

    out: list[Violation] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        if "kind" not in doc or "metadata" not in doc:
            continue
        out += validate_entity(doc, ontology, file=file_str)
    return out


def validate_entities(
    entities: Iterable[dict],
    ontology: Ontology,
) -> list[Violation]:
    """Validate multiple already-loaded entities.

    Args:
        entities: Iterable of entity dicts.
        ontology: The loaded Ontology.

    Returns:
        List of all violations found.
    """
    out: list[Violation] = []
    for e in entities:
        out += validate_entity(e, ontology)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Rule implementations
# ─────────────────────────────────────────────────────────────────────────────


def _entity_ref(entity: dict) -> str:
    """Format entity reference as kind:namespace/name."""
    kind = entity.get("kind", "?")
    md = entity.get("metadata") or {}
    ns = md.get("namespace") or "default"
    name = md.get("name", "?")
    return f"{kind.lower()}:{ns}/{name}"


def _annotations(entity: dict) -> dict:
    """Get metadata.annotations dict, handling missing metadata."""
    md = entity.get("metadata") or {}
    return md.get("annotations") or {}


def _labels(entity: dict) -> dict:
    """Get metadata.labels dict, handling missing metadata."""
    md = entity.get("metadata") or {}
    return md.get("labels") or {}


def _tags(entity: dict) -> list[str]:
    """Get metadata.tags list, handling missing metadata."""
    md = entity.get("metadata") or {}
    return md.get("tags") or []


def _check_kind(
    entity: dict,
    ontology: Ontology,
    file: Optional[str],
) -> list[Violation]:
    """Verify kind is declared in ontology and apiVersion matches."""
    kind = entity.get("kind")
    if not kind:
        return [
            Violation(
                code="DFC001",
                severity=Severity.ERROR,
                rule="kind present",
                entity_ref="?",
                message="entity missing 'kind' field",
                file=file,
            )
        ]

    kind_decl = ontology.get_kind(kind)
    if not kind_decl:
        return [
            Violation(
                code="DFC001",
                severity=Severity.ERROR,
                rule="kind declared in ontology",
                entity_ref=_entity_ref(entity),
                message=f"kind '{kind}' not declared in ontology",
                file=file,
            )
        ]

    # Check apiVersion
    api_version = entity.get("apiVersion")
    if api_version and api_version != kind_decl.apiVersion:
        return [
            Violation(
                code="DFC003",
                severity=Severity.ERROR,
                rule="apiVersion matches kind",
                entity_ref=_entity_ref(entity),
                message=(
                    f"apiVersion '{api_version}' does not match "
                    f"kind '{kind}' (expected '{kind_decl.apiVersion}')"
                ),
                file=file,
            )
        ]

    return []


def _check_annotations(
    entity: dict,
    ontology: Ontology,
    file: Optional[str],
) -> list[Violation]:
    """Verify annotations are declared and values are in enum."""
    kind = entity.get("kind")
    if not kind:
        return []

    kind_decl = ontology.get_kind(kind)
    if not kind_decl:
        return []

    anns = _annotations(entity)
    out: list[Violation] = []

    for ann_key, ann_value in anns.items():
        ann_decl = kind_decl.annotations.get(ann_key)

        # Check if annotation is declared
        if not ann_decl:
            out.append(
                Violation(
                    code="DFC101",
                    severity=Severity.ERROR,
                    rule="annotation declared",
                    entity_ref=_entity_ref(entity),
                    message=f"annotation '{ann_key}' not declared in ontology",
                    file=file,
                )
            )
            continue

        # Check if deprecated
        if ann_decl.deprecated:
            out.append(
                Violation(
                    code="DFC104",
                    severity=Severity.WARNING,
                    rule="annotation not deprecated",
                    entity_ref=_entity_ref(entity),
                    message=f"annotation '{ann_key}' is deprecated",
                    file=file,
                )
            )

        # Check if value is in enum
        if ann_decl.enum and ann_value not in ann_decl.enum:
            out.append(
                Violation(
                    code="DFC103",
                    severity=Severity.ERROR,
                    rule="annotation value in enum",
                    entity_ref=_entity_ref(entity),
                    message=(
                        f"annotation '{ann_key}': value '{ann_value}' "
                        f"not in enum {ann_decl.enum}"
                    ),
                    file=file,
                    extra={"invalid_value": ann_value, "valid_values": ann_decl.enum},
                )
            )

    return out


def _check_labels(
    entity: dict,
    ontology: Ontology,
    file: Optional[str],
) -> list[Violation]:
    """Verify labels are declared and values are valid (enum or boolean)."""
    kind = entity.get("kind")
    if not kind:
        return []

    kind_decl = ontology.get_kind(kind)
    if not kind_decl:
        return []

    labels = _labels(entity)
    out: list[Violation] = []

    for label_key, label_value in labels.items():
        label_decl = kind_decl.labels.get(label_key)

        # Check if label is declared
        if not label_decl:
            out.append(
                Violation(
                    code="DFC201",
                    severity=Severity.ERROR,
                    rule="label declared",
                    entity_ref=_entity_ref(entity),
                    message=f"label '{label_key}' not declared in ontology",
                    file=file,
                )
            )
            continue

        # Check if deprecated
        if label_decl.deprecated:
            out.append(
                Violation(
                    code="DFC204",
                    severity=Severity.WARNING,
                    rule="label not deprecated",
                    entity_ref=_entity_ref(entity),
                    message=f"label '{label_key}' is deprecated",
                    file=file,
                )
            )

        # Check if value is in enum (if specified)
        if label_decl.enum and label_value not in label_decl.enum:
            out.append(
                Violation(
                    code="DFC203",
                    severity=Severity.ERROR,
                    rule="label value in enum",
                    entity_ref=_entity_ref(entity),
                    message=(
                        f"label '{label_key}': value '{label_value}' "
                        f"not in {label_decl.enum}"
                    ),
                    file=file,
                )
            )
        # If no enum is defined, labels must be boolean "true" (Kubernetes style)
        elif not label_decl.enum and label_value not in ("true", True):
            out.append(
                Violation(
                    code="DFC203",
                    severity=Severity.ERROR,
                    rule="label value is boolean 'true'",
                    entity_ref=_entity_ref(entity),
                    message=(
                        f"label '{label_key}': value must be 'true', "
                        f"got '{label_value}'"
                    ),
                    file=file,
                )
            )

    return out


def _check_tags(
    entity: dict,
    ontology: Ontology,
    file: Optional[str],
) -> list[Violation]:
    """Verify tags are declared and count is within bounds."""
    kind = entity.get("kind")
    if not kind:
        return []

    kind_decl = ontology.get_kind(kind)
    if not kind_decl:
        return []

    tags = _tags(entity)
    out: list[Violation] = []

    # Check tag count
    if len(tags) > ontology.tag_policy.max_count:
        out.append(
            Violation(
                code="DFC303",
                severity=Severity.WARNING,
                rule="tag count within bounds",
                entity_ref=_entity_ref(entity),
                message=(
                    f"too many tags ({len(tags)}); "
                    f"max is {ontology.tag_policy.max_count}"
                ),
                file=file,
            )
        )

    # Check individual tags
    for tag in tags:
        tag_decl = kind_decl.tags.get(tag)

        # Tags are allowed to be free-form, but warn if declared
        # This is a "soft" check — unknown tags don't error
        if tag_decl and tag_decl.deprecated:
            out.append(
                Violation(
                    code="DFC301",
                    severity=Severity.WARNING,
                    rule="tag not deprecated",
                    entity_ref=_entity_ref(entity),
                    message=f"tag '{tag}' is deprecated",
                    file=file,
                )
            )

    return out


def _check_spec(
    entity: dict,
    ontology: Ontology,
    file: Optional[str],
) -> list[Violation]:
    """Verify spec.type is in declared enum."""
    kind = entity.get("kind")
    if not kind:
        return []

    kind_decl = ontology.get_kind(kind)
    if not kind_decl:
        return []

    if "type" not in kind_decl.spec:
        return []

    spec = entity.get("spec") or {}
    spec_type = spec.get("type")

    if not spec_type:
        return []

    # Get the allowed values
    spec_type_decl = kind_decl.spec.get("type", {})
    if isinstance(spec_type_decl, dict):
        allowed_values = spec_type_decl.get("values", [])
    else:
        allowed_values = []

    if allowed_values and spec_type not in allowed_values:
        return [
            Violation(
                code="DFC401",
                severity=Severity.ERROR,
                rule="spec.type in declared enum",
                entity_ref=_entity_ref(entity),
                message=(
                    f"spec.type: value '{spec_type}' not in "
                    f"enum {allowed_values}"
                ),
                file=file,
                extra={"invalid_value": spec_type, "valid_values": allowed_values},
            )
        ]

    return []

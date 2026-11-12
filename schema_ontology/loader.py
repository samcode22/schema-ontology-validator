"""Ontology YAML loader and type definitions.

The ontology is a single YAML file that declares:
  - kinds (e.g., Service, Job)
  - annotations (metadata.annotations with per-kind scope)
  - labels (metadata.labels with per-kind scope)
  - tags (metadata.tags with per-kind scope and count bounds)
  - spec fields (apiVersion-specific validation)

This module provides type-safe loaders to parse the ontology and make
it available to the validator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass(frozen=True)
class AnnotationDecl:
    """Annotation declaration in ontology."""

    id: str
    scope: list[str]  # Which kinds can have this annotation
    required: bool = False
    enum: Optional[list[str]] = None
    deprecated: bool = False


@dataclass(frozen=True)
class LabelDecl:
    """Label declaration in ontology."""

    id: str
    scope: list[str]  # Which kinds can have this label
    enum: Optional[list[str]] = None  # Valid boolean values, usually ["true"]
    deprecated: bool = False


@dataclass(frozen=True)
class TagDecl:
    """Tag declaration in ontology."""

    id: str
    scope: list[str]  # Which kinds can have this tag
    deprecated: bool = False


@dataclass(frozen=True)
class SpecTypeDecl:
    """spec.type field declaration."""

    kind: str  # "enum", "string", "number", etc.
    values: Optional[list[str]] = None  # If kind=="enum", the valid values
    required: bool = False


@dataclass(frozen=True)
class KindDecl:
    """Kind declaration in ontology."""

    id: str
    apiVersion: str
    annotations: dict[str, AnnotationDecl] = field(default_factory=dict)
    labels: dict[str, LabelDecl] = field(default_factory=dict)
    tags: dict[str, TagDecl] = field(default_factory=dict)
    spec: dict[str, Any] = field(default_factory=dict)  # spec.type, etc.
    required_annotations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TagPolicy:
    """Global tag constraints."""

    max_count: int = 8
    disallowed_duplicates: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Ontology:
    """Loaded ontology. Provides query methods for validation."""

    schema_version: str
    kinds: dict[str, KindDecl] = field(default_factory=dict)
    tag_policy: TagPolicy = field(default_factory=TagPolicy)
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str | Path) -> Ontology:
        """Load ontology from YAML file.

        Raises:
            FileNotFoundError: If ontology file does not exist.
            ValueError: If ontology format is invalid.
            yaml.YAMLError: If YAML parsing fails.
        """
        p = Path(path)

        # Check file exists
        if not p.exists():
            raise FileNotFoundError(f"Ontology file not found: {path}")

        if not p.is_file():
            raise ValueError(f"Ontology path is not a file: {path}")

        # Load YAML
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse ontology YAML: {e}")
        except OSError as e:
            raise FileNotFoundError(f"Cannot read ontology file: {e}")

        if not isinstance(data, dict):
            raise ValueError(f"Ontology must be a YAML mapping; got {type(data)}")

        # Require schema_version
        if "schema_version" not in data:
            raise ValueError("Ontology must have a 'schema_version' field")

        schema_version = data.get("schema_version")
        if not isinstance(schema_version, str):
            raise ValueError(f"schema_version must be a string; got {type(schema_version)}")

        config = data.get("config", {})

        if not isinstance(config, dict):
            raise ValueError(f"config section must be a mapping; got {type(config)}")

        # Parse kinds
        kinds: dict[str, KindDecl] = {}
        kinds_list = data.get("kinds", [])

        if not isinstance(kinds_list, list):
            raise ValueError(f"kinds section must be a list; got {type(kinds_list)}")

        for kind_data in kinds_list:
            if not isinstance(kind_data, dict):
                raise ValueError(f"Each kind must be a YAML mapping; got {type(kind_data)}")

            kind_id = kind_data.get("id")
            if not kind_id:
                raise ValueError("Every kind must have an 'id' field")

            if not isinstance(kind_id, str):
                raise ValueError(f"Kind id must be a string; got {type(kind_id)}")

            # Parse annotations
            annotations: dict[str, AnnotationDecl] = {}
            for ann_data in kind_data.get("annotations", []):
                ann_id = ann_data.get("id")
                if ann_id:
                    annotations[ann_id] = AnnotationDecl(
                        id=ann_id,
                        scope=ann_data.get("scope", []),
                        required=ann_data.get("required", False),
                        enum=ann_data.get("enum"),
                        deprecated=ann_data.get("deprecated", False),
                    )

            # Parse labels
            labels: dict[str, LabelDecl] = {}
            for label_data in kind_data.get("labels", []):
                label_id = label_data.get("id")
                if label_id:
                    labels[label_id] = LabelDecl(
                        id=label_id,
                        scope=label_data.get("scope", []),
                        enum=label_data.get("enum"),
                        deprecated=label_data.get("deprecated", False),
                    )

            # Parse tags
            tags: dict[str, TagDecl] = {}
            for tag_data in kind_data.get("tags", []):
                tag_id = tag_data.get("id")
                if tag_id:
                    tags[tag_id] = TagDecl(
                        id=tag_id,
                        scope=tag_data.get("scope", []),
                        deprecated=tag_data.get("deprecated", False),
                    )

            # Parse spec
            spec = kind_data.get("spec", {})

            kinds[kind_id] = KindDecl(
                id=kind_id,
                apiVersion=kind_data.get("apiVersion", ""),
                annotations=annotations,
                labels=labels,
                tags=tags,
                spec=spec,
                required_annotations=kind_data.get("required_annotations", []),
            )

        # Parse tag policy
        tag_policy_data = data.get("tags", {})
        tag_policy = TagPolicy(
            max_count=tag_policy_data.get("max_count", 8),
            disallowed_duplicates=tag_policy_data.get(
                "disallowed_duplicates", []
            ),
        )

        return cls(
            schema_version=schema_version,
            kinds=kinds,
            tag_policy=tag_policy,
            config=config,
        )

    def get_kind(self, kind: str) -> Optional[KindDecl]:
        """Get a kind declaration by name."""
        return self.kinds.get(kind)

    def has_annotation(self, kind: str, ann_id: str) -> bool:
        """Check if a kind allows an annotation."""
        kind_decl = self.get_kind(kind)
        return kind_decl is not None and ann_id in kind_decl.annotations

    def get_annotation(
        self, kind: str, ann_id: str
    ) -> Optional[AnnotationDecl]:
        """Get an annotation declaration for a kind."""
        kind_decl = self.get_kind(kind)
        if kind_decl:
            return kind_decl.annotations.get(ann_id)
        return None

    def has_label(self, kind: str, label_id: str) -> bool:
        """Check if a kind allows a label."""
        kind_decl = self.get_kind(kind)
        return kind_decl is not None and label_id in kind_decl.labels

    def get_label(self, kind: str, label_id: str) -> Optional[LabelDecl]:
        """Get a label declaration for a kind."""
        kind_decl = self.get_kind(kind)
        if kind_decl:
            return kind_decl.labels.get(label_id)
        return None

    def has_tag(self, kind: str, tag_id: str) -> bool:
        """Check if a kind allows a tag."""
        kind_decl = self.get_kind(kind)
        return kind_decl is not None and tag_id in kind_decl.tags

    def get_tag(self, kind: str, tag_id: str) -> Optional[TagDecl]:
        """Get a tag declaration for a kind."""
        kind_decl = self.get_kind(kind)
        if kind_decl:
            return kind_decl.tags.get(tag_id)
        return None

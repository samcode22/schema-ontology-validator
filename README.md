# Schema Ontology Validator

Validate YAML against a declarative schema. Get AI-powered suggestions to fix violations. Works everywhere — CLI, pre-commit, Python API.

---

## ⚡ Quick Start (2 minutes)

### 1. Install

```bash
pip install -e .
```

### 2. Try it

```bash
# Validate valid example
ontology-validator --ontology examples/ontology.yaml validate examples/ontology.yaml
# Output: ✓ All valid

# See all violation codes
ontology-validator list-rules
```

### 3. Use in your project

```bash
# Create your YAML file (service.yaml)
# Then validate:
ontology-validator --ontology examples/ontology.yaml validate service.yaml
```

---

## 🤖 AI-Powered Suggestions

Get OpenAI-powered recommendations for fixing violations and improving schemas.

### Fix Violations with AI

```bash
export OPENAI_API_KEY=your-key-here
ontology-validator --ontology examples/ontology.yaml suggest catalog/
```

Output:
```
📍 service:default/api - DFC103
   Issue: annotation 'tier': value 'gold' not in enum ['tier-1', 'tier-2', 'tier-3']
   💡 AI Suggestion:
      Use tier-1 for critical services, tier-2 for standard, tier-3 for low-priority.
      Since this is a payment API, tier-1 is recommended. Change 'gold' to 'tier-1'.
```

### Analyze Your Schema

```bash
ontology-validator analyze examples/ontology.yaml
```

Output:
```
AI SCHEMA ANALYSIS & RECOMMENDATIONS

• Consider adding a 'owner_email' annotation for automated notifications
• Add 'pagerduty_id' annotation for critical services
• Your label 'env' should also cover 'staging' environment
• ...
```

---

## Full Usage

### CLI

```bash
ontology-validator --ontology examples/ontology.yaml validate catalog/
ontology-validator list-rules
```

### Python

```python
from schema_ontology import Ontology, validate_entity

ontology = Ontology.from_file("examples/ontology.yaml")
violations = validate_entity(entity_dict, ontology)

for v in violations:
    print(f"{v.code}: {v.message}")
```

### Get AI Suggestions Programmatically

```python
from schema_ontology import Ontology, validate_entity
from schema_ontology.ai_suggestions import get_violation_suggestion

ontology = Ontology.from_file("examples/ontology.yaml")
violations = validate_entity(entity_dict, ontology)

for v in violations:
    print(f"{v.code}: {v.message}")
    suggestion = get_violation_suggestion(v)  # Get OpenAI's recommendation
    print(f"Fix: {suggestion}")
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: ontology
        name: Ontology Validator
        entry: ontology-validator --ontology examples/ontology.yaml validate
        language: system
        files: ^catalog/.*\.ya?ml$
        pass_filenames: true
```

## Schema Format

Define your schema in `ontology.yaml`:

```yaml
schema_version: "1.0"

kinds:
  - id: Service
    apiVersion: v1
    annotations:
      - id: owner
        scope: [Service]
      - id: tier
        enum: [tier-1, tier-2, tier-3]
    labels:
      - id: env
        enum: [dev, prod]
    spec:
      type:
        kind: enum
        values: [microservice, lambda]

tags:
  max_count: 8
```

## Violation Codes

- **DFC001** — Kind not declared
- **DFC003** — apiVersion mismatch
- **DFC101** — Unknown annotation
- **DFC103** — Annotation value not in enum
- **DFC201** — Unknown label
- **DFC203** — Label value invalid
- **DFC401** — spec.type value not in enum

## Example

Validate this entity against `examples/ontology.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  annotations:
    owner: team-a
    tier: tier-1
  labels:
    env: prod
spec:
  type: microservice
```

```bash
ontology-validator --ontology examples/ontology.yaml validate service.yaml
# Output: ✓ All valid
```

## Adding Custom Rules

Edit `schema_ontology/validator.py` and add a `_check_*()` function. Then call it in `validate_entity()`.

Example: Add a rule checking owner is in a known list.

```python
def _check_owner_exists(entity, ontology, file):
    owner = entity.get("metadata", {}).get("annotations", {}).get("owner")
    if owner not in ["team-a", "team-b"]:
        return [Violation(code="DFC999", ...)]
    return []
```

Add to `CODE_FAMILY` in `violations.py`:
```python
CODE_FAMILY = {
    ...
    "DFC999": "Owner not in known teams",
}
```

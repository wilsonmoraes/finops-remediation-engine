---
paths:
  - "app/detectors/**/*.py"
  - "app/modules/**/service.py"
  - "app/modules/**/router.py"
  - "app/repos/**/*.py"
---

# Provider-Neutral Behavior

> Core detectors and the API never branch on a provider-name literal. Provider specifics live
> behind `app/providers/<name>/`; the core keys on the normalized `Resource` shape.

The engine is AWS-first but designed so Azure (and others) drop in without touching the core.
The way that stays true is: the core never asks *which cloud is this?* — it asks *what shape is
this resource, and is it orphaned?*

## The rule

- **Never** write `if resource.provider == "aws"`, `provider_name == "azure"`, or any
  provider-name branch in `app/detectors/**`, `app/modules/**/{service,router}.py`, or
  `app/repos/**`.
- Detection rules key on normalized fields: `resource_type` (`ebs_volume`, `ec2_instance`,
  `elastic_ip`, `load_balancer`, `snapshot`, ...), `state`, `attached`, `last_activity_at`,
  `monthly_cost`. These names are provider-agnostic; the parser maps each provider's native
  vocabulary onto them.
- The decommission command is provider-specific by nature, so it lives in
  `app/providers/<name>/remediation.py` and is selected via the `Provider` registry keyed on
  `resource.provider` — that single lookup is the *only* sanctioned place provider identity is
  read, and it dispatches to an adapter rather than branching on a literal.

## Where provider identity is allowed

Provenance and dispatch, not behavior forks in the core:

- The provider **registry / factory** (`app/providers/__init__.py`) that maps
  `resource.provider -> Provider` adapter. This is dispatch, not a behavior branch.
- Display labels in the dashboard ("AWS", "Azure").
- The `resources.provider` column as a provenance/audit field.

## The seam

Adding Azure later means: write `app/providers/azure/parser.py` (Azure usage CSV → `Resource[]`)
and `app/providers/azure/remediation.py` (`Resource` → `az ...` command), register the adapter,
and add no `if provider == "azure"` anywhere in the core. If a new provider forces a core edit,
the abstraction leaked — fix the `Resource` shape, not the core.

## Out of scope here

- Remediation safety — see `remediation-safety.md`.
- Remediation determinism — see `remediation-determinism.md`.

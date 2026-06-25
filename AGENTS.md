# Repository guide for AI agents and contributors

This file defines the **standard, repeatable process** for extending the
`hashicorp.terraform` Ansible collection — primarily for **adding a new
Terraform Cloud/Enterprise resource** as an Ansible module backed by the
[`pytfe`](https://pypi.org/project/pytfe/) SDK.

Follow it exactly so every resource looks and behaves the same. When in doubt,
**mirror an existing module** rather than inventing a new shape.

---

## 1. Architecture in one minute

Each resource is implemented in two layers plus tests:

| Layer | Path | Responsibility |
|---|---|---|
| **Adapter** (`module_utils`) | `plugins/module_utils/<resource>.py` | Thin, pytfe-backed CRUD helpers (`list_/get_/create_/update_/delete_`). No Ansible logic. |
| **Module** | `plugins/modules/<resource>.py` | Argspec, idempotency, check-mode, `state: present/absent`, docs/examples/return. |
| **Info module** (optional) | `plugins/modules/<resource>_info.py` | Read-only lookups: by ID, by name, or list by organization. |
| **Unit tests** | `tests/unit/plugins/{module_utils,modules}/test_<resource>.py` | Mocked, fast, deterministic. |
| **Integration tests** | `tests/integration/targets/<resource>/` | Live CRUD + idempotency against a real org. |

All HTTP goes through pytfe via the shared `TerraformClient`. **Never** use
`requests`, `urllib`, or `ansible.builtin.uri` in business logic.

---

## 2. Reference implementations to copy

These are the canonical patterns. Read them before writing anything.

- **Simple resource (org-scoped, name-keyed):**
  `plugins/module_utils/ssh_keys.py`, `plugins/modules/ssh_keys.py`,
  `plugins/module_utils/agent_pool.py`, `plugins/modules/agent_pool.py`
- **Info module (by id / by name / list):** `plugins/modules/team_info.py`,
  `plugins/modules/agent_pool_info.py`
- **Richer drift detection:** `plugins/modules/agent_pool.py` (`_has_drift`,
  `_desired_payload`), `plugins/modules/workspace.py`, `plugins/modules/project.py`
- **Integration target:** `tests/integration/targets/ssh_keys/`,
  `tests/integration/targets/agent_pool/`
- **Unit tests:** `tests/unit/plugins/module_utils/test_ssh_keys.py`,
  `tests/unit/plugins/modules/test_agent_pool.py`

---

## 3. Step-by-step: add a new resource `foo`

### 3.1 Inspect the pytfe surface first

```bash
.nopush/venv-latest/bin/python - <<'PY'
from pytfe import TFEClient, TFEConfig
c = TFEClient(config=TFEConfig(token="dummy"))
print([m for m in dir(c.foos) if not m.startswith("_")])     # methods
from pytfe.models import FooCreateOptions, FooUpdateOptions   # option fields
for cls in (FooCreateOptions, FooUpdateOptions):
    print(cls.__name__, list(cls.model_fields))
PY
```

Confirm the resource exists in pytfe **and** in the TFE provider
(`hashicorp/terraform-provider-tfe`, `website/docs/r/`) so naming matches user
expectations.

### 3.2 Adapter — `plugins/module_utils/foo.py`

- Import pytfe models inside a `try/except ImportError` block with stub
  fallbacks (so sanity import checks pass without pytfe installed).
- Import `TerraformClient`, and `format_response`, `safe_api_call` from
  `module_utils/utils`.
- Expose focused helpers; treat `NotFound` as non-fatal in read paths:

```python
def list_foos(adapter, organization): ...        # -> List[Dict]; NotFound -> []
def get_foo(adapter, foo_id): ...                 # -> Dict | None; NotFound -> None
def get_foo_by_name(adapter, organization, name): ...
def create_foo(adapter, organization, data): ...  # FooCreateOptions.model_validate(data)
def update_foo(adapter, foo_id, data): ...        # FooUpdateOptions.model_validate(data)
def delete_foo(adapter, foo_id): ...
```

- Build options with `<Model>Options.model_validate(data)` — never hand-craft
  JSON:API payloads when a model exists.
- Wrap mutating calls in `safe_api_call(op, *args, error_context="...")`.

### 3.3 Module — `plugins/modules/foo.py`

- `DOCUMENTATION` uses `extends_documentation_fragment: hashicorp.terraform.common`
  (gives `tfe_token`, `tfe_address`, TLS/proxy/timeout options + `TFE_TOKEN`
  fallback). Set `version_added` to the upcoming release.
- Resolver `_fetch_foo(adapter, params)` → by `foo_id` else by
  `(organization, name)`.
- `state_present(adapter, params, check_mode)`:
  1. fetch current; if `None` → validate required (`organization`, `name`, …),
     honor `check_mode`, then `create`.
  2. else compute drift on the user-supplied (non-`None`) fields only; `update`
     if drift, else return `{"changed": False, **current}`.
- `state_absent(...)`: delete if present (honor `check_mode`); else
  `{"changed": False, "msg": "Foo is already absent."}`.
- `main()`: `AnsibleTerraformModule(argument_spec=..., required_one_of=...,
  supports_check_mode=True)`, dispatch with `match params["state"]`, wrap in
  `try/except` → `module.fail_json(msg=to_text(e))`.

### 3.4 Info module — `plugins/modules/foo_info.py` (if a read use-case exists)

Mirror `team_info` / `agent_pool_info`: argspec `foo_id`/`organization`/`name`,
`required_one_of=[("foo_id","organization")]`,
`required_by={"name": ("organization",)}`,
`mutually_exclusive=[("foo_id","organization"),("foo_id","name")]`. Return a
single `foo` for id/name lookups and a `foos` list for org listing.

---

## 4. Conventions (non-negotiable)

- **pytfe only** for all resource operations.
- **Idempotency:** identical `state: present` → `changed: false`; repeated
  `absent` → `changed: false`. Compare only fields the user supplied.
- **Sensitive values** that are write-only server-side (e.g. SSH private keys,
  variable values) cannot be diffed — mark the arg `no_log: True`, document that
  re-runs are idempotent on name only, and **do not** assert on the returned
  value in tests (use idempotency to prove the write instead).
- **Return shape:** the collection returns resource fields **flattened** at the
  top level (no JSON:API `attributes` wrapper) — `format_response` does
  `model_dump(mode="json", exclude_none=True)`. Document `RETURN` accordingly.
- **`check_mode`** supported on every mutating module; report `changed: true`
  with a `... check mode` message, perform no API write.
- **Messages:** include `msg` for delete, no-op, and check-mode outcomes.
- **Naming:** module = resource name; info module = `<resource>_info`.

---

## 5. Wiring (easy to forget)

- **`meta/runtime.yml`** — add the module(s) to `action_groups.terraform` so
  `module_defaults` (group auth) applies.
- **Changelog** — add `changelogs/fragments/<resource>_module.yml` with a
  `minor_changes` entry. (New modules also auto-appear under "New Modules" in
  the generated changelog.)
- **Integration target** — `tests/integration/targets/<resource>/meta/main.yml`
  must `dependencies: [prepare_tfc]` (provides `tfc_token` + `organization`).

---

## 6. Testing requirements

**Unit (`pytest`, mocked):**
- adapter: list / get / get-by-name / create / update / delete, plus
  `NotFound` → empty/None paths.
- module: `_fetch_*`, drift helpers, `state_present` (create / create-check-mode
  / missing-required-raises / idempotent / update / update-check-mode),
  `state_absent` (delete / no-op / check-mode).
- info module: by-id (+ not-found fails), by-name (+ not-found fails), list.

**Integration (`tests/integration/targets/<resource>/tasks/main.yml`):**
- `module_defaults` with `tfe_token: "{{ tfc_token }}"`, unique names via
  `uuidgen`, create + assert, idempotent re-create + assert, info lookups,
  update + idempotent update, check-mode delete, delete + assert, delete-again
  no-op, and an `always:` best-effort cleanup block.

---

## 7. Validation commands

Run from the repo root. `<COLL>` = a collection path containing
`ansible_collections/hashicorp/terraform` (symlink the repo into one for local
runs).

```bash
# style
black --check plugins tests && isort --check plugins tests && flake8 plugins tests

# unit (collection must be importable as ansible_collections.hashicorp.terraform)
ANSIBLE_COLLECTIONS_PATH=<COLL> pytest tests/unit/plugins/.../test_<resource>.py -q

# module docs schema + examples + return + cross-refs
ANSIBLE_COLLECTIONS_PATH=<COLL> antsibull-docs lint-collection-docs \
  --plugin-docs --check-extra-docs-refs --validate-collection-refs self .

# sanity (validate-modules etc.) — CI runs the full matrix
ansible-test sanity --docker -v plugins/modules/<resource>.py

# changelog fragment lint
antsibull-changelog lint
```

A live smoke test against a real org (token via `TFE_TOKEN`, never written to
files) is strongly recommended before opening a PR:
create → idempotent re-run → update → info → delete → delete-again, with cleanup.

---

## 8. Quality gates (must pass before PR)

- [ ] All resource operations go through the pytfe SDK (no raw HTTP).
- [ ] Idempotency implemented and covered by unit **and** integration tests.
- [ ] `check_mode` supported and tested.
- [ ] `DOCUMENTATION` / `EXAMPLES` / `RETURN` complete and accurate (return
      shape matches actual flattened output).
- [ ] Added to `meta/runtime.yml` `action_groups`.
- [ ] Changelog fragment added.
- [ ] `black` / `isort` / `flake8` / `antsibull-docs lint` / unit tests green.
- [ ] If replacing raw `ansible.builtin.uri` usage in integration tests, all
      occurrences are migrated to the new module.

---

## 9. Deliverable summary to provide

When done, report: (1) files added/updated, (2) idempotency strategy, (3) pytfe
models/methods used, (4) unit + integration coverage summary, (5) any
live-verification output.

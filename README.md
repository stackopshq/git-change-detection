# git-change-detection

Detect which Ansible playbooks need to run based on git changes and metadata files.

## Usage

```bash
git-change-detection <START_SHA> <END_SHA> \
  --metadata ansible/inventory/prod/.metadata.yml \
  --metadata ansible/playbooks/.metadata.yml \
  --json
```

## Metadata format

Create `.metadata.yml` files that map file glob patterns to playbook names:

```yaml
playbooks/setup-networking.yml:
  stage: 1
  depends_on: []
  paths:
    - "ansible/roles/networking/**"
    - "ansible/inventory/*/group_vars/networking.yml"

playbooks/setup-monitoring.yml:
  stage: 2
  depends_on:
    - "playbooks/setup-networking.yml"
  paths:
    - "ansible/roles/monitoring/**"
```

## Output (JSON)

```json
{
  "playbooks/setup-networking.yml": {
    "triggered": true,
    "stage": 1,
    "depends_on": []
  },
  "playbooks/setup-monitoring.yml": {
    "triggered": true,
    "stage": 2,
    "depends_on": ["playbooks/setup-networking.yml"]
  }
}
```

- **`triggered`**: `true` if any changed file matches the patterns, or if a dependency was triggered
- **`stage`**: execution order (sorted by the CI)
- **`depends_on`**: list of playbook names this depends on (triggers cascade)

## Install

```bash
pip install git-change-detection
```

## Development

```bash
uv sync
uv run git-change-detection --help
```

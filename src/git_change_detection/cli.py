"""CLI entry point for git-change-detection."""

from __future__ import annotations

import json
import sys

import click
import yaml

from git_change_detection.detector import detect_changes


@click.command()
@click.argument("start")
@click.argument("end")
@click.option(
    "--metadata",
    "-m",
    multiple=True,
    required=True,
    help="Path to a .metadata.yml file (can be specified multiple times)",
)
@click.option("--json-output", "--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--repo-dir", default=".", help="Path to the git repository")
def main(
    start: str,
    end: str,
    metadata: tuple[str, ...],
    output_json: bool,
    repo_dir: str,
) -> None:
    """Detect which playbooks are triggered by git changes between START and END refs.

    Reads .metadata.yml files that map file glob patterns to playbook names,
    then checks the git diff to determine which playbooks should run.
    """
    try:
        result = detect_changes(
            start=start,
            end=end,
            metadata_files=list(metadata),
            repo_dir=repo_dir,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if output_json:
        # Strip matched_files for clean CI output
        clean = {
            name: {
                "triggered": info["triggered"],
                "stage": info["stage"],
                "depends_on": info["depends_on"],
            }
            for name, info in result.items()
        }
        click.echo(json.dumps(clean, indent=2))
    else:
        triggered = [n for n, i in result.items() if i["triggered"]]
        skipped = [n for n, i in result.items() if not i["triggered"]]

        if triggered:
            click.echo("Triggered playbooks:")
            for name in sorted(triggered):
                info = result[name]
                click.echo(f"  ▶ {name} (stage {info['stage']})")
                for f in info["matched_files"]:
                    click.echo(f"    └─ {f}")
        else:
            click.echo("No playbooks triggered.")

        if skipped:
            click.echo(f"\nSkipped: {', '.join(sorted(skipped))}")


if __name__ == "__main__":
    main()

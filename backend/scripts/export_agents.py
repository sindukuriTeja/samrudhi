"""Export the SAMRUDHI Digital Workforce to third-party agent tool formats.

Borrows the pattern from the agency-agents corpus (msitarzewski/agency-agents,
MIT): one canonical agent definition is rendered into each target tool's native
format, with a machine-readable manifest as the source of truth.

Canonical source  : backend/app/agents/registry.py (194 agents, 11 departments)
Renderers (format):
  * claude-code  -> .md agent files          (identity; frontmatter name/description)
  * gemini-cli   -> .md agent files          (frontmatter name/description/tools)
  * codex        -> .toml custom agents      (name + developer_instructions)
  * cursor       -> .mdc rule files          (description + alwaysApply + body)

Usage:
    python scripts/export_agents.py                 # all tools -> exports/
    python scripts/export_agents.py --tool claude-code
    python scripts/export_agents.py --enriched-only # only the 44 enriched agents
    python scripts/export_agents.py --out /tmp/x

The manifest (exports/manifest.json) is the source of truth: it lists every
agent, its slug, department and the files produced, so a consumer (app, CI,
installer) can branch on it without re-parsing the renderers.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.registry import AGENTS, to_dict  # noqa: E402

# --------------------------------------------------------------------------- #
# Slug + frontmatter helpers
# --------------------------------------------------------------------------- #

def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def agent_slug(agent) -> str:
    """Rename-proof slug: name + canonical ID, so two same-named agents
    (e.g. Lekha in CRT vs LekhaPatra in FIN) never collide."""
    return f"{slugify(agent.name)}-{agent.id.lower()}"


def _description(agent) -> str:
    """One-line description for tool frontmatter (role + dept + top KPI)."""
    kpi = f" KPIs: {', '.join(agent.kpis[:2])}." if agent.kpis else ""
    return (f"{agent.role} in {agent.department} (SAMRUDHI Digital Workforce, "
            f"{agent.dept_code}).{kpi}")


def _body(agent) -> str:
    """The full composed system prompt (mission, duties, outputs, controls,
    specialist craft and governance guardrails) as the agent body."""
    return agent.system_prompt.strip()


# --------------------------------------------------------------------------- #
# Renderers — one per supported `format`
# --------------------------------------------------------------------------- #

def render_claude_code(agent) -> str:
    """Claude Code / GitHub Copilot native agent (.md, identity format)."""
    return (
        "---\n"
        f"name: {agent.name}\n"
        f"description: {_description(agent)}\n"
        "---\n\n"
        f"# {agent.name} — {agent.role}\n\n"
        f"_SAMRUDHI Digital Workforce · {agent.department} · "
        f"{agent.id} · reports to {agent.reports_to} · "
        f"autonomy: {agent.autonomy}_\n\n"
        + _body(agent) + "\n"
    )


def render_gemini_cli(agent) -> str:
    """Gemini CLI agent (.md) — adds an explicit tools hint."""
    return (
        "---\n"
        f"name: {agent.name}\n"
        f"description: {_description(agent)}\n"
        "tools: Read, Write, Edit\n"
        "---\n\n"
        f"# {agent.name} — {agent.role}\n\n"
        f"_SAMRUDHI Digital Workforce · {agent.department} · {agent.id}_\n\n"
        + _body(agent) + "\n"
    )


def _toml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_codex(agent) -> str:
    """Codex custom agent (.toml)."""
    return (
        f'name = "{_toml_escape(agent.name)}"\n'
        f'description = "{_toml_escape(_description(agent))}"\n\n'
        "# SAMRUDHI Digital Workforce — "
        f"{agent.id} · {agent.dept_code} · {agent.role}\n"
        "developer_instructions = '''\n"
        + _body(agent).replace("'''", "'''''") + "\n'''\n"
    )


def render_cursor(agent) -> str:
    """Cursor rule (.mdc) — project-scoped, always applied when the agent's
    domain is in play."""
    return (
        "---\n"
        f"description: {_description(agent)}\n"
        "alwaysApply: false\n"
        "---\n\n"
        f"# {agent.name} — {agent.role} (SAMRUDHI {agent.dept_code})\n\n"
        + _body(agent) + "\n"
    )


# format name -> (renderer, file extension, subdir under exports/<tool>/)
FORMATS = {
    "claude-code": (render_claude_code, "md", "agents"),
    "gemini-cli": (render_gemini_cli, "md", "agents"),
    "codex": (render_codex, "toml", "agents"),
    "cursor": (render_cursor, "mdc", "rules"),
}


# --------------------------------------------------------------------------- #
# Export driver
# --------------------------------------------------------------------------- #

def export(out_dir: Path, tools: list[str], enriched_only: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "_note": (
            "Source of truth for the SAMRUDHI Digital Workforce export. "
            "Generated by backend/scripts/export_agents.py from "
            "backend/app/agents/registry.py. One entry per agent; `files` "
            "lists the rendered path per tool (relative to exports/). "
            "`enriched` marks agents carrying agency-agents specialist craft."
        ),
        "agents": [],
    }

    for agent in AGENTS:
        if enriched_only and not agent.enriched:
            continue
        slug = agent_slug(agent)
        files = {}
        for tool in tools:
            renderer, ext, subdir = FORMATS[tool]
            dest = out_dir / tool / subdir / f"{slug}.{ext}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(renderer(agent), encoding="utf-8")
            files[tool] = f"{tool}/{subdir}/{slug}.{ext}"
        entry = to_dict(agent)
        entry["slug"] = slug
        entry["files"] = files
        manifest["agents"].append(entry)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "exports"),
                    help="output directory (default: <repo>/exports)")
    ap.add_argument("--tool", action="append", choices=sorted(FORMATS),
                    help="tool to export (repeatable; default: all)")
    ap.add_argument("--enriched-only", action="store_true",
                    help="only export the agents carrying specialist craft")
    args = ap.parse_args()

    tools = args.tool or sorted(FORMATS)
    out_dir = Path(args.out)
    manifest = export(out_dir, tools, args.enriched_only)
    n = len(manifest["agents"])
    print(f"exported {n} agents x {len(tools)} tools -> {out_dir}")
    print(f"manifest: {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
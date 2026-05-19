"""Stub reporter for Phase 3. Phase 7 replaces this with a real Claude call."""


def draft(brief: str, notes: list[str], sources: list[dict], summary: str) -> str:
    lines = [f"# Research: {brief}", ""]
    if summary:
        lines += ["## Summary", summary, ""]
    if notes:
        lines += ["## Notes"]
        lines += [f"- {n}" for n in notes]
        lines.append("")
    lines.append("## Sources")
    if sources:
        for i, s in enumerate(sources, start=1):
            lines.append(f"{i}. [{s['title']}]({s['url']}) — {s['claim']}")
    else:
        lines.append("_No sources cited._")
    return "\n".join(lines) + "\n"

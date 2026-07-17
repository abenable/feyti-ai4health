"""Author CTD section documents from extracted text + classification."""

from __future__ import annotations

import re

from app.services import llm
from app.services.ctd_map import CTD_MAP


def _find_parent_context(section_path: str) -> str:
    """Return a one-line description of where this section lives in the CTD tree."""
    parts = section_path.split(".")
    ancestors = []
    for i in range(1, len(parts)):
        ancestor = ".".join(parts[:i])
        if ancestor in CTD_MAP and ancestor != section_path:
            ancestors.append(f"{ancestor}: {CTD_MAP[ancestor]}")
    if ancestors:
        return "Section hierarchy:\n" + "\n".join(f"- {a}" for a in ancestors)
    return ""


def _build_prompt(
    extracted_text: str,
    classification: dict,
    prior_markdown: str | None = None,
    feedback: str | None = None,
) -> str:
    section_path = classification.get("section_path", "")
    title = classification.get("title") or CTD_MAP.get(section_path, "CTD Section")
    summary = classification.get("summary", "")
    key_points = classification.get("key_points", []) or []
    module = classification.get("module", "")

    hierarchy = _find_parent_context(section_path)

    lines = [
        "You are a regulatory medical writer preparing a CTD (Common Technical Document) section for a drug registration dossier.",
        f"Write the complete Markdown body for section {section_path}: {title}",
        f"Module: {module}",
        "",
        hierarchy,
        "",
        "Requirements:",
        f"- The document must open with a single H1: '# {title}'",
        f"- Use section path {section_path} in the H1 or first paragraph so reviewers can confirm the target.",
        "- Structure the content using appropriate Markdown headings, paragraphs, and bullet lists.",
        "- Do not invent efficacy, safety, or quality data that is not supported by the source text below.",
        "- Use regulatory, formal language suitable for a CTD submission.",
        "- Do not include any '[placeholder]' text; write real content or omit the placeholder entirely.",
    ]

    if summary:
        lines.extend(["", f"Document summary (for context): {summary}"])
    if key_points:
        lines.extend(["", "Key source points:"] + [f"- {kp}" for kp in key_points])

    lines.extend([
        "",
        "SOURCE TEXT (extracted from uploaded document):",
        "---",
        extracted_text,
        "---",
    ])

    if prior_markdown:
        lines.extend([
            "",
            "PRIOR DRAFT (revise this, do not simply repeat it):",
            "---",
            prior_markdown,
            "---",
        ])

    if feedback:
        lines.extend([
            "",
            f"REVIEWER FEEDBACK (address this in your revised draft): {feedback}",
        ])

    lines.extend([
        "",
        "Return ONLY the Markdown document. No extra commentary before or after.",
    ])

    return "\n".join(lines)


def _strip_placeholders(text: str) -> str:
    """Remove any literal placeholder markup the model may have emitted,
    without destroying Markdown paragraph structure (blank lines matter)."""
    cleaned = re.sub(r"\[placeholder\]", "", text, flags=re.IGNORECASE)
    # Collapse runs of 3+ newlines (which placeholder removal can create) down
    # to a single blank line; keep the single blank lines that separate blocks.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


async def generate_document(
    extracted_text: str,
    classification: dict,
    prior_markdown: str | None = None,
    feedback: str | None = None,
) -> str:
    """Generate (or regenerate) a CTD section Markdown document."""
    prompt = _build_prompt(extracted_text, classification, prior_markdown, feedback)
    # A full CTD section can be long; lift the provider's default cap so the
    # document isn't truncated mid-section. 8192 is DeepSeek's max.
    raw = await llm.generate_text(prompt, max_tokens=8192)
    return _strip_placeholders(raw)


if __name__ == "__main__":  # ponytail self-check
    import asyncio

    async def _self_check() -> None:
        text = (
            "This document describes the stability program for the drug product. "
            "Three batches were stored at 25C/60% RH and 40C/75% RH for 24 months. "
            "All results remained within specification."
        )
        classification = {
            "section_path": "3.2.P.8.3",
            "title": "Stability Data",
            "module": "Module 3 — Quality",
            "summary": "Stability data summary.",
            "key_points": ["24-month data", "ICH conditions"],
        }
        # Avoid network in self-check by patching llm.generate_text.
        import app.services.llm as llm_module

        async def fake_generate_text(prompt: str, max_tokens: int | None = None) -> str:
            return (
                f"# {classification['title']}\n\n"
                "## 3.2.P.8.3 Stability Data\n\n"
                "This section presents stability data. [placeholder]\n\n"
                "- Batch data under ICH conditions\n"
            )

        llm_module.generate_text = fake_generate_text
        result = await generate_document(text, classification)
        assert result, "generate_document returned empty markdown"
        first_h1 = result.splitlines()[0].strip()
        assert first_h1 == f"# {classification['title']}", first_h1
        assert "[placeholder]" not in result.lower()
        # #2 guard: paragraph-separating blank lines must survive stripping.
        assert "\n\n" in result, "blank lines (paragraph structure) were destroyed"
        print("OK — generate_document produces titled, placeholder-free, structured Markdown")

    asyncio.run(_self_check())

"""Author CTD section documents from extracted text + classification."""

from __future__ import annotations

import re

from app.services import llm
from app.services.ctd_map import CTD_MAP
from app.services.dossier_service import context_block


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


# Marker the model must use for required data that the source does not contain.
# Rendered prominently in the review UI; a human fills these before approval.
GAP_MARKER = "⚠️ TO BE PROVIDED"


def _build_prompt(
    extracted_text: str,
    classification: dict,
    prior_markdown: str | None = None,
    feedback: str | None = None,
    augment: bool = False,
) -> str:
    section_path = classification.get("section_path", "")
    title = classification.get("title") or CTD_MAP.get(section_path, "CTD Section")
    summary = classification.get("summary", "")
    key_points = classification.get("key_points", []) or []
    module = classification.get("module", "")

    hierarchy = _find_parent_context(section_path)
    product = context_block(
        "PRODUCT CONTEXT (this dossier is being prepared for the following product; "
        "keep the document consistent with these facts):"
    )

    lines = [
        "You are a regulatory medical writer preparing a CTD (Common Technical Document) section for a drug registration dossier.",
        f"Write the complete Markdown body for section {section_path}: {title}",
        f"Module: {module}",
        "",
        *([product, ""] if product else []),
        *([hierarchy, ""] if hierarchy else []),
        "Requirements:",
        f"- The document must open with a single H1: '# {title}'",
        f"- Use section path {section_path} in the H1 or first paragraph so reviewers can confirm the target.",
        "- Structure the content using appropriate Markdown headings, paragraphs, and bullet lists.",
        "- Do not invent efficacy, safety, or quality data that is not supported by the source text below.",
        "- Use regulatory, formal language suitable for a CTD submission.",
        "- Do not include any '[placeholder]' text; write real content or omit the placeholder entirely.",
    ]

    if augment:
        # Structural completion ONLY: fill the shape, never the facts. The
        # factual guardrail above still applies — instead of inventing missing
        # data, the model must emit an explicit, human-fillable gap marker.
        lines.extend([
            "",
            "AUGMENT MODE — the source is incomplete. Expand it into a COMPLETE, "
            "submission-shaped section:",
            "- Add every subsection and heading this CTD section is expected to "
            "contain per ICH M4, even if the source omits them.",
            "- Add standard regulatory framing, definitions, and boilerplate that "
            "are true for any product of this kind.",
            "- Reorganize and properly restate the data the source DOES provide.",
            "- CRITICAL: for any REQUIRED factual data the source does NOT contain "
            "(numbers, results, specifications, study outcomes, dates, batch data), "
            f"do NOT invent it. Insert a blockquote line exactly: '> {GAP_MARKER}: "
            "<precise description of the missing data>'.",
            "- Never present a gap marker's content as if it were real data.",
        ])

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
    augment: bool = False,
) -> str:
    """Generate (or regenerate) a CTD section Markdown document.

    augment=True expands sparse source into a complete, submission-shaped
    section, marking required-but-missing FACTS with a '> ⚠️ TO BE PROVIDED: …'
    gap line instead of inventing them.
    """
    prompt = _build_prompt(extracted_text, classification, prior_markdown, feedback, augment)
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

        # Augment mode: prompt must carry the no-invention guardrail + gap marker,
        # and the gap marker must survive stripping (it isn't a '[placeholder]').
        aug_prompt = _build_prompt(text, classification, augment=True)
        assert "AUGMENT MODE" in aug_prompt and GAP_MARKER in aug_prompt
        assert "do NOT invent" in aug_prompt
        gap_line = f"> {GAP_MARKER}: 24-month assay results"
        assert gap_line in _strip_placeholders(f"# X\n\n{gap_line}\n"), "gap marker was stripped"
        print("OK — generate_document + safe augment mode (gap markers preserved)")

    asyncio.run(_self_check())

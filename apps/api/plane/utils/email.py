# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import html
import re

# Django imports
from django.utils.html import strip_tags

# Matches an entire <style>...</style> or <script>...</script> block,
# including its contents, case-insensitively and across newlines.
_STYLE_OR_SCRIPT_BLOCK_RE = re.compile(
    r"<(style|script)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)

# Three or more consecutive newlines (i.e. two or more blank lines in a
# row) collapse down to a single blank line.
_MULTIPLE_BLANK_LINES_RE = re.compile(r"\n{3,}")


def generate_plain_text_from_html(html_content: str) -> str:
    """Build a plain-text alternative from a rendered HTML email body.

    Email clients that cannot (or choose not to) render HTML fall back to
    the plain-text part of a multipart message. This turns the HTML output
    of `render_to_string(...)` for one of our `emails/` templates into
    readable prose: markup is removed, `<style>`/`<script>` blocks are
    dropped entirely (their contents are not meant to be read), and the
    large vertical gaps left behind by table/div-heavy templates are
    collapsed so the result reads as paragraphs rather than a sparse
    column of mostly blank lines.

    Any input - including empty strings, plain text with no markup, or
    malformed HTML - returns a sensible string rather than raising.
    """
    if not html_content:
        return ""

    # Drop <style> and <script> blocks (tag + contents). Left in place,
    # stripping tags alone would leave their CSS/JS bodies behind as
    # visible, meaningless text.
    text = _STYLE_OR_SCRIPT_BLOCK_RE.sub("", html_content)

    # Remove all remaining HTML tags.
    text = strip_tags(text)

    # Decode entities (&amp;, &eacute;, ...) left behind by strip_tags.
    text = html.unescape(text)

    # A non-breaking space reads as an ordinary space in plain text.
    text = text.replace(" ", " ")

    # Pretty-printed templates leave a whitespace-only or empty line for
    # every tag that used to hold layout structure (tables, divs, ...).
    # Trim each line, then collapse consecutive blank lines into at most
    # one, so removed markup doesn't read as a sparse column of gaps.
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = _MULTIPLE_BLANK_LINES_RE.sub("\n\n", text)

    # Trim outer whitespace, then add a single blank line of padding on
    # each side, matching how these messages are composed.
    text = text.strip("\n \t")
    if not text:
        return ""

    return f"\n{text}\n"

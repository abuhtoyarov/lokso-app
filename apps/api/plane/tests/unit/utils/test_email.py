# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from pathlib import Path

import pytest
from django.template.loader import render_to_string

from plane.utils.email import generate_plain_text_from_html

TEMPLATES_DIR = (
    Path(__file__).resolve().parents[4] / "templates" / "emails"
)


@pytest.mark.unit
class TestGeneratePlainTextFromHtml:
    """Test the generate_plain_text_from_html function"""

    # -- Basic tag stripping -------------------------------------------------

    def test_strips_simple_tags(self):
        html = "<p>Hello <strong>world</strong></p>"
        result = generate_plain_text_from_html(html)
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "Hello" in result
        assert "world" in result

    def test_strips_nested_table_markup(self):
        html = (
            "<table><tr><td><h1>Title</h1></td></tr>"
            "<tr><td><p>Body text</p></td></tr></table>"
        )
        result = generate_plain_text_from_html(html)
        assert "<" not in result
        assert ">" not in result
        assert "Title" in result
        assert "Body text" in result

    def test_decodes_html_entities(self):
        html = "<p>Tom &amp; Jerry &mdash; caf&eacute;</p>"
        result = generate_plain_text_from_html(html)
        assert "&amp;" not in result
        assert "Tom & Jerry" in result
        assert "café" in result

    def test_converts_non_breaking_space_to_regular_space(self):
        html = "<p>Hello&nbsp;world</p>"
        result = generate_plain_text_from_html(html)
        assert " " not in result
        assert "Hello world" in result

    # -- CSS / script removal -------------------------------------------------

    def test_strips_style_block_contents(self):
        html = (
            "<html><head><style>"
            "body, table, td, p { margin: 0; padding: 0; }"
            ".email-container { width: 100% !important; }"
            "</style></head><body><p>Real content</p></body></html>"
        )
        result = generate_plain_text_from_html(html)
        assert "{" not in result
        assert "}" not in result
        assert "margin" not in result
        assert "font-family" not in result
        assert ".email-container" not in result
        assert "Real content" in result

    def test_strips_style_block_with_media_query(self):
        html = (
            "<style>"
            "@media only screen and (max-width: 600px) {"
            ".email-content { padding: 24px 20px !important; } }"
            "</style><p>Kept text</p>"
        )
        result = generate_plain_text_from_html(html)
        assert "@media" not in result
        assert "px" not in result
        assert "Kept text" in result

    def test_strips_multiple_style_blocks(self):
        html = (
            "<style>a { color: red; }</style>"
            "<p>Middle</p>"
            "<style>b { color: blue; }</style>"
        )
        result = generate_plain_text_from_html(html)
        assert "color" not in result
        assert "Middle" in result

    def test_strips_script_block_contents(self):
        html = (
            "<script>var x = 1; document.write('should not appear');</script>"
            "<p>Visible</p>"
        )
        result = generate_plain_text_from_html(html)
        assert "document.write" not in result
        assert "should not appear" not in result
        assert "Visible" in result

    def test_strips_inline_style_attribute_values(self):
        # Attribute values are removed along with the tag itself, not just
        # <style> block contents.
        html = '<p style="font-family: Arial, sans-serif; color: red;">Text</p>'
        result = generate_plain_text_from_html(html)
        assert "font-family" not in result
        assert "Text" in result

    # -- Blank-line collapsing -------------------------------------------------

    def test_collapses_runs_of_blank_lines(self):
        html = "<p>First</p>\n\n\n\n\n<p>Second</p>"
        result = generate_plain_text_from_html(html)
        assert "\n\n\n" not in result
        assert "First" in result
        assert "Second" in result

    def test_collapses_whitespace_only_lines(self):
        html = "<p>First</p>\n   \n\t\n   \n<p>Second</p>"
        result = generate_plain_text_from_html(html)
        assert "\n\n\n" not in result
        lines = result.strip("\n").splitlines()
        # No line should be pure whitespace once collapsed.
        assert all(line == line.strip() for line in lines)

    def test_deeply_nested_empty_structure_collapses(self):
        # Mimics table/div "scaffolding" that leaves many blank lines once
        # tags are stripped.
        html = (
            "<table><tr><td></td></tr></table>\n"
            "<div>\n  <div>\n    <p>Payload</p>\n  </div>\n</div>\n"
            "<table><tr><td></td></tr></table>"
        )
        result = generate_plain_text_from_html(html)
        assert "\n\n\n" not in result
        assert "Payload" in result

    # -- Trimming / padding -------------------------------------------------

    def test_no_leading_or_trailing_pile_of_whitespace(self):
        html = "\n\n\n   <p>Content</p>   \n\n\n"
        result = generate_plain_text_from_html(html)
        assert result.startswith("\n")
        assert not result.startswith("\n\n\n")
        assert result.rstrip("\n") != ""
        assert not result.endswith("\n\n\n")

    def test_padding_is_at_most_a_single_blank_line(self):
        html = "<p>Content</p>"
        result = generate_plain_text_from_html(html)
        # Strip exactly one leading and trailing newline of "padding" and
        # confirm there isn't more hiding behind it.
        assert result[:1] == "\n"
        core = result.strip("\n")
        assert core == "Content"

    # -- Robustness / non-goals -------------------------------------------------

    def test_empty_string_does_not_crash(self):
        result = generate_plain_text_from_html("")
        assert result == ""

    def test_none_like_falsy_input_does_not_crash(self):
        result = generate_plain_text_from_html("")
        assert isinstance(result, str)

    def test_plain_text_with_no_markup_is_returned_readably(self):
        html = "Just a plain sentence with no tags at all."
        result = generate_plain_text_from_html(html)
        assert "Just a plain sentence with no tags at all." in result

    def test_malformed_html_does_not_raise(self):
        html = "<p>Unclosed paragraph <div>and a stray <span>tag"
        # Should not raise, and should still surface the text.
        result = generate_plain_text_from_html(html)
        assert "Unclosed paragraph" in result
        assert "and a stray" in result

    def test_malformed_style_block_does_not_raise(self):
        html = "<style>body { margin: 0;<p>Broken up to here</p>"
        result = generate_plain_text_from_html(html)
        assert isinstance(result, str)

    def test_whitespace_only_input_returns_sensibly(self):
        result = generate_plain_text_from_html("   \n\n   \t  ")
        assert result.strip() == ""

    # -- Real template fixtures -------------------------------------------------

    def test_forgot_password_template_strips_css_and_keeps_body_text(self):
        # Read the raw template (not rendered by Django) - it still uses
        # `{{ variable }}` placeholder syntax, so we check for concrete CSS
        # fragments rather than a blanket "no curly braces" rule.
        html = (TEMPLATES_DIR / "auth" / "forgot_password.html").read_text()
        result = generate_plain_text_from_html(html)

        # No CSS should have leaked into the plain-text version.
        assert "font-family" not in result
        assert "@media" not in result
        assert "border-collapse" not in result
        assert "-ms-interpolation-mode" not in result
        assert "<style" not in result

        # No HTML tags should remain (Jinja-style `{{ }}` placeholders are
        # not tags and are allowed to survive an un-rendered read).
        assert "<p" not in result
        assert "<div" not in result
        assert "<table" not in result

        # Recognisable body copy should survive.
        assert "Reset your Локсо password" in result
        assert "We received a request to reset your Локсо password" in result

        # No sprawling runs of blank lines from collapsed table/div scaffolding.
        assert "\n\n\n" not in result

    def test_forgot_password_template_rendered_via_django(self):
        html = render_to_string(
            "emails/auth/forgot_password.html",
            {
                "forgot_password_url": "https://lokso.ru/reset?token=abc123",
                "email": "user@example.com",
            },
        )
        result = generate_plain_text_from_html(html)

        assert "{" not in result
        assert "}" not in result
        assert "font-family" not in result
        assert "https://lokso.ru/reset?token=abc123" in result
        assert "user@example.com" in result
        assert "Reset your Локсо password" in result

    def test_workspace_invitation_template_strips_css_and_keeps_body_text(self):
        html = render_to_string(
            "emails/invitations/workspace_invitation.html",
            {
                "first_name": "Артём",
                "workspace_name": "Локсо HQ",
                "abs_url": "https://lokso.ru/accept?token=xyz",
                "email": "invitee@example.com",
            },
        )
        result = generate_plain_text_from_html(html)

        assert "{" not in result
        assert "}" not in result
        assert "font-family" not in result
        assert "email-container" not in result
        assert "Join Локсо HQ on Локсо" in result
        assert "https://lokso.ru/accept?token=xyz" in result

    def test_all_real_templates_produce_css_free_output(self):
        """Smoke-test every shipped email template read raw (not rendered
        through Django - these still contain `{{ var }}` / `{% tag %}`
        placeholder syntax, which is not CSS and is fine to survive). The
        static CSS declared in <style> blocks must never survive."""
        template_paths = sorted(TEMPLATES_DIR.rglob("*.html"))
        assert len(template_paths) >= 12

        for path in template_paths:
            html = path.read_text()
            result = generate_plain_text_from_html(html)
            assert "<style" not in result, f"<style> tag leaked from {path}"
            assert "font-family" not in result, f"CSS leaked from {path}"
            assert "-ms-interpolation-mode" not in result, f"CSS leaked from {path}"

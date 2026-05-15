"""
search_onenote tool — drop this into your agent.py

SETUP (one-time):
  Set these environment variables before running your agent:
    ONENOTE_ACCESS_TOKEN   — your Microsoft Graph API access token
    ONENOTE_NOTEBOOK_NAME  — (optional) filter to a specific notebook, e.g. "Healing Knowledge Base"

HOW TO GET AN ACCESS TOKEN (simple way for personal use):
  1. Go to: https://developer.microsoft.com/en-us/graph/graph-explorer
  2. Sign in with your Microsoft account
  3. In the top-right, click your avatar → copy the Access Token
  4. Paste it into your .env file as ONENOTE_ACCESS_TOKEN
  Token expires in ~1 hour. For production, use OAuth2 refresh tokens (ask me to help set that up).
"""

import os
import re
import requests


# ── 1. Tool definition (add this to your TOOLS list) ──────────────────────────

SEARCH_ONENOTE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_onenote",
        "description": (
            "Searches the healer's OneNote knowledge base for pages matching a query. "
            "Returns the page title, notebook, section, and text content. "
            "Use this to look up healing phase information, conflict-emotion patterns, "
            "organ relationships, or any knowledge stored in OneNote."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search term — can be a symptom, organ name, emotion, "
                        "conflict type, or any keyword. Examples: 'liver', "
                        "'separation conflict', 'skin healing phase', 'kidney fear'."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of pages to return (default: 5, max: 10).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


# ── 2. Tool implementation ─────────────────────────────────────────────────────

def _search_onenote(query: str, max_results: int = 5) -> str:
    """
    Searches OneNote via Microsoft Graph API.
    Returns formatted text ready for the agent to reason over.
    """
    access_token = os.getenv("ONENOTE_ACCESS_TOKEN")
    if not access_token:
        return (
            "Error: ONENOTE_ACCESS_TOKEN environment variable is not set. "
            "Get your token from https://developer.microsoft.com/en-us/graph/graph-explorer"
        )

    max_results = min(max_results or 5, 10)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Step 1: Search for matching pages
    search_url = "https://graph.microsoft.com/v1.0/me/onenote/pages"
    params = {
        "$search": f'"{query}"',
        "$select": "id,title,createdDateTime,lastModifiedDateTime,parentSection,parentNotebook",
        "$top": max_results,
        "$expand": "parentSection,parentNotebook",
    }

    try:
        resp = requests.get(search_url, headers=headers, params=params, timeout=15)
    except requests.exceptions.Timeout:
        return "Error: OneNote API request timed out. Check your internet connection."
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to Microsoft Graph API."

    if resp.status_code == 401:
        return (
            "Error: Access token is expired or invalid. "
            "Get a fresh token from https://developer.microsoft.com/en-us/graph/graph-explorer"
        )
    if resp.status_code == 403:
        return (
            "Error: Insufficient permissions. Make sure your Azure app has 'Notes.Read' "
            "or 'Notes.ReadWrite' permission granted."
        )
    if not resp.ok:
        return f"Error: OneNote API returned {resp.status_code} — {resp.text[:300]}"

    pages = resp.json().get("value", [])
    if not pages:
        return f"No OneNote pages found matching '{query}'."

    # Step 2: Fetch content for each matching page
    results = []
    for page in pages:
        page_id    = page.get("id", "")
        title      = page.get("title", "Untitled")
        notebook   = page.get("parentNotebook", {}).get("displayName", "Unknown notebook")
        section    = page.get("parentSection", {}).get("displayName", "Unknown section")
        modified   = page.get("lastModifiedDateTime", "")[:10]

        content_text = _fetch_page_content(page_id, headers)

        results.append(
            f"📄 Page: {title}\n"
            f"   Notebook: {notebook} › {section}\n"
            f"   Last modified: {modified}\n"
            f"   Content:\n{content_text}\n"
        )

    separator = "\n" + "─" * 60 + "\n"
    header = f"Found {len(results)} OneNote page(s) for '{query}':\n" + "─" * 60 + "\n"
    return header + separator.join(results)


def _fetch_page_content(page_id: str, headers: dict) -> str:
    """Fetches and cleans HTML content from a OneNote page."""
    content_url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}/content"
    try:
        resp = requests.get(content_url, headers=headers, timeout=15)
        if not resp.ok:
            return "  (could not fetch page content)"
        html = resp.text
        text = _strip_html(html)
        # Trim very long pages to keep context window manageable
        if len(text) > 2000:
            text = text[:2000] + "\n  ... (page truncated — ask for more if needed)"
        # Indent for readability inside agent output
        return "\n".join(f"  {line}" for line in text.splitlines() if line.strip())
    except Exception:
        return "  (error reading page content)"


def _strip_html(html: str) -> str:
    """Removes HTML tags and decodes common entities."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&nbsp;", " ")
            .replace("&#39;", "'")
            .replace("&quot;", '"')
    )
    # Collapse whitespace but preserve paragraph breaks
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned


# ── 3. How to wire it into your agent.py ──────────────────────────────────────
#
# Step A — Add to TOOLS list:
#   from search_onenote_tool import SEARCH_ONENOTE_TOOL
#   TOOLS = [ ...your existing tools..., SEARCH_ONENOTE_TOOL ]
#
# Step B — Add to _TOOL_MAP:
#   from search_onenote_tool import _search_onenote
#   _TOOL_MAP = {
#       "terminal":      lambda a: _terminal(a["command"]),
#       "file_read":     lambda a: _file_read(a["path"]),
#       "file_write":    lambda a: _file_write(a["path"], a["content"]),
#       "search_onenote": lambda a: _search_onenote(
#                             a["query"],
#                             a.get("max_results", 5)
#                         ),
#   }
#
# Step C — Set your token in .env or shell:
#   export ONENOTE_ACCESS_TOKEN="eyJ0eXAiOiJKV1Q..."
#
# That's it. Your agent will now call search_onenote automatically
# whenever it needs to look something up from your healing knowledge base.
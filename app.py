import base64
import io

import streamlit as st

from notebook_utils import diff_notebooks, parse_notebook

st.set_page_config(page_title="Log Viewer Analysis", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar: upload snapshots only
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Snapshots")
    title = st.text_input("Title", value="Log Viewer — Notebook Snapshot Diff", label_visibility="collapsed")
    uploaded_files = st.file_uploader(
        "Upload .ipynb snapshots",
        type=["ipynb"],
        accept_multiple_files=True,
    )
    uploaded_files = sorted(uploaded_files, key=lambda f: f.name)

snapshots = [{"file": f} for f in uploaded_files]

st.title(title)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def render_cell(cell: dict, key_prefix: str = ""):
    """Render a single notebook cell."""
    if cell["cell_type"] == "code":
        if cell["source"]:
            st.code(cell["source"], language="python")
    else:
        src = cell["source"] or ""
        if src.strip():
            st.markdown(src)

    for output in cell.get("outputs", []):
        if output["type"] == "text":
            st.text(output["data"])
        elif output["type"] == "image":
            try:
                img_bytes = base64.b64decode(output["data"])
                st.image(img_bytes)
            except Exception:
                st.caption("[image output — could not render]")


def render_inline_diff(diff_lines: list[str]):
    """Render unified diff lines with green/red line highlights."""
    html_lines = []
    for line in diff_lines:
        if line.startswith("---") or line.startswith("+++"):
            continue  # skip file headers
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith("+"):
            style = "background:#d4edda;color:#155724"
        elif line.startswith("-"):
            style = "background:#f8d7da;color:#721c24"
        elif line.startswith("@@"):
            style = "background:#e2e3e5;color:#6c757d"
        else:
            style = "background:#f8f9fa;color:#212529"
        html_lines.append(
            f'<div style="font-family:monospace;font-size:13px;'
            f'padding:1px 8px;white-space:pre;{style}">{escaped}</div>'
        )
    html = (
        '<div style="border:1px solid #dee2e6;border-radius:4px;'
        'overflow:hidden;margin-bottom:8px">'
        + "".join(html_lines)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _cell_label(cell: dict) -> str:
    src = (cell.get("source") or "").strip()
    first_line = src.splitlines()[0] if src else ""
    return first_line[:60] + ("…" if len(first_line) > 60 else "") if first_line else "(empty)"


def render_diff_cell(entry: dict):
    status = entry["status"]

    if status == "unchanged":
        return

    elif status == "added":
        with st.expander(f"+ {_cell_label(entry['cell_b'])}", expanded=False):
            render_cell(entry["cell_b"])

    elif status == "removed":
        with st.expander(f"- {_cell_label(entry['cell_a'])}", expanded=False):
            render_cell(entry["cell_a"])

    elif status == "changed":
        with st.expander(f"~ {_cell_label(entry['cell_b'])}", expanded=False):
            if entry["text_diff"]:
                render_inline_diff(entry["text_diff"])
            else:
                render_cell(entry["cell_b"])


def render_full_notebook(cells: list[dict]):
    for cell in cells:
        render_cell(cell)
        st.divider()


# ---------------------------------------------------------------------------
# HTML export
# ---------------------------------------------------------------------------

def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _cell_to_html(cell: dict) -> str:
    parts = []
    if cell["cell_type"] == "code":
        if cell["source"]:
            src = _html_escape(cell["source"])
            parts.append(
                f'<pre style="background:#f6f8fa;border:1px solid #e1e4e8;'
                f'border-radius:4px;padding:10px;font-size:13px;overflow-x:auto">'
                f'<code>{src}</code></pre>'
            )
    else:
        src = (cell["source"] or "").strip()
        if src:
            parts.append(f'<p style="margin:4px 0">{_html_escape(src)}</p>')

    for output in cell.get("outputs", []):
        if output["type"] == "text":
            parts.append(
                f'<pre style="background:#fff;border:1px solid #e1e4e8;'
                f'border-radius:4px;padding:8px;font-size:12px">'
                f'{_html_escape(output["data"])}</pre>'
            )
        elif output["type"] == "image":
            parts.append(
                f'<img src="data:image/png;base64,{output["data"]}" '
                f'style="max-width:100%;margin:4px 0">'
            )
    return "".join(parts)


def _diff_lines_to_html(diff_lines: list[str]) -> str:
    rows = []
    for line in diff_lines:
        if line.startswith("---") or line.startswith("+++"):
            continue
        escaped = _html_escape(line)
        if line.startswith("+"):
            style = "background:#d4edda;color:#155724"
        elif line.startswith("-"):
            style = "background:#f8d7da;color:#721c24"
        elif line.startswith("@@"):
            style = "background:#e2e3e5;color:#6c757d"
        else:
            style = "background:#f8f9fa;color:#212529"
        rows.append(
            f'<div style="font-family:monospace;font-size:13px;'
            f'padding:1px 8px;white-space:pre;{style}">{escaped}</div>'
        )
    return (
        '<div style="border:1px solid #dee2e6;border-radius:4px;'
        'overflow:hidden;margin-bottom:8px">' + "".join(rows) + "</div>"
    )


def _details(summary: str, body: str, open: bool = False) -> str:
    open_attr = " open" if open else ""
    return (
        f'<details{open_attr} style="margin-bottom:6px;border:1px solid #dee2e6;'
        f'border-radius:4px;padding:6px 10px">'
        f'<summary style="cursor:pointer;font-family:monospace;font-size:13px">'
        f'{_html_escape(summary)}</summary>'
        f'<div style="margin-top:8px">{body}</div></details>'
    )


def build_html(snapshots: list, parsed: list, title: str = "") -> str:
    sections = []
    for i in range(len(snapshots) - 1):
        cells_a = parsed[i]
        cells_b = parsed[i + 1]
        name_b = snapshots[i + 1]["file"].name

        prompt = st.session_state.get(f"prompt_{name_b}", "")
        block = []

        if prompt:
            block.append(
                f'<div style="background:#e8f4fd;border-left:3px solid #1a73e8;'
                f'border-radius:4px;padding:10px 14px;margin-bottom:12px;'
                f'font-size:15px">{_html_escape(prompt)}</div>'
            )

        if cells_a is None or cells_b is None:
            block.append('<p style="color:#856404">Could not parse one or both snapshots.</p>')
            sections.append("".join(block))
            continue

        diff = diff_notebooks(cells_a, cells_b)
        added = sum(1 for d in diff if d["status"] == "added")
        removed = sum(1 for d in diff if d["status"] == "removed")
        changed = sum(1 for d in diff if d["status"] == "changed")
        unchanged = sum(1 for d in diff if d["status"] == "unchanged")
        block.append(
            f'<p style="color:#6c757d;font-size:13px;margin-bottom:8px">'
            f'{_html_escape(name_b)} · {added} added · {removed} removed · '
            f'{changed} changed · {unchanged} unchanged</p>'
        )

        for entry in diff:
            status = entry["status"]
            if status == "unchanged":
                continue
            elif status == "added":
                label = f"+ {_cell_label(entry['cell_b'])}"
                body = _cell_to_html(entry["cell_b"])
            elif status == "removed":
                label = f"- {_cell_label(entry['cell_a'])}"
                body = _cell_to_html(entry["cell_a"])
            else:  # changed
                label = f"~ {_cell_label(entry['cell_b'])}"
                body = (
                    _diff_lines_to_html(entry["text_diff"])
                    if entry["text_diff"]
                    else _cell_to_html(entry["cell_b"])
                )
            block.append(_details(label, body))

        full_nb = "".join(_cell_to_html(c) for c in cells_b)
        block.append(_details(f"View full notebook — {name_b}", full_nb))
        block.append('<hr style="border:none;border-top:1px solid #dee2e6;margin:20px 0">')
        sections.append("".join(block))

    body_html = "\n".join(sections) if sections else "<p>No snapshots loaded.</p>"
    escaped_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escaped_title}</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:40px auto;padding:0 20px}}</style>
</head>
<body>
<h1>{escaped_title}</h1>
{body_html}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main area: pairwise diffs
# ---------------------------------------------------------------------------

# Parse all uploaded notebooks (cache per file content to avoid re-parsing)
parsed: list[list[dict] | None] = []
for snap in snapshots:
    if snap["file"] is not None:
        try:
            snap["file"].seek(0)
            cells = parse_notebook(io.TextIOWrapper(snap["file"], encoding="utf-8"))
            parsed.append(cells)
        except Exception as e:
            st.error(f"Failed to parse {snap['file'].name}: {e}")
            parsed.append(None)
    else:
        parsed.append(None)

if snapshots:
    with st.sidebar:
        st.divider()
        html_export = build_html(snapshots, parsed, title)
        st.download_button(
            "Download as HTML",
            data=html_export,
            file_name="notebook-diff.html",
            mime="text/html",
            use_container_width=True,
        )

# Show conversation log
if not snapshots:
    st.info("Upload .ipynb snapshots in the sidebar to get started.")

for i in range(len(snapshots) - 1):
    cells_a = parsed[i]
    cells_b = parsed[i + 1]
    name_b = snapshots[i + 1]["file"].name if snapshots[i + 1]["file"] else f"Snapshot {i + 2}"

    # Prompt input styled as a chat message
    prompt = st.text_area(
        "Prompt",
        key=f"prompt_{name_b}",
        height=80,
        label_visibility="collapsed",
        placeholder="Enter prompt...",
    )
    if prompt:
        st.markdown(
            f'<div style="background:#e8f4fd;border-left:3px solid #1a73e8;'
            f'border-radius:4px;padding:10px 14px;margin-bottom:12px;'
            f'font-size:15px">{prompt}</div>',
            unsafe_allow_html=True,
        )

    if cells_a is None or cells_b is None:
        st.warning("Upload both snapshots to see the diff.")
        continue

    diff = diff_notebooks(cells_a, cells_b)

    added = sum(1 for d in diff if d["status"] == "added")
    removed = sum(1 for d in diff if d["status"] == "removed")
    changed = sum(1 for d in diff if d["status"] == "changed")
    unchanged = sum(1 for d in diff if d["status"] == "unchanged")
    st.caption(
        f"{name_b} · {added} added · {removed} removed · {changed} changed · {unchanged} unchanged"
    )

    for entry in diff:
        render_diff_cell(entry)

    with st.expander(f"View full notebook — {name_b}"):
        render_full_notebook(cells_b)

    st.divider()

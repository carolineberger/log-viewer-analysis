import base64
import io

import streamlit as st

from notebook_utils import diff_notebooks, parse_notebook

st.set_page_config(page_title="Log Viewer Analysis", layout="wide")
st.title("Log Viewer — Notebook Snapshot Diff")

# ---------------------------------------------------------------------------
# Sidebar: upload snapshots + prompts
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Snapshots")
    uploaded_files = st.file_uploader(
        "Upload .ipynb snapshots",
        type=["ipynb"],
        accept_multiple_files=True,
    )
    uploaded_files = sorted(uploaded_files, key=lambda f: f.name)

    snapshots = []
    for f in uploaded_files:
        st.divider()
        st.caption(f.name)
        prompt = st.text_area("Prompt", key=f"prompt_{f.name}", height=80)
        snapshots.append({"file": f, "prompt": prompt})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def render_cell(cell: dict, key_prefix: str = ""):
    """Render a single notebook cell."""
    if cell["cell_type"] == "code":
        st.code(cell["source"] or "(empty)", language="python")
    else:
        src = cell["source"] or ""
        if src.strip():
            st.markdown(src)
        else:
            st.caption("(empty markdown cell)")

    for output in cell.get("outputs", []):
        if output["type"] == "text":
            st.text(output["data"])
        elif output["type"] == "image":
            try:
                img_bytes = base64.b64decode(output["data"])
                st.image(img_bytes)
            except Exception:
                st.caption("[image output — could not render]")


def render_diff_cell(entry: dict):
    status = entry["status"]

    if status == "unchanged":
        with st.expander("unchanged cell", expanded=False):
            render_cell(entry["cell_b"])

    elif status == "added":
        with st.container():
            st.markdown(
                '<div style="background:#d4edda;padding:8px;border-left:4px solid #28a745;'
                'border-radius:4px;margin-bottom:4px"><strong>+ added</strong></div>',
                unsafe_allow_html=True,
            )
            render_cell(entry["cell_b"])

    elif status == "removed":
        with st.container():
            st.markdown(
                '<div style="background:#f8d7da;padding:8px;border-left:4px solid #dc3545;'
                'border-radius:4px;margin-bottom:4px"><strong>- removed</strong></div>',
                unsafe_allow_html=True,
            )
            render_cell(entry["cell_a"])

    elif status == "changed":
        with st.container():
            st.markdown(
                '<div style="background:#fff3cd;padding:8px;border-left:4px solid #ffc107;'
                'border-radius:4px;margin-bottom:4px"><strong>~ changed</strong></div>',
                unsafe_allow_html=True,
            )
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("Before")
                render_cell(entry["cell_a"])
            with col_b:
                st.caption("After")
                render_cell(entry["cell_b"])
            if entry["text_diff"]:
                with st.expander("Inline text diff"):
                    diff_text = "".join(entry["text_diff"])
                    st.code(diff_text, language="diff")


def render_full_notebook(cells: list[dict]):
    for cell in cells:
        render_cell(cell)
        st.divider()


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

# Show pairwise diffs
for i in range(len(snapshots) - 1):
    cells_a = parsed[i]
    cells_b = parsed[i + 1]
    prompt_b = snapshots[i + 1]["prompt"]
    name_a = snapshots[i]["file"].name if snapshots[i]["file"] else f"Snapshot {i + 1}"
    name_b = snapshots[i + 1]["file"].name if snapshots[i + 1]["file"] else f"Snapshot {i + 2}"

    st.header(f"Diff: {name_a}  →  {name_b}")

    if prompt_b:
        st.info(f"**Prompt for snapshot {i + 2}:** {prompt_b}")

    if cells_a is None or cells_b is None:
        st.warning("Upload both snapshots to see the diff.")
        continue

    diff = diff_notebooks(cells_a, cells_b)

    added = sum(1 for d in diff if d["status"] == "added")
    removed = sum(1 for d in diff if d["status"] == "removed")
    changed = sum(1 for d in diff if d["status"] == "changed")
    unchanged = sum(1 for d in diff if d["status"] == "unchanged")
    st.caption(
        f"{added} added · {removed} removed · {changed} changed · {unchanged} unchanged"
    )

    for entry in diff:
        render_diff_cell(entry)

    with st.expander(f"View full notebook — {name_b}"):
        render_full_notebook(cells_b)

    st.divider()

if not snapshots:
    st.info("Upload .ipynb snapshots in the sidebar to get started.")

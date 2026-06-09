import io

import streamlit as st

from notebook_utils import diff_notebooks, parse_notebook

st.set_page_config(page_title="AI Change Analysis", layout="wide")

st.title("AI Change Analysis")

# ---------------------------------------------------------------------------
# Sidebar: upload snapshots
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Snapshots")
    uploaded_files = st.file_uploader(
        "Upload .ipynb snapshots",
        type=["ipynb"],
        accept_multiple_files=True,
    )
    uploaded_files = sorted(uploaded_files, key=lambda f: f.name)

snapshots = [{"file": f} for f in uploaded_files]

# Parse notebooks
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

if not snapshots:
    st.info("Upload .ipynb snapshots in the sidebar to get started.")
    st.stop()

# ---------------------------------------------------------------------------
# AI Analysis
# ---------------------------------------------------------------------------

st.subheader("Analysis Settings")

api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
model = st.selectbox(
    "Model",
    ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
)
system_prompt = st.text_area(
    "System prompt",
    value=(
        "You are an expert data scientist reviewing changes between Jupyter notebook snapshots. "
        "Analyse the diff provided and give a concise, insightful summary of what changed, "
        "why it might have changed, and any concerns or recommendations."
    ),
    height=100,
)

if st.button("Run AI Analysis", type="primary", disabled=not api_key):
    if not api_key:
        st.warning("Enter an API key to run analysis.")
        st.stop()

    try:
        import anthropic
    except ImportError:
        st.error("anthropic package not installed. Run: pip install anthropic")
        st.stop()

    client = anthropic.Anthropic(api_key=api_key)

    for i in range(len(snapshots) - 1):
        cells_a = parsed[i]
        cells_b = parsed[i + 1]
        name_a = snapshots[i]["file"].name
        name_b = snapshots[i + 1]["file"].name

        st.markdown(f"### {name_a} → {name_b}")

        if cells_a is None or cells_b is None:
            st.warning("Could not parse one or both snapshots.")
            continue

        diff = diff_notebooks(cells_a, cells_b)
        added = [d for d in diff if d["status"] == "added"]
        removed = [d for d in diff if d["status"] == "removed"]
        changed = [d for d in diff if d["status"] == "changed"]

        st.caption(
            f"{len(added)} added · {len(removed)} removed · {len(changed)} changed · "
            f"{sum(1 for d in diff if d['status'] == 'unchanged')} unchanged"
        )

        if not (added or removed or changed):
            st.success("No changes detected between these snapshots.")
            continue

        # Build diff text for the prompt
        diff_lines = []
        for entry in diff:
            status = entry["status"]
            if status == "unchanged":
                continue
            elif status == "added":
                src = (entry["cell_b"].get("source") or "").strip()
                diff_lines.append(f"[ADDED {entry['cell_b']['cell_type']} cell]\n{src}")
            elif status == "removed":
                src = (entry["cell_a"].get("source") or "").strip()
                diff_lines.append(f"[REMOVED {entry['cell_a']['cell_type']} cell]\n{src}")
            elif status == "changed":
                lines = entry.get("text_diff") or []
                diff_lines.append(
                    f"[CHANGED {entry['cell_b']['cell_type']} cell]\n" + "\n".join(lines)
                )

        diff_text = "\n\n---\n\n".join(diff_lines)
        user_message = (
            f"Here is the diff between notebook snapshots '{name_a}' and '{name_b}':\n\n"
            f"{diff_text}\n\nPlease analyse these changes."
        )

        with st.spinner("Analysing..."):
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            analysis = response.content[0].text

        st.markdown(analysis)
        st.divider()

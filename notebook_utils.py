import difflib
import nbformat


def parse_notebook(file) -> list[dict]:
    """Parse an .ipynb file and return a list of cell dicts."""
    nb = nbformat.read(file, as_version=4)
    cells = []
    for cell in nb.cells:
        outputs = []
        for output in getattr(cell, "outputs", []):
            if output.get("output_type") in ("stream", "execute_result", "display_data"):
                if "text" in output:
                    text = output["text"]
                    if isinstance(text, list):
                        text = "".join(text)
                    outputs.append({"type": "text", "data": text})
                elif "data" in output:
                    data = output["data"]
                    if "image/png" in data:
                        outputs.append({"type": "image", "data": data["image/png"]})
                    elif "text/plain" in data:
                        text = data["text/plain"]
                        if isinstance(text, list):
                            text = "".join(text)
                        outputs.append({"type": "text", "data": text})
        cells.append({
            "cell_type": cell.cell_type,
            "source": cell.source,
            "outputs": outputs,
        })
    return cells


def diff_notebooks(cells_a: list[dict], cells_b: list[dict]) -> list[dict]:
    """Compute a cell-level diff between two lists of cells.

    Returns a list of dicts with keys:
        status: 'added' | 'removed' | 'changed' | 'unchanged'
        cell_a: cell from snapshot A (None if added)
        cell_b: cell from snapshot B (None if removed)
        text_diff: unified diff lines for changed cells (else None)
    """
    sources_a = [c["source"] for c in cells_a]
    sources_b = [c["source"] for c in cells_b]

    matcher = difflib.SequenceMatcher(None, sources_a, sources_b, autojunk=False)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                result.append({
                    "status": "unchanged",
                    "cell_a": cells_a[i],
                    "cell_b": cells_b[j],
                    "text_diff": None,
                })
        elif tag == "replace":
            # Pair up cells; extras become added/removed
            pairs = max(i2 - i1, j2 - j1)
            for k in range(pairs):
                ia = i1 + k
                jb = j1 + k
                if ia < i2 and jb < j2:
                    diff_lines = list(difflib.unified_diff(
                        cells_a[ia]["source"].splitlines(keepends=True),
                        cells_b[jb]["source"].splitlines(keepends=True),
                        lineterm="",
                    ))
                    result.append({
                        "status": "changed",
                        "cell_a": cells_a[ia],
                        "cell_b": cells_b[jb],
                        "text_diff": diff_lines,
                    })
                elif ia < i2:
                    result.append({
                        "status": "removed",
                        "cell_a": cells_a[ia],
                        "cell_b": None,
                        "text_diff": None,
                    })
                else:
                    result.append({
                        "status": "added",
                        "cell_a": None,
                        "cell_b": cells_b[jb],
                        "text_diff": None,
                    })
        elif tag == "delete":
            for i in range(i1, i2):
                result.append({
                    "status": "removed",
                    "cell_a": cells_a[i],
                    "cell_b": None,
                    "text_diff": None,
                })
        elif tag == "insert":
            for j in range(j1, j2):
                result.append({
                    "status": "added",
                    "cell_a": None,
                    "cell_b": cells_b[j],
                    "text_diff": None,
                })

    return result

import json

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Annotate", layout="wide")


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _highlight_style() -> str:
    return """<style>
.ann-mark {
  position: relative;
  display: inline;
}
.ann-mark::after {
  content: attr(data-note);
  position: absolute;
  bottom: 100%;
  left: 0;
  white-space: pre;
  background: #333;
  color: #fff;
  font-size: 12px;
  padding: 3px 7px;
  border-radius: 4px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 9999;
  max-width: 300px;
  white-space: normal;
  word-wrap: break-word;
}
.ann-mark:hover::after {
  opacity: 1;
}
</style>"""


def _highlight_script(annotations: list) -> str:
    data = json.dumps(annotations)
    return f"""<script>
(function() {{
  var annotations = {data};

  function escapeRegex(s) {{
    return s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
  }}

  function highlightText(root, text, color, note) {{
    if (!text) return;
    var re = new RegExp(escapeRegex(text), 'g');
    var walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_TEXT,
      {{
        acceptNode: function(node) {{
          var p = node.parentNode;
          while (p && p !== root) {{
            var tag = p.nodeName.toUpperCase();
            if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'MARK') {{
              return NodeFilter.FILTER_REJECT;
            }}
            p = p.parentNode;
          }}
          return NodeFilter.FILTER_ACCEPT;
        }}
      }}
    );
    var nodes = [];
    var n;
    while ((n = walker.nextNode())) nodes.push(n);

    nodes.forEach(function(node) {{
      var val = node.nodeValue;
      var match;
      var lastIndex = 0;
      var frag = document.createDocumentFragment();
      var found = false;
      re.lastIndex = 0;
      while ((match = re.exec(val)) !== null) {{
        if (match.index > lastIndex) {{
          frag.appendChild(document.createTextNode(val.slice(lastIndex, match.index)));
        }}
        var mark = document.createElement('mark');
        mark.className = 'ann-mark';
        mark.style.background = color;
        mark.setAttribute('data-note', note);
        mark.appendChild(document.createTextNode(match[0]));
        frag.appendChild(mark);
        lastIndex = match.index + match[0].length;
        found = true;
      }}
      if (found) {{
        if (lastIndex < val.length) {{
          frag.appendChild(document.createTextNode(val.slice(lastIndex)));
        }}
        node.parentNode.replaceChild(frag, node);
      }}
    }});
  }}

  function run() {{
    annotations.forEach(function(ann) {{
      highlightText(document.body, ann.text, ann.color, ann.note);
    }});
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', run);
  }} else {{
    run();
  }}
}})();
</script>"""


def build_preview_html(html_bytes: bytes, annotations: list) -> str:
    html = html_bytes.decode("utf-8", errors="replace")
    injection = _highlight_style() + _highlight_script(annotations)
    if "</body>" in html:
        html = html.replace("</body>", injection + "</body>", 1)
    else:
        html = html + injection
    return html


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "annotations" not in st.session_state:
    st.session_state.annotations = []
if "annotate_html_bytes" not in st.session_state:
    st.session_state.annotate_html_bytes = None
if "annotate_html_name" not in st.session_state:
    st.session_state.annotate_html_name = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Annotate")
    uploaded = st.file_uploader("Upload HTML file", type=["html", "htm"])

    if uploaded is not None:
        if uploaded.name != st.session_state.annotate_html_name:
            st.session_state.annotate_html_bytes = uploaded.read()
            st.session_state.annotate_html_name = uploaded.name
            st.session_state.annotations = []

    if st.session_state.annotate_html_bytes is not None:
        st.divider()
        annotated = build_preview_html(
            st.session_state.annotate_html_bytes,
            st.session_state.annotations,
        )
        st.download_button(
            "Download annotated HTML",
            data=annotated,
            file_name=st.session_state.annotate_html_name or "annotated.html",
            mime="text/html",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title("Annotate")

if st.session_state.annotate_html_bytes is None:
    st.info("Upload an HTML file in the sidebar to get started.")
    st.stop()

col_viewer, col_form = st.columns([3, 1])

# --- Form column ---
with col_form:
    st.subheader("Add annotation")
    ann_text = st.text_area("Text to highlight", key="ann_text", height=80)
    ann_note = st.text_area("Note", key="ann_note", height=80)
    ann_color = st.color_picker("Highlight color", value="#FFFF00", key="ann_color")

    if st.button("Add", use_container_width=True):
        if ann_text.strip():
            st.session_state.annotations.append(
                {"text": ann_text, "note": ann_note, "color": ann_color}
            )
            st.rerun()

    if st.session_state.annotations:
        st.divider()
        st.caption(f"{len(st.session_state.annotations)} annotation(s)")
        for i, ann in enumerate(st.session_state.annotations):
            cols = st.columns([1, 5, 1])
            with cols[0]:
                st.markdown(
                    f'<div style="width:18px;height:18px;background:{ann["color"]};'
                    f'border:1px solid #ccc;border-radius:3px;margin-top:6px"></div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                label = ann["text"][:30] + ("…" if len(ann["text"]) > 30 else "")
                st.markdown(
                    f'<div style="font-size:13px;padding-top:6px;overflow:hidden;'
                    f'white-space:nowrap;text-overflow:ellipsis" title="{ann["text"]}">'
                    f'{label}</div>',
                    unsafe_allow_html=True,
                )
            with cols[2]:
                if st.button("×", key=f"del_{i}", help="Delete"):
                    st.session_state.annotations.pop(i)
                    st.rerun()

# --- Viewer column ---
with col_viewer:
    preview = build_preview_html(
        st.session_state.annotate_html_bytes,
        st.session_state.annotations,
    )
    components.html(preview, height=900, scrolling=True)

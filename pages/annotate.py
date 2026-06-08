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


def _selection_script() -> str:
    return """<script>
(function() {
  var toast = null;

  function showToast(text) {
    if (toast) toast.remove();
    toast = document.createElement('div');
    toast.textContent = '\u2713 "' + text.slice(0, 40) + (text.length > 40 ? '\u2026' : '') + '" \u2192 form';
    toast.style.cssText = (
      'position:fixed;bottom:16px;left:50%;transform:translateX(-50%);' +
      'background:#333;color:#fff;padding:6px 14px;border-radius:20px;' +
      'font-size:13px;z-index:99999;pointer-events:none;opacity:1;' +
      'transition:opacity 0.4s'
    );
    document.body.appendChild(toast);
    setTimeout(function() { toast.style.opacity = '0'; }, 1800);
    setTimeout(function() { if (toast) { toast.remove(); toast = null; } }, 2200);
  }

  function setParentTextArea(labelText, value) {
    try {
      var parent = window.parent;
      var containers = parent.document.querySelectorAll('[data-testid="stTextArea"]');
      for (var i = 0; i < containers.length; i++) {
        var label = containers[i].querySelector('label p, label');
        if (label && label.textContent.trim() === labelText) {
          var ta = containers[i].querySelector('textarea');
          if (!ta) continue;
          var setter = Object.getOwnPropertyDescriptor(
            parent.HTMLTextAreaElement.prototype, 'value'
          ).set;
          setter.call(ta, value);
          ta.dispatchEvent(new parent.Event('input', { bubbles: true }));
          return true;
        }
      }
    } catch (e) {}
    return false;
  }

  document.addEventListener('mouseup', function() {
    var sel = window.getSelection();
    if (!sel) return;
    var text = sel.toString();
    if (!text.trim()) return;
    var ok = setParentTextArea('Text to highlight', text);
    if (ok) showToast(text);
  });
})();
</script>"""


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


def _inject(html: str, injection: str) -> str:
    if "</body>" in html:
        return html.replace("</body>", injection + "</body>", 1)
    return html + injection


def build_preview_html(html_bytes: bytes, annotations: list) -> str:
    html = html_bytes.decode("utf-8", errors="replace")
    return _inject(html, _highlight_style() + _highlight_script(annotations) + _selection_script())


def _sticky_note_script() -> str:
    return """<script>
(function() {
  function buildStickyNotes() {
    var marks = document.querySelectorAll('.ann-mark');
    if (!marks.length) return;

    var panel = document.createElement('div');
    panel.style.cssText = [
      'position:fixed', 'right:0', 'top:0', 'bottom:0', 'width:210px',
      'overflow-y:auto', 'background:#f5f5f5', 'border-left:1px solid #ddd',
      'padding:14px 10px', 'box-sizing:border-box',
      'font-family:sans-serif', 'font-size:12px', 'z-index:9999'
    ].join(';');

    var title = document.createElement('div');
    title.textContent = 'Annotations';
    title.style.cssText = (
      'font-weight:bold;font-size:13px;margin-bottom:10px;color:#444;' +
      'padding-bottom:6px;border-bottom:1px solid #ddd'
    );
    panel.appendChild(title);

    document.body.style.marginRight = '225px';

    var seen = {};
    marks.forEach(function(mark) {
      var note = mark.getAttribute('data-note') || '';
      var color = mark.style.background || '#FFFF00';
      var key = color + '|' + note;
      if (seen[key]) return;
      seen[key] = true;

      var card = document.createElement('div');
      card.style.cssText = [
        'background:' + color,
        'border-radius:4px', 'padding:8px 10px', 'margin-bottom:8px',
        'border:1px solid rgba(0,0,0,0.12)',
        'box-shadow:1px 2px 4px rgba(0,0,0,0.1)',
        'cursor:pointer', 'word-wrap:break-word'
      ].join(';');

      var txt = mark.textContent || '';
      var excerpt = document.createElement('div');
      excerpt.textContent = '\u201c' + txt.slice(0, 40) + (txt.length > 40 ? '\u2026' : '') + '\u201d';
      excerpt.style.cssText = 'font-style:italic;font-size:11px;opacity:0.75;margin-bottom:4px';
      card.appendChild(excerpt);

      if (note) {
        var noteDiv = document.createElement('div');
        noteDiv.textContent = note;
        card.appendChild(noteDiv);
      }

      card.addEventListener('click', function() {
        mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
        mark.style.outline = '3px solid rgba(0,0,0,0.4)';
        setTimeout(function() { mark.style.outline = ''; }, 1500);
      });

      panel.appendChild(card);
    });

    document.body.appendChild(panel);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildStickyNotes);
  } else {
    buildStickyNotes();
  }
})();
</script>"""


def build_annotated_html(html_bytes: bytes, annotations: list) -> str:
    html = html_bytes.decode("utf-8", errors="replace")
    return _inject(html, _highlight_style() + _highlight_script(annotations) + _sticky_note_script())


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
        annotated = build_annotated_html(
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
    ann_color = st.color_picker("Highlight color", value="#FFFF00", key="ann_color")
    with st.form("annotation_form", clear_on_submit=True):
        ann_text = st.text_area("Text to highlight", key="ann_text", height=80)
        ann_note = st.text_area("Note", key="ann_note", height=80)
        submitted = st.form_submit_button("Add", use_container_width=True)
    if submitted and ann_text.strip():
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

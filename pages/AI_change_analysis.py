import os
import streamlit as st
from dotenv import load_dotenv
import litellm
from bs4 import BeautifulSoup

load_dotenv()

litellm.api_base = "https://litellm.stream.cavi.au.dk/"
MODEL = "openai/natai/gpt-oss"


st.set_page_config(page_title="AI Change Analysis", layout="wide")


@st.dialog("Enter API Key")
def ask_for_api_key():
    st.write("Enter your API key to use AI analysis.")
    key = st.text_input("API Key", type="password")
    if st.button("Submit"):
        if key.strip():
            st.session_state["LITE_LLM_KEY"] = key.strip()
            st.rerun()
        else:
            st.error("Please enter a valid API key.")


if "LITE_LLM_KEY" not in st.session_state:
    env_key = os.environ.get("LITE_LLM_KEY")
    if env_key:
        st.session_state["LITE_LLM_KEY"] = env_key
    else:
        ask_for_api_key()
        st.stop()

litellm.api_key = st.session_state["LITE_LLM_KEY"]

st.title("AI Change Analysis")

with st.sidebar:
    st.header("Input")
    uploaded_html = st.file_uploader(
        "Upload exported HTML diff",
        type=["html"],
    )

if uploaded_html is None:
    st.info("Upload an HTML diff file in the sidebar to get started.")
    st.stop()

html_content = uploaded_html.read().decode("utf-8")
st.success(f"Loaded: {uploaded_html.name}")

_CHAR_LIMIT = 8000


def annotate_html(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    details_elements = [
        d for d in soup.find_all("details")
        if d.find("summary") and d.find("summary").get_text(strip=True)[:1] in ("+", "-", "~")
    ]
    descriptions = []
    for details in details_elements:
        summary = details.find("summary")
        label = summary.get_text(strip=True)
        body_div = details.find("div")
        full_body = body_div.get_text(separator="\n", strip=True) if body_div else ""
        truncated = len(full_body) > _CHAR_LIMIT
        body_text = full_body[:_CHAR_LIMIT]
        resp = litellm.completion(
            model=MODEL,
            api_base=litellm.api_base,
            api_key=litellm.api_key,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"This is a notebook cell change labeled '{label}'.\n\n"
                        f"{body_text}\n\n"
                        "Describe this change in exactly two sentences."
                    ),
                }
            ],
        )
        description = resp.choices[0].message.content or ""
        descriptions.append(f"{label}: {description}")

        annotation = soup.new_tag(
            "div",
            style=(
                "flex:0 0 220px;background:#fffbe6;border-left:3px solid #f0ad4e;"
                "border-radius:4px;padding:6px 10px;"
                "font-size:12px;font-family:sans-serif;align-self:flex-start"
            ),
        )
        annotation.string = description
        if truncated:
            note = soup.new_tag(
                "div",
                style="margin-top:6px;font-size:11px;color:#856404;font-style:italic",
            )
            note.string = "Note: input was truncated."
            annotation.append(note)

        wrapper = soup.new_tag(
            "div",
            style="display:flex;gap:10px;align-items:flex-start;margin-bottom:6px",
        )
        details.replace_with(wrapper)
        wrapper.append(annotation)
        wrapper.append(details)
    return str(soup), descriptions


with st.spinner("Annotating changes..."):
    annotated_html, descriptions = annotate_html(html_content)

with st.spinner("Generating overview..."):
    overview_text = "\n".join(descriptions)[:_CHAR_LIMIT]
    response = litellm.completion(
        model=MODEL,
        api_base=litellm.api_base,
        api_key=litellm.api_key,
        messages=[
            {
                "role": "user",
                "content": (
                    "The following are descriptions of individual notebook cell changes. "
                    "Give a two-sentence overview of what changed.\n\n"
                    + overview_text
                ),
            }
        ],
    )

st.subheader("Overview")
st.write(response.choices[0].message.content)

original_name = uploaded_html.name
stem = original_name.rsplit(".", 1)[0] if "." in original_name else original_name
download_name = f"{stem}-AI-annotated.html"

with st.sidebar:
    st.download_button(
        "Download annotated HTML",
        data=annotated_html,
        file_name=download_name,
        mime="text/html",
        use_container_width=True,
    )

st.subheader("HTML Preview")
st.components.v1.html(annotated_html, height=600, scrolling=True)

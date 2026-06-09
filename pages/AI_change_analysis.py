import os
import streamlit as st
from dotenv import load_dotenv
import litellm

load_dotenv()

litellm.api_key = os.environ.get("LITE_LLM_KEY")
litellm.api_base = "https://litellm.stream.cavi.au.dk/"

MODEL = "openai/natai/gpt-oss"


st.set_page_config(page_title="AI Change Analysis", layout="wide")

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

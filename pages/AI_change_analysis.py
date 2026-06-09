import streamlit as st

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

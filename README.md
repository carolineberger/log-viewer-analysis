# Log Viewer Analysis

A Streamlit app for building a timeline of Jupyter notebook snapshots and the prompts that drove each change. Upload a sequence of `.ipynb` files to visualize how a notebook evolved over time, paired with the prompts that produced each version. Diffs can optionally be enriched with AI-generated annotations that describe what changed at each step.

## Features

- Upload `.ipynb` snapshot files to generate a side-by-side diff
- Pair each diff with the prompt that drove the change (manual entry to ensure correct pairing)
- Browse code changes alongside the full notebook context
- Export diffs as standalone HTML files
- In progress - AI-powered change analysis via the AI Change Analysis page

## Live Application

The app is available at https://log-viewer-analysis.streamlit.app/

An API key is required for the AI Change Analysis page. Contact Caroline at caroline.berger@cs.au.dk to request a key.

## Getting Started

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run View_Generator.py
```

### Usage

View Generator

1. Upload `.ipynb` snapshot files (before and after) - order by v1, v2, ...
2. Paste the prompt from the logs that corresponds to the change
3. Inspect the generated diff — added/removed cells are highlighted
4. Export to HTML for sharing or later analysis

AI Change Analysis

1. Enter API key (reach out to Caroline at caroline.berger@cs.au.dk)
2. Upload the exported HTML from View Generator
3. Inspect the overview and the annotations
4. Export the annotated HTML for sharing or later analysis

## Screenshots

![Diff view](screenshots/image.png)
![Prompt pairing](screenshots/image-1.png)
![Code change view](screenshots/image-2.png)
![Full notebook context](screenshots/image-3.png)
![Export](screenshots/image-5.png)
![AI analysis](screenshots/image-4.png)

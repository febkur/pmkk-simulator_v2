# PMKK System Dynamics Simulator — Streamlit

A lightweight educational System Dynamics playground for Vensim `.mdl` models.

## User flow

1. Open the Streamlit URL.
2. Upload a self-contained `.mdl` file.
3. The app reads the model with PySD.
4. Inputs appear as sliders on the left.
5. All selected outputs appear as an adaptive small-multiples graph grid on the right.
6. Moving a slider reruns the uploaded model.

The simulator page is designed as a fixed desktop viewport rather than a long dashboard. The whole page does not vertically scroll. If a model contains more controls than can physically fit on the screen, only the left control pane scrolls; the graph pane remains visible.

## Recommended Vensim annotations

Use the variable comment field to explicitly control the UI:

```text
Training Coverage = 0.45
~ dmnl
~ @input min=0 max=1 step=0.05 label="Training coverage"
|

Formal Employment = INTEG(...)
~ People
~ @output label="Formal employment"
|
```

- `@input` exposes the variable as a slider.
- `min`, `max`, and `step` control the slider range.
- `label` controls the human-facing label.
- `@output` adds the variable to the outcome graph grid.

When explicit tags are present, all tagged inputs and outputs are included and the layout adapts to their count. For untagged models, the app uses conservative automatic detection to avoid exposing hundreds of technical variables by accident.

## Compatibility

The intended experience is “upload a compatible `.mdl` and run it automatically,” not a guarantee that every possible Vensim model will work unchanged. This version is best for self-contained models. Models that depend on external Excel/VDF/direct-data files, unsupported Vensim functions, complex macros, or other features that PySD cannot translate may require adaptation.

## Deploy on Streamlit Community Cloud

Use:

- Repository: your GitHub repository
- Branch: `main`
- Main file path: `app.py`

Streamlit Cloud installs the dependencies from `requirements.txt` automatically.

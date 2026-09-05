# PMKK System Dynamics Simulator — Streamlit edition

A deliberately small educational System Dynamics simulator:

1. Open the Streamlit link.
2. Upload a self-contained Vensim `.mdl` model.
3. The app reads the model.
4. Vensim variables marked `@input` become sliders.
5. Variables marked `@output` become outcome charts.
6. Changing a slider reruns the equations through PySD.

There is no separate frontend, REST API, CORS configuration, GitHub Pages workflow, or database.

## Repository structure

```text
pmkk-simulator/
├── .streamlit/
│   └── config.toml
├── sample/
│   └── simple_population.mdl
├── app.py
├── model_parser.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Vensim annotations

Put annotations in the comment/documentation field of a Vensim variable.

### Interactive input

```text
Training Coverage = 0.45
~ dmnl
~ @input min=0 max=1 step=0.05 label="Training coverage"
|
```

### Output

```text
Formal Employment = INTEG(...)
~ People
~ @output label="Formal employment"
|
```

Supported input metadata:

- `@input`
- `min=`
- `max=`
- `step=`
- `label=`

Output metadata:

- `@output`
- `label=`

If no tags are present, the app falls back to numeric constants for inputs and stock variables (`INTEG`) for outputs.

## Model limitation for this educational version

The uploaded `.mdl` should be self-contained. Models that depend on external Excel, VDF, or direct-data files are intentionally rejected so the user only has to upload one Vensim file.

## Run locally

```bash
python -m venv .venv
```

Activate the virtual environment, then:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push these files to a GitHub repository.
2. Sign in at https://share.streamlit.io with GitHub.
3. Select **Create app**.
4. Choose the repository and branch `main`.
5. Set the entrypoint to `app.py`.
6. Choose an app URL if desired.
7. Deploy.

Streamlit Community Cloud reads `requirements.txt` from the repository and installs PySD automatically.

## Suggested public flow

```text
Public Streamlit URL
        ↓
Upload .mdl
        ↓
PySD reads Vensim
        ↓
Inputs become sliders
        ↓
Simulation reruns
        ↓
Outcome charts update
```

from __future__ import annotations

import hashlib
import math
import tempfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from model_parser import ParsedModel, parse_model_text


st.set_page_config(
    page_title="PMKK System Dynamics Simulator",
    page_icon="↗",
    layout="wide",
    initial_sidebar_state="collapsed",
)


BASE_CSS = """
<style>
    [data-testid="stHeader"] {background: rgba(255,255,255,0); height: 0;}
    [data-testid="stToolbar"] {visibility: hidden; height: 0; position: fixed;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .block-container {
        max-width: 1500px;
        padding-top: 1.25rem;
        padding-bottom: 1.25rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }

    .eyebrow {
        font-size: .72rem;
        letter-spacing: .11em;
        text-transform: uppercase;
        font-weight: 700;
        opacity: .56;
        margin-bottom: .25rem;
    }

    .hero-title {
        font-size: clamp(1.9rem, 3.4vw, 3.2rem);
        line-height: 1.02;
        letter-spacing: -.04em;
        font-weight: 720;
        margin: 0 0 .55rem 0;
    }

    .hero-copy {
        max-width: 760px;
        font-size: 1rem;
        line-height: 1.6;
        opacity: .72;
        margin-bottom: 1.35rem;
    }

    .sim-title {
        font-size: clamp(1.25rem, 2.2vw, 1.9rem);
        line-height: 1.1;
        letter-spacing: -.025em;
        font-weight: 720;
        margin: 0;
    }

    .sim-meta {
        font-size: .78rem;
        opacity: .6;
        margin-top: .2rem;
    }

    .section-title {
        font-size: .7rem;
        text-transform: uppercase;
        letter-spacing: .1em;
        font-weight: 700;
        opacity: .55;
        margin-bottom: .35rem;
    }

    div[data-testid="stFileUploader"] section {
        border-radius: 16px;
        padding-top: 1.1rem;
        padding-bottom: 1.1rem;
    }

    div[data-testid="stSlider"] {
        padding-top: 0;
        padding-bottom: .08rem;
    }

    div[data-testid="stSlider"] label p {
        font-size: .82rem;
        font-weight: 600;
    }

    div[data-baseweb="slider"] {
        margin-top: -.25rem;
        margin-bottom: -.25rem;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 999px;
    }

    .compat-note {
        border: 1px solid rgba(127,127,127,.18);
        background: rgba(127,127,127,.045);
        border-radius: 12px;
        padding: .72rem .85rem;
        font-size: .82rem;
        line-height: 1.45;
        opacity: .78;
        margin-top: .75rem;
    }

    @media (max-width: 900px) {
        .block-container {padding: .8rem;}
    }
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)


SIMULATOR_CSS = """
<style>
    /* The simulator is a viewport, not a vertically scrolling dashboard. */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        height: 100vh;
        overflow: hidden;
    }

    [data-testid="stAppViewContainer"] > .main {
        overflow: hidden;
    }

    .block-container {
        height: 100vh;
        max-width: none;
        overflow: hidden;
        padding-top: .7rem;
        padding-bottom: .65rem;
    }

    /* Streamlit keys become CSS classes. Each side owns its overflow. */
    .st-key-control_panel {
        height: calc(100vh - 106px);
        overflow-y: auto;
        overflow-x: hidden;
        padding: .75rem .8rem .5rem .1rem;
        scrollbar-width: thin;
        border-top: 1px solid rgba(127,127,127,.16);
    }

    .st-key-chart_panel {
        height: calc(100vh - 106px);
        overflow: hidden;
        padding: .45rem 0 0 .15rem;
        border-top: 1px solid rgba(127,127,127,.16);
    }

    .st-key-control_panel::-webkit-scrollbar {width: 6px;}
    .st-key-control_panel::-webkit-scrollbar-thumb {
        background: rgba(127,127,127,.25);
        border-radius: 10px;
    }

    .st-key-chart_panel [data-testid="stPlotlyChart"] {
        height: calc(100vh - 148px);
    }

    .st-key-chart_panel [data-testid="stPlotlyChart"] > div,
    .st-key-chart_panel [data-testid="stPlotlyChart"] .js-plotly-plot,
    .st-key-chart_panel [data-testid="stPlotlyChart"] .plot-container {
        height: 100% !important;
    }

    @media (max-width: 900px) {
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            height: auto;
            overflow: auto;
        }
        .block-container {height: auto; overflow: visible;}
        .st-key-control_panel, .st-key-chart_panel {
            height: auto;
            overflow: visible;
        }
    }
</style>
"""


SAMPLE_PATH = Path(__file__).parent / "sample" / "simple_population.mdl"


def decode_mdl(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("The .mdl text encoding could not be read.")


def model_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def prepare_model(data: bytes, filename: str) -> tuple[ParsedModel, object, Path]:
    """Parse the uploaded Vensim file and translate it with PySD."""
    import pysd

    text = decode_mdl(data)
    metadata = parse_model_text(text, filename)

    workdir = Path(tempfile.mkdtemp(prefix="pmkk_sd_"))
    model_path = workdir / "uploaded_model.mdl"
    model_path.write_bytes(data)

    model = pysd.read_vensim(model_path)
    return metadata, model, workdir


def load_uploaded_model(data: bytes, filename: str) -> tuple[ParsedModel, object]:
    digest = model_hash(data)

    if st.session_state.get("model_digest") != digest:
        metadata, model, workdir = prepare_model(data, filename)
        st.session_state.model_digest = digest
        st.session_state.model_metadata = metadata
        st.session_state.model_object = model
        st.session_state.model_workdir = str(workdir)
        st.session_state.slider_epoch = st.session_state.get("slider_epoch", 0) + 1

    return st.session_state.model_metadata, st.session_state.model_object


def clear_model() -> None:
    for key in [
        "pending_upload",
        "model_digest",
        "model_metadata",
        "model_object",
        "model_workdir",
        "model_uploader",
    ]:
        st.session_state.pop(key, None)


def reset_sliders() -> None:
    st.session_state.slider_epoch = st.session_state.get("slider_epoch", 0) + 1


def format_number(value: float) -> str:
    value = float(value)
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{value:,.0f}"
    if absolute >= 100:
        return f"{value:,.1f}"
    if absolute >= 1:
        return f"{value:,.2f}"
    if absolute == 0:
        return "0"
    return f"{value:.4g}"


def run_model(model: object, metadata: ParsedModel, params: dict[str, float]) -> pd.DataFrame:
    output_names = [output.name for output in metadata.outputs]
    result = model.run(params=params, return_columns=output_names)
    if result.empty:
        raise RuntimeError("The model ran but returned no simulation values.")
    return result


def adaptive_grid(count: int) -> tuple[int, int]:
    """Choose a compact near-square graph grid for the right-hand viewport."""
    if count <= 1:
        cols = 1
    elif count <= 4:
        cols = 2
    elif count <= 9:
        cols = 3
    elif count <= 16:
        cols = 4
    else:
        cols = min(5, math.ceil(math.sqrt(count * 1.25)))
    return math.ceil(count / cols), cols


def build_outcome_figure(result: pd.DataFrame, metadata: ParsedModel) -> go.Figure:
    outputs = metadata.outputs
    rows, cols = adaptive_grid(len(outputs))

    titles: list[str] = []
    for output in outputs:
        final_value = result[output.name].iloc[-1]
        unit = f" {output.unit}" if output.unit else ""
        titles.append(f"{output.label} · {format_number(final_value)}{unit}")

    vertical_spacing = 0.10 if rows <= 2 else max(0.035, min(0.075, 0.20 / rows))
    horizontal_spacing = 0.08 if cols <= 2 else 0.055

    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=titles,
        vertical_spacing=vertical_spacing,
        horizontal_spacing=horizontal_spacing,
    )

    time_label = metadata.time.get("unit") or "Time"
    x_values = result.index

    for index, output in enumerate(outputs):
        row = index // cols + 1
        col = index % cols + 1
        unit = output.unit or ""

        fig.add_trace(
            go.Scatter(
                x=x_values,
                y=result[output.name],
                mode="lines",
                name=output.label,
                showlegend=False,
                hovertemplate=(
                    f"{time_label}: %{{x}}<br>"
                    + f"{output.label}: %{{y:,.4g}}"
                    + (f" {unit}" if unit else "")
                    + "<extra></extra>"
                ),
            ),
            row=row,
            col=col,
        )

        # Keep every mini-chart readable without spending space on repeated titles.
        fig.update_xaxes(
            title_text=time_label if row == rows else None,
            showgrid=False,
            zeroline=False,
            nticks=5,
            tickfont=dict(size=9),
            title_font=dict(size=9),
            row=row,
            col=col,
        )
        fig.update_yaxes(
            title_text=unit if unit else None,
            showgrid=True,
            gridcolor="rgba(127,127,127,0.13)",
            zeroline=False,
            nticks=5,
            tickfont=dict(size=9),
            title_font=dict(size=9),
            row=row,
            col=col,
        )

    fig.update_layout(
        autosize=True,
        height=700,
        margin=dict(l=24, r=12, t=36, b=18),
        hovermode="closest",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=10),
    )
    fig.update_annotations(font_size=11)
    return fig


def render_upload_screen() -> None:
    st.markdown('<div class="eyebrow">Educational simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Upload a model.<br>Explore the system.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Upload a self-contained Vensim <code>.mdl</code>. '
        'The app reads the model, creates the interactive assumptions, runs the equations with PySD, '
        'and lays out all selected outcomes automatically.</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Upload Vensim model",
        type=["mdl"],
        label_visibility="collapsed",
        key="model_uploader",
        help="Self-contained Vensim .mdl models work best. Models that rely on external files or unsupported Vensim features may require adaptation.",
    )

    c1, c2 = st.columns([1.2, 4])
    with c1:
        if SAMPLE_PATH.exists():
            st.download_button(
                "Download sample .mdl",
                data=SAMPLE_PATH.read_bytes(),
                file_name="simple_population.mdl",
                mime="text/plain",
                use_container_width=True,
            )
    with c2:
        st.markdown(
            '<div class="compat-note"><strong>Recommended:</strong> tag variables with '
            '<code>@input min=… max=… step=…</code> and <code>@output</code>. '
            'If no tags are present, the app falls back to automatic detection.</div>',
            unsafe_allow_html=True,
        )

    if uploaded is not None:
        st.session_state.pending_upload = {"name": uploaded.name, "data": uploaded.getvalue()}
        st.rerun()


def render_simulator(upload: dict) -> None:
    st.markdown(SIMULATOR_CSS, unsafe_allow_html=True)

    try:
        metadata, model = load_uploaded_model(upload["data"], upload["name"])
    except Exception as exc:
        st.error("I couldn't open this Vensim model.")
        st.exception(exc)
        if st.button("Choose another model"):
            clear_model()
            st.rerun()
        return

    header_left, header_middle, header_right = st.columns([4.6, 2.4, 1.1], vertical_alignment="center")
    with header_left:
        st.markdown('<div class="eyebrow">System Dynamics Playground</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sim-title">{metadata.name}</div>', unsafe_allow_html=True)
    with header_middle:
        time_unit = metadata.time.get("unit") or "time"
        st.markdown(
            f'<div class="sim-meta">{format_number(metadata.time["initial"])} → '
            f'{format_number(metadata.time["final"])} {time_unit} &nbsp;·&nbsp; '
            f'{len(metadata.inputs)} inputs &nbsp;·&nbsp; {len(metadata.outputs)} outcomes</div>',
            unsafe_allow_html=True,
        )
    with header_right:
        if st.button("Change model", use_container_width=True):
            clear_model()
            st.rerun()

    controls_col, graph_col = st.columns([0.29, 0.71], gap="medium")

    params: dict[str, float] = {}
    with controls_col:
        with st.container(key="control_panel"):
            title_col, reset_col = st.columns([2.2, 1], vertical_alignment="center")
            with title_col:
                st.markdown('<div class="section-title">Assumptions</div>', unsafe_allow_html=True)
            with reset_col:
                st.button("Reset", on_click=reset_sliders, use_container_width=True)

            epoch = st.session_state.get("slider_epoch", 0)
            for item in metadata.inputs:
                label = item.label
                if item.unit:
                    label = f"{label} · {item.unit}"

                params[item.name] = st.slider(
                    label,
                    min_value=float(item.min),
                    max_value=float(item.max),
                    value=float(item.default),
                    step=float(item.step),
                    key=f"slider_{epoch}_{item.name}",
                )

            if not metadata.inputs:
                st.caption("No interactive numeric assumptions were detected in this model.")

    with graph_col:
        with st.container(key="chart_panel"):
            st.markdown('<div class="section-title">Outcomes</div>', unsafe_allow_html=True)
            try:
                result = run_model(model, metadata, params)
            except Exception as exc:
                st.error("The model loaded, but the simulation could not run with the current settings.")
                st.exception(exc)
                return

            figure = build_outcome_figure(result, metadata)
            st.plotly_chart(
                figure,
                use_container_width=True,
                config={
                    "displayModeBar": False,
                    "responsive": True,
                    "scrollZoom": False,
                },
            )


if "pending_upload" not in st.session_state:
    render_upload_screen()
else:
    render_simulator(st.session_state.pending_upload)

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from model_parser import ParsedModel, parse_model_text


st.set_page_config(
    page_title="PMKK System Dynamics Simulator",
    page_icon="↗",
    layout="wide",
    initial_sidebar_state="collapsed",
)


CUSTOM_CSS = """
<style>
    [data-testid="stHeader"] {background: rgba(255,255,255,0);}
    [data-testid="stToolbar"] {visibility: hidden; height: 0; position: fixed;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .block-container {
        max-width: 1240px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

    .eyebrow {
        font-size: .78rem;
        letter-spacing: .11em;
        text-transform: uppercase;
        font-weight: 700;
        opacity: .58;
        margin-bottom: .5rem;
    }

    .hero-title {
        font-size: clamp(2rem, 4vw, 3.65rem);
        line-height: 1.02;
        letter-spacing: -.045em;
        font-weight: 720;
        margin: 0 0 .8rem 0;
    }

    .hero-copy {
        max-width: 720px;
        font-size: 1.05rem;
        line-height: 1.7;
        opacity: .72;
        margin-bottom: 1.7rem;
    }

    .model-strip {
        border: 1px solid rgba(127,127,127,.22);
        border-radius: 14px;
        padding: .8rem 1rem;
        margin-bottom: 1.25rem;
        font-size: .9rem;
        opacity: .78;
    }

    .section-title {
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: .1em;
        font-weight: 700;
        opacity: .58;
        margin-bottom: .85rem;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(127,127,127,.20);
        border-radius: 14px;
        padding: .75rem .9rem;
    }

    div[data-testid="stFileUploader"] section {
        border-radius: 18px;
        padding-top: 1.3rem;
        padding-bottom: 1.3rem;
    }

    div[data-testid="stSlider"] {padding-bottom: .35rem;}
    .stButton > button {border-radius: 999px;}
    .stDownloadButton > button {border-radius: 999px;}

    @media (max-width: 780px) {
        .block-container {padding-top: 1rem;}
        .hero-title {font-size: 2.25rem;}
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


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
    """Parse the model, translate it with PySD, and keep it for this session."""
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


def render_upload_screen() -> None:
    st.markdown('<div class="eyebrow">Educational simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Explore a system.<br>Change one assumption.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Upload a self-contained Vensim <code>.mdl</code> model. '
        'The simulator reads the equations, exposes the selected assumptions, and shows how the system behaves over time.</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Upload Vensim model",
        type=["mdl"],
        label_visibility="collapsed",
        key="model_uploader",
        help="Use a self-contained Vensim .mdl model. External Excel/VDF data sources are not supported in this educational version.",
    )

    c1, c2 = st.columns([1, 4])
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
        st.caption("Tip: add `@input` and `@output` inside Vensim variable comments to control what appears in the simulator.")

    if uploaded is not None:
        st.session_state.pending_upload = {
            "name": uploaded.name,
            "data": uploaded.getvalue(),
        }
        st.rerun()


def render_simulator(upload: dict) -> None:
    try:
        metadata, model = load_uploaded_model(upload["data"], upload["name"])
    except Exception as exc:
        st.error("I couldn't open this Vensim model.")
        st.exception(exc)
        if st.button("Choose another model"):
            st.session_state.pop("pending_upload", None)
            st.rerun()
        return

    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown('<div class="eyebrow">System Dynamics Playground</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="hero-title">{metadata.name}</div>', unsafe_allow_html=True)
    with top_right:
        st.write("")
        if st.button("Change model", use_container_width=True):
            for key in [
                "pending_upload",
                "model_digest",
                "model_metadata",
                "model_object",
                "model_workdir",
                "model_uploader",
            ]:
                st.session_state.pop(key, None)
            st.rerun()

    time_unit = metadata.time.get("unit") or "time"
    st.markdown(
        f'<div class="model-strip">Simulation: <strong>{format_number(metadata.time["initial"])}</strong> → '
        f'<strong>{format_number(metadata.time["final"])}</strong> {time_unit} &nbsp;·&nbsp; '
        f'{len(metadata.inputs)} interactive input(s) &nbsp;·&nbsp; {len(metadata.outputs)} output(s)</div>',
        unsafe_allow_html=True,
    )

    controls, results_panel = st.columns([0.32, 0.68], gap="large")

    params: dict[str, float] = {}
    with controls:
        st.markdown('<div class="section-title">Assumptions</div>', unsafe_allow_html=True)

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

        st.button("Reset assumptions", on_click=reset_sliders, use_container_width=True)
        st.caption("The simulation uses only the equations contained in the uploaded Vensim model.")

    try:
        result = run_model(model, metadata, params)
    except Exception as exc:
        with results_panel:
            st.error("The model loaded, but the simulation could not run with the current settings.")
            st.exception(exc)
        return

    with results_panel:
        st.markdown('<div class="section-title">Outcomes</div>', unsafe_allow_html=True)

        metric_columns = st.columns(min(len(metadata.outputs), 3))
        for index, output in enumerate(metadata.outputs[:3]):
            final_value = result[output.name].iloc[-1]
            initial_value = result[output.name].iloc[0]
            delta = final_value - initial_value
            unit_suffix = f" {output.unit}" if output.unit else ""
            with metric_columns[index]:
                st.metric(
                    output.label,
                    f"{format_number(final_value)}{unit_suffix}",
                    f"{format_number(delta)} vs start",
                    delta_color="off",
                    border=False,
                )

        for output in metadata.outputs:
            st.markdown(f"#### {output.label}")
            chart_data = result[[output.name]].rename(columns={output.name: output.label})
            st.line_chart(chart_data, use_container_width=True, height=260)
            if output.unit:
                st.caption(output.unit)


if "pending_upload" not in st.session_state:
    render_upload_screen()
else:
    render_simulator(st.session_state.pending_upload)

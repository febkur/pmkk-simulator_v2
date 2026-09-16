from __future__ import annotations

import hashlib
import math
import re
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
    [data-testid="stHeader"] {background: transparent; height: 0;}
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
        font-size: .70rem;
        line-height: 1.35;
        letter-spacing: .035em;
        text-transform: none;
        font-weight: 650;
        opacity: .62;
        margin: 0 auto .3rem auto;
        max-width: 40rem;
        text-align: center;
    }

    .sim-page-title {
        width: 100%;
        text-align: center;
        font-size: clamp(1.05rem, 1.45vw, 1.38rem);
        line-height: 1.25;
        letter-spacing: -.012em;
        font-weight: 720;
        opacity: .94;
        margin: .15rem auto .8rem auto;
        padding: 0 10rem;
        box-sizing: border-box;
    }

    @media (max-width: 900px) {
        .sim-page-title {
            padding: 0 1rem;
            font-size: 1rem;
        }
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
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)


LANDING_CSS = """
<style>
    /* Landing page only */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        background: #07111d !important;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 50% -15%, rgba(34, 211, 238, .09), transparent 34%),
            linear-gradient(180deg, #07111d 0%, #09131f 100%) !important;
    }

    .block-container {
        max-width: 1180px;
        padding-top: 0 !important;
    }

    .landing-spacer {
        height: clamp(2.2rem, 7vh, 4.8rem);
    }

    /* Rectangle 1: title */
    .landing-title-card {
        position: relative;
        width: min(860px, 90vw);
        margin: 0 auto 2.2rem;
        padding: 1.45rem 2.4rem 1.55rem;
        text-align: center;
        border: 1px solid rgba(103, 232, 249, .42);
        border-radius: 24px;
        background: rgba(10, 24, 39, .78);
        box-shadow:
            0 20px 55px rgba(0, 0, 0, .28),
            inset 0 1px 0 rgba(255, 255, 255, .035);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }

    .landing-title-card::after {
        content: "";
        position: absolute;
        left: 12%;
        right: 12%;
        bottom: -1px;
        height: 1px;
        background: linear-gradient(90deg, transparent, #67e8f9, transparent);
        opacity: .7;
    }

    .landing-title {
        margin: 0;
        color: #f8fafc;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: clamp(1.6rem, 2.7vw, 2.35rem);
        line-height: 1.2;
        letter-spacing: -.035em;
        font-weight: 650;
        text-shadow: 0 0 24px rgba(103, 232, 249, .035);
    }

    /* Rectangle 2: uploader */
    .st-key-landing_upload {
        width: min(390px, 84vw);
        margin: 0 auto 1.15rem;
    }

    .st-key-landing_upload [data-testid="stFileUploader"] > label {
        display: none;
    }

    .st-key-landing_upload section {
        min-height: 118px;
        padding: 1rem !important;
        border: 1px solid rgba(103, 232, 249, .32) !important;
        border-radius: 18px !important;
        background: rgba(12, 27, 43, .88) !important;
        box-shadow: 0 14px 38px rgba(0, 0, 0, .20);
        transition: border-color .18s ease, background .18s ease, transform .18s ease;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }

    .st-key-landing_upload [data-testid="stFileUploaderDropzone"] {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: .55rem !important;
        text-align: center !important;
    }

    .st-key-landing_upload [data-testid="stFileUploaderDropzoneInstructions"] {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }

    .st-key-landing_upload section:hover {
        border-color: rgba(103, 232, 249, .72) !important;
        background: rgba(14, 34, 53, .95) !important;
        transform: translateY(-1px);
    }

    .st-key-landing_upload [data-testid="stFileUploaderDropzoneInstructions"] span {
        font-size: 0 !important;
    }

    .st-key-landing_upload [data-testid="stFileUploaderDropzoneInstructions"] span::after {
        content: "Upload file .mdl";
        display: inline-block;
        font-size: .94rem;
        font-weight: 650;
        letter-spacing: -.01em;
        color: #e6f7fb;
    }

    .st-key-landing_upload [data-testid="stFileUploaderDropzoneInstructions"] small {
        display: none !important;
    }

    .st-key-landing_upload button {
        min-height: 42px !important;
        padding: 0 1.05rem !important;
        border: 1px solid rgba(103, 232, 249, .45) !important;
        border-radius: 12px !important;
        background: #0e7490 !important;
        color: #ffffff !important;
        font-weight: 650 !important;
        box-shadow: none !important;
    }

    .st-key-landing_upload button:hover {
        border-color: #67e8f9 !important;
        background: #0b829f !important;
        color: white !important;
    }

    /* Rectangle 3: sample model */
    .st-key-sample_download {
        width: min(300px, 76vw);
        margin: .65rem auto 0;
    }

    .st-key-sample_download .stDownloadButton > button {
        width: 100%;
        min-height: 56px;
        border: 1px solid rgba(148, 163, 184, .24) !important;
        border-radius: 16px !important;
        background: rgba(12, 27, 43, .72) !important;
        color: #cbd5e1 !important;
        font-weight: 600 !important;
        letter-spacing: -.01em;
        box-shadow: 0 10px 28px rgba(0, 0, 0, .14);
        transition: border-color .18s ease, color .18s ease, background .18s ease, transform .18s ease;
    }

    .st-key-sample_download .stDownloadButton > button p {
        color: #cbd5e1 !important;
    }

    .st-key-sample_download .stDownloadButton > button:hover {
        border-color: rgba(103, 232, 249, .52) !important;
        background: rgba(14, 34, 53, .92) !important;
        color: #f8fafc !important;
        transform: translateY(-1px);
    }

    .st-key-sample_download .stDownloadButton > button:hover p {
        color: #f8fafc !important;
    }

    @media (max-width: 900px) {
        .block-container {padding-left: .9rem; padding-right: .9rem;}
        .landing-spacer {height: 1.8rem;}
        .landing-title-card {
            padding: 1.15rem 1.15rem 1.25rem;
            border-radius: 20px;
            margin-bottom: 1.55rem;
        }
        .landing-title {
            font-size: clamp(1.35rem, 6vw, 1.85rem);
        }
    }
</style>
"""


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
        padding: .45rem .15rem .6rem .15rem;
        border-top: 1px solid rgba(127,127,127,.16);
    }

    .graph-filter-caption {
        font-size: .68rem;
        letter-spacing: .055em;
        text-transform: uppercase;
        font-weight: 700;
        opacity: .55;
        margin: .15rem 0 .15rem 0;
    }

    .directorate-code {
        text-align: center;
        font-size: .82rem;
        line-height: 1.15;
        font-weight: 760;
        letter-spacing: .015em;
        margin: .05rem 0 .1rem 0;
    }

    .directorate-subtitle {
        min-height: 2.25rem;
        text-align: center;
        font-size: .58rem;
        line-height: 1.25;
        opacity: .55;
        margin: 0 0 .35rem 0;
    }

    .directorate-empty {
        text-align: center;
        font-size: .65rem;
        line-height: 1.4;
        opacity: .45;
        padding: 1.25rem .3rem;
    }

    .indicator-card-title {
        font-size: .68rem;
        line-height: 1.25;
        text-align: center;
        font-weight: 700;
        margin: .15rem .15rem 0;
    }

    .indicator-card-meta {
        font-size: .58rem;
        line-height: 1.25;
        text-align: center;
        opacity: .58;
        margin: .12rem .15rem .15rem;
    }

    /* Keep controls compact enough for five side-by-side directorate columns. */
    .st-key-chart_panel [data-testid="stMultiSelect"] label p {
        font-size: .62rem;
        font-weight: 650;
    }

    .st-key-chart_panel [data-baseweb="tag"] {
        max-width: 100%;
        font-size: .58rem;
    }

    .st-key-chart_panel [data-testid="stPlotlyChart"] {
        margin-top: -.15rem;
        margin-bottom: .15rem;
    }

    .st-key-control_panel::-webkit-scrollbar {width: 6px;}
    .st-key-control_panel::-webkit-scrollbar-thumb {
        background: rgba(127,127,127,.25);
        border-radius: 10px;
    }

    .st-key-chart_panel [data-testid="stPlotlyChart"] {
        width: 100%;
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
MAX_SAVED_SCENARIOS = 3

DIRECTORATE_ORDER = ["PKKS", "KJS", "NAKER", "KSE", "KUMKM"]
DIRECTORATE_LABELS = {
    "PKKS": "Penanggulangan Kemiskinan dan Kesejahteraan Sosial (PKKS)",
    "KJS": "Kependudukan dan Jaminan Sosial (KJS)",
    "NAKER": "Ketenagakerjaan (Naker)",
    "KSE": "Kemandirian Sosial dan Ekonomi (KSE)",
    "KUMKM": "Koperasi dan UMKM (KUMKM)",
    "__UNGROUPED__": "Belum dikelompokkan",
}

DIRECTORATE_SHORT_LABELS = {
    "PKKS": "PKKS",
    "KJS": "KJS",
    "NAKER": "Naker",
    "KSE": "KSE",
    "KUMKM": "KUMKM",
}

DIRECTORATE_SUBTITLES = {
    "PKKS": "Kemiskinan & Kesejahteraan Sosial",
    "KJS": "Kependudukan & Jaminan Sosial",
    "NAKER": "Ketenagakerjaan",
    "KSE": "Kemandirian Sosial & Ekonomi",
    "KUMKM": "Koperasi & UMKM",
}


CATALOG_DIRECTORATE_ALIASES = {
    "PKKS": "PKKS",
    "PENANGGULANGAN KEMISKINAN DAN KESEJAHTERAAN SOSIAL": "PKKS",
    "KJS": "KJS",
    "KEPENDUDUKAN DAN JAMINAN SOSIAL": "KJS",
    "NAKER": "NAKER",
    "KETENAGAKERJAAN": "NAKER",
    "KSE": "KSE",
    "KEMANDIRIAN SOSIAL DAN EKONOMI": "KSE",
    "KEMANDIRIAN SOSIAL EKONOMI": "KSE",
    "KUMKM": "KUMKM",
    "KOPERASI DAN UMKM": "KUMKM",
    "KOPERASI-UMKM": "KUMKM",
    "KOPERASI UMKM": "KUMKM",
}


def _catalog_directorate_code(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = re.sub(r"\s+", " ", str(value).strip()).upper().replace("_", " ")
    return CATALOG_DIRECTORATE_ALIASES.get(text)


def _catalog_indicator_id(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    match = re.search(r"\d+", str(value))
    return match.group(0) if match else None


def _find_indicator_catalog_path() -> Path | None:
    base = Path(__file__).resolve().parent
    candidates = [
        base / "data" / "IndikatorPMKK.xlsx",
        base / "IndikatorPMKK.xlsx",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = list(base.rglob("IndikatorPMKK.xlsx"))
    return matches[0] if matches else None


@st.cache_data(show_spinner=False)
def load_indicator_catalog() -> tuple[dict[tuple[str, str], str], str | None]:
    """Load official indicator names from the Excel sheet 1_General."""
    path = _find_indicator_catalog_path()
    if path is None:
        return {}, None

    frame = pd.read_excel(
        path,
        sheet_name="1_General",
        header=None,
        usecols="B:D",
    )

    catalog: dict[tuple[str, str], str] = {}
    current_directorate: str | None = None

    for directorate_raw, number_raw, indicator_name in frame.itertuples(index=False, name=None):
        row_directorate = _catalog_directorate_code(directorate_raw)
        if row_directorate:
            current_directorate = row_directorate

        indicator_id = _catalog_indicator_id(number_raw)
        if (
            current_directorate
            and indicator_id
            and indicator_name is not None
            and not pd.isna(indicator_name)
        ):
            catalog[(current_directorate, indicator_id)] = str(indicator_name).strip()

    return catalog, str(path)


def official_indicator_name(output, catalog: dict[tuple[str, str], str]) -> str:
    directorate = getattr(output, "directorate", None)
    indicator = getattr(output, "indicator", None)
    if directorate and indicator:
        official = catalog.get((str(directorate), str(indicator)))
        if official:
            return official
    return output.label


def official_indicator_dropdown_label(
    output,
    catalog: dict[tuple[str, str], str],
) -> str:
    name = official_indicator_name(output, catalog)
    indicator = getattr(output, "indicator", None)
    directorate = getattr(output, "directorate", None)

    if directorate and indicator and (str(directorate), str(indicator)) in catalog:
        return f"{indicator} — {name}"
    if indicator:
        return f"{indicator} — {name} · belum cocok dengan Excel"
    return f"{name} · belum diberi indicator="


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
        st.session_state.saved_scenarios = []
        st.session_state.scenario_counter = 0
        st.session_state.active_param_override = {}
        st.session_state.baseline_result = None
        st.session_state.baseline_digest = None

    return st.session_state.model_metadata, st.session_state.model_object


def clear_model() -> None:
    for key in [
        "pending_upload",
        "model_digest",
        "model_metadata",
        "model_object",
        "model_workdir",
        "model_uploader",
        "saved_scenarios",
        "scenario_counter",
        "active_param_override",
        "baseline_result",
        "baseline_digest",
    ]:
        st.session_state.pop(key, None)


def reset_sliders() -> None:
    st.session_state.active_param_override = {}
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


def params_match(left: dict[str, float], right: dict[str, float]) -> bool:
    """True when two slider configurations are effectively identical."""
    if set(left) != set(right):
        return False
    return all(
        math.isclose(float(left[key]), float(right[key]), rel_tol=1e-9, abs_tol=1e-12)
        for key in left
    )


def delta_from_baseline(current: float, baseline: float) -> str:
    """A neutral higher/lower comparison for graph titles."""
    current = float(current)
    baseline = float(baseline)
    difference = current - baseline

    if math.isclose(difference, 0.0, rel_tol=1e-9, abs_tol=1e-12):
        return "≈ baseline"

    arrow = "↑" if difference > 0 else "↓"
    if not math.isclose(baseline, 0.0, abs_tol=1e-12):
        percentage = abs(difference / baseline) * 100
        return f"{arrow} {percentage:.1f}% vs baseline"

    return f"{arrow} {format_number(abs(difference))} vs baseline"


def find_matching_scenario(params: dict[str, float], scenarios: list[dict]) -> str | None:
    for scenario in scenarios:
        if params_match(params, scenario.get("params", {})):
            return str(scenario.get("name", "Scenario"))
    return None


def load_saved_scenario(params: dict[str, float]) -> None:
    st.session_state.active_param_override = dict(params)
    st.session_state.slider_epoch = st.session_state.get("slider_epoch", 0) + 1


def _normalize_component_name(name: str) -> str:
    """Normalize Vensim/PySD names for safe matching.

    Vensim allows quoted names such as "Jumlah Perusahaan Korporasi (Unit)".
    The lightweight .mdl parser removes those display quotes, while PySD may
    keep them in its namespace. Matching through the namespace avoids sending
    an invalid component name to model.run().
    """
    text = str(name).strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def _namespace_dict(model: object) -> dict[str, str]:
    namespace = getattr(model, "namespace", None)
    if callable(namespace):
        namespace = namespace()
    if not namespace:
        namespace = getattr(model, "_namespace", None)
    return dict(namespace or {})


def _resolve_component_name(model: object, requested_name: str) -> str:
    """Return the exact PySD-recognized real component name.

    We intentionally resolve against the namespace generated by PySD instead
    of assuming that text parsed from the .mdl is byte-for-byte identical.
    This is especially important for quoted Vensim variable names.
    """
    namespace = _namespace_dict(model)
    if not namespace:
        return requested_name

    # Fast path: exact real-name or Python-safe-name match.
    if requested_name in namespace:
        return requested_name
    if requested_name in namespace.values():
        return requested_name

    target = _normalize_component_name(requested_name)
    for real_name, py_name in namespace.items():
        if _normalize_component_name(real_name) == target:
            return real_name
        if _normalize_component_name(py_name) == target:
            return py_name

    # Extra fallback for Vensim names where quoting is semantically irrelevant.
    quoted = f'"{requested_name.strip(chr(34))}"'
    if quoted in namespace:
        return quoted

    raise NameError(
        f"Variable '{requested_name}' was found in the .mdl text but could not "
        "be matched to the translated PySD model."
    )


def _find_result_column(result: pd.DataFrame, *candidates: str) -> str | None:
    for candidate in candidates:
        if candidate in result.columns:
            return candidate

    normalized_candidates = {_normalize_component_name(candidate) for candidate in candidates}
    for column in result.columns:
        if _normalize_component_name(str(column)) in normalized_candidates:
            return column
    return None


def run_model(model: object, metadata: ParsedModel, params: dict[str, float]) -> pd.DataFrame:
    # Resolve the user-facing .mdl names to the exact names PySD generated.
    # This fixes quoted Vensim names such as "Variable (Unit)".
    resolved_params: dict[str, float] = {}
    for name, value in params.items():
        resolved_params[_resolve_component_name(model, name)] = value

    requested_outputs: list[str] = []
    output_pairs: list[tuple[str, str]] = []
    for output in metadata.outputs:
        resolved = _resolve_component_name(model, output.name)
        requested_outputs.append(resolved)
        output_pairs.append((output.name, resolved))

    result = model.run(params=resolved_params, return_columns=requested_outputs)
    if result.empty:
        raise RuntimeError("The model ran but returned no simulation values.")

    # Always return columns using the clean names expected by the UI, regardless
    # of whether PySD returned quoted real names or Python-safe names.
    clean = pd.DataFrame(index=result.index)
    for display_name, resolved_name in output_pairs:
        column = _find_result_column(result, display_name, resolved_name)
        if column is None:
            raise RuntimeError(
                f"The model ran, but output '{display_name}' was not returned by PySD."
            )
        clean[display_name] = result[column]

    return clean


def group_outputs_by_directorate(outputs: list) -> dict[str, list]:
    """Group @output variables using directorate tags from Vensim comments."""
    grouped: dict[str, list] = {}
    for output in outputs:
        code = getattr(output, "directorate", None) or "__UNGROUPED__"
        grouped.setdefault(code, []).append(output)
    return grouped


def ordered_directorates(grouped: dict[str, list]) -> list[str]:
    """Keep PMKK directorates in a stable, familiar order."""
    ordered = [code for code in DIRECTORATE_ORDER if code in grouped]
    extras = sorted(
        code for code in grouped
        if code not in DIRECTORATE_ORDER and code != "__UNGROUPED__"
    )
    if "__UNGROUPED__" in grouped:
        extras.append("__UNGROUPED__")
    return ordered + extras


def directorate_display(code: str) -> str:
    return DIRECTORATE_LABELS.get(code, code)


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


def build_outcome_figure(
    active_result: pd.DataFrame,
    baseline_result: pd.DataFrame,
    metadata: ParsedModel,
    saved_scenarios: list[dict],
    active_label: str,
    active_matches_saved: bool,
    outputs: list | None = None,
) -> go.Figure:
    """Small-multiple outcome charts with baseline and scenario comparison."""
    outputs = outputs or metadata.outputs
    rows, cols = adaptive_grid(len(outputs))

    titles: list[str] = []
    for output in outputs:
        final_value = active_result[output.name].iloc[-1]
        baseline_value = baseline_result[output.name].iloc[-1]
        unit = f" {output.unit}" if output.unit else ""
        delta = delta_from_baseline(final_value, baseline_value)
        titles.append(
            f"{output.label}<br>"
            f"<span style='font-size:9px;opacity:.72'>"
            f"{format_number(final_value)}{unit} · {delta}</span>"
        )

    # Keep subplot titles, x-axis ticks, and the next row from colliding.
    # More rows get a taller canvas and controlled vertical gaps.
    if rows <= 1:
        vertical_spacing = 0.08
    elif rows == 2:
        vertical_spacing = 0.18
    elif rows == 3:
        vertical_spacing = 0.145
    elif rows == 4:
        vertical_spacing = 0.105
    else:
        vertical_spacing = min(0.09, 0.34 / max(rows - 1, 1))

    horizontal_spacing = 0.09 if cols <= 2 else 0.065

    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=titles,
        vertical_spacing=vertical_spacing,
        horizontal_spacing=horizontal_spacing,
    )

    time_label = metadata.time.get("unit") or "Time"
    # Smooth only the visual connection between simulated time points.
    # This does NOT modify the values returned by the Vensim/PySD model.
    spline_shape = "spline"
    spline_smoothing = 0.55

    baseline_style = dict(
        color="#64748b",
        width=1.7,
        dash="dash",
        shape=spline_shape,
        smoothing=spline_smoothing,
    )
    active_style = dict(
        color="#22d3ee",
        width=2.5,
        shape=spline_shape,
        smoothing=spline_smoothing,
    )
    saved_styles = [
        dict(
            color="#a78bfa",
            width=1.9,
            dash="dot",
            shape=spline_shape,
            smoothing=spline_smoothing,
        ),
        dict(
            color="#34d399",
            width=1.9,
            dash="dashdot",
            shape=spline_shape,
            smoothing=spline_smoothing,
        ),
        dict(
            color="#f59e0b",
            width=1.9,
            dash="longdash",
            shape=spline_shape,
            smoothing=spline_smoothing,
        ),
    ]

    for index, output in enumerate(outputs):
        row = index // cols + 1
        col = index % cols + 1
        unit = output.unit or ""

        # Baseline is always present so every outcome has a stable reference.
        fig.add_trace(
            go.Scatter(
                x=baseline_result.index,
                y=baseline_result[output.name],
                mode="lines",
                name="Baseline",
                legendgroup="baseline",
                showlegend=index == 0,
                line=baseline_style,
                hovertemplate=(
                    "Baseline<br>"
                    f"{time_label}: %{{x}}<br>"
                    + f"{output.label}: %{{y:,.4g}}"
                    + (f" {unit}" if unit else "")
                    + "<extra></extra>"
                ),
            ),
            row=row,
            col=col,
        )

        # Saved scenarios stay visible for comparison.
        for scenario_index, scenario in enumerate(saved_scenarios):
            scenario_result = scenario["result"]
            style = saved_styles[scenario_index % len(saved_styles)]
            fig.add_trace(
                go.Scatter(
                    x=scenario_result.index,
                    y=scenario_result[output.name],
                    mode="lines",
                    name=scenario["name"],
                    legendgroup=scenario["name"],
                    showlegend=index == 0,
                    line=style,
                    hovertemplate=(
                        f"{scenario['name']}<br>"
                        f"{time_label}: %{{x}}<br>"
                        + f"{output.label}: %{{y:,.4g}}"
                        + (f" {unit}" if unit else "")
                        + "<extra></extra>"
                    ),
                ),
                row=row,
                col=col,
            )

        # Do not duplicate the same line after the active setting has just been saved.
        if not active_matches_saved:
            fig.add_trace(
                go.Scatter(
                    x=active_result.index,
                    y=active_result[output.name],
                    mode="lines",
                    name=active_label,
                    legendgroup="active",
                    showlegend=index == 0,
                    line=active_style,
                    hovertemplate=(
                        f"{active_label}<br>"
                        f"{time_label}: %{{x}}<br>"
                        + f"{output.label}: %{{y:,.4g}}"
                        + (f" {unit}" if unit else "")
                        + "<extra></extra>"
                    ),
                ),
                row=row,
                col=col,
            )

        fig.update_xaxes(
            title_text=time_label if row == rows else None,
            showgrid=False,
            zeroline=False,
            nticks=5,
            tickfont=dict(size=8),
            title_font=dict(size=9),
            automargin=True,
            ticklabelstandoff=4,
            row=row,
            col=col,
        )
        fig.update_yaxes(
            title_text=unit if unit else None,
            showgrid=True,
            gridcolor="rgba(127,127,127,0.13)",
            zeroline=False,
            nticks=5,
            tickfont=dict(size=8),
            title_font=dict(size=9),
            automargin=True,
            title_standoff=7,
            row=row,
            col=col,
        )

    # A fixed 700px canvas was too short for 3+ rows and caused labels to collide.
    # Scale the canvas with the number of output rows instead.
    figure_height = max(700, 260 * rows + 150)

    fig.update_layout(
        autosize=True,
        height=figure_height,
        margin=dict(l=38, r=20, t=120, b=34),
        hovermode="closest",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.105,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
            bgcolor="rgba(15,23,42,0.78)",
            bordercolor="rgba(148,163,184,0.18)",
            borderwidth=1,
            itemsizing="constant",
        ),
    )
    fig.update_annotations(
        font_size=10,
        yshift=10,
    )
    return fig



def build_single_output_figure(
    output,
    active_result: pd.DataFrame,
    baseline_result: pd.DataFrame,
    metadata: ParsedModel,
    saved_scenarios: list[dict],
    active_label: str,
    active_matches_saved: bool,
    display_label: str | None = None,
) -> go.Figure:
    """Compact one-indicator chart for one directorate column."""
    fig = go.Figure()
    time_label = metadata.time.get("unit") or "Time"
    chart_label = display_label or output.label

    spline_shape = "spline"
    spline_smoothing = 0.55

    fig.add_trace(
        go.Scatter(
            x=baseline_result.index,
            y=baseline_result[output.name],
            mode="lines",
            name="Baseline",
            line=dict(
                color="#64748b",
                width=1.4,
                dash="dash",
                shape=spline_shape,
                smoothing=spline_smoothing,
            ),
            hovertemplate=(
                "Baseline<br>"
                f"{time_label}: %{{x}}<br>"
                f"{chart_label}: %{{y:,.4g}}"
                + (f" {output.unit}" if output.unit else "")
                + "<extra></extra>"
            ),
        )
    )

    saved_styles = [
        dict(color="#a78bfa", width=1.55, dash="dot"),
        dict(color="#34d399", width=1.55, dash="dashdot"),
        dict(color="#f59e0b", width=1.55, dash="longdash"),
    ]

    for scenario_index, scenario in enumerate(saved_scenarios):
        style = saved_styles[scenario_index % len(saved_styles)]
        fig.add_trace(
            go.Scatter(
                x=scenario["result"].index,
                y=scenario["result"][output.name],
                mode="lines",
                name=scenario["name"],
                line=dict(
                    **style,
                    shape=spline_shape,
                    smoothing=spline_smoothing,
                ),
                hovertemplate=(
                    f"{scenario['name']}<br>"
                    f"{time_label}: %{{x}}<br>"
                    f"{chart_label}: %{{y:,.4g}}"
                    + (f" {output.unit}" if output.unit else "")
                    + "<extra></extra>"
                ),
            )
        )

    if not active_matches_saved:
        fig.add_trace(
            go.Scatter(
                x=active_result.index,
                y=active_result[output.name],
                mode="lines",
                name=active_label,
                line=dict(
                    color="#22d3ee",
                    width=2.0,
                    shape=spline_shape,
                    smoothing=spline_smoothing,
                ),
                hovertemplate=(
                    f"{active_label}<br>"
                    f"{time_label}: %{{x}}<br>"
                    f"{chart_label}: %{{y:,.4g}}"
                    + (f" {output.unit}" if output.unit else "")
                    + "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        height=215,
        margin=dict(l=8, r=6, t=5, b=20),
        showlegend=False,
        hovermode="closest",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=8),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        nticks=3,
        tickfont=dict(size=7),
        automargin=True,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(127,127,127,0.12)",
        zeroline=False,
        nticks=4,
        tickfont=dict(size=7),
        automargin=True,
    )
    return fig


def graph_legend_html(saved_scenarios: list[dict], active_label: str, active_matches_saved: bool) -> str:
    """One shared legend for all five directorate columns."""
    items = [
        '<span style="display:inline-flex;align-items:center;gap:.3rem">'
        '<span style="width:18px;border-top:2px dashed #64748b"></span>Baseline</span>'
    ]
    saved_colors = ["#a78bfa", "#34d399", "#f59e0b"]
    for index, scenario in enumerate(saved_scenarios):
        color = saved_colors[index % len(saved_colors)]
        items.append(
            '<span style="display:inline-flex;align-items:center;gap:.3rem">'
            f'<span style="width:18px;border-top:2px dashed {color}"></span>'
            f'{scenario["name"]}</span>'
        )
    if not active_matches_saved:
        items.append(
            '<span style="display:inline-flex;align-items:center;gap:.3rem">'
            '<span style="width:18px;border-top:2px solid #22d3ee"></span>'
            f'{active_label}</span>'
        )
    return (
        '<div style="display:flex;justify-content:center;align-items:center;'
        'gap:.85rem;flex-wrap:wrap;font-size:.63rem;opacity:.76;'
        'margin:.05rem 0 .55rem 0;">'
        + "".join(items)
        + "</div>"
    )


def render_upload_screen() -> None:
    # Minimal opening screen: identity, upload, and one sample model.
    st.markdown(LANDING_CSS, unsafe_allow_html=True)
    st.markdown('<div class="landing-spacer"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="landing-title-card">
            <div class="landing-title">
                Website Dynamic System<br>
                Deputi Bidang<br>
                Pemberdayaan Masyarakat, Kependudukan,<br>
                dan Ketenagakerjaan
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1.3, 1, 1.3])
    with center:
        with st.container(key="landing_upload"):
            uploaded = st.file_uploader(
                "Upload file .mdl dynamic system",
                type=["mdl"],
                label_visibility="collapsed",
                key="model_uploader",
                help="Upload a self-contained Vensim .mdl model.",
            )

        if SAMPLE_PATH.exists():
            with st.container(key="sample_download"):
                st.download_button(
                    "Sample file .mdl",
                    data=SAMPLE_PATH.read_bytes(),
                    file_name="simple_population.mdl",
                    mime="text/plain",
                    use_container_width=True,
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
        st.caption(str(exc).strip())
        with st.expander("Technical details"):
            st.code(f"{type(exc).__name__}: {exc}")
        if st.button("Ganti model"):
            clear_model()
            st.rerun()
        return

    saved_scenarios = st.session_state.setdefault("saved_scenarios", [])
    st.session_state.setdefault("scenario_counter", 0)
    st.session_state.setdefault("active_param_override", {})

    # Full-width title: centered relative to the entire website.
    st.markdown(
        '<div class="sim-page-title">Dynamic System lingkup Deputi Bidang '
        'Pemberdayaan Masyarakat, Kependudukan, dan Ketenagakerjaan</div>',
        unsafe_allow_html=True,
    )

    header_left, header_middle, header_right = st.columns([4.6, 2.4, 1.1], vertical_alignment="center")
    with header_left:
        st.markdown(f'<div class="sim-title">{metadata.name}</div>', unsafe_allow_html=True)
    with header_middle:
        st.markdown(
            f'<div class="sim-meta" style="text-align:center;">'
            f'{format_number(metadata.time["initial"])} - '
            f'{format_number(metadata.time["final"])}</div>',
            unsafe_allow_html=True,
        )
    with header_right:
        if st.button("Ganti model", use_container_width=True):
            clear_model()
            st.rerun()

    controls_col, graph_col = st.columns([0.29, 0.71], gap="medium")

    indicator_catalog, indicator_catalog_path = load_indicator_catalog()

    params: dict[str, float] = {}
    save_requested = False

    with controls_col:
        with st.container(key="control_panel"):
            title_col, reset_col = st.columns([2.2, 1], vertical_alignment="center")
            with title_col:
                st.markdown('<div class="section-title">Assumptions</div>', unsafe_allow_html=True)
            with reset_col:
                st.button("Reset", on_click=reset_sliders, use_container_width=True)

            # This container is declared before the sliders so scenario actions remain
            # easy to reach even in models with many inputs. It is populated below.
            scenario_area = st.container()

            epoch = st.session_state.get("slider_epoch", 0)
            override = st.session_state.get("active_param_override", {})
            for item in metadata.inputs:
                label = item.label
                if item.unit:
                    label = f"{label} · {item.unit}"

                start_value = float(override.get(item.name, item.default))
                start_value = min(max(start_value, float(item.min)), float(item.max))

                params[item.name] = st.slider(
                    label,
                    min_value=float(item.min),
                    max_value=float(item.max),
                    value=start_value,
                    step=float(item.step),
                    key=f"slider_{epoch}_{item.name}",
                )

            if not metadata.inputs:
                st.caption("No interactive numeric assumptions were detected in this model.")

            with scenario_area:
                st.markdown('<div class="section-title">Scenario</div>', unsafe_allow_html=True)
                save_col, clear_col = st.columns(2)
                with save_col:
                    save_requested = st.button(
                        "＋ Simpan skenario",
                        use_container_width=True,
                        disabled=len(saved_scenarios) >= MAX_SAVED_SCENARIOS or not metadata.inputs,
                    )
                with clear_col:
                    if st.button(
                        "Hapus skenario",
                        use_container_width=True,
                        disabled=not saved_scenarios,
                    ):
                        st.session_state.saved_scenarios = []
                        st.session_state.scenario_counter = 0
                        saved_scenarios = []

                if saved_scenarios:
                    scenario_buttons = st.columns(len(saved_scenarios))
                    for index, scenario in enumerate(saved_scenarios):
                        with scenario_buttons[index]:
                            if st.button(
                                scenario["name"],
                                key=f"load_scenario_{index}",
                                use_container_width=True,
                                help=f"Load {scenario['name']} back into the sliders",
                            ):
                                load_saved_scenario(scenario["params"])
                                st.rerun()

                if len(saved_scenarios) >= MAX_SAVED_SCENARIOS:
                    st.caption(f"Maksimum {MAX_SAVED_SCENARIOS} skenario tersimpan. Hapus skenario untuk membuat yang baru.")
                else:
                    st.caption("Geser slider untuk melihat dampak.")

    with graph_col:
        with st.container(key="chart_panel"):
            initial_year = format_number(metadata.time["initial"])
            final_year = format_number(metadata.time["final"])
            st.markdown(
                f'<div class="section-title">Grafik Hasil (Tahun {initial_year}-{final_year})</div>',
                unsafe_allow_html=True,
            )

            baseline_params = {item.name: float(item.default) for item in metadata.inputs}

            try:
                digest = st.session_state.get("model_digest")
                if (
                    st.session_state.get("baseline_digest") != digest
                    or st.session_state.get("baseline_result") is None
                ):
                    st.session_state.baseline_result = run_model(model, metadata, baseline_params)
                    st.session_state.baseline_digest = digest

                baseline_result = st.session_state.baseline_result
                active_result = run_model(model, metadata, params)
            except Exception as exc:
                st.error("The model loaded, but the simulation could not run with the current settings.")
                st.caption(str(exc).strip())
                with st.expander("Technical details"):
                    st.code(f"{type(exc).__name__}: {exc}")
                return

            # Save the exact current slider state and its result.
            if save_requested:
                if params_match(params, baseline_params):
                    st.toast("Nilai saat ini sama dengan baseline.")
                elif find_matching_scenario(params, saved_scenarios):
                    st.toast("Skenario dengan pengaturan yang sama sudah tersimpan.")
                elif len(saved_scenarios) < MAX_SAVED_SCENARIOS:
                    st.session_state.scenario_counter += 1
                    scenario_name = f"Skenario {st.session_state.scenario_counter}"
                    st.session_state.saved_scenarios.append(
                        {
                            "name": scenario_name,
                            "params": dict(params),
                            "result": active_result.copy(),
                        }
                    )
                    st.toast(f"{scenario_name} disimpan.")
                    st.rerun()

            saved_scenarios = st.session_state.get("saved_scenarios", [])
            matching_name = find_matching_scenario(params, saved_scenarios)
            active_matches_saved = matching_name is not None
            if params_match(params, baseline_params):
                active_label = "Baseline"
                active_matches_saved = True
            else:
                active_label = matching_name or "Skenario aktif"

            grouped_outputs = group_outputs_by_directorate(metadata.outputs)
            ungrouped_count = len(grouped_outputs.get("__UNGROUPED__", []))

            missing_indicator_count = 0
            invalid_mapping_count = 0
            for output in metadata.outputs:
                directorate = getattr(output, "directorate", None)
                indicator = getattr(output, "indicator", None)
                if directorate in DIRECTORATE_ORDER:
                    if not indicator:
                        missing_indicator_count += 1
                    elif indicator_catalog and (str(directorate), str(indicator)) not in indicator_catalog:
                        invalid_mapping_count += 1

            # A single shared legend keeps the five narrow columns clean.
            st.markdown(
                graph_legend_html(saved_scenarios, active_label, active_matches_saved),
                unsafe_allow_html=True,
            )

            if indicator_catalog_path is None:
                st.caption(
                    "IndikatorPMKK.xlsx belum ditemukan. Website sementara memakai nama variabel Vensim. "
                    "Simpan Excel di data/IndikatorPMKK.xlsx atau di root repository."
                )
            elif not indicator_catalog:
                st.caption(
                    "IndikatorPMKK.xlsx ditemukan, tetapi katalog pada sheet 1_General belum dapat dibaca."
                )

            if ungrouped_count:
                st.caption(
                    f"{ungrouped_count} output belum diberi tag direktorat dan belum ditampilkan. "
                    "Tambahkan directorate=PKKS, KJS, NAKER, KSE, atau KUMKM pada Comment @output di Vensim."
                )

            if missing_indicator_count:
                st.caption(
                    f"{missing_indicator_count} output sudah memiliki direktorat tetapi belum memiliki indicator=. "
                    "Contoh: @output directorate=NAKER indicator=34."
                )

            if invalid_mapping_count:
                st.caption(
                    f"{invalid_mapping_count} output memiliki directorate+indicator yang tidak cocok dengan katalog Excel."
                )

            directorate_columns = st.columns(5, gap="small")

            # Five permanent columns. Every multiselect starts empty, so no graph
            # is shown until the user explicitly chooses one or more indicators.
            for column, code in zip(directorate_columns, DIRECTORATE_ORDER):
                with column:
                    st.markdown(
                        f'<div class="directorate-code">{DIRECTORATE_SHORT_LABELS[code]}</div>'
                        f'<div class="directorate-subtitle">{DIRECTORATE_SUBTITLES[code]}</div>',
                        unsafe_allow_html=True,
                    )

                    outputs_for_directorate = grouped_outputs.get(code, [])
                    output_lookup = {item.name: item for item in outputs_for_directorate}

                    selected_names = st.multiselect(
                        "Pilih indikator",
                        options=list(output_lookup),
                        default=[],
                        format_func=lambda name, lookup=output_lookup, catalog=indicator_catalog: (
                            official_indicator_dropdown_label(lookup[name], catalog)
                        ),
                        placeholder=(
                            "Pilih indikator"
                            if output_lookup
                            else "Belum ada indikator"
                        ),
                        key=f"directorate_indicators_{code}",
                        disabled=not bool(output_lookup),
                        label_visibility="collapsed",
                    )

                    # Each directorate has its own independent vertical scroll area.
                    with st.container(height=575, border=False):
                        if not selected_names:
                            st.markdown(
                                '<div class="directorate-empty">Pilih indikator untuk menampilkan grafik.</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            for indicator_index, output_name in enumerate(selected_names):
                                output = output_lookup[output_name]
                                final_value = active_result[output.name].iloc[-1]
                                baseline_value = baseline_result[output.name].iloc[-1]
                                unit = f" {output.unit}" if output.unit else ""
                                delta = delta_from_baseline(final_value, baseline_value)
                                display_name = official_indicator_name(output, indicator_catalog)
                                indicator_number = getattr(output, "indicator", None)
                                number_prefix = (
                                    f'<span style="opacity:.52">{indicator_number} · </span>'
                                    if indicator_number else ""
                                )

                                with st.container(border=True):
                                    st.markdown(
                                        f'<div class="indicator-card-title">{number_prefix}{display_name}</div>'
                                        f'<div class="indicator-card-meta">'
                                        f'{format_number(final_value)}{unit} · {delta}</div>',
                                        unsafe_allow_html=True,
                                    )

                                    figure = build_single_output_figure(
                                        output=output,
                                        active_result=active_result,
                                        baseline_result=baseline_result,
                                        metadata=metadata,
                                        saved_scenarios=saved_scenarios,
                                        active_label=active_label,
                                        active_matches_saved=active_matches_saved,
                                        display_label=display_name,
                                    )
                                    st.plotly_chart(
                                        figure,
                                        use_container_width=True,
                                        key=f"chart_{code}_{output.name}_{indicator_index}",
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

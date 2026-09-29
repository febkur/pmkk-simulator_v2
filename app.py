from __future__ import annotations

import hashlib
import math
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from openpyxl import load_workbook
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

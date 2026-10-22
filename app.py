"""
app.py — CacheScope Interactive Web Dashboard (Streamlit).

UI Design:
  - Glassmorphism frosted-glass cards on deep gradient background
  - Linear.app aesthetic: minimal, dark, ultra-clean
  - Teal (#0F766E) primary + Indigo (#4338CA) secondary accent system
  - Two-page flow: Config → Run → Full Results
  - Priority: KPIs, What-If sweep, Heatmap, Access Pattern Detector
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from cache_analyzer.cache import CacheConfig
from cache_analyzer.simulator import CacheSimulator
from cache_analyzer.replacement import available_policies
from cache_analyzer.workload import available_workloads, get_workload, TraceLoader
from cache_analyzer.workload.real_patterns import (
    trace_cache_thrashing_loop,
    trace_strided_column_matrix,
    trace_direct_mapped_conflict,
    trace_sequential_streaming,
    trace_temporal_hotspot,
    trace_matrix_multiplication,
    trace_quicksort,
    trace_image_convolution,
    trace_binary_search,
    trace_linked_list_traversal,
    trace_interleaved_threads,
    generate_all_pattern_datasets,
)
from cache_analyzer.pattern_detector import AccessPatternDetector
from cache_analyzer.whatif import WhatIfAnalyzer
from cache_analyzer.database import CacheDatabase

st.set_page_config(
    page_title="CacheScope — Hardware Cache Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "page" not in st.session_state:
    st.session_state["page"] = "config"
if "sim_data" not in st.session_state:
    st.session_state["sim_data"] = None



# =========================================================================
# GLASSMORPHISM + LINEAR.APP DESIGN SYSTEM
# =========================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;0,9..40,900;1,9..40,400&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    /* ── Base ── */
    html, body, [class*="css"], .stApp {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background: #16171d !important;
        color: #f1f5f9 !important;
        min-height: 100vh;
    }

    /* Fix Streamlit default top header bar */
    header[data-testid="stHeader"] {
        background: rgba(22, 23, 29, 0.95) !important;
        backdrop-filter: blur(14px) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
        height: 38px !important;
    }
    /* Collapse toolbar overlap */
    div[data-testid="stToolbar"] {
        display: none !important;
    }

    /* Ambient light-black depth gradient behind floating cards */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background:
            radial-gradient(ellipse 80% 60% at 50% 0%, rgba(255, 255, 255, 0.05) 0%, transparent 70%),
            radial-gradient(ellipse 70% 50% at 50% 100%, rgba(0, 0, 0, 0.45) 0%, transparent 75%);
        pointer-events: none;
        z-index: 0;
    }

    h1, h2, h3, h4, h5 {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        letter-spacing: -0.02em !important;
    }

    code, kbd, pre { font-family: 'JetBrains Mono', monospace !important; }

    .block-container {
        padding-top: 0.4rem !important;
        padding-bottom: 3rem !important;
        max-width: 1380px !important;
        position: relative;
        z-index: 1;
        margin-top: -38px !important;
    }

    /* ── Glass Card Base ── */
    .glass-card {
        background: rgba(11, 12, 16, 0.92);
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 20px;
        position: relative;
        box-shadow:
            0 2px 4px rgba(0, 0, 0, 0.4),
            0 12px 28px -4px rgba(0, 0, 0, 0.65),
            0 24px 50px -8px rgba(0, 0, 0, 0.75),
            0 0 0 1px rgba(255, 255, 255, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.14);
        transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .glass-card:hover {
        border-color: rgba(255, 255, 255, 0.35);
        transform: translateY(-4px);
        box-shadow:
            0 6px 12px rgba(0, 0, 0, 0.5),
            0 20px 40px -4px rgba(0, 0, 0, 0.75),
            0 36px 70px -6px rgba(0, 0, 0, 0.85),
            0 0 0 1px rgba(255, 255, 255, 0.20),
            inset 0 1px 0 rgba(255, 255, 255, 0.22);
    }

    /* ── Streamlit border containers → floating content cards ── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(11, 12, 16, 0.94) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 20px !important;
        position: relative !important;
        box-shadow:
            0 2px 4px rgba(0, 0, 0, 0.4),
            0 12px 28px -4px rgba(0, 0, 0, 0.65),
            0 24px 50px -8px rgba(0, 0, 0, 0.75),
            0 0 0 1px rgba(255, 255, 255, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.14) !important;
        transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(255, 255, 255, 0.35) !important;
        transform: translateY(-4px) !important;
        box-shadow:
            0 6px 12px rgba(0, 0, 0, 0.5),
            0 20px 40px -4px rgba(0, 0, 0, 0.75),
            0 36px 70px -6px rgba(0, 0, 0, 0.85),
            0 0 0 1px rgba(255, 255, 255, 0.20),
            inset 0 1px 0 rgba(255, 255, 255, 0.22) !important;
    }

    /* ── Brand Header ── */
    .cs-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 0 0 28px 0;
        margin-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .cs-logo-badge {
        width: 44px;
        height: 44px;
        background: #ffffff;
        color: #09090b;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.35rem;
        font-weight: 900;
        box-shadow: 0 4px 20px rgba(255, 255, 255, 0.25);
        flex-shrink: 0;
    }
    .cs-brand-name {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #ffffff;
        line-height: 1.1;
    }
    .cs-brand-sub {
        font-size: 0.8rem;
        color: #94a3b8;
        font-weight: 500;
        margin-top: 2px;
        letter-spacing: 0.01em;
    }
    .cs-header-pills {
        margin-left: auto;
        display: flex;
        gap: 8px;
        align-items: center;
    }
    .cs-pill {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 5px 14px;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.30);
        color: #ffffff;
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(8px);
        transition: all 0.2s ease;
    }
    .cs-pill:hover {
        border-color: #ffffff;
        background: rgba(255, 255, 255, 0.14);
        color: #ffffff;
    }
    .cs-pill-ind {
        border-color: rgba(134, 239, 172, 0.40);
        color: #86efac;
        background: rgba(134, 239, 172, 0.08);
    }
    .cs-pill-ind:hover {
        border-color: #86efac;
        background: rgba(134, 239, 172, 0.18);
        color: #ffffff;
    }

    /* ── Hero Section (Floating Card) ── */
    .cs-hero {
        text-align: center;
        padding: 36px 24px 32px;
        margin-bottom: 28px;
        background: rgba(11, 12, 16, 0.94);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        position: relative;
        overflow: hidden;
        box-shadow:
            0 4px 8px rgba(0, 0, 0, 0.4),
            0 16px 36px -4px rgba(0, 0, 0, 0.65),
            0 30px 60px -8px rgba(0, 0, 0, 0.75),
            inset 0 1px 0 rgba(255, 255, 255, 0.14);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .cs-hero:hover {
        border-color: rgba(255, 255, 255, 0.35);
        transform: translateY(-4px);
        box-shadow:
            0 8px 16px rgba(0, 0, 0, 0.5),
            0 24px 48px -4px rgba(0, 0, 0, 0.75),
            0 40px 80px -8px rgba(0, 0, 0, 0.85),
            inset 0 1px 0 rgba(255, 255, 255, 0.22);
    }
    .cs-hero::before {
        content: '';
        position: absolute;
        top: -60px; left: 50%; transform: translateX(-50%);
        width: 500px; height: 220px;
        background: radial-gradient(ellipse, rgba(255,255,255,0.06) 0%, transparent 70%);
        pointer-events: none;
    }
    .cs-hero-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.73rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #ffffff;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.28);
        border-radius: 999px;
        padding: 5px 16px;
        margin-bottom: 16px;
    }
    .cs-hero-title {
        font-size: 2.6rem;
        font-weight: 900;
        letter-spacing: -0.04em;
        color: #ffffff;
        line-height: 1.1;
        margin-bottom: 12px;
    }
    .cs-hero-sub {
        font-size: 1.02rem;
        color: #94a3b8;
        max-width: 680px;
        margin: 0 auto;
        line-height: 1.6;
        font-weight: 400;
    }

    /* ── KPI Cards (Floating) ── */
    .kpi-card {
        background: rgba(11, 12, 16, 0.94);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-top: 2px solid #ffffff;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow:
            0 2px 6px rgba(0, 0, 0, 0.35),
            0 10px 24px -4px rgba(0, 0, 0, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.12);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        border-color: rgba(255, 255, 255, 0.40);
        border-top-color: #ffffff;
        box-shadow:
            0 6px 14px rgba(0, 0, 0, 0.5),
            0 18px 36px -4px rgba(0, 0, 0, 0.75),
            0 0 20px rgba(255, 255, 255, 0.10),
            inset 0 1px 0 rgba(255, 255, 255, 0.20);
    }
    .kpi-card-accent { border-top-color: #ffffff; }
    .kpi-card-accent:hover {
        border-top-color: #ffffff;
        border-color: rgba(255, 255, 255, 0.45);
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.25), 0 0 20px rgba(255, 255, 255, 0.12), 0 12px 28px rgba(0,0,0,0.60);
    }
    .kpi-card-warn { border-top-color: #f59e0b; }
    .kpi-card-warn:hover {
        border-top-color: #fbbf24;
        border-color: rgba(245, 158, 11, 0.45);
        box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.25), 0 0 20px rgba(245, 158, 11, 0.22), 0 12px 28px rgba(0, 0, 0, 0.60);
    }
    .kpi-title {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin-bottom: 6px;
    }
    .kpi-val {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }
    .kpi-note {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 4px;
        font-weight: 500;
    }

    /* ── Address Bit Strip ── */
    .bit-strip {
        display: flex;
        gap: 8px;
        margin-top: 14px;
    }
    .bit-item {
        flex: 1;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 10px;
        padding: 10px 12px;
        text-align: center;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .bit-item:hover {
        background: rgba(255, 255, 255, 0.10);
        border-color: rgba(255, 255, 255, 0.50);
        transform: translateY(-2px);
        box-shadow: 0 0 16px rgba(255, 255, 255, 0.12), 0 6px 18px rgba(0,0,0,0.4);
    }
    .bit-name {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #94a3b8;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }
    .bit-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.3rem;
        font-weight: 700;
        color: #ffffff;
    }

    /* ── Geometry Summary Banner ── */
    .geo-banner {
        font-size: 0.82rem;
        color: #cbd5e1;
        margin-top: 12px;
        padding: 10px 14px;
        background: rgba(18, 18, 22, 0.65);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-left: 3px solid #ffffff;
        transition: all 0.25s ease;
    }
    .geo-banner:hover {
        border-color: rgba(255, 255, 255, 0.30);
        border-left-color: #ffffff;
        box-shadow: 0 0 14px rgba(255, 255, 255, 0.08);
    }

    /* ── Workload Footprint Box ── */
    .footprint-box {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 10px;
        padding: 12px 16px;
        margin: 16px 0;
        font-size: 0.88rem;
        color: #cbd5e1;
        line-height: 1.6;
        transition: all 0.25s ease;
    }
    .footprint-box:hover {
        border-color: rgba(255, 255, 255, 0.35);
        box-shadow: 0 0 16px rgba(255, 255, 255, 0.10), 0 4px 16px rgba(0,0,0,0.4);
    }
    .footprint-box strong { color: #ffffff; }

    /* ── Architecture Banner on Results (Floating) ── */
    .arch-banner {
        background: rgba(11, 12, 16, 0.94);
        backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 14px 22px;
        margin: 14px 0 22px 0;
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        align-items: center;
        font-size: 0.84rem;
        color: #cbd5e1;
        box-shadow: 0 4px 14px rgba(0,0,0,0.45), 0 10px 24px -4px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.12);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .arch-banner:hover {
        border-color: rgba(255, 255, 255, 0.35);
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.55), 0 16px 36px -4px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.20);
    }
    .arch-item { display: flex; flex-direction: column; gap: 1px; }
    .arch-label { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }
    .arch-val { font-weight: 700; color: #ffffff; font-size: 0.9rem; }
    .arch-mono { font-family: 'JetBrains Mono', monospace; color: #ffffff; font-size: 0.85rem; font-weight: 600; }

    /* ── Results Header ── */
    .results-header {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 8px 0 20px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .results-title {
        font-size: 1.65rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.03em;
        margin: 0;
    }
    .results-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.28);
        border-radius: 999px;
        padding: 4px 14px;
        color: #ffffff;
        font-weight: 600;
    }

    /* ── Buttons (High-contrast pure white primary like reference website) ── */
    div.stButton > button[kind="primary"] {
        background: #ffffff !important;
        color: #09090b !important;
        border: 1px solid #ffffff !important;
        border-radius: 999px !important;
        font-weight: 700 !important;
        font-size: 0.98rem !important;
        padding: 12px 28px !important;
        box-shadow: 0 4px 20px rgba(255, 255, 255, 0.22), inset 0 1px 0 rgba(255,255,255,0.5) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        letter-spacing: -0.01em !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #f1f5f9 !important;
        color: #000000 !important;
        border-color: #ffffff !important;
        box-shadow: 0 6px 30px rgba(255, 255, 255, 0.40) !important;
        transform: translateY(-2px) !important;
    }
    div.stButton > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.28) !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
        padding: 8px 20px !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.14) !important;
        border-color: rgba(255, 255, 255, 0.6) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px !important;
        background: rgba(14, 14, 18, 0.70) !important;
        backdrop-filter: blur(12px) !important;
        padding: 6px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04) !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 8px 18px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        color: #94a3b8 !important;
        border: 1px solid transparent !important;
        background-color: transparent !important;
        transition: all 0.2s ease !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff !important;
        background: rgba(255, 255, 255, 0.06) !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.10) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: 1px solid rgba(255, 255, 255, 0.32) !important;
        box-shadow: 0 0 16px rgba(255, 255, 255, 0.08) !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    /* ── Inputs ── */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] {
        background: rgba(18, 18, 22, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 9px !important;
        color: #ffffff !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.2s ease !important;
    }
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="input"] > div:hover,
    div[data-baseweb="base-input"]:hover,
    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="input"] > div:focus-within {
        border-color: rgba(255, 255, 255, 0.50) !important;
        box-shadow: 0 0 14px rgba(255, 255, 255, 0.12) !important;
    }
    div[data-baseweb="select"] * { color: #ffffff !important; }

    /* ── Sliders ── */
    div[data-testid="stSlider"] [role="slider"] {
        background: #ffffff !important;
        border-color: #ffffff !important;
        box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.25) !important;
    }
    div[data-testid="stSlider"] [data-testid="stSliderTrackFill"] {
        background: linear-gradient(90deg, #64748b, #ffffff) !important;
    }

    /* ── Dataframes ── */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
        background: rgba(14, 14, 18, 0.60) !important;
        backdrop-filter: blur(8px) !important;
        overflow: hidden !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stDataFrame"]:hover {
        border-color: rgba(255, 255, 255, 0.35) !important;
        box-shadow: 0 0 16px rgba(255, 255, 255, 0.10) !important;
    }

    /* ── Expanders (Floating) ── */
    div[data-testid="stExpander"] {
        background: rgba(11, 12, 16, 0.92) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(12px) !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08) !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stExpander"]:hover {
        border-color: rgba(255, 255, 255, 0.35) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.15) !important;
    }

    /* ── Metrics (native st.metric - Floating) ── */
    div[data-testid="stMetric"] {
        background: rgba(11, 12, 16, 0.94) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(255, 255, 255, 0.35) !important;
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.16) !important;
    }

    /* ── Section labels ── */
    .section-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #ffffff;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-label::after {
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, rgba(255, 255, 255, 0.35), transparent);
    }

    /* ── Info box ── */
    .info-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.20);
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 0.84rem;
        color: #f1f5f9;
        margin-top: 8px;
        line-height: 1.5;
        transition: all 0.25s ease;
    }
    .info-box:hover {
        border-color: rgba(255, 255, 255, 0.40);
        box-shadow: 0 0 14px rgba(255, 255, 255, 0.10);
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 999px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.4); }
</style>
""", unsafe_allow_html=True)


# =========================================================================
# PAGE 1: CONFIGURATION & WORKLOAD SELECTION
# =========================================================================
if st.session_state["page"] == "config":

    # Brand Header
    st.markdown("""
        <div class="cs-header">
            <div class="cs-logo-badge">⚡</div>
            <div>
                <div class="cs-brand-name">CacheScope</div>
                <div class="cs-brand-sub">Hardware Cache Behavior Analyzer & Optimizer</div>
            </div>
            <div class="cs-header-pills">
                <span class="cs-pill">Live Simulation</span>
                <span class="cs-pill cs-pill-ind">What-If Engine</span>
                <span class="cs-pill">3C Classification</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Hero
    st.markdown("""
        <div class="cs-hero">
            <div class="cs-hero-eyebrow">⚡ HARDWARE CACHE AUDIT ENGINE</div>
            <div class="cs-hero-title">Analyze. Simulate. Optimize.</div>
            <div class="cs-hero-sub">
                Simulate authentic memory workloads through physical cache hierarchies.
                Diagnose compulsory, capacity &amp; conflict misses — and instantly explore
                what changes to the architecture would do.
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_geom, col_workload = st.columns([1, 1], gap="large")

    with col_geom:
        with st.container(border=True):
            st.markdown('<div class="section-label">🛠️ Cache Geometry & Microarchitecture</div>', unsafe_allow_html=True)

            c_size_col, b_size_col = st.columns(2)
            with c_size_col:
                cache_size_kb = st.select_slider(
                    "Cache Capacity",
                    options=[1, 2, 4, 8, 16, 32, 64],
                    value=4,
                    format_func=lambda x: f"{x} KB",
                    help="Total data memory capacity.",
                )
                cache_size_bytes = cache_size_kb * 1024

            with b_size_col:
                block_size_bytes = st.select_slider(
                    "Line / Block Size",
                    options=[16, 32, 64, 128],
                    value=64,
                    format_func=lambda x: f"{x} Bytes",
                    help="Granularity of spatial transfers from main memory.",
                )

            assoc_col, pol_col = st.columns(2)
            with assoc_col:
                assoc_option = st.selectbox(
                    "Associativity (Ways per Set)",
                    options=[
                        "1-Way (Direct Mapped)",
                        "2-Way Set-Associative",
                        "4-Way Set-Associative",
                        "8-Way Set-Associative",
                        "Fully Associative",
                    ],
                    index=0,
                )
                if "1-Way" in assoc_option:
                    assoc_val = 1
                elif "2-Way" in assoc_option:
                    assoc_val = 2
                elif "4-Way" in assoc_option:
                    assoc_val = 4
                elif "8-Way" in assoc_option:
                    assoc_val = 8
                else:
                    assoc_val = 0

            with pol_col:
                policies_list = available_policies()
                default_pol_idx = policies_list.index("LRU") if "LRU" in policies_list else 0
                policy = st.selectbox(
                    "Eviction / Replacement Policy",
                    options=policies_list,
                    index=default_pol_idx,
                )

            st.markdown('<div class="section-label" style="margin-top:16px;">⏱️ Access Latency Model (AMAT)</div>', unsafe_allow_html=True)
            t1, t2 = st.columns(2)
            with t1:
                hit_time = st.number_input("L1 Hit Time (cycles)", value=1.0, min_value=0.1, step=0.5)
            with t2:
                miss_penalty = st.number_input("Miss Penalty (cycles)", value=100.0, min_value=1.0, step=10.0)

            temp_config = CacheConfig(
                cache_size=cache_size_bytes,
                block_size=block_size_bytes,
                associativity=assoc_val,
                replacement_policy=policy,
                hit_time=hit_time,
                miss_penalty=miss_penalty,
                name=f"{cache_size_kb}KB_{assoc_val if assoc_val > 0 else 'FA'}way",
            )

            st.markdown(f"""
                <div style="font-size:0.7rem; font-weight:700; text-transform:uppercase; color:#64748b; margin-top:16px; letter-spacing:0.08em; margin-bottom:8px;">
                    32-BIT ADDRESS DECOMPOSITION
                </div>
                <div class="bit-strip">
                    <div class="bit-item">
                        <div class="bit-name">Tag Bits</div>
                        <div class="bit-value">{temp_config.tag_bits}</div>
                    </div>
                    <div class="bit-item">
                        <div class="bit-name">Set Index</div>
                        <div class="bit-value">{temp_config.index_bits}</div>
                    </div>
                    <div class="bit-item">
                        <div class="bit-name">Offset Bits</div>
                        <div class="bit-value">{temp_config.offset_bits}</div>
                    </div>
                </div>
                <div class="geo-banner">
                    <strong style="color:#22d3ee;">{temp_config.num_lines:,}</strong> total lines &bull;
                    <strong style="color:#22d3ee;">{temp_config.num_sets:,}</strong> sets &bull;
                    <strong style="color:#e2e8f0;">{temp_config.organization_str()}</strong>
                </div>
            """, unsafe_allow_html=True)

    with col_workload:
        with st.container(border=True):
            st.markdown('<div class="section-label">📂 Memory Access Workload & Benchmark</div>', unsafe_allow_html=True)

            trace_source = st.radio(
                "Workload Source",
                ["Standard Workload Generators", "Upload / Saved Trace File"],
                horizontal=True,
            )

            trace: list[int] = []
            workload_name = "Workload"

            if trace_source == "Standard Workload Generators":
                wk_choice = st.selectbox(
                    "Select Access Pattern",
                    [
                        "LOCALITY — Temporal and spatial locality access stream",
                        "SEQUENTIAL — Linear consecutive address stream",
                        "LOOP — Cyclic loop repeating a fixed working set",
                        "MATRIX — 2D Matrix traversal (row-major vs column-major)",
                        "RANDOM — Uncorrelated memory address stream",
                    ],
                )
                count = st.slider("Number of Memory Accesses", min_value=128, max_value=2048, value=512, step=64)

                if "LOCALITY" in wk_choice:
                    gen = get_workload("LOCALITY", count=count)
                    trace = gen.generate()
                    workload_name = f"Locality_{count}"
                    st.caption("Generates multi-stream addresses with temporal (80%) and spatial reuse — includes cache set aliasing for realistic conflict pressure.")

                elif "SEQUENTIAL" in wk_choice:
                    stride = st.selectbox("Access Stride (bytes)", [4, 8, 16, 64], index=0)
                    gen = get_workload("SEQUENTIAL", stride=stride, count=count)
                    trace = gen.generate()
                    workload_name = f"Sequential_stride{stride}"
                    st.caption(f"Streams a working-set vector repeatedly with stride {stride} bytes across multiple passes.")

                elif "LOOP" in wk_choice:
                    loop_blocks = st.slider("Loop Working Set (Unique Blocks)", min_value=8, max_value=128, value=80, step=8)
                    gen = get_workload("LOOP", num_elements=loop_blocks, element_size=temp_config.block_size, iterations=max(2, count // loop_blocks))
                    trace = gen.generate()
                    workload_name = f"Loop_{loop_blocks}blocks"
                    st.caption(f"Repeats a loop of {loop_blocks} blocks ({loop_blocks * temp_config.block_size} Bytes). When loop size > cache lines, capacity thrashing occurs.")

                elif "MATRIX" in wk_choice:
                    order = st.radio("Matrix Traversal Order", ["row-major", "column-major"], horizontal=True)
                    gen = get_workload("MATRIX", rows=32, cols=32, element_size=8, order=order)
                    trace = gen.generate()
                    workload_name = f"Matrix_32x32_{order}"
                    st.caption("2-pass 32×32 matrix traversal. Row-major is cache-friendly; column-major induces severe strided conflict misses.")

                else:
                    gen = get_workload("RANDOM", count=count)
                    trace = gen.generate()
                    workload_name = f"Random_{count}"
                    st.caption("Uniformly random memory addresses — no locality, maximum cold/capacity miss pressure.")

            else:
                file_mode = st.radio("Trace Input Method", ["Pick Saved File (datasets/*.trace)", "Upload / Paste Trace"], horizontal=True)
                if file_mode == "Pick Saved File (datasets/*.trace)":
                    dataset_files = []
                    if os.path.exists("datasets"):
                        dataset_files = sorted([f for f in os.listdir("datasets") if f.endswith(".trace") or f.endswith(".txt") or f.endswith(".csv")])
                    if dataset_files:
                        selected_file = st.selectbox("Select File", dataset_files)
                        filepath = os.path.join("datasets", selected_file)
                        trace = TraceLoader(filepath=filepath).generate()
                        workload_name = f"Dataset({selected_file})"
                        st.caption(f"Loaded {len(trace):,} accesses from `{filepath}`.")
                    else:
                        trace = get_workload("LOCALITY", count=512).generate()
                        workload_name = "DefaultLocality"
                else:
                    uploaded_file = st.file_uploader("Upload Trace File (.txt, .csv, .trace)", type=["txt", "csv", "trace", "dat"])
                    pasted_text = st.text_area("Or Paste Raw Addresses (Hex or Decimal):", height=100)
                    if uploaded_file:
                        content = uploaded_file.getvalue().decode("utf-8", errors="replace")
                        trace = TraceLoader(text_content=content).generate()
                        workload_name = f"Uploaded({uploaded_file.name})"
                    elif pasted_text.strip():
                        trace = TraceLoader(text_content=pasted_text).generate()
                        workload_name = "PastedTrace"
                    else:
                        trace = get_workload("LOCALITY", count=512).generate()
                        workload_name = "DefaultLocality"

            unique_blocks = len(set(a // temp_config.block_size for a in trace))
            footprint_kb = round((unique_blocks * temp_config.block_size) / 1024, 2)
            cap_ratio = footprint_kb / (temp_config.cache_size / 1024)
            cap_color = "#22d3ee" if cap_ratio <= 1 else ("#D97706" if cap_ratio <= 1.5 else "#DC2626")

            st.markdown(f"""
                <div class="footprint-box">
                    <strong>Workload Ready:</strong> {len(trace):,} authentic memory accesses<br>
                    <strong>Working Set:</strong> {unique_blocks} unique blocks ({footprint_kb} KB)
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    <strong>Cache Capacity:</strong> {temp_config.cache_size // 1024} KB
                    &nbsp;&nbsp;<span style="color:{cap_color}; font-weight:700;">
                        {'✓ Fits in cache' if cap_ratio <= 1 else ('⚠ ~{:.0f}% over capacity'.format((cap_ratio-1)*100) if cap_ratio <= 1.5 else '✕ Exceeds capacity — expect capacity misses')}
                    </span>
                </div>
            """, unsafe_allow_html=True)

            run_btn = st.button("⚡ Run Cache Simulation & Analysis", use_container_width=True, type="primary")
            if run_btn:
                with st.spinner(f"Simulating {len(trace):,} memory accesses through hardware pipeline..."):
                    sim = CacheSimulator(temp_config)
                    res = sim.run(trace, workload_name=workload_name)
                    st.session_state["sim_data"] = {
                        "config": temp_config,
                        "result": res,
                        "trace": trace,
                        "workload_name": workload_name,
                        "footprint_kb": footprint_kb,
                    }
                    st.session_state["page"] = "results"
                    st.rerun()


# =========================================================================
# PAGE 2: RESULTS & WHAT-IF DASHBOARD
# =========================================================================
elif st.session_state["page"] == "results":
    if st.session_state["sim_data"] is None:
        st.session_state["page"] = "config"
        st.rerun()

    data = st.session_state["sim_data"]
    config: CacheConfig = data["config"]
    result = data["result"]
    trace: list[int] = data["trace"]
    workload_name: str = data["workload_name"]
    footprint_kb: float = data.get("footprint_kb", round((len(set(a // config.block_size for a in trace)) * config.block_size) / 1024, 2))
    metrics = result.metrics

    # Brand Header (results page)
    st.markdown("""
        <div class="cs-header">
            <div class="cs-logo-badge">⚡</div>
            <div>
                <div class="cs-brand-name">CacheScope</div>
                <div class="cs-brand-sub">Hardware Cache Behavior Analyzer & Optimizer</div>
            </div>
            <div class="cs-header-pills">
                <span class="cs-pill">Live Simulation</span>
                <span class="cs-pill cs-pill-ind">What-If Engine</span>
                <span class="cs-pill">3C Classification</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Results page top bar
    top_l, top_r = st.columns([4, 1.2], vertical_alignment="center")
    with top_l:
        st.markdown(f"""
            <div class="results-header">
                <span class="results-title">Simulation Results</span>
                <span class="results-badge">{workload_name}</span>
                <span class="results-badge">{len(trace):,} accesses</span>
            </div>
        """, unsafe_allow_html=True)
    with top_r:
        if st.button("⬅ Reconfigure", use_container_width=True, type="secondary"):
            st.session_state["page"] = "config"
            st.rerun()

    # Architecture Banner
    st.markdown(f"""
        <div class="arch-banner">
            <div class="arch-item">
                <span class="arch-label">Capacity</span>
                <span class="arch-val">{config.cache_size//1024} KB</span>
            </div>
            <div class="arch-item">
                <span class="arch-label">Block Size</span>
                <span class="arch-val">{config.block_size} B</span>
            </div>
            <div class="arch-item">
                <span class="arch-label">Organization</span>
                <span class="arch-val">{config.organization_str()}</span>
            </div>
            <div class="arch-item">
                <span class="arch-label">Sets / Lines</span>
                <span class="arch-val">{config.num_sets:,} / {config.num_lines:,}</span>
            </div>
            <div class="arch-item">
                <span class="arch-label">Policy</span>
                <span class="arch-val">{config.replacement_policy}</span>
            </div>
            <div class="arch-item">
                <span class="arch-label">Bit Split</span>
                <span class="arch-mono">Tag:{config.tag_bits} | Set:{config.index_bits} | Off:{config.offset_bits}</span>
            </div>
            <div class="arch-item">
                <span class="arch-label">AMAT</span>
                <span class="arch-mono">{metrics.amat:.2f} cycles</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # KPI Cards
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Total Accesses</div>
                <div class="kpi-val">{metrics.total_accesses:,}</div>
                <div class="kpi-note">Memory Operations</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        hr_color = "#ffffff" if metrics.hit_rate >= 80 else ("#f59e0b" if metrics.hit_rate >= 50 else "#ef4444")
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Hit Rate</div>
                <div class="kpi-val" style="color:{hr_color};">{metrics.hit_rate:.1f}%</div>
                <div class="kpi-note">{metrics.hits:,} cache hits</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="kpi-card kpi-card-accent">
                <div class="kpi-title">Miss Rate</div>
                <div class="kpi-val" style="color:#ffffff;">{metrics.miss_rate:.1f}%</div>
                <div class="kpi-note">{metrics.misses:,} cache misses</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class="kpi-card kpi-card-warn">
                <div class="kpi-title">Evictions</div>
                <div class="kpi-val" style="color:#fbbf24;">{metrics.evictions:,}</div>
                <div class="kpi-note">Line replacements</div>
            </div>
        """, unsafe_allow_html=True)
    with k5:
        amat_color = "#ffffff" if metrics.amat <= 3 else ("#f59e0b" if metrics.amat <= 10 else "#ef4444")
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Effective AMAT</div>
                <div class="kpi-val" style="color:{amat_color};">{metrics.amat:.2f}</div>
                <div class="kpi-note">Cycles per access</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    # Analysis Tabs
    tab_whatif, tab_perf, tab_patterns, tab_heatmap, tab_state = st.tabs([
        "🔮  What-If Analysis",
        "📊  3C Miss Breakdown",
        "🔍  Pattern Detector",
        "🔥  Set Heatmap",
        "🔬  Cache Inspector",
    ])

    # ── TAB 1: WHAT-IF ──
    with tab_whatif:
        with st.container(border=True):
            st.markdown("### 🔮 What-If Multi-Configuration Sweep")
            st.caption("Evaluates alternative cache microarchitectures against the **identical memory trace** and explains WHY performance changed.")

            whatif_analyzer = WhatIfAnalyzer()
            experiment = whatif_analyzer.run_sweep(config, trace, workload_name=workload_name)

            df_table = pd.DataFrame(experiment.to_table_data())
            st.dataframe(df_table, use_container_width=True)

            cfg_names = [experiment.baseline_result.config.name] + [r.config.name for r in experiment.alternative_results]
            hit_rates = [experiment.baseline_result.metrics.hit_rate] + [r.metrics.hit_rate for r in experiment.alternative_results]
            amats = [experiment.baseline_result.metrics.amat] + [r.metrics.amat for r in experiment.alternative_results]
            colors = ["#06b6d4"] + ["#22d3ee" if hr >= hit_rates[0] else "#DC2626" for hr in hit_rates[1:]]

            chart_fig = go.Figure()
            chart_fig.add_trace(go.Bar(
                x=cfg_names, y=hit_rates, name="Hit Rate (%)",
                marker=dict(color=colors, opacity=0.85),
                marker_line=dict(color="rgba(255,255,255,0.08)", width=1),
            ))
            chart_fig.add_trace(go.Scatter(
                x=cfg_names, y=amats, name="AMAT (cycles)",
                yaxis="y2", mode="lines+markers",
                marker=dict(color="#D97706", size=7, symbol="circle"),
                line=dict(color="#D97706", width=2.5, dash="dot"),
            ))
            chart_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(10,22,40,0.0)",
                plot_bgcolor="rgba(15,23,42,0.5)",
                font=dict(family="Inter, sans-serif", color="#94a3b8", size=12),
                title=dict(text="Hit Rate vs AMAT — Architecture Comparison", font=dict(size=14, color="#e2e8f0"), x=0),
                yaxis=dict(title="Hit Rate (%)", range=[0, 108], gridcolor="rgba(148,163,184,0.08)", zerolinecolor="rgba(148,163,184,0.1)"),
                yaxis2=dict(title="AMAT (cycles)", overlaying="y", side="right", gridcolor="rgba(148,163,184,0.05)"),
                legend=dict(x=0.01, y=0.99, bgcolor="rgba(15,23,42,0.8)", bordercolor="rgba(148,163,184,0.15)", borderwidth=1),
                height=360,
                margin=dict(l=20, r=20, t=44, b=30),
                bargap=0.25,
            )
            st.plotly_chart(chart_fig, use_container_width=True)

            st.markdown("#### 💡 Architectural Explanations")
            for idx, exp in enumerate(experiment.explanations, 1):
                with st.expander(f"Alt #{idx}: {exp.title} — {exp.primary_reason}", expanded=(idx == 1)):
                    st.markdown(f"**Narrative:**\n\n{exp.detailed_narrative}")
                    st.markdown("**Evidence:**")
                    for ev in exp.evidence_points:
                        st.markdown(f"- {ev}")

    # ── TAB 2: 3C MISS BREAKDOWN ──
    with tab_perf:
        with st.container(border=True):
            p1, p2 = st.columns(2)
            with p1:
                st.markdown("#### Hit vs Miss Ratio")
                pie_fig = go.Figure(data=[go.Pie(
                    labels=["Cache Hits", "Cache Misses"],
                    values=[metrics.hits, metrics.misses],
                    hole=0.58,
                    marker=dict(colors=["#06b6d4", "#0891b2"], line=dict(color="rgba(12,12,15,0.6)", width=3)),
                    textinfo="label+percent",
                    textfont=dict(family="Inter", size=12, color="#e2e8f0"),
                )])
                pie_fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter", color="#94a3b8"),
                    height=300,
                    margin=dict(l=10, r=10, t=20, b=10),
                    showlegend=True,
                    legend=dict(bgcolor="rgba(15,23,42,0.7)", bordercolor="rgba(148,163,184,0.1)"),
                )
                st.plotly_chart(pie_fig, use_container_width=True)

            with p2:
                st.markdown("#### 3C Miss Classification")
                miss_labels = ["Compulsory\n(Cold)", "Capacity", "Conflict"]
                miss_vals = [metrics.compulsory_misses, metrics.capacity_misses, metrics.conflict_misses]
                miss_colors = ["#06b6d4", "#0891b2", "#D97706"]
                bar_fig = go.Figure(data=[go.Bar(
                    x=miss_labels, y=miss_vals,
                    marker=dict(color=miss_colors, opacity=0.85),
                    marker_line=dict(color="rgba(255,255,255,0.08)", width=1),
                    text=miss_vals, textposition="outside",
                    textfont=dict(color="#e2e8f0", size=12),
                )])
                bar_fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.5)",
                    font=dict(family="Inter", color="#94a3b8"),
                    height=300,
                    margin=dict(l=10, r=10, t=30, b=10),
                    yaxis=dict(gridcolor="rgba(148,163,184,0.08)", zerolinecolor="rgba(148,163,184,0.1)"),
                    showlegend=False,
                )
                st.plotly_chart(bar_fig, use_container_width=True)

            st.markdown("""
                <div class="info-box">
                    <strong>3C Miss Principles:</strong><br>
                    &bull; <strong>Compulsory (Cold):</strong> First-ever access to a block — unavoidable on initial reference.<br>
                    &bull; <strong>Capacity:</strong> Working set exceeds cache capacity — would miss even in a fully associative cache of the same size.<br>
                    &bull; <strong>Conflict:</strong> Multiple blocks compete for the same cache set, evicting each other even when total capacity is sufficient.
                </div>
            """, unsafe_allow_html=True)

    # ── TAB 3: ACCESS PATTERN DETECTOR ──
    with tab_patterns:
        with st.container(border=True):
            st.markdown("### 🔍 Access Pattern Characterization")
            detector = AccessPatternDetector(default_block_size=config.block_size)
            pat_report = detector.analyze(trace)

            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title">Dominant Pattern</div>
                        <div class="kpi-val" style="font-size:1.45rem; color:#22d3ee;">{pat_report.dominant_pattern}</div>
                        <div class="kpi-note">{pat_report.confidence*100:.1f}% confidence</div>
                    </div>
                """, unsafe_allow_html=True)
            with pc2:
                tl = pat_report.temporal_locality_score * 100
                tl_color = "#22d3ee" if tl >= 70 else ("#D97706" if tl >= 40 else "#DC2626")
                st.markdown(f"""
                    <div class="kpi-card kpi-card-accent">
                        <div class="kpi-title">Temporal Locality</div>
                        <div class="kpi-val" style="font-size:1.45rem; color:{tl_color};">{tl:.1f}%</div>
                        <div class="kpi-note">Short-window block reuse</div>
                    </div>
                """, unsafe_allow_html=True)
            with pc3:
                sl = pat_report.spatial_locality_score * 100
                sl_color = "#22d3ee" if sl >= 70 else ("#D97706" if sl >= 40 else "#DC2626")
                st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title">Spatial Locality</div>
                        <div class="kpi-val" style="font-size:1.45rem; color:{sl_color};">{sl:.1f}%</div>
                        <div class="kpi-note">Adjacent line clustering</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
            st.markdown('<div class="section-label">🔧 Microarchitectural Recommendations</div>', unsafe_allow_html=True)
            for rec in pat_report.recommendations:
                st.markdown(f"- {rec}")

    # ── TAB 4: SET HEATMAP ──
    with tab_heatmap:
        with st.container(border=True):
            st.markdown("### 🔥 Cache Set Access Intensity Heatmap")
            counts = np.array(metrics.set_access_counts)
            num_sets = len(counts)

            if num_sets > 0:
                cols_n = 16 if num_sets >= 16 else max(1, num_sets)
                rows_n = int(np.ceil(num_sets / cols_n))
                padded = np.zeros(rows_n * cols_n)
                padded[:num_sets] = counts
                grid = padded.reshape((rows_n, cols_n))

                heat_fig = px.imshow(
                    grid,
                    color_continuous_scale=[[0, "rgba(10,12,14,0.85)"], [0.33, "#0891b2"], [0.66, "#06b6d4"], [1, "#DC2626"]],
                    labels=dict(x="Set Column", y="Set Row", color="Accesses"),
                    title=f"Set Utilization — {num_sets} Total Sets",
                )
                heat_fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.5)",
                    font=dict(family="Inter", color="#94a3b8"),
                    height=340,
                    margin=dict(l=20, r=20, t=44, b=20),
                    title_font=dict(size=14, color="#e2e8f0"),
                )
                st.plotly_chart(heat_fig, use_container_width=True)

                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Active Sets", f"{metrics.active_sets} / {num_sets}")
                sc2.metric("Peak Set Accesses", f"{metrics.max_set_accesses:,}")
                sc3.metric("Utilization Variance", f"{metrics.utilization_variance:.2f}")

    # ── TAB 5: CACHE INSPECTOR ──
    with tab_state:
        with st.container(border=True):
            st.markdown("### 🔬 Step-by-Step Cache Inspector")
            st.caption("Inspect recorded memory events and the physical contents of each cache set.")

            event_data = [e.to_dict() for e in result.events[:100]]
            if event_data:
                df_events = pd.DataFrame(event_data)
                st.dataframe(
                    df_events[["step", "address_hex", "block_number", "set_index", "tag", "result", "way_index", "miss_type"]],
                    use_container_width=True,
                )
                if len(result.events) > 100:
                    st.caption(f"Showing first 100 of {len(result.events)} total events.")

            snapshot = getattr(result, "final_cache_snapshot", None)
            if not snapshot:
                try:
                    sim = CacheSimulator(config)
                    sim.run(trace, workload_name=workload_name)
                    snapshot = sim.cache.get_snapshot()
                    result.final_cache_snapshot = snapshot
                except Exception:
                    snapshot = []

            if snapshot:
                st.markdown("#### 📦 Physical Structure: `Cache.sets`")
                st.caption(
                    f"The simulated cache consists of a list of **{len(snapshot)} Sets**, each containing **{config.associativity} Ways**. "
                    f"Addresses are mapped via `set_index = block_number % {config.num_sets}`. "
                    f"When a set is full, the **{config.replacement_policy}** policy selects the victim way to evict."
                )
                sets_summary = []
                for s in snapshot:
                    ways_desc = []
                    for w_idx, w in enumerate(s["ways"]):
                        if w["valid"]:
                            ways_desc.append(f"Way {w_idx}: Blk {w['block_number']} (Tag {hex(w['tag'])})")
                        else:
                            ways_desc.append(f"Way {w_idx}: [Empty]")
                    sets_summary.append({
                        "Set": f"Set {s['set_index']}",
                        "Resident Ways & Blocks": " | ".join(ways_desc),
                        "Accesses": s["access_count"],
                        "Hits": s["hit_count"],
                        "Misses": s["miss_count"],
                        "Evictions": s["eviction_count"],
                    })
                st.dataframe(pd.DataFrame(sets_summary), use_container_width=True, height=260)

            st.markdown("#### 🔍 Single Set Deep Inspector")
            selected_set = st.number_input(
                "Set Index", min_value=0, max_value=max(0, config.num_sets - 1), value=0, step=1,
            )
            if snapshot and selected_set < len(snapshot):
                target_ways = snapshot[selected_set]["ways"]
                set_info = [{
                    "Way": f"Way {w_idx}",
                    "Status": "VALID" if w["valid"] else "EMPTY",
                    "Tag Hex": hex(w["tag"]) if w["valid"] else "—",
                    "Block Number": w["block_number"] if w["valid"] else "—",
                    "Access Count": w["access_count"] if w["valid"] else "—",
                    "Last Clock": w["last_access"] if w["valid"] else "—",
                    "Inserted Clock": w["inserted_at"] if w["valid"] else "—",
                } for w_idx, w in enumerate(target_ways)]
                st.table(pd.DataFrame(set_info))

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Export
    with st.container(border=True):
        exp_col1, exp_col2, _ = st.columns([1, 1, 2])
        with exp_col1:
            csv_data = pd.DataFrame([e.to_dict() for e in result.events]).to_csv(index=False)
            st.download_button(
                label="📥 Download Events CSV",
                data=csv_data,
                file_name="cachescope_events.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with exp_col2:
            if st.button("💾 Save Run to Database", use_container_width=True):
                db = CacheDatabase()
                exp_id = db.save_simulation(result)
                st.success(f"Saved to `cachescope.db` (ID: {exp_id})")

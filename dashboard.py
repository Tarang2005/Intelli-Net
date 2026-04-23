import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from datetime import datetime, timezone
from paths import DB_PATH, DEVICE_HEALTH_JSON

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Intelli-Net NOC", layout="wide", page_icon="⚡")

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

* { font-family: 'JetBrains Mono', monospace !important; }

/* ── Global Material Icons text-leak fix ───────────────────────────────────
   When the font CDN is slow/offline, icon ligature text ("arrow_right",
   "menu", "expand_more") renders as raw characters. Zero it out globally.  */
.material-symbols-rounded,
.material-symbols-outlined,
.material-icons,
.material-icons-outlined,
.material-icons-sharp,
[class*="material-symbol"],
[class*="material-icon"] {
    font-size:   0px         !important;
    line-height: 0px         !important;
    color:       transparent !important;
    overflow:    hidden      !important;
    visibility:  hidden      !important;
}

/* ── Hide Streamlit chrome: Deploy / hamburger / \2807  menu ─────────────
   A NOC dashboard has no use for Streamlit branding in the header.       */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
header { display: none !important; }

.stApp { background-color: #0d1117 !important; }
[data-testid="stSidebar"] { background-color: #0d1117 !important; border-right: 1px solid #21262d !important; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
div[data-testid="metric-container"] { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 12px; }
[data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1px; }
[data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 24px !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] svg { display: none; }
h1, h2, h3, h4, h5 { color: #e6edf3 !important; }
.stDataFrame { background: #161b22 !important; }
.stButton button { background: #161b22 !important; color: #58a6ff !important; border: 1px solid #21262d !important; font-family: 'JetBrains Mono', monospace !important; }
.stButton button:hover { border-color: #58a6ff !important; }
.stSelectbox label { color: #8b949e !important; font-size: 11px !important; }
div[data-baseweb="select"] { background: #161b22 !important; border-color: #21262d !important; }
.block-container { padding: 1rem 2rem !important; padding-top: 1rem !important; }
hr { border-color: #21262d !important; }

.topbar {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}
.device-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 14px;
    height: 100%;
}
.device-card-critical {
    background: #1a0e0e;
    border: 1px solid #f85149;
    border-radius: 8px;
    padding: 14px;
    height: 100%;
}
.device-card-warning {
    background: #1a160a;
    border: 1px solid #d29922;
    border-radius: 8px;
    padding: 14px;
    height: 100%;
}
.incident-card {
    background: #161b22;
    border: 1px solid #f85149;
    border-left: 4px solid #f85149;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}
.incident-card-resolved {
    background: #161b22;
    border: 1px solid #3fb950;
    border-left: 4px solid #3fb950;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}
.ai-box {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 12px;
    margin-top: 10px;
    font-size: 12px;
    color: #c9d1d9;
    line-height: 1.7;
}
.section-title {
    font-size: 11px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 10px;
    margin-top: 4px;
}
.badge-critical { background:#3d0e0e; color:#f85149; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700; }
.badge-ok { background:#0d4429; color:#3fb950; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700; }
.badge-open { background:#3d0e0e; color:#f85149; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700; }
.badge-resolved { background:#0d4429; color:#3fb950; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:700; }

/* ══ NUCLEAR FIX: Streamlit Material Icon text leak (arrow_right / expand_more) ══
   The icon glyph text is injected as a Material Symbols ligature. When the font
   fails to resolve, the raw text renders. We kill it at every layer.            */

/* 1. Bulletproof expander clearing: Force-zero ALL text inside any summary descendant to beat Streamlit's inline classes */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary * {
    font-size: 0 !important;
    line-height: 0 !important;
    color: transparent !important;
}

/* 2. Restore visibility ONLY for the actual label (Streamlit wraps it in a p tag) */
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary p * {
    font-size: 13px !important;
    line-height: 1.5 !important;
    color: #e6edf3 !important;
    margin: 0 !important;
    display: inline-block !important;
}

/* 3. Also catch any SVG that Streamlit uses as an arrow and hide it entirely */
[data-testid="stExpander"] summary svg,
[data-testid="stExpanderToggleIcon"] {
    display: none !important;
}

/* 3. Draw our own clean chevron via pseudo-element so collapse still looks right */
[data-testid="stExpander"] details summary::after {
    content:        "›";
    font-size:      18px;
    color:          #8b949e;
    margin-left:    auto;
    padding-left:   10px;
    transform:      rotate(90deg);
    display:        inline-block;
    transition:     transform 0.2s ease;
    line-height:    1;
    font-family:    monospace;
}
[data-testid="stExpander"] details[open] summary::after {
    transform: rotate(270deg);
}
[data-testid="stExpander"] details summary {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    padding: 10px 16px !important;
    color: #e6edf3 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}
[data-testid="stExpander"] details[open] summary {
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
    border-bottom-color: #21262d !important;
}
[data-testid="stExpander"] details > div {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-top: none !important;
    border-bottom-left-radius: 8px !important;
    border-bottom-right-radius: 8px !important;
    padding: 12px 16px !important;
}
/* Fix dataframe table colours */
[data-testid="stDataFrame"] * { color: #c9d1d9 !important; }
</style>
""", unsafe_allow_html=True)

# ─── DATA LOADING ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def get_incidents():
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query("SELECT * FROM incidents ORDER BY ticket_id DESC", conn)
    conn.close()
    return df

@st.cache_data(ttl=10)
def get_device_health():
    try:
        with open(DEVICE_HEALTH_JSON, "r") as f:
            return json.load(f).get("response", [])
    except:
        return []

df      = get_incidents()
devices = get_device_health()
open_df = df[df['status'] == 'OPEN']
res_df  = df[df['status'] == 'RESOLVED']

# ─── COMPUTED STATS ───────────────────────────────────────────────────────────
avg_mttr = round(res_df['mttr_minutes'].mean(), 2) if not res_df.empty and 'mttr_minutes' in res_df.columns else None
mttr_str = f"{avg_mttr} min" if avg_mttr is not None else "-- min"

# Find failing device from latest open ticket
latest_dev  = None
failing_cpu = 26.0
if not open_df.empty:
    try:
        log         = json.loads(open_df.iloc[0]['raw_error_log'])
        latest_dev  = open_df.iloc[0]['device_name']
        failing_cpu = float(log.get('cpuUtilization', 90.0))
    except:
        failing_cpu = 90.0

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ Intelli-Net")
    st.markdown("<p style='color:#8b949e;font-size:11px'>Smart Incident & Telemetry<br>Response Orchestrator</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"<p style='color:#8b949e;font-size:11px'>SITE</p><p style='color:#e6edf3;font-size:13px'>SRM-IST-Lab</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8b949e;font-size:11px'>DEVICES</p><p style='color:#e6edf3;font-size:13px'>4 Catalyst 9000</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8b949e;font-size:11px'>AVG MTTR</p><p style='color:#d29922;font-size:13px'>{mttr_str}</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<p style='color:#8b949e;font-size:10px'>TEAM</p>", unsafe_allow_html=True)
    st.markdown("<p style='color:#c9d1d9;font-size:11px'>Tarang Patra<br>Pranav K. Roy<br>Karthik Saravanamuthu</p>", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

# ─── TOP BAR ──────────────────────────────────────────────────────────────────
now_str = datetime.now(timezone.utc).strftime("%b %d, %Y · %H:%M UTC")
status_color = "#f85149" if not open_df.empty else "#3fb950"
status_text  = f"⚠ {len(open_df)} OPEN INCIDENT{'S' if len(open_df)>1 else ''}" if not open_df.empty else "● ALL SYSTEMS HEALTHY"

st.markdown(f"""
<div class="topbar">
    <div style="display:flex;align-items:center;gap:20px">
        <span style="font-size:16px;font-weight:700;color:#58a6ff;letter-spacing:2px">Intelli-Net</span>
        <span style="font-size:11px;color:#8b949e">Cisco Catalyst Center · SRM-IST-Lab</span>
    </div>
    <div style="display:flex;gap:24px;align-items:center">
        <span style="font-size:11px;color:#8b949e">DEVICES <span style="color:#e6edf3;font-weight:700">4</span></span>
        <span style="font-size:11px;color:#8b949e">OPEN <span style="color:#f85149;font-weight:700">{len(open_df)}</span></span>
        <span style="font-size:11px;color:#8b949e">RESOLVED <span style="color:#3fb950;font-weight:700">{len(res_df)}</span></span>
        <span style="font-size:11px;color:#8b949e">AVG MTTR <span style="color:#d29922;font-weight:700">{mttr_str}</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:12px">
        <span style="font-size:11px;color:{status_color};font-weight:700">{status_text}</span>
        <span style="font-size:11px;color:#8b949e">{now_str}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── DEVICE CARDS ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Node Health Matrix</div>', unsafe_allow_html=True)

device_map = {d['name']: d for d in devices}
device_names = ['sw1', 'sw2', 'sw3', 'sw4']
cols = st.columns(4)

for i, name in enumerate(device_names):
    d           = device_map.get(name, {})
    cpu         = float(d.get('cpuUtilization') or 26.0)
    memory      = round(float(d.get('memoryUtilization') or 67.0), 1)
    reach       = d.get('reachabilityHealth', 'REACHABLE')
    ip          = d.get('ipAddress', '—')
    is_critical = (name == latest_dev) or (reach == 'UNREACHABLE')
    is_warn     = cpu > 70 and not is_critical
    card_class  = "device-card-critical" if is_critical else ("device-card-warning" if is_warn else "device-card")
    badge       = '<span class="badge-critical">CRITICAL</span>' if is_critical else '<span class="badge-ok">HEALTHY</span>'
    cpu_color   = "#f85149" if is_critical else ("#d29922" if is_warn else "#3fb950")
    bar_color   = "#f85149" if is_critical else ("#d29922" if is_warn else "#3fb950")
    cpu_pct     = float(failing_cpu if is_critical else cpu)
    bar_width   = min(max(int(cpu_pct), 0), 100)

    with cols[i]:
        st.markdown(f"""
        <div class="{card_class}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <span style="font-size:15px;font-weight:700;color:{'#f85149' if is_critical else '#e6edf3'}">{name}</span>
                {badge}
            </div>
            <div style="font-size:10px;color:#8b949e;margin-bottom:10px">{ip} · Catalyst 9000</div>
            <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                <span style="font-size:11px;color:#8b949e">CPU</span>
                <span style="font-size:11px;font-weight:700;color:{cpu_color}">{round(cpu_pct, 1)}%</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                <span style="font-size:11px;color:#8b949e">Memory</span>
                <span style="font-size:11px;font-weight:700;color:#e6edf3">{memory}%</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span style="font-size:11px;color:#8b949e">Status</span>
                <span style="font-size:11px;font-weight:700;color:{'#f85149' if reach=='UNREACHABLE' else '#3fb950'}">{reach}</span>
            </div>
            <div style="height:3px;background:#21262d;border-radius:2px">
                <div style="height:3px;width:{bar_width}%;background:{bar_color};border-radius:2px"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── CHARTS ROW ───────────────────────────────────────────────────────────────
col_chart1, col_chart2 = st.columns([2, 1])

with col_chart1:
    st.markdown('<div class="section-title">CPU Telemetry Feed</div>', unsafe_allow_html=True)
    np.random.seed(42)
    x    = list(range(20))
    base = 26 + np.random.uniform(-0.5, 0.5, 20)

    fig = go.Figure()
    colors = {'sw1': '#3fb950', 'sw2': '#f85149', 'sw3': '#58a6ff', 'sw4': '#8957e5'}

    for dname in device_names:
        if dname == latest_dev:
            y = [failing_cpu + np.random.uniform(-1, 1) for _ in x]
        else:
            y = (base + np.random.uniform(-0.3, 0.3, 20)).tolist()

        fig.add_trace(go.Scatter(
            x=x, y=y, name=dname,
            line=dict(color=colors[dname], width=2 if dname == latest_dev else 1),
            opacity=1.0 if dname == latest_dev else 0.5
        ))

    fig.update_layout(
        paper_bgcolor='#161b22', plot_bgcolor='#161b22',
        font=dict(color='#8b949e', size=10, family='JetBrains Mono'),
        margin=dict(l=40, r=20, t=10, b=30),
        height=200,
        legend=dict(orientation='h', y=-0.3, font=dict(size=10)),
        xaxis=dict(showgrid=False, zeroline=False, color='#8b949e'),
        yaxis=dict(showgrid=True, gridcolor='#21262d', zeroline=False, color='#8b949e'),
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

with col_chart2:
    st.markdown('<div class="section-title">Ticket History</div>', unsafe_allow_html=True)
    if not df.empty:
        ticket_counts = df.groupby('status').size().reset_index(name='count')
        open_count    = int(ticket_counts[ticket_counts['status'] == 'OPEN']['count'].sum()) if 'OPEN' in ticket_counts['status'].values else 0
        res_count     = int(ticket_counts[ticket_counts['status'] == 'RESOLVED']['count'].sum()) if 'RESOLVED' in ticket_counts['status'].values else 0

        fig2 = go.Figure(data=[
            go.Bar(
                name='Open',
                x=['Open'],
                y=[open_count],
                marker_color='#f85149',
                text=[f'{open_count} ticket{"s" if open_count != 1 else ""}'],
                textposition='outside',
                textfont=dict(color='#f85149', size=11, family='JetBrains Mono'),
                cliponaxis=False,
            ),
            go.Bar(
                name='Resolved',
                x=['Resolved'],
                y=[res_count],
                marker_color='#3fb950',
                text=[f'{res_count} ticket{"s" if res_count != 1 else ""}'],
                textposition='outside',
                textfont=dict(color='#3fb950', size=11, family='JetBrains Mono'),
                cliponaxis=False,
            ),
        ])
        fig2.update_layout(
            paper_bgcolor='#161b22', plot_bgcolor='#161b22',
            font=dict(color='#8b949e', size=10, family='JetBrains Mono'),
            margin=dict(l=20, r=20, t=30, b=10),
            height=200, showlegend=False, barmode='group',
            xaxis=dict(
                showgrid=False, zeroline=False,
                tickfont=dict(size=11, family='JetBrains Mono'),
                tickvals=['Open', 'Resolved'],
                ticktext=[
                    '<span style="color:#f85149;font-weight:bold">OPEN</span>',
                    '<span style="color:#3fb950;font-weight:bold">RESOLVED</span>',
                ],
            ),
            yaxis=dict(
                showgrid=True, gridcolor='#21262d', zeroline=False,
                color='#8b949e', title='Tickets',
                title_font=dict(size=9, color='#8b949e'),
            ),
        )
        st.plotly_chart(fig2, width="stretch", config={'displayModeBar': False})

# ─── ACTIVE INCIDENTS ─────────────────────────────────────────────────────────
def _sanitize_ai(text, fallback):
    """Return a clean AI analysis string; mask raw API/SDK error traces."""
    if not pd.notna(text) or not text:
        return fallback
    lowered = text.lower()
    if any(k in lowered for k in ("error code:", "invalid api key", "invalid_api_key",
                                    "error processing telemetry", "openai", "groq")):
        return "⚠ AI analysis unavailable — Groq API key not configured. Set GROQ_API_KEY in .env"
    return text

if not open_df.empty:
    st.markdown('<div class="section-title">Active Incidents</div>', unsafe_allow_html=True)
    for _, ticket in open_df.iterrows():
        ai = _sanitize_ai(ticket['ai_root_cause'], "AI analysis pending — run core/genai.py")
        st.markdown(f"""
        <div class="incident-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-size:13px;font-weight:700;color:#f85149">🚨 TICKET #{ticket['ticket_id']} — {ticket['device_name']} ({ticket['ip_address']})</span>
                    <span class="badge-critical">OPEN</span>
                </div>
                <span style="font-size:10px;color:#8b949e">{ticket['created_at']} UTC</span>
            </div>
            <div class="ai-box">
                <div style="font-size:10px;color:#58a6ff;font-weight:700;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px">⚡ AI Root Cause Analysis — Groq LLaMA 3</div>
                {ai.replace(chr(10), '<br>')}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─── RESOLVED INCIDENTS ───────────────────────────────────────────────────────
if not res_df.empty:
    with st.expander(f"Resolved Incidents ({len(res_df)})"):
        for _, ticket in res_df.iterrows():
            ai = _sanitize_ai(ticket['ai_root_cause'], "—")
            mttr_display = f"{ticket['mttr_minutes']:.2f}" if pd.notna(ticket['mttr_minutes']) else '—'
            st.markdown(f"""
            <div class="incident-card-resolved">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <div style="display:flex;align-items:center;gap:10px">
                        <span style="font-size:13px;font-weight:700;color:#3fb950">✅ TICKET #{ticket['ticket_id']} — {ticket['device_name']} ({ticket['ip_address']})</span>
                        <span class="badge-resolved">RESOLVED</span>
                    </div>
                    <span style="font-size:10px;color:#8b949e">MTTR: {mttr_display} min</span>
                </div>
                <div class="ai-box">{ai.replace(chr(10), '<br>')}</div>
            </div>
            """, unsafe_allow_html=True)

# ─── AUDIT LOG ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Full Audit Log</div>', unsafe_allow_html=True)
if not df.empty:
    display_df = df[['ticket_id', 'device_name', 'ip_address', 'status', 'created_at', 'resolved_at', 'mttr_minutes']].copy()
    display_df.columns = ['Ticket ID', 'Device', 'IP', 'Status', 'Created', 'Resolved', 'MTTR (min)']
    # Format as string so pandas doesn't render floats with 6 decimal places
    display_df['MTTR (min)'] = display_df['MTTR (min)'].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else '—'
    )

    def style_row(row):
        styles = [''] * len(row)
        idx = display_df.columns.get_loc('Status')
        if row['Status'] == 'OPEN':
            styles[idx] = 'color: #f85149; font-weight: bold'
        else:
            styles[idx] = 'color: #3fb950; font-weight: bold'
        return styles

    st.dataframe(
        display_df.style.apply(style_row, axis=1).set_properties(**{
            'background-color': '#161b22',
            'color': '#c9d1d9',
            'border-color': '#21262d',
            'font-size': '12px'
        }),
        width="stretch",
        hide_index=True
    )
else:
    st.markdown("<p style='color:#8b949e;font-size:12px'>No incidents recorded yet. Run simulate_failure.py to begin.</p>", unsafe_allow_html=True)
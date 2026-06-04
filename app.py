# app.py — InnoVentures Meeting Intelligence Agent
import streamlit as st
import asyncio
import os
import time
import tempfile
import base64
from pathlib import Path

from pipeline.transcribe import transcribe_audio
from pipeline.extract import extract_meeting_data
from pipeline.template import populate_mom_template

from utils.email_sender import send_mom_email

# ─── Page Config ──────────────────────────────────────────
st.set_page_config(
    page_title="Meeting Agent · InnoVentures",
    page_icon="🔁",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Load logo as base64 for embedding ────────────────────
def get_logo_b64():
    logo_path = Path("assets/InnoVentures_Logo.png")
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

logo_b64 = get_logo_b64()

# ─── Custom CSS ───────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ── Root & Reset ── */
:root {
    --navy:     #0A1628;
    --navy-mid: #0F1E38;
    --navy-card:#132040;
    --teal:     #00C2C7;
    --teal-dim: #00878a;
    --blue:     #1B4F8A;
    --white:    #FFFFFF;
    --gray-100: #E8EDF5;
    --gray-400: #8A9BB5;
    --gray-600: #4A5E7A;
    --success:  #22C55E;
    --warning:  #F59E0B;
    --radius:   12px;
}

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: var(--navy) !important;
    color: var(--gray-100) !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Main container ── */
.block-container {
    max-width: 760px !important;
    padding: 0 1.5rem 4rem !important;
    margin: 0 auto !important;
}

/* ── Header banner ── */
.inv-header {
    background: linear-gradient(135deg, var(--navy-mid) 0%, var(--navy) 100%);
    border-bottom: 1px solid rgba(0,194,199,0.2);
    padding: 1.5rem 0 1.2rem;
    margin: 0 -1.5rem 2rem;
    text-align: center;
}
.inv-header img { height: 36px; margin-bottom: 0.5rem; }
.inv-tagline {
    font-size: 0.78rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--teal);
    font-weight: 500;
}
.inv-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--white);
    margin: 0.5rem 0 0;
    letter-spacing: -0.02em;
}
.inv-subtitle {
    font-size: 0.88rem;
    color: var(--gray-400);
    margin-top: 0.25rem;
}

/* ── Cards ── */
.inv-card {
    background: var(--navy-card);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.inv-card-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 0.75rem;
}

/* ── Metrics row ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin: 1rem 0;
}
.metric-box {
    background: var(--navy-card);
    border: 1px solid rgba(0,194,199,0.15);
    border-radius: 8px;
    padding: 0.85rem;
    text-align: center;
}
.metric-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--teal);
    line-height: 1;
}
.metric-lbl {
    font-size: 0.72rem;
    color: var(--gray-400);
    margin-top: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── Section heading ── */
.section-heading {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--teal);
    border-bottom: 1px solid rgba(0,194,199,0.15);
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 0.75rem;
}

/* ── Bullet items ── */
.inv-item {
    padding: 0.6rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    font-size: 0.9rem;
    color: var(--gray-100);
    line-height: 1.55;
}
.inv-item:last-child { border-bottom: none; }

/* ── Action item row ── */
.action-row {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
    padding: 0.75rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.action-row:last-child { border-bottom: none; }
.action-dot {
    width: 8px; height: 8px;
    background: var(--teal);
    border-radius: 50%;
    margin-top: 0.4rem;
    flex-shrink: 0;
}
.action-task { font-size: 0.9rem; color: var(--white); font-weight: 500; }
.action-assignee { font-size: 0.8rem; color: var(--teal-dim); margin-top: 0.15rem; }

/* ── Meeting title bar ── */
.meeting-title-bar {
    background: linear-gradient(90deg, var(--navy-card) 0%, rgba(0,194,199,0.05) 100%);
    border-left: 3px solid var(--teal);
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1.2rem;
    margin-bottom: 1rem;
}
.meeting-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--white);
}
.meeting-meta { font-size: 0.8rem; color: var(--gray-400); margin-top: 0.2rem; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--navy-card) !important;
    border-radius: 8px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--gray-400) !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.4rem 1rem !important;
}
.stTabs [aria-selected="true"] {
    background: var(--teal) !important;
    color: var(--navy) !important;
    font-weight: 600 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--navy-card) !important;
    border: 2px dashed rgba(0,194,199,0.3) !important;
    border-radius: var(--radius) !important;
    padding: 0.5rem !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--teal) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--teal) !important;
    color: var(--navy) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: 0.02em !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: var(--teal-dim) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:disabled {
    background: var(--gray-600) !important;
    color: var(--gray-400) !important;
    transform: none !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: transparent !important;
    color: var(--teal) !important;
    border: 1.5px solid var(--teal) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    background: rgba(0,194,199,0.1) !important;
}

/* ── Text area + text input ── */
.stTextArea textarea, .stTextInput input {
    background: var(--navy-card) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: var(--white) !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 2px rgba(0,194,199,0.15) !important;
}

/* ── Status / expander ── */
[data-testid="stExpander"] {
    background: var(--navy-card) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: var(--radius) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 500 !important;
    color: var(--gray-100) !important;
}

/* ── Progress bar ── */
.stProgress > div > div > div {
    background: var(--teal) !important;
}
.stProgress > div > div {
    background: rgba(0,194,199,0.15) !important;
    border-radius: 4px !important;
}

/* ── Status box ── */
[data-testid="stStatusWidget"] { display: none; }
.stStatus { background: var(--navy-card) !important; border-radius: var(--radius) !important; }

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.07) !important; margin: 1.5rem 0 !important; }

/* ── Footer ── */
.inv-footer {
    text-align: center;
    padding: 1.5rem 0 0;
    font-size: 0.75rem;
    color: var(--gray-600);
    border-top: 1px solid rgba(255,255,255,0.06);
    margin-top: 2rem;
}
.inv-footer span { color: var(--teal); }
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────
if logo_b64:
    st.markdown(f"""
    <div class="inv-header">
        <img src="data:image/png;base64,{logo_b64}" alt="InnoVentures" />
        <div class="inv-tagline">Internal Tool · AI Department</div>
        <div class="inv-title">Meeting Intelligence Agent</div>
        <div class="inv-subtitle">Audio or notes → professional Minutes of Meeting in seconds</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="inv-header">
        <div style="font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:700;color:white;letter-spacing:-0.02em">
            INNOVE<span style="color:#00C2C7">∞</span>TURES
        </div>
        <div class="inv-tagline" style="margin-top:0.4rem">Internal Tool · AI Department</div>
        <div class="inv-title">Meeting Intelligence Agent</div>
        <div class="inv-subtitle">Audio or notes → professional Minutes of Meeting in seconds</div>
    </div>
    """, unsafe_allow_html=True)

# ─── Input Section ────────────────────────────────────────
tab_audio, tab_text = st.tabs(["  🎙️  Upload Recording  ", "  📝  Paste Notes  "])

audio_file = None
text_input = None

with tab_audio:
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    audio_file = st.file_uploader(
        "Drag and drop or click to upload",
        type=["mp3", "wav", "m4a", "mp4", "ogg", "webm", "flac", "aac"],
        label_visibility="visible",
    )
    if audio_file:
        st.audio(audio_file)
        st.markdown(f"<div style='font-size:0.8rem;color:#8A9BB5;margin-top:0.5rem'>📎 {audio_file.name} · {audio_file.size/1024/1024:.1f} MB</div>", unsafe_allow_html=True)

with tab_text:
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    text_input = st.text_area(
        "Paste transcript or meeting notes",
        height=220,
        placeholder="Paste your meeting notes or transcript here...",
        label_visibility="visible",
    )

# ─── Generate Button ──────────────────────────────────────
st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
can_process = audio_file is not None or (text_input and text_input.strip())

if st.button(
    "Generate Minutes of Meeting →",
    type="primary",
    disabled=not can_process,
    use_container_width=True,
):
    progress = st.progress(0)
    status = st.status("Processing...", expanded=True)
    start_time = time.time()

    try:
        if audio_file:
            status.write("🎙️ Transcribing audio with Gemini Pro...")
            progress.progress(10)

            suffix = os.path.splitext(audio_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_file.getbuffer())
                tmp_path = tmp.name

            transcript = asyncio.run(transcribe_audio(tmp_path))
            os.unlink(tmp_path)
        else:
            status.write("📝 Reading text input...")
            transcript = text_input

        progress.progress(33)
        status.write(f"✅ Transcript ready · {len(transcript):,} characters")

        status.write("🧠 Extracting meeting data with Claude Haiku...")
        progress.progress(45)

        meeting_data = asyncio.run(extract_meeting_data(transcript))

        progress.progress(70)
        status.write(f"✅ Extracted · {len(meeting_data.action_items)} actions · {len(meeting_data.decisions)} decisions")

        status.write("📄 Generating MoM document...")
        progress.progress(85)

        doc_path = populate_mom_template(meeting_data)
        progress.progress(100)
        elapsed = time.time() - start_time

        # Cost
        is_audio = audio_file is not None
        if is_audio:
            audio_tokens = int(audio_file.size / 16000) * 25
            cost_t = (audio_tokens / 1_000_000) * 1.25 + (len(transcript) // 4 / 1_000_000) * 5.0
        else:
            cost_t = 0
        cost_e = ((len(transcript) // 4 + 500) / 1_000_000) * 0.80 + (1500 / 1_000_000) * 4.0
        total_cost = cost_t + cost_e

        status.update(label="✅ MoM ready", state="complete")

        with open(doc_path, "rb") as f:
            doc_bytes = f.read()

        st.session_state["results"] = {
            "meeting_data": meeting_data,
            "doc_bytes": doc_bytes,
            "doc_filename": os.path.basename(doc_path),
            "elapsed": elapsed,
            "total_cost": total_cost,
        }

    except Exception as e:
        status.update(label="❌ Error", state="error")
        st.error(f"{str(e)}")

# ─── Results ──────────────────────────────────────────────
if "results" in st.session_state:
    r = st.session_state["results"]
    d = r["meeting_data"]

    # Meeting title bar
    st.markdown(f"""
    <div class="meeting-title-bar">
        <div class="meeting-name">{d.title}</div>
        <div class="meeting-meta">{d.date} &nbsp;·&nbsp; {len(d.attendees)} attendees &nbsp;·&nbsp; Generated in {r['elapsed']:.0f}s</div>
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-box"><div class="metric-val">{len(d.action_items)}</div><div class="metric-lbl">Actions</div></div>
        <div class="metric-box"><div class="metric-val">{len(d.decisions)}</div><div class="metric-lbl">Decisions</div></div>
        <div class="metric-box"><div class="metric-val">{len(d.follow_ups)}</div><div class="metric-lbl">Follow-ups</div></div>
        <div class="metric-box"><div class="metric-val">${r['total_cost']:.3f}</div><div class="metric-lbl">Cost</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Attendees
    st.markdown('<div class="section-heading">Attendees</div>', unsafe_allow_html=True)
    attendee_html = "".join(f'<div class="inv-item">👤 {a}</div>' for a in d.attendees)
    st.markdown(f'<div class="inv-card">{attendee_html}</div>', unsafe_allow_html=True)

    # Agenda
    st.markdown('<div class="section-heading">Agenda</div>', unsafe_allow_html=True)
    agenda_html = "".join(f'<div class="inv-item">· {a}</div>' for a in d.agenda)
    st.markdown(f'<div class="inv-card">{agenda_html}</div>', unsafe_allow_html=True)

    # Discussion
    st.markdown('<div class="section-heading">Discussion Points</div>', unsafe_allow_html=True)
    disc_html = "".join(f'<div class="inv-item">• {dp}</div>' for dp in d.discussion_points)
    st.markdown(f'<div class="inv-card">{disc_html}</div>', unsafe_allow_html=True)

    # Decisions
    st.markdown('<div class="section-heading">Decisions Made</div>', unsafe_allow_html=True)
    dec_html = "".join(f'<div class="inv-item">✓ {dec}</div>' for dec in d.decisions)
    st.markdown(f'<div class="inv-card">{dec_html}</div>', unsafe_allow_html=True)

    # Action Items
    st.markdown('<div class="section-heading">Action Items</div>', unsafe_allow_html=True)
    action_html = "".join(
        f'<div class="action-row"><div class="action-dot"></div><div><div class="action-task">{ai.task}</div><div class="action-assignee">→ {ai.assignee}</div></div></div>'
        for ai in d.action_items
    )
    st.markdown(f'<div class="inv-card">{action_html}</div>', unsafe_allow_html=True)

    # Follow-ups
    st.markdown('<div class="section-heading">Follow-ups</div>', unsafe_allow_html=True)
    fu_html = "".join(f'<div class="inv-item">🔄 {fu}</div>' for fu in d.follow_ups)
    st.markdown(f'<div class="inv-card">{fu_html}</div>', unsafe_allow_html=True)

    # Download + Email
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])

    with col1:
        st.download_button(
            label="📥  Download MoM Document",
            data=r["doc_bytes"],
            file_name=r["doc_filename"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    with col2:
        if st.button("🔄  New Meeting", use_container_width=True):
            del st.session_state["results"]
            st.rerun()

    # Email section
    with st.expander("📧 Send via Email", expanded=False):

        recipients = st.text_input(
            "Recipients (comma-separated emails)",
            placeholder="Tariq@innoventures.ae, client@company.com",
        )

        email_note = st.text_area(
            "Message",
            value=(
                f"Hi,\n\n"
                f"Please find attached the Minutes of Meeting for "
                f"\"{d.title}\" held on {d.date}.\n\n"
                f"Best regards,\n"
                f"InnoVentures"
            ),
            height=120,
        )

        if st.button("📤 Send Email", disabled=not recipients):

            try:
                emails = [
                    email.strip()
                    for email in recipients.split(",")
                    if email.strip()
                ]

                send_mom_email(
                    recipients=emails,
                    subject=f"Minutes of Meeting - {d.title}",
                    body=email_note,
                    doc_bytes=r["doc_bytes"],
                    filename=r["doc_filename"],
                )

                st.success("✅ Email sent successfully!")

            except Exception as e:
                st.error(f"Email failed: {str(e)}")

# ─── Footer ───────────────────────────────────────────────
st.markdown("""
<div class="inv-footer">
    Meeting Intelligence Agent · AGT-009 · <span>InnoVentures</span> AI Department<br>
    Powered by Gemini 2.5 Pro · Claude Haiku 4.5
</div>
""", unsafe_allow_html=True)
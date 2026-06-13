import streamlit as st
import threading
import queue
import os

from pipeline import run_pipeline
from models import Lead

st.set_page_config(page_title="LinkedIn Lead Finder", page_icon="🔍", layout="wide")

st.title("🔍 LinkedIn Lead Finder")
st.caption("Finds Open-to-Work AI/ML engineers in India with verified emails.")

with st.sidebar:
    st.header("⚙️ Configuration")
    apify_token = st.text_input("Apify API Token", type="password",
                                 value=os.getenv("APIFY_API_TOKEN", ""))
    prospeo_key = st.text_input("Prospeo API Key", type="password",
                                 value=os.getenv("PROSPEO_API_KEY", ""))
    st.caption("Prospeo free tier: 50 enrich requests/day. "
               "Pipeline stops automatically when the limit is hit.")

run_btn = st.button("▶️ Run Pipeline", type="primary",
                    disabled=not (apify_token and prospeo_key))

if run_btn:
    log_queue: queue.Queue = queue.Queue()
    results: list = []
    errors: list  = []

    def _run():
        def log(msg):
            log_queue.put(("log", msg))
        try:
            leads = run_pipeline(apify_token, prospeo_key, log=log)
            log_queue.put(("done", leads))
        except Exception as exc:
            log_queue.put(("error", str(exc)))

    thread = threading.Thread(target=_run)
    thread.start()

    log_placeholder = st.empty()
    log_lines: list[str] = []

    while thread.is_alive() or not log_queue.empty():
        try:
            kind, payload = log_queue.get(timeout=0.2)
            if kind == "log":
                log_lines.append(payload)
                log_placeholder.code("\n".join(log_lines), language=None)
            elif kind == "done":
                results.extend(payload)
                break
            elif kind == "error":
                errors.append(payload)
                break
        except queue.Empty:
            continue

    thread.join()

    if errors:
        st.error(f"Pipeline error: {errors[0]}")
    elif not results:
        st.warning("No leads with verified emails found.")
    else:
        st.success(f"✅ Found {len(results)} lead(s) with verified emails!")

        st.subheader("📋 Results")
        rows = [
            {
                "Name":     l.full_name,
                "Headline": l.headline,
                "Company":  l.company_name or "—",
                "Location": l.location,
                "Email":    l.email or "—",
                "LinkedIn": l.url,
            }
            for l in results
        ]
        st.dataframe(rows, use_container_width=True)

        st.subheader("🧑‍💼 Lead Cards")
        for lead in results:
            with st.expander(f"{lead.full_name} — {lead.headline}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Company:** {lead.company_name or '—'}")
                    st.write(f"**Location:** {lead.location}")
                with col2:
                    st.write(f"**Email:** `{lead.email}`")
                    st.markdown(f"[LinkedIn Profile]({lead.url})")
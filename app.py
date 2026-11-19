import json
import os
import secrets
import sqlite3
import streamlit as st
from core import NOTES, SAMPLE, SOURCES, STATUSES, compare, export

st.set_page_config(page_title="Scope review", layout="centered")
postgres = os.getenv("DATABASE_URL")
def database():
    if postgres:
        import psycopg
        return psycopg.connect(postgres)
    return sqlite3.connect("reviews.sqlite")
marker = "%s" if postgres else "?"
token = st.query_params.get("review", "")
if len(token)!=43 or not all(c.isalnum() or c in "-_" for c in token):
    token = secrets.token_urlsafe(32)
    st.query_params["review"] = token
def save(data):
    with database() as db:
        db.execute(f"INSERT INTO reviews VALUES ({marker},{marker}) ON CONFLICT(id) DO UPDATE SET body=excluded.body",(token,json.dumps(data)))
def draft(notes,rows,mode):
    return dict(notes=notes, mode=mode, timeline="", version=secrets.token_hex(6), items=[dict(quote=q,source=s,wording=w,status=STATUSES[0]) for q,s,w in rows])
with database() as db:
    db.execute("CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
    record = db.execute(f"SELECT body FROM reviews WHERE id={marker}",(token,)).fetchone()
if record:
    review = json.loads(record[0])
else:
    review = draft(NOTES, SAMPLE, "Prepared sample")
    # Form widget keys must stay stable across the first submit rerun.
    save(review)
st.title("ScopeTrace")
st.caption("Synthetic customer project · Anyone with this private review link can edit this draft.")
with st.expander("Sales, contract and historical evidence"):
    for source, passage in SOURCES.items():
        st.markdown(f"**{source}**")
        st.write(passage)
notes = st.text_area("Discovery notes",review["notes"],max_chars=10000)
if st.button("Analyze discovery",disabled=not notes.strip() or not os.getenv("OPENAI_API_KEY")):
    try:
        with st.spinner("Comparing discovery with project evidence"):
            rows = compare(notes)
        review = draft(notes,rows,"Live analysis")
        save(review)
        st.rerun()
    except Exception:
        st.error("Analysis could not be completed. Your saved review is available below. Retry when ready.")
if not os.getenv("OPENAI_API_KEY"):
    st.caption("Sample review available. Live analysis requires a server-side OpenAI key.")
st.subheader(review["mode"])
st.caption("A successful new analysis starts a fresh draft for this link. Download your current draft first.")
with st.form("decisions-"+review["version"]):
    for index,item in enumerate(review["items"]):
        st.markdown(f"**Discovery finding {index+1}**")
        st.write(item["quote"])
        st.info(item["source"]+" · "+SOURCES.get(item["source"],"No supporting source identified."))
        item["status"]=st.selectbox("Scope decision",STATUSES,index=STATUSES.index(item["status"]),key=f'{review["version"]}-s{index}')
        item["wording"]=st.text_area("Wording for the scope document",item["wording"],key=f'{review["version"]}-w{index}')
    review["timeline"]=st.text_area("Customer data needs and timeline implications",review["timeline"])
    if st.form_submit_button("Save review"):
        save(review)
        st.rerun()
if record:
    st.download_button("Download saved Word draft",export(json.loads(record[0])),file_name="Implementation-scope.docx")

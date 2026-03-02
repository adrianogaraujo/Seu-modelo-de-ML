from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = st.secrets.get("api_base_url", "http://api:8000")

st.set_page_config(page_title="Risco Credito AM", layout="wide")
st.title("Nowcasting de Risco de Credito - Amazonas")

col1, col2 = st.columns(2)
with col1:
    if st.button("Executar Pipeline"):
        resp = requests.post(f"{API_BASE_URL}/pipeline/run", timeout=120)
        st.json(resp.json())

with col2:
    month = st.text_input("Mes de referencia (YYYY-MM)", value="2026-01")
    if st.button("Gerar Nowcast"):
        payload = {"reference_month": month}
        resp = requests.post(f"{API_BASE_URL}/predict/nowcast", json=payload, timeout=30)
        st.json(resp.json())

st.subheader("Serie Historica")
from_month = st.text_input("Inicio", value="2024-01")
to_month = st.text_input("Fim", value="2026-01")
if st.button("Consultar Serie"):
    resp = requests.get(
        f"{API_BASE_URL}/series/target",
        params={"from": from_month, "to": to_month},
        timeout=30,
    )
    data = resp.json()
    st.dataframe(data.get("points", []), use_container_width=True)


from __future__ import annotations

import os

import requests
import streamlit as st


API_BASE_URL = st.secrets.get("api_base_url", os.getenv("API_BASE_URL", "http://api:8000"))


st.set_page_config(page_title="Risco Credito AM", layout="wide")
st.title("Nowcasting de Risco de Credito - Amazonas")


def _show_response(resp: requests.Response) -> None:
    """Show JSON payload on success, and HTTP detail on errors."""
    try:
        payload = resp.json()
    except ValueError:
        payload = {"detail": resp.text}

    if resp.ok:
        st.json(payload)
        return

    detail = payload.get("detail") if isinstance(payload, dict) else None
    if detail is None:
        detail = payload
    st.error(f"HTTP {resp.status_code}: {detail}")


col1, col2 = st.columns(2)
with col1:
    if st.button("Executar Pipeline"):
        response = requests.post(f"{API_BASE_URL}/pipeline/run", timeout=120)
        _show_response(response)

with col2:
    month = st.text_input("Mes de referencia (YYYY-MM)", value="2026-01")
    if st.button("Gerar Nowcast"):
        payload = {"reference_month": month}
        response = requests.post(f"{API_BASE_URL}/predict/nowcast", json=payload, timeout=30)
        _show_response(response)

st.subheader("Serie Historica")
from_month = st.text_input("Inicio", value="2024-01")
to_month = st.text_input("Fim", value="2026-01")
if st.button("Consultar Serie"):
    response = requests.get(
        f"{API_BASE_URL}/series/target",
        params={"from": from_month, "to": to_month},
        timeout=30,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text}

    if response.ok:
        st.dataframe(payload.get("points", []), use_container_width=True)
    else:
        detail = payload.get("detail") if isinstance(payload, dict) else payload
        st.error(f"HTTP {response.status_code}: {detail}")

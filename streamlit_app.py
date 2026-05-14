import json
import requests
import pandas as pd
import streamlit as st


API_URL = "http://127.0.0.1:8000/api/v1/market-rent/estimate"


st.set_page_config(
    page_title="Market Rent Engine",
    layout="wide",
)

st.title("Industrial Market Rent Engine")

st.markdown(
    """
    Transparent industrial lease comp adjustment engine with
    audit trail, confidence scoring, and adjustment waterfall.
    """
)


target_asset = {
    "address": "4150 S 51st Ave, Phoenix, AZ 85043",
    "submarket": "Sky Harbor",
    "total_sf": 145000,
    "year_built": 2008,
    "clear_height_ft": 32,
    "as_of": "2025-09-30",
}


response = requests.post(API_URL, json=target_asset)

if response.status_code != 200:
    st.error(response.text)
    st.stop()

data = response.json()


point = data["point_estimate_psf_yr"]
low = data["low_psf_yr"]
high = data["high_psf_yr"]
confidence = data["confidence"]


col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Estimated Market Rent",
        f"${point} PSF/YR",
    )

with col2:
    st.metric(
        "Range",
        f"${low} - ${high}",
    )

with col3:
    st.metric(
        "Confidence",
        f"{float(confidence) * 100:.0f}%",
    )


st.divider()

st.subheader("Adjustment Waterfall")

waterfall_df = pd.DataFrame(data["waterfall"])

st.dataframe(
    waterfall_df,
    use_container_width=True,
    hide_index=True,
)


st.divider()

st.subheader("Used Comparable Leases")

used_df = pd.DataFrame(data["used_comps"])

used_cols = [
    "address",
    "submarket",
    "rent_psf_yr",
    "lease_sf",
    "year_built",
    "clear_height_ft",
    "confidence",
    "reason",
]

st.dataframe(
    used_df[used_cols],
    use_container_width=True,
    hide_index=True,
)


st.divider()

st.subheader("Dropped Comparable Leases")

dropped_df = pd.DataFrame(data["dropped_comps"])

drop_cols = [
    "address",
    "submarket",
    "rent_psf_yr",
    "confidence",
    "reason",
]

st.dataframe(
    dropped_df[drop_cols],
    use_container_width=True,
    hide_index=True,
)
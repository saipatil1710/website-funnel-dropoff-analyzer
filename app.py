from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Website Funnel Analyzer", page_icon="📊", layout="wide")

APP_DIR = Path(__file__).resolve().parent
DATA_PATH = APP_DIR / "data" / "2019-Oct.csv"
REQUIRED_COLUMNS = [
    "event_time", "event_type", "product_id", "user_id", "user_session",
    "category_code", "brand",
]


@st.cache_data(show_spinner="Loading October event data...", max_entries=2)
def load_events(file_path: str, file_mtime: float) -> pd.DataFrame:
    events = pd.read_csv(
        file_path,
        usecols=REQUIRED_COLUMNS,
        dtype={"event_type": "category", "category_code": "category", "brand": "category"},
    )
    events["event_time"] = pd.to_datetime(events["event_time"], utc=True, errors="coerce")
    events = events.dropna(subset=["event_time", "event_type", "user_session"]).copy()
    events["event_type"] = events["event_type"].astype(str).str.lower().str.strip()
    events["brand"] = events["brand"].astype("string").fillna("Unknown")
    events["category_code"] = events["category_code"].astype("string").fillna("Unknown")
    return events.sort_values(["user_session", "event_time"], kind="stable").reset_index(drop=True)


@st.cache_data(show_spinner="Building the selected session funnel...", max_entries=6)
def build_session_funnel(
    file_path: str, file_mtime: float, segment_column: str, segment_value: str
) -> pd.DataFrame:
    events = load_events(file_path, file_mtime)
    if segment_column:
        events = events.loc[events[segment_column].astype("string") == segment_value]
    if events.empty:
        return pd.DataFrame()

    work = events.sort_values(["user_session", "event_time"], kind="stable").copy()
    sessions = work["user_session"]
    event_types = work["event_type"]
    work["_view"] = event_types.eq("view")
    work["_view_seen"] = work.groupby(sessions, sort=False)["_view"].cummax()
    work["_cart"] = event_types.eq("cart") & work["_view_seen"]
    work["_cart_seen"] = work.groupby(sessions, sort=False)["_cart"].cummax()
    work["_purchase"] = event_types.eq("purchase") & work["_cart_seen"]
    work["_view_time"] = work["event_time"].where(work["_view"])
    work["_cart_time"] = work["event_time"].where(work["_cart"])
    work["_purchase_time"] = work["event_time"].where(work["_purchase"])

    session_funnel = (
        work.groupby("user_session", sort=False)
        .agg(
            view=("_view", "any"), cart=("_cart", "any"), purchase=("_purchase", "any"),
            view_time=("_view_time", "min"), cart_time=("_cart_time", "min"),
            purchase_time=("_purchase_time", "min"),
        )
        .reset_index()
    )
    session_funnel["view_date"] = session_funnel["view_time"].dt.date
    return session_funnel


st.title("Website Funnel Drop-off Analyzer")
st.caption("October 2019 cosmetics-store events · Session-based view → cart → purchase analysis")

if not DATA_PATH.exists():
    st.error(f"Dataset not found. Place the Kaggle file at `{DATA_PATH}` and rerun the app.")
    st.stop()

file_mtime = DATA_PATH.stat().st_mtime
events = load_events(str(DATA_PATH), file_mtime)
if events.empty:
    st.error("The CSV has no usable rows after timestamp and session cleanup.")
    st.stop()

min_date, max_date = events["event_time"].min().date(), events["event_time"].max().date()

with st.sidebar:
    st.header("Dashboard filters")
    selected_dates = st.date_input(
        "Session first-view date range", value=(min_date, max_date),
        min_value=min_date, max_value=max_date,
        help="The date is based on the session's first qualifying product view (UTC).",
    )
    funnel_choice = st.selectbox(
        "Conversion step to inspect",
        ["View → cart", "Cart → purchase", "View → purchase"],
    )
    segment_type = st.selectbox("Segment by", ["All sessions", "Brand", "Category"])
    segment_column, segment_value = "", ""
    if segment_type != "All sessions":
        segment_column = "brand" if segment_type == "Brand" else "category_code"
        options = sorted(events[segment_column].astype("string").dropna().unique())
        segment_value = st.selectbox(f"Choose {segment_type.lower()}", options)

if isinstance(selected_dates, (tuple, list)):
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif len(selected_dates) == 1:
        start_date = end_date = selected_dates[0]
    else:
        st.info("Select a start and end date to view the dashboard.")
        st.stop()
else:
    start_date = end_date = selected_dates

session_funnel = build_session_funnel(str(DATA_PATH), file_mtime, segment_column, segment_value)
if session_funnel.empty:
    st.warning("No events match the selected segment.")
    st.stop()

visible_sessions = session_funnel.loc[
    session_funnel["view"] & session_funnel["view_date"].between(start_date, end_date)
].copy()
if visible_sessions.empty:
    st.warning("No viewed sessions match the selected date range and segment.")
    st.stop()

counts = visible_sessions[["view", "cart", "purchase"]].sum().astype(int)
view_to_cart = counts["cart"] / counts["view"] if counts["view"] else 0.0
cart_to_purchase = counts["purchase"] / counts["cart"] if counts["cart"] else 0.0
view_to_purchase = counts["purchase"] / counts["view"] if counts["view"] else 0.0
metric_columns = {
    "View → cart": "view_to_cart", "Cart → purchase": "cart_to_purchase",
    "View → purchase": "view_to_purchase",
}
metric_values = {
    "view_to_cart": view_to_cart, "cart_to_purchase": cart_to_purchase,
    "view_to_purchase": view_to_purchase,
}
selected_metric = metric_columns[funnel_choice]

daily = (
    visible_sessions.groupby("view_date")
    .agg(view_sessions=("view", "sum"), cart_sessions=("cart", "sum"),
         purchase_sessions=("purchase", "sum"))
    .reset_index().sort_values("view_date")
)
daily["view_to_cart"] = daily["cart_sessions"] / daily["view_sessions"]
daily["cart_to_purchase"] = daily["purchase_sessions"] / daily["cart_sessions"].replace(0, np.nan)
daily["view_to_purchase"] = daily["purchase_sessions"] / daily["view_sessions"]
daily["selected_dropoff"] = 1 - daily[selected_metric]
q1, q3 = daily["selected_dropoff"].quantile([0.25, 0.75])
upper_fence = q3 + 1.5 * (q3 - q1)
daily["high_dropoff_flag"] = daily["selected_dropoff"] > upper_fence

st.subheader("Dataset summary")
summary_columns = st.columns(4)
summary_columns[0].metric("Events loaded", f"{len(events):,}")
summary_columns[1].metric("Unique sessions", f"{events['user_session'].nunique():,}")
summary_columns[2].metric("Date coverage", f"{min_date} to {max_date}")
summary_columns[3].metric("Event types", ", ".join(sorted(events["event_type"].unique())))

with st.expander("Dataset and funnel definitions"):
    st.markdown(
        "- Source: [eCommerce Events History in Cosmetics Shop](https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop).\n"
        "- A session reaches cart only after a product view, and purchase only after that qualifying cart.\n"
        "- Brand/category filters calculate the sequence using events from the selected segment.\n"
        "- `remove_from_cart` does not reset progress; purchases are not matched to a specific carted product.\n"
        "- Device, campaign, landing-page, and checkout fields are not available.\n"
        "- IQR flags are statistical review cues, not explanations of cause."
    )

segment_label = "All sessions" if segment_type == "All sessions" else f"{segment_type}: {segment_value}"
st.subheader("Selected funnel view")
st.caption(
    f"First-view dates: {start_date} to {end_date} · {segment_label} · "
    f"Conversion step: {funnel_choice}"
)
kpi_columns = st.columns(4)
kpi_columns[0].metric("Viewed sessions", f"{counts['view']:,}")
kpi_columns[1].metric("Cart sessions", f"{counts['cart']:,}")
kpi_columns[2].metric("Purchase sessions", f"{counts['purchase']:,}")
kpi_columns[3].metric(funnel_choice, f"{metric_values[selected_metric]:.1%}")

left, right = st.columns(2)
with left:
    st.markdown("#### Ordered funnel")
    funnel_figure = go.Figure(go.Funnel(
        y=["View", "Cart after view", "Purchase after cart"],
        x=[counts["view"], counts["cart"], counts["purchase"]],
        textinfo="value+percent initial",
        marker={"color": ["#3B82F6", "#F59E0B", "#10B981"]},
        hovertemplate="%{y}<br>%{x:,} sessions<extra></extra>",
    ))
    funnel_figure.update_layout(title="Sessions reaching each stage")
    st.plotly_chart(funnel_figure, use_container_width=True)

with right:
    st.markdown("#### Daily conversion and drop-off")
    rate_figure = px.line(
        daily, x="view_date", y=selected_metric, markers=True,
        title=f"Daily {funnel_choice.lower()} conversion",
        labels={"view_date": "Session first-view date", selected_metric: "Conversion rate"},
    )
    rate_figure.update_yaxes(tickformat=".0%")
    flagged = daily.loc[daily["high_dropoff_flag"]]
    if not flagged.empty:
        rate_figure.add_scatter(
            x=flagged["view_date"], y=flagged[selected_metric], mode="markers",
            name="High drop-off review flag",
            marker={"color": "red", "size": 12, "symbol": "circle-open"},
            customdata=flagged[["selected_dropoff"]],
            hovertemplate="%{x}<br>Conversion: %{y:.1%}<br>Drop-off: %{customdata[0]:.1%}<extra></extra>",
        )
    st.plotly_chart(rate_figure, use_container_width=True)
    st.caption(f"IQR review threshold for selected drop-off: {upper_fence:.1%}.")

st.markdown("#### Raw event volume by calendar date")
segment_events = events
if segment_column:
    segment_events = events.loc[events[segment_column].astype("string") == segment_value]
calendar_events = segment_events.loc[
    segment_events["event_time"].dt.date.between(start_date, end_date)
].copy()
calendar_events["event_date"] = calendar_events["event_time"].dt.date
event_volume = (
    calendar_events.groupby(["event_date", "event_type"]).size()
    .rename("events").reset_index()
)
event_volume = event_volume.loc[event_volume["event_type"].isin(["view", "cart", "purchase"])]
volume_figure = px.line(
    event_volume, x="event_date", y="events", color="event_type", markers=True,
    title="Recorded product event counts (calendar date, UTC)",
    labels={"event_date": "Event calendar date", "events": "Event rows"},
)
st.plotly_chart(volume_figure, use_container_width=True)
st.caption(
    "The session funnel uses each session's first qualifying view date. "
    "The event-volume chart groups event rows by their own calendar date."
)

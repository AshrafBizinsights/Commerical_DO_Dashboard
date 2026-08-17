import streamlit as st
import pandas as pd
import numpy as np
import textwrap
import html
import plotly.graph_objects as go

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(page_title="Dashboard", layout="wide")

# ---------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------

st.markdown("""
<style>

html, body, [class*="css"]  {
    font-size:14px;
}

.stSelectbox label,
.stMultiSelect label,
.stDateInput label {
    font-size:14px !important;
    font-weight:600;
}

div[data-baseweb="select"] {
    font-size:14px !important;
}

.stButton button {
    width:100%;
    height:40px;
    font-size:14px;
    font-weight:600;
}

/* ---- Summary status cards ---- */
.summary-card {
    display:flex;
    align-items:flex-start;
    gap:14px;
    background-color:#f7f7f7;
    border:1px solid #e2e2e2;
    border-radius:10px;
    padding:16px 18px;
    margin-bottom:16px;
}
.status-icon {
    flex-shrink:0;
    width:40px;
    height:40px;
    border-radius:8px;
    display:flex;
    align-items:center;
    justify-content:center;
    color:#ffffff;
    font-size:20px;
    font-weight:800;
}
.status-icon-green  { background-color:#3fae54; }
.status-icon-orange { background-color:#f2994a; }
.status-icon-red    { background-color:#eb5757; }
.summary-body {
    flex:1;
    min-width:0;
}
.summary-title {
    font-weight:700;
    font-size:15px;
    color:#222222;upper
    margin-bottom:8px;
}
.summary-line {
    font-size:13px;
    color:#333333;
    padding-bottom:6px;
    margin-bottom:6px;
    border-bottom:1px solid #dddddd;
    cursor:default;
}
.summary-line:last-child {
    border-bottom:none;
    margin-bottom:0;
    padding-bottom:0;
}
.stat-hover {
    cursor:default;
    border-bottom:1px dotted #999999;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# DATA LOADING
# ---------------------------------------------------

def load_data():
    #df = pd.read_csv("Projected_data_full_test_1.csv")
    df = pd.read_csv("combined_results.csv")
    
    df["analysis_type"] = df["analysis_type"].replace({"Primary Source": "Data Source"})
    # filtered_df = df.loc[(df["metric_name"] == "total retail dispenses")& (df["source_pair"] == "iqvia xpo") & (df["analysis_type"] == "Data Source") & (df["audit_date"] == df["audit_date"].max())]
    # max_ds = filtered_df["ds"].max()

  

    # df = (df.sort_values("ds").loc[(df["ds"] > "2025-08-08") & (df["ds"] < max_ds)].copy())
    for col in ["brand_name", "source_pair", "metric_name", "analysis_type"]:
        df[col] = df[col].astype(str).str.upper()

    df["ds"] = pd.to_datetime(df["ds"])

    # audit_date must be parsed too (it wasn't before) - otherwise it stays
    # a raw string, which sorts/orders lexicographically instead of
    # chronologically in the "Audit Date" dropdown below.
    df["audit_date"] = pd.to_datetime(df["audit_date"], errors="coerce")

    config = pd.read_csv("config.csv")
    for col in ["metric_name", "primary_source", "secondary_source", "common_dimensions"]:
        config[col] = config[col].fillna("").astype(str).str.upper()

    return df, config


raw_df, config = load_data()

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------

header_left, header_right = st.columns([5, 1.5])

with header_left:
    st.markdown(
        """
        <div style="
            font-weight:bold;
            color:#1f4e79;
            font-size:32px;
            margin-top:8px;
        ">
            Commercial Data Observability Dashboard
        </div>
        """,
        unsafe_allow_html=True,
    )

# with header_right:
#     audit_dates = sorted(raw_df["audit_date"].dropna().unique(), reverse=True)
#     selected_audit_date = st.selectbox(
#         "Audit Date",
#         audit_dates,
#         index=0,
#         format_func=lambda d: pd.Timestamp(d).strftime("%b %d, %Y %I:%M %p"),
#     )

st.write(" ")



selected_audit_date = raw_df["audit_date"].max()
df = raw_df[raw_df["audit_date"] == selected_audit_date].copy()

# if df.empty:
#     st.warning("No data available for the selected Audit Date.")
#     st.stop()

# ---------------------------------------------------
# CONFIGURATION FILE
# ---------------------------------------------------

st.markdown("""
<style>
div[data-testid="stExpander"] {
    border: 2px solid #4A4A4A !important;
    border-radius: 8px;
}

/* Make expander title bold */
div[data-testid="stExpander"] summary p {
    font-weight: 700 !important;
    font-size: 15px;
}
</style>
""", unsafe_allow_html=True)

with st.expander("View Configuration File"):
    st.dataframe(config, use_container_width=True, hide_index=True)

# ---------------------------------------------------
# PROPHET CHART  (unchanged - math/logic untouched)
# ---------------------------------------------------

EVENT_DOT_COLOR = "#8E44AD"
DEFAULT_PASS_COLOR = "#8c8c8c"


def _is_event(val):
    val_str = str(val).strip().lower()
    return val_str not in ("no event", "", "nan", "none")


def plot_prophet_chart(main_data, title):
    title = title.replace(' VS ', ' vs ')
    main_data = main_data.sort_values("ds").copy()

    pass_data = main_data[main_data["anomaly"] == "Pass"].copy()

    pass_data["event_name"] = pass_data["event_name"].fillna("No Event")
    event_data = pass_data[pass_data["event_name"].apply(_is_event)].copy()
    pass_data = pass_data[~pass_data["event_name"].apply(_is_event)].copy()

    alert_data = main_data[main_data["anomaly"] == "Alert"].copy()
    alert_data["RCA Text"] = alert_data["rca_insight"].fillna("RCA not available").astype(str)
    alert_data["RCA Text Wrapped"] = alert_data["RCA Text"].apply(
        lambda x: "<br>".join(textwrap.wrap(x, width=68, break_long_words=False))
    )

    fail_data = main_data[main_data["anomaly"] == "Fail"].copy()
    fail_data["RCA Text"] = fail_data["rca_insight"].fillna("RCA not available").astype(str)
    fail_data["RCA Text Wrapped"] = fail_data["RCA Text"].apply(
        lambda x: "<br>".join(textwrap.wrap(x, width=68, break_long_words=False))
    )

    holiday_data = main_data[main_data["anomaly"] == "Holiday"].copy()

    fig = go.Figure()

    if main_data["analysis_type"].iloc[0] == "DIGITAL DQ ANALYSIS":
        pass_hover = (
            "<b>Date:</b> %{x|%b %d, %Y}<br>"
            "<b>Actual:</b> %{y:.2f}%<br>"
            "<b>Forecast:</b> %{customdata[0]:.2f}%<br>"
            "<b>Upper Threshold:</b> %{customdata[1]:.2f}%<br>"
            "<b>Lower Threshold:</b> %{customdata[2]:.2f}%<br>"
            "<extra></extra>"
        )
        anomaly_hover = (
            "<b>Date:</b> %{x|%b %d, %Y}<br>"
            "<b>Actual:</b> %{y:.2f}%<br><br>"
            "<b>Event:</b> %{customdata[1]}<br><br>"
            "<b>RCA Insight</b><br>"
            "%{customdata[0]}"
            "<extra></extra>"
        )
    else:  # DATA SOURCES
        pass_hover = (
            "<b>Date:</b> %{x|%b %d, %Y}<br>"
            "<b>Actual:</b> %{y:.2f}<br>"
            "<b>Forecast:</b> %{customdata[0]:.2f}<br>"
            "<b>Upper Threshold:</b> %{customdata[1]:.2f}<br>"
            "<b>Lower Threshold:</b> %{customdata[2]:.2f}<br>"
            "<extra></extra>"
        )
        anomaly_hover = (
            "<b>Date:</b> %{x|%b %d, %Y}<br>"
            "<b>Actual:</b> %{y:.2f}<br><br>"
            "<b>Event:</b> %{customdata[1]}<br><br>"
            "<b>RCA Insight</b><br>"
            "%{customdata[0]}"
            "<extra></extra>"
        )

    fig.add_trace(go.Scatter(
        x=main_data["ds"], y=main_data["yhat_upper"],
        mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=main_data["ds"], y=main_data["yhat_lower"],
        mode="lines", line=dict(width=0), fill="tonexty",
        fillcolor="rgba(184,182,255,0.55)", name="Expected Range", hoverinfo="skip"
    ))

    fig.add_trace(go.Scatter(
        x=pass_data["ds"], y=pass_data["y"], mode="markers", name="Pass",
        marker=dict(color=DEFAULT_PASS_COLOR, size=7),
        customdata=list(zip(pass_data["yhat"], pass_data["yhat_upper"], pass_data["yhat_lower"])),
        hovertemplate=pass_hover
    ))

    if not event_data.empty:
        fig.add_trace(go.Scatter(
            x=event_data["ds"], y=event_data["y"], mode="markers", name="Event",
            marker=dict(color=EVENT_DOT_COLOR, size=7, symbol="circle"),
            customdata=event_data[["event_name"]].fillna("").values,
            hovertemplate="<b>Date:</b> %{x|%b %d, %Y}<br><b>Event:</b> %{customdata[0]}<extra></extra>"
        ))

    fig.add_trace(go.Scatter(
        x=alert_data["ds"], y=alert_data["y"], mode="markers", name="Alert",
        marker=dict(color="#FFA500", size=8),
        customdata=alert_data[["RCA Text Wrapped", "event_name"]].fillna("").values,
        hovertemplate=anomaly_hover
    ))

    fig.add_trace(go.Scatter(
        x=fail_data["ds"], y=fail_data["y"], mode="markers", name="Fail",
        marker=dict(color="#ff4b4b", size=8),
        customdata=fail_data[["RCA Text Wrapped", "event_name"]].fillna("").values,
        hovertemplate=anomaly_hover
    ))

    if not holiday_data.empty:
        fig.add_trace(go.Scatter(
            x=holiday_data["ds"], y=holiday_data["y"], mode="markers", name="Holiday",
            marker=dict(color="#90D5FF", size=7, symbol="circle"),
            customdata=holiday_data[["holiday"]].fillna("").values,
            hovertemplate="<b>Holiday:</b> %{customdata[0]}<extra></extra>"
        ))

    fig.update_layout(
        title=dict(text=title, x=0.5, y=0.98, xanchor="center", yanchor="top"),
        height=450, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40, r=40, t=80, b=80), hovermode="closest",
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        hoverlabel=dict(bgcolor="white", font_size=11, font_family="Arial", align="left")
    )

    fig.update_xaxes(title="Date", showgrid=False, showline=True, linecolor="#d0d0d0")

    y_axis_title = "Metric" if main_data["analysis_type"].iloc[0] == "DIGITAL DQ ANALYSIS" else "Value"
    fig.update_yaxes(title=y_axis_title, showgrid=False, zeroline=True, zerolinecolor="#d0d0d0")

    return fig



def filter_dashboard_data(df, brand, metric, source, analysis_type, time_period):
    return df[
        (df["brand_name"] == brand)
        & (df["metric_name"] == metric)
        & (df["source_pair"] == source)
        & (df["analysis_type"] == analysis_type)
        & (df["time_period"] == time_period)
    ].copy()


# ---------------------------------------------------
# DATA SOURCES DASHBOARD  (unchanged)
# ---------------------------------------------------

def build_primary_dashboard(config, filtered_df, selected_metric, selected_analysis_type, selected_time_period):
    metric_config = config[config["metric_name"] == selected_metric].copy()
    sources = sorted(set(metric_config["primary_source"].dropna()) | set(metric_config["secondary_source"].dropna()))

    for source in sources:
        main_data = filtered_df[filtered_df["source_pair"] == source].sort_values("ds").reset_index(drop=True)
        if main_data.empty:
            continue

        st.markdown(
            f"""<h4 style="margin-top:10px;margin-bottom:10px;color:#1f4e79;font-family:Arial;">
            {selected_metric} {selected_analysis_type} - {source}</h4>""",
            unsafe_allow_html=True
        )
        st.markdown("---")
        new_column_names = {
            "ds": "Date",
            "yhat_lower": "Lower Threshold",
            "yhat_upper": "Upper Threshold",
            "y": "Value",
        }
        main_dataframe = main_data.rename(columns=new_column_names)
        main_dataframe["Lower Threshold"] = main_dataframe["Lower Threshold"].round(2)
        main_dataframe["Upper Threshold"] = main_dataframe["Upper Threshold"].round(2)
        main_dataframe["Value"] = main_dataframe["Value"].round(2)

        display_df = main_dataframe[["Date", "Value", "Lower Threshold", "Upper Threshold", "anomaly", "rca_insight"]]

        fig = plot_prophet_chart(main_data, source)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------
# TRIANGULATION DASHBOARD  (unchanged)
# ---------------------------------------------------

def build_triangulation_dashboard(filtered_df, config, selected_brand, selected_metric, selected_analysis_type, selected_time_period):
    metric_config = config[config["metric_name"] == selected_metric].copy()
    if metric_config.empty:
        st.warning("No configuration found.")
        return

    for _, row in metric_config.iterrows():
        primary_source = row["primary_source"]
        secondary_source = row["secondary_source"]
        source_pair = f"{primary_source} VS {secondary_source}"
        calculated_field = f"{secondary_source} Per {primary_source}".title()
        main_data = filtered_df[filtered_df["source_pair"] == source_pair].sort_values("ds").reset_index(drop=True)
        if main_data.empty:
            continue

        if len(main_data) > 1:
            st.markdown(
                f"""<h4 style="margin-top:10px;margin-bottom:10px;color:#1f4e79;font-family:Arial;">
                {selected_metric} {selected_analysis_type} - {source_pair.replace(' VS ', ' vs ')}</h4>""",
                unsafe_allow_html=True
            )
        st.markdown("---")

        new_column_names = {
            "ds": "Date",
            "yhat_lower": "Lower Threshold",
            "yhat_upper": "Upper Threshold",
            "y": "Value",
        }
        main_dataframe = main_data.rename(columns=new_column_names)
        main_dataframe["Lower Threshold"] = main_dataframe["Lower Threshold"].round(2)
        main_dataframe["Upper Threshold"] = main_dataframe["Upper Threshold"].round(2)
        main_dataframe["primary_metric"] = main_dataframe["primary_metric"].round(2)
        main_dataframe["secondary_metric"] = main_dataframe["secondary_metric"].round(2)
        main_dataframe["Value"] = main_dataframe["Value"].round(2)

        main_dataframe = main_dataframe.rename(columns={"Value": calculated_field})

        display_df = main_dataframe[
            ["Date", "primary_metric", "secondary_metric", calculated_field, "Lower Threshold", "Upper Threshold", "anomaly", "rca_insight"]
        ]

        fig = plot_prophet_chart(main_data, source_pair)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------
# SUMMARY TAB
#
# One status card per metric_name, scoped to the selected Brand + Time
# Period (df is already scoped to the selected audit date). Each card
# aggregates Fail/Alert counts separately for TRIANGULATION and DATA
# SOURCES ("Data source"), each restricted to ITS OWN latest-13-weeks
# window (the two analysis types can report on different dates, so each
# gets its own trailing window rather than assuming a shared date axis).
# ---------------------------------------------------

def safe_rca(row):
    rca = row.get("rca_insight", None)
    return rca if pd.notna(rca) and str(rca).strip() else "RCA not available"


def _latest_13_weeks(sub_df):
    if sub_df.empty:
        return sub_df
    latest_ds = sub_df["ds"].drop_duplicates().sort_values().tail(12)
    return sub_df[sub_df["ds"].isin(latest_ds)]


def _anomaly_stats(sub_df):
    """Given a df already narrowed to one metric + one analysis_type + its
    own latest 12 Months, return (fail_count, alert_count, fail_details,
    alert_details) - fail and alert detail rows kept separate so each can
    get its own tooltip."""
    windowed = _latest_13_weeks(sub_df)

    def _rows(status_value):
        rows = windowed[windowed["anomaly"] == status_value].sort_values("ds")
        return [
            {"source": r["source_pair"], "date": r["ds"], "rca": safe_rca(r)}
            for _, r in rows.iterrows()
        ]

    fail_details = _rows("Fail")
    alert_details = _rows("Alert")

    return len(fail_details), len(alert_details), fail_details, alert_details


def compute_metric_status(metric_df):
    """metric_df: rows for one brand + one metric_name + one time_period
    (both analysis types mixed in). Returns a dict of counts/details."""
    tri_df = metric_df[metric_df["analysis_type"] == "DIGITAL DQ ANALYSIS"]
    ds_df = metric_df[metric_df["analysis_type"] == "DATA SOURCE"]

    tri_fail, tri_alert, tri_fail_details, tri_alert_details = _anomaly_stats(tri_df)
    ds_fail, ds_alert, ds_fail_details, ds_alert_details = _anomaly_stats(ds_df)

    return {
        "tri_fail": tri_fail, "tri_alert": tri_alert,
        "tri_fail_details": tri_fail_details, "tri_alert_details": tri_alert_details,
        "ds_fail": ds_fail, "ds_alert": ds_alert,
        "ds_fail_details": ds_fail_details, "ds_alert_details": ds_alert_details,
    }


def _format_tooltip(details, empty_message="No entries in the latest 12 Months"):
    if not details:
        return empty_message

    tooltip_items = []

    for d in details:
        source_esc = html.escape(str(d["source"]), quote=True)
        rca_esc = html.escape(str(d["rca"]), quote=True)
        date_str = f"{d['date']:%b %d, %Y}"
        tooltip_items.append(f"Source :- {source_esc} on {date_str} &#10;RCA :- {rca_esc}")

    return "&#10;&#10;".join(tooltip_items)


def format_metric_name(metric_name):
    metric_name = metric_name.title()

    replacements = {
        "Hcps": "HCPs",
        "Hcp": "HCP",
        "Trx": "TRx",
        "Npi": "NPI",
        "Rx": "Rx",
    }

    for old, new in replacements.items():
        metric_name = metric_name.replace(old, new)

    return metric_name


def render_summary_card(metric_name, status):
    total_fail = status["tri_fail"] + status["ds_fail"]
    total_alert = status["tri_alert"] + status["ds_alert"]

    if total_fail > 0:
        icon_class, icon_symbol = "status-icon-red", "!"
    elif total_alert > 0:
        icon_class, icon_symbol = "status-icon-orange", "!"
    else:
        icon_class, icon_symbol = "status-icon-green", "&#10003;"

    tri_fail_hover = _format_tooltip(status["tri_fail_details"], "No failures in the latest 12 Months")
    tri_alert_hover = _format_tooltip(status["tri_alert_details"], "No alerts in the latest 12 Months")
    ds_fail_hover = _format_tooltip(status["ds_fail_details"], "No failures in the latest 12 Months")
    ds_alert_hover = _format_tooltip(status["ds_alert_details"], "No alerts in the latest 12 Months")

    card_html = (
        f'<div class="summary-card">'
        f'<div class="status-icon {icon_class}">{icon_symbol}</div>'
        f'<div class="summary-body">'
        f'<div class="summary-title">{format_metric_name(metric_name)}</div>'
        f'<div class="summary-line">'
        f'DIGITAL DQ ANALYSIS :- '
        f'<span class="stat-hover" title="{tri_fail_hover}">{status["tri_fail"]} Failures</span> , '
        f'<span class="stat-hover" title="{tri_alert_hover}">{status["tri_alert"]} Alerts</span>'
        f'</div>'
        f'<div class="summary-line">'
        f'Data source :- '
        f'<span class="stat-hover" title="{ds_fail_hover}">{status["ds_fail"]} Failures</span> , '
        f'<span class="stat-hover" title="{ds_alert_hover}">{status["ds_alert"]} Alerts</span>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_summary_tab(df, selected_brand, selected_time_period):
    sub = df[(df["brand_name"] == selected_brand) & (df["time_period"] == selected_time_period)]

    if sub.empty:
        st.info(f"No '{selected_time_period}' data available for brand '{selected_brand}'.")
        return

    metrics = sub["metric_name"].dropna().unique()

    cols = None
    for i, metric in enumerate(metrics):
        if i % 2 == 0:
            cols = st.columns(2)
        metric_df = sub[sub["metric_name"] == metric]
        status = compute_metric_status(metric_df)
        with cols[i % 2]:
            render_summary_card(metric, status)


# ---------------------------------------------------
# TABS  (moved above the filters - each tab owns its own filters)
# df here is already scoped to the selected audit date.
# ---------------------------------------------------

brands = sorted(df["brand_name"].dropna().unique())

st.markdown("""
<style>

/* -----------------------------
   Streamlit Tabs
------------------------------*/

/* Tab container */
button[data-baseweb="tab"] {
    background-color: #f5f5f5 !important;
    border: 1px solid #1f4e79 !important;
    border-radius: 6px 6px 0 0 !important;
    margin-right: 4px !important;
    padding: 8px 18px !important;
}

/* Tab text */
button[data-baseweb="tab"] p {
    color: #1f4e79 !important;
    font-size: 16px !important;
    font-weight: 700 !important;
}

/* Selected tab */
button[data-baseweb="tab"][aria-selected="true"] {
    background-color: #1f4e79 !important;
    border-color: #1f4e79 !important;
}

/* Selected tab text */
button[data-baseweb="tab"][aria-selected="true"] p {
    color: white !important;
    font-weight: 700 !important;
}

</style>
""", unsafe_allow_html=True)

tab_summary, tab_prophet = st.tabs(["Summary", "Source Deep Dive"])
# =====================================================
# SUMMARY TAB
# =====================================================

with tab_summary:

    summary_filter_container = st.container(border=True)

    with summary_filter_container:
        st.markdown(
            """<div style='font-weight:bold;color:#1f4e79;font-size:20px;margin-top:-10px;'>Filters</div>""",
            unsafe_allow_html=True
        )
        st.write(" ")

        sc1, sc2, sc3 = st.columns([2, 2, 1])

        with sc1:
            summary_brand = st.selectbox("Brand", brands, key="summary_brand")

        summary_brand_df = df[df["brand_name"] == summary_brand]

        with sc2:
            summary_time_periods = sorted(summary_brand_df["time_period"].dropna().unique())
            summary_time_period = st.selectbox("Rolling Period", summary_time_periods, key="summary_time_period")

        with sc3:
            st.markdown("""
            <style>
            div.stButton {
                margin-top: 5px;
            }

            div.stButton > button {
                background-color: #1f4e79;
                color: white;
                border: 1px solid #1f4e79;
                border-radius: 6px;
                font-weight: 600;
            }

            div.stButton > button:hover {
                background-color: #163b5c;
                border-color: #163b5c;
                color: white;
            }

            div.stButton > button:focus:not(:active) {
                background-color: #1f4e79;
                border-color: #1f4e79;
                color: white;
                box-shadow: none;
            }
            </style>
            """, unsafe_allow_html=True)

            summary_submit = st.button("Submit", key="summary_submit")

    summary_container = st.container(border=True)
    with summary_container:
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown(
                """
                <h3 style="
                    margin:0;
                    color:#1f4e79;
                    font-weight:700;
                ">
                    Source Summary
                </h3>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                """
                <div style="
                    text-align:right;
                    margin-top:6px;
                    font-size:13px;
                    color:#dc3545;
                    font-weight:600;
                ">
                    Metrics are based on the latest 12 Months of data.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write(" ")
        if summary_submit:
            render_summary_tab(df, summary_brand, summary_time_period)
            st.markdown(
                """
                <span style="color:red; font-size:25px;">●</span> Failure &nbsp;&nbsp;&nbsp;
                <span style="color:orange; font-size:25px;">●</span> Alert &nbsp;&nbsp;&nbsp;
                <span style="color:green; font-size:25px;">●</span> Pass
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Set your filters above and click **Submit** to load the summary.")

# =====================================================
# PROPHET OUTPUT TAB
# =====================================================

with tab_prophet:

    prophet_filter_container = st.container(border=True)

    with prophet_filter_container:
        st.markdown(
            """<div style='font-weight:bold;color:#1f4e79;font-size:20px;margin-top:-10px;'>Filters</div>""",
            unsafe_allow_html=True
        )
        st.write(" ")

        pc1, pc2, pc3, pc4, pc5, pc6 = st.columns(6)

        with pc1:
            prophet_brand = st.selectbox("Brand", brands, key="prophet_brand")

        prophet_brand_df = df[df["brand_name"] == prophet_brand]

        with pc2:
            
            prophet_metrics = sorted(prophet_brand_df["metric_name"].dropna().unique())
            prophet_metric_display = st.selectbox("Source Name", prophet_metrics, key="prophet_metric")
     

        prophet_metric_df = prophet_brand_df[prophet_brand_df["metric_name"] == prophet_metric_display]

        with pc3:
            prophet_analysis_types = sorted(prophet_metric_df["analysis_type"].dropna().unique())
            if not prophet_analysis_types:
                prophet_analysis_types = ["DATA SOURCE"]
            prophet_analysis_type = st.selectbox("Analysis Type", prophet_analysis_types, key="prophet_analysis_type")
        prophet_analysis_df = prophet_metric_df[prophet_metric_df["analysis_type"] == prophet_analysis_type]

        with pc4:
            prophet_sources = sorted(prophet_analysis_df["source_pair"].dropna().unique())
            source_display = st.selectbox("Metric Name", prophet_sources, key="prophet_source")
        prophet_source_df = prophet_analysis_df[prophet_analysis_df["source_pair"] == source_display]

        with pc5:
            prophet_time_periods = sorted(prophet_source_df["time_period"].dropna().unique())
            prophet_time_period = st.selectbox("Rolling Period", prophet_time_periods, key="prophet_time_period")

        with pc6:
            st.markdown("""
            <style>
            div.stButton {
                margin-top: 5px;
            }

            div.stButton > button {
                background-color: #1f4e79;
                color: white;
                border: 1px solid #1f4e79;
                border-radius: 6px;
                font-weight: 600;
            }

            div.stButton > button:hover {
                background-color: #163b5c;
                border-color: #163b5c;
                color: white;
            }

            div.stButton > button:focus:not(:active) {
                background-color: #1f4e79;
                border-color: #1f4e79;
                color: white;
                box-shadow: none;
            }
            </style>
            """, unsafe_allow_html=True)

            prophet_submit = st.button("Submit", key="prophet_submit")

    prophet_container = st.container(border=True)
    with prophet_container:
        if prophet_submit:
            filtered_df = filter_dashboard_data(df, prophet_brand, prophet_metric_display, source_display, prophet_analysis_type, prophet_time_period)

            if filtered_df.empty:
                st.warning("No data available for the selected combination.")
            else:
                if prophet_analysis_type == "DATA SOURCE":
                    build_primary_dashboard(config, filtered_df, prophet_metric_display, prophet_analysis_type, prophet_time_period)
                else:
                    build_triangulation_dashboard(filtered_df, config, prophet_brand, prophet_metric_display, prophet_analysis_type, prophet_time_period)
        else:
            st.info("Set your filters above and click **Submit** to load the dashboard.")
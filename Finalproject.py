
# ---------- IMPORTS ----------
import pandas as pd
import numpy as np
import streamlit as st
import pydeck as pdk
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# Data loading / cleaning
# ---------------------------------------------------------

# #[FUNC2P]  function with 2+ params, one has a default value
def load_data(filename="ShipwreckDatabase (1).xlsx", nrows=None):

    df = pd.read_excel(filename, nrows=nrows)

    # Rename long column names to simple ones
    df = df.rename(
        columns={
            "VESSEL TYPE": "Type",
            "CAUSE OF LOSS": "Cause",
            "YEAR": "Year",
            "LIVES LOST": "LivesLost",
            "SHIP'S NAME": "ShipName",
            "LATITUDE": "Latitude",
            "LONGITUDE": "Longitude",
        }
    )

    # Clean numeric fields
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["Year"])
    df["Year"] = df["Year"].astype(int)

    # #[LISTCOMP]  list comprehension to clean Type strings
    df["Type"] = [t.strip() if isinstance(t, str) else t for t in df["Type"]]

    df["LivesLost"] = pd.to_numeric(df["LivesLost"], errors="coerce").fillna(0).astype(int)

    # Convert Latitude/Longitude to numeric — drop messy values
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    # #[COLUMNS]  Add a new Fatal column to the DataFrame
    df["Fatal"] = df["LivesLost"] > 0

    return df


# #[FUNCRETURN2]  function returns two or more values
def filter_data(df, year_range, ship_types=None, fatal_only=False):
   
    start_year, end_year = year_range

    # #[FILTER1]  filter by one condition (year range)
    filtered = df[(df["Year"] >= start_year) & (df["Year"] <= end_year)]

    # #[FILTER2]  filter by two or more conditions (year AND type AND fatal flag)
    if ship_types and len(ship_types) > 0:
        filtered = filtered[filtered["Type"].isin(ship_types)]

    if fatal_only:
        filtered = filtered[filtered["Fatal"] == True]

    return filtered, len(filtered)
# ===========================
# MAIN STREAMLIT APP
# ===========================
def main():

    # #[ST3] use Streamlit page config / layout
    st.set_page_config(page_title="Shipwrecks Data Explorer", layout="wide")

    st.title("Shipwrecks Data Explorer")
    st.write("Explore shipwrecks by year, vessel type, cause, and severity.")

    # Load data
    df = load_data()

    # ------------- SIDEBAR FILTERS -------------
    st.sidebar.title("Filters")

    # #[ST2]  slider widget for year range
    min_year = int(df["Year"].min())
    max_year = int(df["Year"].max())
    year_range = st.sidebar.slider(
        "Select Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )

    # #[ST1]  multiselect widget for vessel types (dropdown style)
    vessel_type_options = sorted(df["Type"].dropna().unique().tolist())
    selected_types = st.sidebar.multiselect(
        "Select Vessel Type(s)",
        options=vessel_type_options,
        default=vessel_type_options
    )

    #  [ST3]Third widget – checkbox
    fatal_only = st.sidebar.checkbox("Show only fatal wrecks")

    # ------------- FILTER DATA -------------
    filtered_df, match_count = filter_data(
        df, year_range, ship_types=selected_types, fatal_only=fatal_only
    )

    st.subheader("Summary of Matching Shipwrecks")
    st.write(f"Total matching wrecks: **{match_count}**")

    # Summary block
    # #[DICTMETHOD] using .items() on dictionary
    summary_stats = {
        "Total wrecks": match_count,
        "Fatal wrecks": int(filtered_df["Fatal"].sum()) if not filtered_df.empty else 0,
        "Total lives lost": int(filtered_df["LivesLost"].sum()) if not filtered_df.empty else 0,
    }

    # #[ITERLOOP]  loop through items in a dictionary
    for label, value in summary_stats.items():
        st.write(f"- **{label}:** {value}")

    st.markdown("---")

    # ===========================
    # QUERY 1 — Wrecks per Year (BAR CHART)
    # ===========================
    st.subheader("Wrecks per Year")

    if filtered_df.empty:
        st.write("No data for selected filters.")
    else:
        # groupby year and count records
        wrecks_per_year = (
            filtered_df.groupby("Year")
            .size()
            .reset_index(name="Count")
        )

        # #[SORT]  sort by Year
        wrecks_per_year = wrecks_per_year.sort_values("Year")

        # #[MAXMIN]  find the year with the most wrecks
        max_row = wrecks_per_year.loc[wrecks_per_year["Count"].idxmax()]
        st.write(
            f"Year with most wrecks (filtered): "
            f"**{int(max_row['Year'])}** with **{int(max_row['Count'])}** wrecks."
        )

        # #[CHART1]  bar chart showing wrecks per year
        fig1, ax1 = plt.subplots()
        ax1.bar(wrecks_per_year["Year"], wrecks_per_year["Count"])
        ax1.set_title("Number of Wrecks per Year")
        ax1.set_xlabel("Year")
        ax1.set_ylabel("Number of Wrecks")
        plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
        st.pyplot(fig1)

    st.markdown("---")

    # ===========================
    # QUERY 2 — Causes of Wrecks
    # ===========================
    st.subheader("Main Causes of Shipwrecks")

    if filtered_df.empty:
        st.write("No data available.")
    else:
        # #[PIVOTTABLE]  pivot table by Cause
        cause_pivot = (
            filtered_df.pivot_table(index="Cause", values="Year", aggfunc="count")
            .rename(columns={"Year": "Count"})
            .sort_values("Count", ascending=False)
        )

        # Show full table
        st.write("### Full Cause Table")
        st.dataframe(cause_pivot)

    st.markdown("---")

    # ===========================
    # QUERY 3 — Location Map
    # ===========================
    st.subheader("Shipwreck Locations")

    if filtered_df.empty:
        st.write("No data available.")
    else:
        map_df = filtered_df.dropna(subset=["Latitude", "Longitude"])

        if map_df.empty:
            st.write("No valid numeric coordinates available.")
        else:
            view_state = pdk.ViewState(
                latitude=map_df["Latitude"].mean(),
                longitude=map_df["Longitude"].mean(),
                zoom=5
            )

            # #[MAP]  detailed PyDeck map with tooltip
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=map_df,
                get_position=["Longitude", "Latitude"],
                get_radius=4000,
                get_fill_color=[200, 30, 0, 160],
                pickable=True,
            )

            tooltip = {
                "html": "<b>Ship:</b> {ShipName}<br/>"
                        "<b>Year:</b> {Year}<br/>"
                        "<b>Cause:</b> {Cause}",
                "style": {"backgroundColor": "steelblue", "color": "white"},
            }

            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                tooltip=tooltip
            )

            st.pydeck_chart(deck)

    st.markdown("---")

    # ===========================
    # QUERY 4 — Fatal vs Non-Fatal Pie Chart
    # ===========================
    st.subheader("Fatal vs Non-Fatal Wrecks")

    if filtered_df.empty:
        st.write("No data available.")
    else:
        fatal_counts = (
            filtered_df["Fatal"]
            .value_counts()
            .rename_axis("Fatal")
            .reset_index(name="Count")
        )
        fatal_counts["Label"] = fatal_counts["Fatal"].map(
            {True: "Fatal", False: "Non-Fatal"}
        )

        # #[CHART2] Pie chart showing Fatal vs nonfatal
        fig3, ax3 = plt.subplots()
        ax3.pie(
            fatal_counts["Count"],
            labels=fatal_counts["Label"],
            autopct="%1.1f%%",
            startangle=90,
        )
        ax3.set_title("Fatal vs Non-Fatal Wrecks")
        st.pyplot(fig3)


if __name__ == "__main__":
    main()


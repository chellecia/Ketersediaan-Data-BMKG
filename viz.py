import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.express import colors


def fix_figure_colors(fig):
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_color="black"
    )
    return fig

# === Visualisasi METAR ===
# === Visualisasi METAR ===
# === Visualisasi METAR ===
def show_metar_visualizations(df_metar: pd.DataFrame, return_figs=True):
    st.markdown("<h4 style='color:#0d47a1;'>⚠️ Visualisasi Laporan METAR</h4>", unsafe_allow_html=True)
    figs = []

    daftar_stasiun = df_metar["ICAO"].unique().tolist()
    stasiun_terpilih = st.multiselect(
        "Pilih Stasiun untuk Ditampilkan di Grafik:",
        options=daftar_stasiun,
        default=daftar_stasiun[:3],
        help="Pilih satu atau lebih stasiun"
    )
    df_filter = df_metar[df_metar["ICAO"].isin(stasiun_terpilih)]

    if not df_filter.empty:
        # Line chart per stasiun
        fig1 = px.line(
            df_filter,
            x="Tanggal",
            y="Ketersediaan (%)",
            color="ICAO",
            markers=True,
            title="Tren Ketersediaan Harian METAR per Stasiun",
            color_discrete_sequence=px.colors.qualitative.Vivid
        )
        fig1.update_traces(text=df_filter["Ketersediaan (%)"].round(1), textposition='top center')
        st.plotly_chart(fig1, use_container_width=True)
        figs.append(("tren_ketersediaan.png", fig1))
    else:
        st.info("Silakan pilih minimal satu stasiun untuk menampilkan grafik.")

    # Bar chart rata-rata ketersediaan - continuous color
    mean_df = df_metar.groupby("ICAO")["Ketersediaan (%)"].mean().reset_index()
    mean_df = mean_df.sort_values(by="Ketersediaan (%)", ascending=False)

    fig4 = px.bar(
        mean_df,
        x="ICAO",
        y="Ketersediaan (%)",
        color="Ketersediaan (%)",  # gunakan numerik untuk continuous
        color_continuous_scale=px.colors.sequential.Blues,  
        title="Rata-rata Ketersediaan METAR per Stasiun",
        text=mean_df["Ketersediaan (%)"].round(1)
    )
    fig4.update_traces(textposition='outside')
    fig4.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    st.plotly_chart(fig4, use_container_width=True)
    figs.append(("bar_avg_ketersediaan_continuous.png", fig4))


    # Pie chart status
    pie_data = df_metar["Catatan"].value_counts().reset_index()
    pie_data.columns = ["Status", "Jumlah"]
    fig2 = px.pie(
        pie_data,
        names="Status",
        values="Jumlah",
        title="Distribusi Status Ketersediaan",
       color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig2.update_traces(textinfo='percent+label')
    st.plotly_chart(fig2, use_container_width=True)
    figs.append(("pie_status.png", fig2))


    if return_figs:
        fixed_figs = [(fname, fix_figure_colors(fig)) for fname, fig in figs]
        return fixed_figs


# === Visualisasi RASON ===
# === Visualisasi RASON ===
# === Visualisasi RASON ===#
def show_rason_visualizations(df_rason_harian: pd.DataFrame,
                              df_rason_bulanan: pd.DataFrame,
                              return_figs=True):

    st.markdown("<h4 style='color:#0d47a1;'>⚠️ Visualisasi Laporan RASON </h4>", unsafe_allow_html=True)
    figs = []

    dfh = df_rason_harian.copy()
    dfb = df_rason_bulanan.copy()
   
    # Filter stasiun
    stasiun_list = dfh["Nama Stasiun"].dropna().unique().tolist()
    stasiun_selected = st.multiselect("Pilih Stasiun:",
                                      options=stasiun_list,
                                      default=stasiun_list[:3])

    if stasiun_selected:
        df_day = dfh[dfh["Nama Stasiun"].isin(stasiun_selected)].copy()
        df_day["Total Laporan"] = df_day[["00Z", "12Z"]].notna().sum(axis=1)

        # --- Grafik 1: Time Series jumlah laporan per hari
        fig_daily = px.line(
            df_day,
            x="Tanggal", y="Total Laporan",
            color="Nama Stasiun",
            title=f"Jumlah Laporan Harian Per Stasiun",
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Vivid
        )
        fig_daily.update_yaxes(range=[-0.1, 2.1], dtick=1, title="Jumlah Laporan (0–2)")
        st.plotly_chart(fig_daily, use_container_width=True)
        figs.append((f"time_series_rason.png", fig_daily))

    
    # --- Grafik 3: Bar Chart per stasiun
    dfb_sorted = dfb.sort_values(by="Ketersediaan (%)", ascending=False).reset_index(drop=True)
    avg_availability = dfb_sorted["Ketersediaan (%)"].mean()

    dfb_sorted["Highlight"] = "Normal"
    if len(dfb_sorted) >= 3:
        dfb_sorted.loc[:2, "Highlight"] = "Top 3"
    if len(dfb_sorted) >= 6:
        dfb_sorted.loc[dfb_sorted.tail(3).index, "Highlight"] = "Bottom 3"

    # Ambil tiga warna tegas dari Vivid palette
    vivid_colors = colors.qualitative.Vivid

    color_map = {
        "Top 3": vivid_colors[0],     # misal biru
        "Bottom 3": vivid_colors[1],  # misal oranye
        "Normal": vivid_colors[2]     # misal hijau
}

    fig_sorted = px.bar(
        dfb_sorted,
        x="Nama Stasiun", y="Ketersediaan (%)",
        color="Highlight",
        color_discrete_map=color_map,
        text=dfb_sorted["Ketersediaan (%)"].round(1),
        hover_data=["Jumlah Laporan"],
        title="Ketersediaan Bulanan RASON per Stasiun"
    )
    fig_sorted.add_hline(
        y=avg_availability,
        line_dash="dot", line_color="black",
        annotation_text=f"<span style='color:black; background-color:white; padding:2px;'>Rata-rata {avg_availability:.1f}%</span>",
        annotation_position="top left"
    )
    fig_sorted.update_traces(textposition="outside", cliponaxis = False)
    fig_sorted.update_yaxes(range=[0, 105])
    st.plotly_chart(fig_sorted, use_container_width=True)
    figs.append(("bar_sorted_rason.png", fig_sorted))


    # --- Pie Chart Persentase Laporan 00Z vs 12Z ---
    total_00z = dfh["00Z"].notna().sum()
    total_12z = dfh["12Z"].notna().sum()

    df_pie = pd.DataFrame({
        "Jam": ["00Z", "12Z"],
        "Jumlah Laporan": [total_00z, total_12z]
    })

    fig_pie = px.pie(
        df_pie,
        names="Jam",
        values="Jumlah Laporan",
        title="Persentase Laporan 00Z vs 12Z",
        color="Jam",
        color_discrete_sequence=px.colors.qualitative.Vivid,  # pakai Vivid palette
        hole=0.3
    )

    # Tampilkan persentase di label
    fig_pie.update_traces(textinfo="label+percent", textfont_size=14)

    st.plotly_chart(fig_pie, use_container_width=True)
    figs.append(("pie_00z_12z.png", fig_pie))


    # ==================== Return Figures ====================
    if return_figs:
        fixed_figs = [(fname, fix_figure_colors(fig)) for fname, fig in figs]
        return fixed_figs


# === Visualisasi SPECI ===
# === Visualisasi SPECI ===
# === Visualisasi SPECI ===

def show_speci_visualizations(df_speci_harian: pd.DataFrame, df_speci_bulanan: pd.DataFrame, return_figs = True):
    st.markdown("<h4 style='color:#0d47a1;'>⚠️ Visualisasi Laporan SPECI</h4>", unsafe_allow_html=True)
    figs = []

    # --- 1. Line Chart SPECI Harian per Stasiun ---
    daftar_stasiun = df_speci_harian["ICAO"].unique().tolist()
    stasiun_terpilih = st.multiselect(
        "Pilih Stasiun untuk Ditampilkan di Grafik:",
        options=daftar_stasiun,
        default=daftar_stasiun[:3] if len(daftar_stasiun) >= 3 else daftar_stasiun,
        help="Pilih satu atau lebih stasiun"
    )

    df_filter_speci = df_speci_harian[df_speci_harian["ICAO"].isin(stasiun_terpilih)]

    if not df_filter_speci.empty:
        fig_harian = px.line(
            df_filter_speci,
            x="Tanggal",
            y="Jumlah SPECI Harian",
            color="ICAO",
            markers=True,
            title="Jumlah SPECI Harian per Stasiun",
            color_discrete_sequence=px.colors.qualitative.Vivid,
            hover_data=["Nama Stasiun"]
        )
        fig_harian.update_traces(
            text=df_filter_speci["Jumlah SPECI Harian"].round(1),
            textposition="top center"
        )
        fig_harian.update_layout(template="plotly_white")
        st.plotly_chart(fig_harian, use_container_width=True)
        figs.append(("speci_harian.png", fig_harian))
    else:
        st.info("Silakan pilih minimal satu stasiun untuk menampilkan grafik.")

    df_sorted = df_speci_bulanan.sort_values(by="Jumlah SPECI Bulanan", ascending=False)

    # --- 2. Top 10 Stasiun Kirim SPECI Terbanyak ---
    top10 = df_sorted[df_sorted["Jumlah SPECI Bulanan"] > 0].head(10)

    fig_top10 = px.bar(
        top10,
        x="ICAO", y="Jumlah SPECI Bulanan",
        color="Jumlah SPECI Bulanan",
        color_continuous_scale=px.colors.sequential.Blues,
        hover_data=["Nama Stasiun"],
        title="Top 10 Stasiun dengan SPECI Terbanyak",
        text="Jumlah SPECI Bulanan"
    )
    fig_top10.update_traces(textposition="outside")
    fig_top10.update_layout(template="plotly_white")
    st.plotly_chart(fig_top10, use_container_width=True)
    figs.append(("speci_top10.png", fig_top10))


    if return_figs:
        fixed_figs = [(fname, fix_figure_colors(fig)) for fname, fig in figs]
        return fixed_figs

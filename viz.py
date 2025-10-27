import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.express import colors
import numpy as np

# === Styling konsisten ===
def fix_figure_colors(fig):
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#0d47a1", size=12),
        title_font=dict(size=16, color="#000000"),
        legend=dict(title="", orientation="h", y=-0.2),
        margin=dict(l=50, r=30, t=60, b=50)
    )
    return fig


# === Visualisasi METAR ===
# === Visualisasi METAR ===
# === Visualisasi METAR ===

def show_metar_visualizations(df_harian: pd.DataFrame, df_bulanan :pd.DataFrame, return_figs=True):
    st.markdown("<h3 style='color:#0d47a1;'>📊 Visualisasi Laporan METAR</h4>", unsafe_allow_html=True)
    figs = []
    
    # Rata-rata Laporan METAR Aktual vs. Target (Diharapkan) per Interval Stasiun
    # Hitung rata-rata per interval
    df_grouped = df_harian.groupby("Interval Pengiriman").agg({
        "Laporan Masuk": "mean",
        "Laporan Diharapkan": "mean"
    }).reset_index()

    # Ubah ke long format untuk Plotly Express
    df_long = pd.melt(
        df_grouped,
        id_vars="Interval Pengiriman",
        value_vars=["Laporan Masuk", "Laporan Diharapkan"],
        var_name="Jenis Laporan",
        value_name="Jumlah Rata-rata"
    )

    # Buat grouped bar chart
    fig = px.bar(
        df_long,
        x="Interval Pengiriman",
        y="Jumlah Rata-rata",
        color="Jenis Laporan",
        barmode="group",
        text="Jumlah Rata-rata",
        title="Rata-rata Laporan METAR Aktual vs. Target (Diharapkan) per Interval Stasiun",
        labels={"Interval Pengiriman": "Interval (Jam)"}
    )

    # Format angka di atas batang
    fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')

    # Layout
    fig.update_layout(
        yaxis_title="Jumlah Laporan Rata-rata",
        xaxis=dict(tickmode="linear"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#0d47a1")
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("Rata.png", fix_figure_colors(fig)))


    # ================== Line Chart Ketersediaan Harian per Stasiun ==================
    daftar_stasiun = df_harian["ICAO"].unique().tolist()
    stasiun_terpilih = st.multiselect(
        "Pilih Stasiun untuk Ditampilkan di Grafik:",
        options=daftar_stasiun,
        default=daftar_stasiun[:3],
        help="Pilih satu atau lebih stasiun"
    )

    df_filter = df_harian[df_harian["ICAO"].isin(stasiun_terpilih)]

    if not df_filter.empty:
        # Pastikan tanggal diurutkan
        df_filter = df_filter.sort_values("Tanggal")

        # Line chart per stasiun
        fig1 = px.line(
            df_filter,
            x="Tanggal",
            y="Ketersediaan (%)",
            color="ICAO",
            markers=True,
            title="Tren Ketersediaan Harian METAR per Stasiun",
            color_discrete_sequence=px.colors.qualitative.Vivid,
            hover_data={"Ketersediaan (%)": ':.1f'}
        )

        # Clamp y-axis agar outlier tidak merusak tampilan
        fig1.update_yaxes(range=[0, 110])
        # Hapus text di titik agar chart tidak berantakan
        fig1.update_traces(mode="lines+markers")
        # Styling konsisten
        fig1.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(color="#0d47a1", size=12),
            title_font=dict(size=16, color="#000000"),
            legend=dict(title="", orientation="h", y=-0.2),
            margin=dict(l=50, r=30, t=60, b=50)
        )

        st.plotly_chart(fig1, use_container_width=True)
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
        figs.append(("tren_ketersediaan.png", fig1))

    else:
        st.info("Silakan pilih minimal satu stasiun untuk menampilkan grafik.")

# ================== Donut Chart Status ==================
    pie_data = df_harian["Catatan"].value_counts().reset_index()
    pie_data.columns = ["Status", "Jumlah"]

    fig_status = px.pie(
        pie_data,
        names="Status",
        values="Jumlah",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Plasma
    )
    fig_status.update_traces(textinfo="percent+label")
    fig_status.update_layout(
        annotations=[dict(text=str(pie_data["Jumlah"].sum()), x=0.5, y=0.5,
                          font_size=18, showarrow=False)]
    )
    fig_status.update_layout(title="Distribusi Status Ketersediaan")
    st.plotly_chart(fig_status, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("status_donut.png", fix_figure_colors(fig_status)))

    # return semua fig
    if return_figs:
        return figs


# === Visualisasi RASON ===
# === Visualisasi RASON ===
# === Visualisasi RASON ===

def show_rason_visualizations(df_rason_harian: pd.DataFrame,
                              df_rason_bulanan: pd.DataFrame,
                              return_figs=True):

    st.markdown("<h4 style='color:#0d47a1;'>⚠️ Visualisasi Laporan RASON </h4>", unsafe_allow_html=True)
    figs = []

    dfh = df_rason_harian.copy()
    dfb = df_rason_bulanan.copy()
   
    # --- Grafik 1: Bar Chart Proporsi Stasiun berdasarkan Status ---
    status_counts = dfb["Catatan"].value_counts().reset_index()
    status_counts.columns = ["Catatan", "Jumlah Stasiun"]

    # Buat bar chart
    fig_status_bar = px.bar(
        status_counts,
        x="Catatan",
        y="Jumlah Stasiun",
        color="Catatan",
        text="Jumlah Stasiun",
        color_discrete_sequence=["#0d47a1", "#39e426", "#ffb300"],
        title="Jumlah Stasiun berdasarkan Status Klasifikasi"
    )

    fig_status_bar.update_traces(
        textposition="outside",
        hovertemplate="%{x}: %{y} stasiun",
   
    )
    fig_status_bar.update_layout(
        showlegend=False,
        yaxis_title="Jumlah Stasiun",
        xaxis_title=None,
        template="plotly_white",
        bargap=0.60,
        margin=dict(t=30, b=40, l=50, r=20)
    )

    st.plotly_chart(fig_status_bar, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("bar_status_klasifikasi.png", fig_status_bar))


    # --- Grafik 2: Donut Chart 
    # Hitung jumlah laporan valid per jam
    total_00z = dfh["00Z"].notna().sum()
    total_12z = dfh["12Z"].notna().sum()
    total_all = total_00z + total_12z

    df_pie = pd.DataFrame({
        "Jam": ["00Z", "12Z"],
        "Jumlah Laporan": [total_00z, total_12z]
    })

    # Donut chart tanpa angka total & tanpa hover jumlah
    fig_donut = px.pie(
        df_pie,
        names="Jam",
        values="Jumlah Laporan",
        hole=0.5,
        color="Jam",
        color_discrete_sequence=["#185DA2", "#39e426"],
        title="Distribusi Laporan 00Z vs 12Z"
    )
    # Hanya label + persen, hover dihilangkan
    fig_donut.update_traces(
        textinfo="label+percent",
        textfont_size=14,
        hovertemplate="%{label}: %{percent}"  # hanya label + persen
)
    # Tambah total di tengah
    fig_donut.add_annotation(
        text=f"<b>{total_all}</b><br>Total",
        showarrow=False,
        font_size=14
    )
    fig_donut.update_layout(
        template="plotly_white",
        margin=dict(t=60, b=60, l=60, r=60)
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("donut_00z_12z.png", fig_donut))


    # ============ Total Laporan Lengkap per Hari (Periode Bulan Ini) ================
    # Hitung total laporan per baris (00Z + 12Z)
    dfh["Total Laporan"] = dfh[["00Z", "12Z"]].notna().sum(axis=1)

    # --- 1. Hitung jumlah laporan lengkap (2 laporan/hari) per tanggal ---
    daily_summary = (
        dfh.groupby("Tanggal")["Total Laporan"]
        .apply(lambda x: (x == 2).sum())  # hitung berapa baris lengkap (00Z+12Z)
        .reset_index(name="Laporan Lengkap")
    )

    # --- 2. Visualisasi: Line Chart Total Laporan Lengkap per Tanggal ---
    fig_line = px.line(
        daily_summary,
        x="Tanggal",
        y="Laporan Lengkap",
        markers=True,
        title="Tren Jumlah Stasiun dengan Laporan Harian Lengkap (00Z & 12Z)",
        labels={"Laporan Lengkap": "Jumlah Laporan Lengkap", "Tanggal": "Tanggal"}
    )

    fig_line.update_traces(
        line=dict(width=3, color="#185DA2"),
        marker=dict(size=8, color="#39e426")
    )

    fig_line.update_layout(
       yaxis = dict(
           range =[max(0, daily_summary["Laporan Lengkap"].min()-1),
                   daily_summary["Laporan Lengkap"].max()+1],
           showgrid = True
       ),
       xaxis = dict(showgrid=True),
       hovermode= "x unified"
    )

    st.plotly_chart(fig_line, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("line_laporan_per_hari.png", fig_line))

  
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


# ======== VISUALISASI TAF ============

def show_TAF_visualizations(df_harian: pd.DataFrame, df_bulanan: pd.DataFrame, return_figs=True):
    st.markdown("<h4 style='color:#0d47a1;'>⚠️ Visualisasi Laporan TAF </h4>", unsafe_allow_html=True)
    figs = []
# ---------------- Line Chart: Tren Harian per Stasiun ----------------
    # Ambil semua stasiun yang tersedia
    stasiun_list = df_harian['ICAO'].unique().tolist()
    selected_stasiun = st.multiselect(
        "Pilih Stasiun untuk Tren Harian:",
        options=stasiun_list,
        default=stasiun_list[:5]  # default 5 stasiun saja supaya chart tidak terlalu padat
    )

    # Filter berdasarkan stasiun yang dipilih
    df_filtered = df_harian[df_harian['ICAO'].isin(selected_stasiun)].copy()
    df_filtered['Tanggal'] = pd.to_datetime(df_filtered['Tanggal'], errors='coerce')
    df_filtered = df_filtered.sort_values(['ICAO','Tanggal'])

    # --- Line chart tanpa moving average ---
    fig_line = px.line(
        df_filtered,
        x='Tanggal',
        y='Jumlah TAF Harian',
        color='ICAO',
        markers=True,
        title="Tren Harian TAF per Stasiun",
        hover_data=['Nama Stasiun','Ketersediaan %','Catatan']
    )
    st.plotly_chart(fig_line, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("TAF_line_daily.png", fig_line))


    # ---------------- Bar Chart: Top 5 & Bottom 5 Stasiun ----------------
    df_sum = df_harian.groupby(['ICAO','Nama Stasiun'])['Jumlah TAF Harian'].sum().reset_index()
    df_sum = df_sum.sort_values('Jumlah TAF Harian', ascending=False)
    
    top5 = df_sum.head(5)
    bottom5 = df_sum.tail(5)
    df_bar = pd.concat([top5, bottom5])

    fig_bar = px.bar(
        df_bar,
        x='Jumlah TAF Harian',
        y='ICAO',
        text='Jumlah TAF Harian',
        color='Jumlah TAF Harian',
        color_continuous_scale=px.colors.sequential.Plasma[::-1],
        title="Top 5 & Bottom 5 Stasiun TAF Bulanan",
    )
    fig_bar.update_traces(textposition="outside")
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("TAF_bar_top_bottom.png", fig_bar))
   
   

    # Hitung distribusi

    df_status = df_harian["Catatan"].value_counts().reset_index()
    df_status.columns = ["Status", "Jumlah"]

    fig_status = px.pie(
        df_status,
        names="Status",
        values="Jumlah",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Teal[::-1], 
    )
    fig_status.update_traces(textinfo="percent+label")
    fig_status.update_layout(
        annotations=[dict(text=str(df_status["Jumlah"].sum()), x=0.5, y=0.5,
                          font_size=18, showarrow=False)]
    )
    fig_status.update_layout(title="Distribusi Status Ketersediaan")
    st.plotly_chart(fig_status, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("status_donut.png", fix_figure_colors(fig_status)))


    if return_figs:
        fixed_figs = [(fname, fix_figure_colors(fig)) for fname, fig in figs]
        return fixed_figs

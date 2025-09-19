import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.express import colors

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
def show_metar_visualizations(df_harian: pd.DataFrame, df_bulanan :pd.DataFrame, return_figs=True):
    st.markdown("<h3 style='color:#0d47a1;'>📊 Visualisasi Laporan METAR</h4>", unsafe_allow_html=True)
    figs = []
    
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

    # ================== Interval Pengiriman  ==================
    # Filter data normal (≤100%)
    interval_normal = df_harian[df_harian["Ketersediaan (%)"] <= 100]
    interval_df = interval_normal.groupby("Interval Pengiriman")["Ketersediaan (%)"].mean().reset_index()

 # hitung outlier
    anomali_count = df_harian[df_harian["Ketersediaan (%)"] > 100]\
        .groupby("Interval Pengiriman")["Ketersediaan (%)"].count().reset_index()
    anomali_count.rename(columns={"Ketersediaan (%)": "Outlier"}, inplace=True)

    custom_blue_scale = [
        [0.0, "#c6dbef"],  # biru tua untuk nilai rendah
        [0.5, "#2171b5"],  # biru medium
        [1.0, "#08306b"]   # biru muda tapi masih jelas
    ]
    # Buat bar chart rata-rata
    fig_interval = px.bar(
        interval_df,
        x="Interval Pengiriman",
        y="Ketersediaan (%)",
        color="Ketersediaan (%)",
        color_continuous_scale=custom_blue_scale,
        text=interval_df["Ketersediaan (%)"].round(1),
        title="Pengaruh Interval Pengiriman terhadap Rata-rata Ketersediaan"
    )
    fig_interval.update_traces(textposition="outside")

    # Tambahkan jumlah outlier sebagai text di atas bar
    for i, row in anomali_count.iterrows():
        fig_interval.add_annotation(
            x=row["Interval Pengiriman"],
            y=100,  # di atas bar
            text=f"{row['Outlier']} outlier >100%",
            showarrow=False,
            font=dict(color="red", size=12)
        )

    # Styling konsisten
    fig_interval = fix_figure_colors(fig_interval)

    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    # Tampilkan di Streamlit
    st.plotly_chart(fig_interval, use_container_width=True)
    figs.append(("interval_jam.png", fig_interval))

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

# ================== Tabel ==================
    st.markdown(
        "<h6 style='color:#000000; font-weight: bold;'>Laporan Masuk vs Diharapkan per Jam Operasional</h5>",
        unsafe_allow_html=True
    )

    if "Jam Operasional" in df_harian.columns:
        # Urutkan jam kronologis
        df_harian["Jam Operasional"] = pd.Categorical(
            df_harian["Jam Operasional"],
            categories=sorted(df_harian["Jam Operasional"].unique()),
            ordered=True
        )

        jam_df = df_harian.groupby("Jam Operasional").agg(
            {"Laporan Masuk": "sum", "Laporan Diharapkan": "sum"}
        ).reset_index()

        # Hitung persentase capaian
        jam_df["Persentase (%)"] = (jam_df["Laporan Masuk"] / jam_df["Laporan Diharapkan"] * 100).round(1)

        # Buat style untuk heatmap sederhana
        def color_scale(val):
            if val >= 100:
                color = 'background-color: #2ca02c; color: white'  # hijau
            elif val >= 50:
                color = 'background-color: #ffdd57; color: black'  # kuning
            else:
                color = 'background-color: #d62728; color: white'  # merah
            return color
        # Terapkan style di kolom persentase
        styled_df = jam_df.style.applymap(color_scale, subset=["Persentase (%)"])
        st.dataframe(styled_df, use_container_width=True)

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
   
    # --- Grafik 1: Horizontal Bar Chart per stasiun
    dfb_sorted = dfb.sort_values(by="Ketersediaan (%)", ascending=True).reset_index(drop=True)
    avg_availability = dfb_sorted["Ketersediaan (%)"].mean()

    dfb_sorted["Highlight"] = "Normal"
    if len(dfb_sorted) >= 3:
        dfb_sorted.loc[:2, "Highlight"] = "Bottom 3"
        dfb_sorted.loc[dfb_sorted.tail(3).index, "Highlight"] = "Top 3"

    vivid_colors = px.colors.qualitative.Vivid
    color_map = {
        "Top 3": vivid_colors[0],
        "Bottom 3": vivid_colors[1],
        "Normal": vivid_colors[2]
    }

    fig_barh = px.bar(
        dfb_sorted,
        y="Nama Stasiun", x="Ketersediaan (%)",
        color="Highlight",
        color_discrete_map=color_map,
        text=dfb_sorted["Ketersediaan (%)"].round(1),
        hover_data=["Jumlah Laporan"],
        title="Ketersediaan Bulanan RASON per Stasiun"
    )
    fig_barh.add_vline(
        x=avg_availability,
        line_dash="dot", line_color="black",
        annotation_text=f"Rata-rata {avg_availability:.1f}%",
        annotation_position="top"
    )
    fig_barh.update_traces(textposition="outside", cliponaxis=False)
    fig_barh.update_xaxes(range=[0, 105])
    st.plotly_chart(fig_barh, use_container_width=True)
    figs.append(("barh_sorted_rason.png", fig_barh))


    # --- Grafik 2: Donut Chart 
    # Hitung jumlah laporan valid per jam
    total_00z = dfh["00Z"].notna().sum()
    total_12z = dfh["12Z"].notna().sum()

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
    st.plotly_chart(fig_donut, use_container_width=True)
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    figs.append(("donut_00z_12z.png", fig_donut))



# ============ Rata rata Laporan Per Hari ================
    # Hitung total laporan per baris (00Z + 12Z)
    dfh["Total Laporan"] = dfh[["00Z", "12Z"]].notna().sum(axis=1)

    # --- 1. Agregasi harian ---
    daily_summary = dfh.groupby("Tanggal")["Total Laporan"].value_counts().unstack(fill_value=0)
    daily_summary["Total Laporan"] = daily_summary.sum(axis=1)
    daily_summary = daily_summary.reset_index()

    # --- 2. Ubah nama hari ke bahasa Indonesia ---
    hari_map = {
        "Monday": "Senin",
        "Tuesday": "Selasa",
        "Wednesday": "Rabu",
        "Thursday": "Kamis",
        "Friday": "Jumat",
        "Saturday": "Sabtu",
        "Sunday": "Minggu"
    }
    daily_summary["Hari"] = pd.to_datetime(daily_summary["Tanggal"]).dt.day_name().map(hari_map)

    # --- 3. Rename kolom '2' menjadi 'Laporan Lengkap' untuk lebih jelas ---
    if 2 in daily_summary.columns:
        daily_summary = daily_summary.rename(columns={2: "Laporan Lengkap"})
    else:
        daily_summary["Laporan Lengkap"] = 0  # jika tidak ada laporan lengkap sama sekali

    # --- 4. Rata-rata laporan lengkap per hari dalam seminggu ---
    weekly_pattern = daily_summary.groupby("Hari")["Laporan Lengkap"].mean().reindex([
        "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"
    ]).reset_index().rename(columns={"Laporan Lengkap": "Rata-rata Laporan Lengkap"})


    # --- 5. Visualisasi: Bar Chart Rata-rata Laporan Lengkap per Hari ---
    custom_green = [
    [0.0,"#ADF1AD"],  # nilai terendah → hijau tua
    [1.0, "#006400"]   # nilai tertinggi → hijau cerah
]
    fig_bar = px.bar(
        weekly_pattern,
        x="Hari",
        y="Rata-rata Laporan Lengkap",
        title="Rata-rata Jumlah Laporan Lengkap per Hari",
        text=weekly_pattern["Rata-rata Laporan Lengkap"].round(1),
        labels={"Rata-rata Laporan Lengkap": "Rata-rata Laporan Lengkap", "Hari": "Hari"},
        color="Rata-rata Laporan Lengkap",  # Warna berbeda per hari
        color_continuous_scale=custom_green, 
        range_color=[weekly_pattern["Rata-rata Laporan Lengkap"].min(), weekly_pattern["Rata-rata Laporan Lengkap"].max()]
    )
    fig_bar.update_traces(textposition="outside")
    st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
    st.plotly_chart(fig_bar, use_container_width=True)

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



# ========TAF ============

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

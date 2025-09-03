# libraries

import streamlit as st
import asyncio, nest_asyncio, aiohttp
import pandas as pd
import numpy as np
import calendar
import re
from io import BytesIO
import zipfile

from auth import get_bmkg_token
from station import fetch_all_stations_info
from fetcher import fetch_gts_data
from runner import fetch_and_analyze_metar, fetch_and_analyze_speci, fetch_and_analyze_rason
from viz import show_metar_visualizations, show_speci_visualizations, show_rason_visualizations
from streamlit_option_menu import option_menu



# --- WRAPPERS ---
async def fetch_and_analyze_metar_wrapper(tahun, bulan, mode, station_info_map):
    token = await get_bmkg_token()
    async with aiohttp.ClientSession() as session:
        return await fetch_and_analyze_metar(
            token, session, tahun, bulan, mode, station_info_map, fetch_gts_data
        )

async def fetch_and_analyze_rason_wrapper(tahun, bulan, station_info_map):
    token = await get_bmkg_token()
    async with aiohttp.ClientSession() as session:
        return await fetch_and_analyze_rason(
            token, session, tahun, bulan, station_info_map, fetch_gts_data
        )

async def fetch_and_analyze_speci_wrapper(tahun, bulan, station_info_map):
    token = await get_bmkg_token()
    async with aiohttp.ClientSession() as session:
        return await fetch_and_analyze_speci(
            token, session, tahun, bulan, station_info_map, fetch_gts_data
        )
        
# --- Page Config ---        
st.set_page_config(page_title="Analisis Ketersediaan Data Cuaca BMKG", layout="wide")
# st.markdown("""
# <div style="
#     background: linear-gradient(to right, #1f77b4, #2ca02c);
#     padding: 30px;
#     border-radius: 15px;
#     text-align: center;
#     color: white;
#     box-shadow: 0 4px 6px rgba(0,0,0,0.1);
# ">
#     <h1 style="margin: 0; font-size: 40px; font-weight: bold;">📡 Analisis Ketersediaan Data Cuaca BMKG</h1>
#     <p style="margin: 5px 0 0; font-size: 20px;">METAR • RASON • SPECI</p>
# </div>
# """, unsafe_allow_html=True)

st.markdown("""
<h1 style="
    font-size: 40px;
    font-weight: bold;
    text-align: center;
    background: linear-gradient(to right, #1f77b4, #2ca02c);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
">
📡 Analisis Ketersediaan Data Cuaca BMKG
</h1>
<p style="text-align: center; font-size: 20px;">METAR • RASON • SPECI</p>
""", unsafe_allow_html=True)


# ======= Fungsi Async Wrapper =======
# Streamlit tidak bisa langsung menjalankan fungsi async
# Fungsi ini membuat kita bisa memanggil fungsi async secara sinkron   
nest_asyncio.apply()

def run_async(func, *args, **kwargs):
    """Menjalankan fungsi async secara sinkron di Streamlit"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(func(*args, **kwargs))

async def get_stations_wrapper():
    try:
        token = await get_bmkg_token()
    except Exception as e:
        import traceback
        print("DEBUG LOGIN BMKG:", e)
        traceback.print_exc()
        raise 
    async with aiohttp.ClientSession() as session:
            stations = await fetch_all_stations_info(token, session)
    return stations

        
# Ambil daftar stasiun sekali di awal aplikasi
# Disimpan di session_state supaya bisa digunakan di seluruh tab

if "stations_list_global" not in st.session_state:
    with st.spinner("Mengambil daftar stasiun..."):
        try:
            # Jalankan coroutine secara sinkron di Streamlit
            st.session_state["stations_list_global"] = run_async(get_stations_wrapper)
        except Exception as e:
            st.error(f"Gagal mengambil daftar stasiun: {e}")
            st.session_state["stations_list_global"] = {}

# Ambil dari session_state
stations_list_global = st.session_state.get("stations_list_global", {})
# Buat mapping ICAO untuk analisis
station_info_map = stations_list_global


# ================= MAIN STREAMLIT =================
# --- Sidebar: Navigasi ---# --- Sidebar Option Menu ---
with st.sidebar:
    st.markdown(
        """
        <style>
        .sidebar-title {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 30px;        /* lebih besar */
            font-weight: 700;       /* lebih tebal */
            color: #000000;         
            margin-bottom: 20px;
        }
        </style>
        <div class="sidebar-title">
            Analisis Data
        </div>
        """,
        unsafe_allow_html=True
    )

    menu = option_menu(
        menu_title=None,
        options=["METAR", "RASON", "SPECI"],
        icons=["cloud", "bar-chart", "activity"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {
                "padding": "0px",
                "background-color": "#ffffff",
                "border-radius": "8px",
            },
            "icon": {
                "font-size": "18px",
                "color": "#1565c0",
            },
            "nav-link": {
                "font-size": "16px",
                "text-align": "left",
                "margin": "5px 0",
                "padding": "8px 12px",
                "color": "#333333",
                "--hover-color": "#e3f2fd",  # hover biru muda
            },
            "nav-link-selected": {
                "background-color": "#50c656",
                "color": "white",
                "font-weight": "bold",
            },
        }
    )


# --- PENJELASAN MENU ---
penjelasan = {
    "METAR": {
        "judul": "Analisis Data METAR",
        "lengkap": (
            "METAR adalah laporan cuaca rutin dari bandara yang biasanya dikeluarkan setiap 30 menit "
            "atau 1 jam, tergantung stasiun. Laporan ini memberikan informasi cuaca permukaan secara "
            "detail, termasuk suhu, tekanan udara, arah dan kecepatan angin, visibilitas, serta fenomena "
            "cuaca seperti hujan, kabut, atau badai. Data METAR sangat penting untuk operasi penerbangan "
            "dan keselamatan penerbangan."
        )
    },
    "RASON": {
        "judul": "Analisis Data RASON",
        "lengkap": (
            "RASON adalah laporan pengamatan atmosfer yang menggunakan balon cuaca, dikeluarkan dua kali "
            "sehari (00Z dan 12Z). Laporan ini mencakup profil vertikal atmosfer, termasuk suhu, kelembaban, "
            "tekanan udara, dan arah serta kecepatan angin. RASON digunakan untuk analisis meteorologi, "
            "pemodelan cuaca, dan prediksi cuaca jangka pendek."
        )
    },
    "SPECI": {
        "judul": "Analisis Data SPECI",
        "lengkap": (
            "SPECI adalah laporan cuaca khusus yang dikeluarkan di luar jadwal METAR rutin, ketika terjadi "
            "perubahan cuaca signifikan, misalnya badai, hujan lebat, kabut tebal, atau perubahan angin ekstrem. "
            "Formatnya mirip dengan METAR, namun fokus pada kondisi cuaca yang memerlukan perhatian segera, "
            "sehingga penting untuk pemantauan keselamatan dan peringatan dini."
        )
    }
}

# Fungsi helper biar ga nulis berulang
st.write("") 
def show_penjelasan(menu):
    st.subheader(penjelasan[menu]["judul"])
    with st.expander("📘 Penjelasan Singkat"):
        st.write(penjelasan[menu]["lengkap"])


# ================= TAB METAR =================
# ================= TAB METAR =================
# ================= TAB METAR =================

if menu == "METAR":
    show_penjelasan("METAR")
    st.markdown("<br>", unsafe_allow_html=True)  
    
    # --- Input ---
    col1, col2 = st.columns(2)
    tahun = col1.selectbox("Pilih Tahun", list(range(2020, 2026)), index=5)
    bulan = col2.selectbox("Pilih Bulan", list(range(1, 13)), index=0)

    mode = st.radio("Mode Perhitungan", ["Otomatis", "Interval 1 Jam"], key="metar_mode")
    
    # # --- FILTER METAR ---
    # if not stations_list_global:
    #     st.warning("Daftar stasiun belum tersedia, coba muat ulang aplikasi.")

    if st.button("Analisis METAR"):
        with st.spinner("Mengambil dan menganalisis data METAR..."):
            try:
                    df_metar = run_async(fetch_and_analyze_metar_wrapper, tahun, bulan, mode, station_info_map)
                    # simpan di session state supaya bisa diakses di filter dan di visualisasi
                    st.session_state["df_metar_raw"] = df_metar
                    st.session_state["metar_analisis_selesai"] = True
            except Exception as e:
                    st.error(f"Gagal analisis Metar:{e}")
                    
    # jika analisis selesai    
    if st.session_state.get("metar_analisis_selesai", False):
        metar_subtabs = st.tabs(["📄 Tabel Analisis", "📊 Visualisasi"])       
        
        with metar_subtabs[0]:  
            # Kalau analisis sudah selesai, tampilkan filter
            if st.session_state.get("metar_analisis_selesai", False):
                df_metar = st.session_state["df_metar_raw"]     
                
                # Hitung KPI
                total_stasiun = df_metar["ICAO"].nunique()
                total_laporan = len(df_metar)
                persentase_lengkap = df_metar["Status Lengkap"].mean() * 100
                tidak_lengkap = 100 - persentase_lengkap

                st.markdown(
                    "<h4 style='margin-top:15px; color:#000000;'>📊 Ringkasan METAR</h4>",
                    unsafe_allow_html=True
                )

                col1, col2, col3, col4 = st.columns(4)

                def kpi_card(col, title, value, color="#1565C0", bg_color="#f9f9f9", text_color="#333"):
                    col.markdown(f"""
                    <div style="
                        background-color:{bg_color};
                        padding:6px 6px;
                        border-radius:6px;
                        text-align:center;
                        box-shadow:1px 1px 3px rgba(0,0,0,0.08);
                        width:100%;
                        display:flex;
                        flex-direction:column;
                        justify-content:center;
                        align-items:center;
                        transition: all 0.2s ease-in-out;
                    " onmouseover="this.style.transform='scale(1.02)';" 
                    onmouseout="this.style.transform='scale(1)';">
                        <h4 style="margin:0; font-size:1.2rem; line-height:0.8; color:{text_color};">{title}</h4>
                        <h2 style="margin:0; font-size:1.5rem; line-height:0.8; color:{color};">{value}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                kpi_card(col1, "📡 Jumlah Stasiun", total_stasiun)
                kpi_card(col2, "📑 Total Laporan", total_laporan)
                kpi_card(col3, "✅ Lengkap (%)", f"{persentase_lengkap:.1f}%")
                kpi_card(col4, "⚠️ Tidak Lengkap (%)", f"{tidak_lengkap:.1f}%")



                st.markdown("<br>", unsafe_allow_html=True)

                with st.expander("⚙️ Filter Lanjutan"):
                    # --- Filter berdasarkan ICAO ---
                    stasiun_opsi = sorted(df_metar["ICAO"].unique())
                    selected_stations = st.multiselect(
                                "Pilih Stasiun (ICAO)",
                                options=stasiun_opsi,
                                default=stasiun_opsi, # default semua terpilih
                                key="filter_metar_icao" 
                            )
                    df_metar = df_metar[df_metar["ICAO"].isin(selected_stations)]     
                    
                    # --- Filter berdasarkan Status Ketersediaan ---
                    status_filter = st.selectbox("Filter Status Ketersediaan", 
                                                 ["Semua", "Lengkap", "Tidak Lengkap"], 
                                                 key="filter_metar_status")
                    
                    if status_filter == "Lengkap":
                            df_metar = df_metar[df_metar["Status Lengkap"] == True]
                    elif status_filter == "Tidak Lengkap":
                            df_metar = df_metar[df_metar["Status Lengkap"] == False]
                    

                    # --- Filter berdasarkan Jam Operasional --- 
                    jam_opsi = sorted(df_metar["Jam Operasional"].unique())
                    selected_ops = st.multiselect(
                            "Pilih Jam Operasional",
                            options=jam_opsi,
                            default=jam_opsi,
                            key="filter_metar_jam"
                        )
                    df_metar = df_metar[df_metar["Jam Operasional"].isin(selected_ops)]

                # --- simpan hasil filter
                st.session_state["df_metar"] = df_metar

                # buat salinan khusus untuk display (tanpa kolom Status Lengkap)
                df_metar_display = df_metar.copy()
                if "Status Lengkap" in df_metar_display.columns:
                        df_metar_display = df_metar_display.drop(columns=["Status Lengkap"])

                st.markdown("<br>", unsafe_allow_html=True)  # spasi vertikal kecil
                st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)  # spasi lebih besar

                st.dataframe(df_metar_display, use_container_width=True)

                # --- Download tetap pakai data asli 
                df_metar_download = df_metar.copy()
                if "Status Lengkap" in df_metar_download.columns:
                    df_metar_download = df_metar_download.drop(columns=["Status Lengkap"])
    
                df_metar_download["Catatan"] = df_metar_download["Catatan"].apply(
                        lambda x: re.sub(r"[^0-9A-Za-z\s\-]", "", str(x))
                    )

                csv = df_metar_download.to_csv(index=False).encode("utf-8")
                st.download_button(
                        label="📥Download CSV METAR",
                        data=csv,
                        file_name=f"metar_{tahun}_{bulan}.csv",
                        mime="text/csv"
                    )
                
            # ================= TAB VISUALISASI =================
            with metar_subtabs[1]:

                df_filtered = st.session_state["df_metar"]
                figs = show_metar_visualizations(df_filtered, return_figs=True)

                # buat ZIP
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for filename, fig in figs:
                        fig.update_layout(
                        template="plotly_white",
                        paper_bgcolor="white",
                        plot_bgcolor="white"
                    )
                                
                        img_bytes = fig.to_image(format="png", engine="kaleido") 
                        # , width=1200, height=800, scale=2
                        zf.writestr(f"{filename}.png", img_bytes)

                st.download_button(
                    label="📥 Download Semua Grafik (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"metar_grafik_{tahun}_{bulan}.zip",
                    mime="application/zip"
            )
        
    else:
        st.warning("Lakukan analisis METAR terlebih dahulu.")



# ================= TAB RASON =================
# ================= TAB RASON =================
# ================= TAB RASON =================

if menu == "RASON":
    show_penjelasan("RASON")
    st.markdown("<br>", unsafe_allow_html=True)  

    # === INPUT TAHUN & BULAN ===
    col1, col2 = st.columns(2)
    tahun = col1.selectbox("Pilih Tahun", options=list(range(2020, 2101)), index=5, key="rason_tahun")
    bulan = col2.selectbox("Pilih Bulan", list(range(1, 13)),  index=0, key="rason_bulan")
    
    # === TOMBOL ANALISIS ===
    if st.button("Analisis RASON"):
        with st.spinner("Mengambil dan menganalisis data RASON..."):
            try:
                df_rason_harian, df_rason_bulanan = run_async(
                    fetch_and_analyze_rason_wrapper, tahun, bulan, station_info_map
                )
                if not df_rason_harian.empty:
                    st.session_state["df_rason"] = (df_rason_harian, df_rason_bulanan)
                    st.session_state["rason_analisis_selesai"] = True
            except Exception as e:
                st.error(f"Gagal analisis RASON: {e}")

    # === JIKA ANALISIS SELESAI ===
    if st.session_state.get("rason_analisis_selesai", False):
        rason_subtabs = st.tabs(["📄 Tabel Analisis", "📊 Visualisasi"])


        # ================= TAB TABEL =================
        with rason_subtabs[0]:
            df_rason_harian, df_rason_bulanan = st.session_state["df_rason"]

            # === KPI CARDS ===
            total_stasiun = df_rason_harian["WMO ID"].nunique()
            total_laporan = len(df_rason_harian)
            total_hari_data = df_rason_harian["Tanggal"].nunique() if "Tanggal" in df_rason_harian else 0

            hari_dalam_bulan = calendar.monthrange(tahun, bulan)[1]
            hari_tanpa_data = max(0, hari_dalam_bulan - total_hari_data)

            st.markdown('<h4 style="color:#000000;">📊 Ringkasan RASON</h4>', unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            
            # Fungsi untuk membuat card compact
            def kpi_card(col, title, value, color="#1565C0", bg_color="#f9f9f9", text_color="#333"):
                    col.markdown(f"""
                    <div style="
                        background-color:{bg_color};
                        padding:6px 6px;
                        border-radius:6px;
                        text-align:center;
                        box-shadow:1px 1px 3px rgba(0,0,0,0.08);
                        width:100%;
                        display:flex;
                        flex-direction:column;
                        justify-content:center;
                        align-items:center;
                        transition: all 0.2s ease-in-out;
                    " onmouseover="this.style.transform='scale(1.02)';" 
                    onmouseout="this.style.transform='scale(1)';">
                        <h4 style="margin:0; font-size:1.2rem; line-height:0.8; color:{text_color};">{title}</h4>
                        <h2 style="margin:0; font-size:1.5rem; line-height:0.8; color:{color};">{value}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                
            # Tampilkan KPI
            kpi_card(col1, "📡 Jumlah Stasiun", total_stasiun)
            kpi_card(col2, "📑 Total Laporan", total_laporan)
            kpi_card(col3, "📆 Hari Ada Data", total_hari_data)
            kpi_card(col4, "⚠️ Hari Tanpa Data", hari_tanpa_data)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # === FILTER WMO ===
            opsi_wmo = sorted(df_rason_harian["WMO ID"].unique())
            selected_wmo = st.multiselect(
                "Filter Stasiun (WMO ID)",
                options=opsi_wmo,
                default=opsi_wmo,
                key="filter_wmo_rason"
            )
            if selected_wmo:
                df_rason_harian = df_rason_harian[df_rason_harian["WMO ID"].isin(selected_wmo)]
                df_rason_bulanan = df_rason_bulanan[df_rason_bulanan["WMO ID"].isin(selected_wmo)]

            # === TABEL HARIAN ===
            st.markdown('<h4 style="color:#000000;">Rekap Harian</h4>', unsafe_allow_html=True)
            st.dataframe(df_rason_harian, use_container_width=True)
            st.download_button(
                label="📥 Download CSV RASON Harian",
                data=df_rason_harian.to_csv(index=False).encode("utf-8"),
                file_name=f"rason_harian_{tahun}_{bulan}.csv",
                mime="text/csv"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # === TABEL BULANAN ===
            st.markdown('<h4 style="color:#000000;">Rekap Bulanan</h4>', unsafe_allow_html=True)
            df_rason_bulanan_download = df_rason_bulanan.copy()
            df_rason_bulanan_download["Catatan"] = df_rason_bulanan_download["Catatan"].apply(
                lambda x: re.sub(r"[^0-9A-Za-z\s\-]", "", str(x))
            )

            st.dataframe(df_rason_bulanan, use_container_width=True)
            st.download_button(
                label="📥 Download CSV RASON Bulanan",
                data=df_rason_bulanan_download.to_csv(index=False).encode("utf-8"),
                file_name=f"rason_bulanan_{tahun}_{bulan}.csv",
                mime="text/csv"
            )

        # ================= TAB VISUALISASI =================
        with rason_subtabs[1]:
            df_rason_harian_vis, df_rason_bulanan_vis = st.session_state["df_rason"]

            figs = show_rason_visualizations(df_rason_harian_vis, df_rason_bulanan_vis, return_figs=True)
            
            # === BUAT ZIP GRAFIK ===
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for filename, fig in figs:
                    fig.update_layout(
                        template="plotly_white",
                        paper_bgcolor="white",
                        plot_bgcolor="white"
                    )
                    img_bytes = fig.to_image(format="png", engine="kaleido")
                    zf.writestr(f"{filename}.png", img_bytes)

            zip_buffer.seek(0)
            st.download_button(
                label="📥 Download Semua Grafik (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"rason_grafik_{tahun}_{bulan}.zip",
                mime="application/zip"
            )
    else:
        st.warning("Lakukan analisis RASON terlebih dahulu.")


# ================= TAB SPECI =================
# ================= TAB SPECI =================
# ================= TAB SPECI =================

if menu == "SPECI":
    show_penjelasan("SPECI")
    st.markdown("<br>", unsafe_allow_html=True)  

    # === INPUT ===
    col1, col2 = st.columns(2)
    tahun = col1.selectbox("Pilih Tahun",  options=list(range(2020, 2101)), index=5, key="speci_tahun")
    bulan = col2.selectbox("Pilih Bulan", list(range(1, 13)), index=0, key="speci_bulan")

    # === TOMBOL ANALISIS ===
    if st.button("Analisis SPECI"):
        with st.spinner("Mengambil dan menganalisis data SPECI..."):
            try:
                df_speci_harian, df_speci_bulanan = run_async(
                    fetch_and_analyze_speci_wrapper, tahun, bulan, station_info_map
                )
                st.session_state["df_speci"] = (df_speci_harian, df_speci_bulanan)
                st.session_state["speci_analisis_selesai"] = True
            except Exception as e:
                    st.error(f"Gagal analisis SPECI: {e}")
                    
                                
    # === JIKA ANALISIS SELESAI ===       
    if st.session_state.get("speci_analisis_selesai", False):        
        speci_subtabs = st.tabs(["📄 Tabel Analisis", "📊 Visualisasi"])
            
        # ================= TAB TABEL ===============   
        with speci_subtabs[0]:   
            if st.session_state.get("speci_analisis_selesai", False):          
                df_speci_harian, df_speci_bulanan = st.session_state["df_speci"]   
                
                # === KPI SPECI ===
                total_stasiun_aktif = df_speci_harian["ICAO"].nunique()
                total_laporan_speci = len(df_speci_harian)
                total_hari_aktif = df_speci_harian["Tanggal"].nunique() if "Tanggal" in df_speci_harian else 0                
                rata2_speci_per_hari = (total_laporan_speci / total_hari_aktif) if total_hari_aktif > 0 else 0

                with st.container():    
                    st.markdown('<h4 style="color:#000000;">📊 Ringkasan SPECI</h4>', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns(3)
                    
                    def kpi_card(col, title, value, color="#1565C0", bg_color="#f9f9f9", text_color="#333"):
                        col.markdown(f"""
                        <div style="
                            background-color:{bg_color};
                            padding:6px 6px;
                            border-radius:6px;
                            text-align:center;
                            box-shadow:1px 1px 3px rgba(0,0,0,0.08);
                            width:100%;
                            display:flex;
                            flex-direction:column;
                            justify-content:center;
                            align-items:center;
                            transition: all 0.2s ease-in-out;
                        " onmouseover="this.style.transform='scale(1.02)';" 
                        onmouseout="this.style.transform='scale(1)';">
                            <h4 style="margin:0; font-size:1.2rem; line-height:0.8; color:{text_color};">{title}</h4>
                            <h2 style="margin:0; font-size:1.5rem; line-height:0.8; color:{color};">{value}</h2>
                        </div>
                        """, unsafe_allow_html=True)


                    # Tampilkan KPI SPECI
                    kpi_card(col1, "📡 Jumlah Stasiun", total_stasiun_aktif, "#1565C0")  # biru tegas
                    kpi_card(col2, "📑 Total Laporan", total_laporan_speci, "#1565C0")
                    kpi_card(col3, "⚡ Rata-rata SPECI/Hari Aktif", f"{rata2_speci_per_hari:.2f}", "#1565C0")

                st.markdown("<br>", unsafe_allow_html=True) 
                st.markdown("<br>", unsafe_allow_html=True) 
                
                # === FILTER ICAO ===
                valid_icao = set(station_info_map.keys())
                icao_options = sorted([icao for icao in df_speci_harian["ICAO"].unique() if icao in valid_icao])
                selected_icao_speci = st.multiselect(
                    "Filter Stasiun (ICAO)",
                    options=icao_options,
                    default=icao_options,
                    key="filter_icao_speci"
                )
                if selected_icao_speci:
                    df_speci_harian = df_speci_harian[df_speci_harian["ICAO"].isin(selected_icao_speci)]
                    df_speci_bulanan = df_speci_bulanan[df_speci_bulanan["ICAO"].isin(selected_icao_speci)]

                st.markdown("<br>", unsafe_allow_html=True) 
                
                # === TABEL HARIAN ===
                st.markdown('<h4 style="color:#000000;">Rekap Harian</h4>', unsafe_allow_html=True)
                st.dataframe(df_speci_harian, use_container_width=True)
                st.download_button(
                    label="📥 Download CSV SPECI Harian",
                    data=df_speci_harian.to_csv(index=False).encode("utf-8"),
                    file_name=f"speci_harian_{tahun}_{bulan}.csv",
                    mime="text/csv"
                )
                st.markdown("<br>", unsafe_allow_html=True)
                
                # === TABEL BULANAN ===
                st.markdown('<h4 style="color:#000000;">Rekap Bulanan</h4>', unsafe_allow_html=True)
                st.dataframe(df_speci_bulanan, use_container_width=True)
                st.download_button(
                    label="📥 Download CSV SPECI Bulanan",
                    data=df_speci_bulanan.to_csv(index=False).encode("utf-8"),
                    file_name=f"speci_bulanan_{tahun}_{bulan}.csv",
                    mime="text/csv"
                )

        # ================= TAB VISUALISASI =================
        with speci_subtabs[1]:
            df_speci_harian, df_speci_bulanan = st.session_state["df_speci"]

            tahun = st.session_state["speci_tahun"]
            bulan = st.session_state["speci_bulan"]

            figs = show_speci_visualizations(df_speci_harian, df_speci_bulanan, return_figs=True)

            # === BUAT ZIP GRAFIK ===
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for filename, fig in figs:
                    fig.update_layout(
                        template="plotly_white",
                        paper_bgcolor="white",
                        plot_bgcolor="white"
                    )
                    img_bytes = fig.to_image(format="png", engine="kaleido")
                    zf.writestr(f"{filename}.png", img_bytes)

            zip_buffer.seek(0)
            st.download_button(
                label="📥 Download Semua Grafik (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"speci_grafik_{tahun}_{bulan}.zip",
                mime="application/zip"
            )
    else:
        st.warning("Lakukan analisis SPECI terlebih dahulu.")



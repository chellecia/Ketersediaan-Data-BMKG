import streamlit as st
import asyncio, nest_asyncio, aiohttp
import calendar
import re
from io import BytesIO
import zipfile
from auth import get_bmkg_token
from station import fetch_all_stations_info
from fetcher import fetch_gts_data
from wrapper import (
    fetch_and_analyze_metar, 
    fetch_and_analyze_speci, 
    fetch_and_analyze_rason, 
    fetch_and_analyze_TAF)
from viz import show_metar_visualizations, show_speci_visualizations, show_rason_visualizations, show_TAF_visualizations
from streamlit_option_menu import option_menu



# ================== LOGIN ==================

# Dummy user database (ganti sesuai kebutuhan)
USERS = {
    "intern2025": "analyZ2025",
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- Login Page ---
if not st.session_state.logged_in:
    st.set_page_config(page_title="Login - Analisis BMKG", layout="centered")

    st.title("🔑 Login Aplikasi Analisis Cuaca BMKG")
    input_username = st.text_input("Username")
    input_password = st.text_input("Password", type="password")

    if st.button("Login"):
        if input_username in USERS and USERS[input_username] == input_password:
            st.session_state.logged_in = True
            st.session_state.username = input_username
            st.success("Login berhasil! Memuat aplikasi...")
            st.rerun()
        else:
            st.error("❌ Username atau password salah.")

    st.stop()  # hentikan eksekusi kalau belum login

        
# --- Page Config ---        
st.set_page_config(page_title="Analisis Ketersediaan Data Cuaca BMKG", layout="wide")
        
# ======= Inisialisasi station_info_map =======
async def init_station_info():
    async with aiohttp.ClientSession() as session:
        token = await get_bmkg_token()
        stations = await fetch_all_stations_info(token, session)

        station_info_map = {}
        for s in stations:
            icao = (s.get("cccc") or "").strip().upper()
            if not icao:  # kalau kosong, skip
                continue
            station_info_map[icao] = {
                "wmo": s.get("wmo_id", "-"),
                "name": s.get("station_name", icao),
            }
        return station_info_map

# Ambil dari session_state dengan aman
station_info_map = st.session_state.get("station_info_map", {})

# ======= WRAPPERS =======
async def fetch_and_analyze_metar_wrapper(tahun, bulan, mode,station_info_map):
    token = await get_bmkg_token()
    async with aiohttp.ClientSession() as session:
        return await fetch_and_analyze_metar(
            token, session, tahun, bulan, mode, station_info_map, fetch_gts_data
        )

async def fetch_and_analyze_speci_wrapper(tahun, bulan, station_info_map):
    token = await get_bmkg_token()
    async with aiohttp.ClientSession() as session:
        return await fetch_and_analyze_speci(
            token, session, tahun, bulan, station_info_map, fetch_gts_data
        )

async def fetch_and_analyze_rason_wrapper(tahun, bulan, station_info_map):
    token = await get_bmkg_token()
    async with aiohttp.ClientSession() as session:
        return await fetch_and_analyze_rason(
            token, session, tahun, bulan, station_info_map, fetch_gts_data
        )

async def fetch_and_analyze_TAF_wrapper(tahun, bulan, station_info_map):
    token = await get_bmkg_token()
    async with aiohttp.ClientSession() as session:
        return await fetch_and_analyze_TAF(
            token, session, tahun, bulan, station_info_map, fetch_gts_data
        )

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
<p style="text-align: center; font-size: 20px;">METAR • RASON • SPECI • TAF</p>
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
        options=["METAR", "RASON", "SPECI", "TAF"],
        icons=["cloud", "bar-chart", "activity", "file-text"],
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

# Tombol logout
with st.sidebar:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
        
# --- PENJELASAN MENU ---
penjelasan = {
    "METAR": {
        "judul": "Analisis Data METAR",
        "lengkap": (
            "METAR (Meteorological Aerodrome Report) adalah nama sandi pelaporan cuaca rutin untuk penerbangan"
        )
    },
    "RASON": {
        "judul": "Analisis Data RASON",
        "lengkap": (
            "RASON (Radiosonde Observation) adalah laporan pengamatan atmosfer yang menggunakan balon cuaca"
        )
    },
    "SPECI": {
        "judul": "Analisis Data SPECI",
        "lengkap": (
            "SPECI (Special Weather Report) adalah nama sandi pelaporan cuaca khusus terpilih untuk penerbangan"
    )
        },
    "TAF": {
        "judul": "Analisis Data TAF",
        "lengkap": (
            "TAF (Terminal Aerodrome Forecast) adalah nama sandi untuk prakiraan cuaca di bandar udara"
        )
    }
}

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
    ">
        <h4 style="margin:0; font-size:1.2rem; line-height:0.8; color:{text_color};">{title}</h4>
        <h2 style="margin:0; font-size:1.5rem; line-height:0.8; color:{color};">{value}</h2>
    </div>
    """, unsafe_allow_html=True)

# Fungsi helper biar ga nulis berulang
st.write("") 
def show_penjelasan(menu):
    st.subheader(penjelasan[menu]["judul"])
    with st.expander("📘 Penjelasan Singkat"):
        st.write(penjelasan[menu]["lengkap"])


# ================= TAB METAR =================
if menu == "METAR":
    show_penjelasan("METAR")
    st.markdown("<br>", unsafe_allow_html=True)  

    # --- Input Tahun & Bulan ---
    col1, col2 = st.columns(2)
    tahun = col1.selectbox("Pilih Tahun", list(range(2020, 2026)), index=5)
    bulan = col2.selectbox("Pilih Bulan", list(range(1, 13)), index=0)

    mode = st.radio("Mode Perhitungan", ["Otomatis", "Interval 1 Jam"], key="metar_mode")

    if st.button("Analisis METAR"):
        with st.spinner("Mengambil dan menganalisis data METAR..."):
            try:
                df_harian, df_bulanan = run_async(
                    fetch_and_analyze_metar_wrapper, tahun, bulan, mode, station_info_map
                )
                st.session_state["df_metar_raw"] = (df_harian, df_bulanan)
                st.session_state["metar_analisis_selesai"] = True
            except Exception as e:
                st.error(f"Gagal analisis METAR: {e}")

    # Jika analisis selesai
    if st.session_state.get("metar_analisis_selesai", False):
        metar_subtabs = st.tabs(["📄 Tabel Analisis", "📊 Visualisasi"])

        # ================= TAB TABEL =================
        with metar_subtabs[0]:
            df_harian, df_bulanan = st.session_state["df_metar_raw"]

            # Hitung KPI
            total_stasiun = df_harian["ICAO"].nunique()
            total_laporan = len(df_harian)
            persentase_lengkap = df_harian["Status Lengkap"].mean() * 100
            tidak_lengkap = 100 - persentase_lengkap

            st.markdown("<h4 style='margin-top:15px; color:#000000;'>📊 Ringkasan METAR</h4>", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)

            kpi_card(col1, "📡 Jumlah Stasiun", total_stasiun)
            kpi_card(col2, "📑 Total Record Harian", total_laporan)
            kpi_card(col3, "✅ Lengkap (%)", f"{persentase_lengkap:.1f}%")
            kpi_card(col4, "⚠️ Tidak Lengkap (%)", f"{tidak_lengkap:.1f}%")

            st.markdown("<br>", unsafe_allow_html=True)

            # ================= FILTER =================
            with st.expander("⚙️ Filter Lanjutan"):
                # Filter ICAO
                stasiun_opsi = sorted(df_harian["ICAO"].unique())
                selected_stations = st.multiselect(
                    "Pilih Stasiun (ICAO)",
                    options=stasiun_opsi,
                    default=stasiun_opsi,
                    key="filter_metar_ICAO"
                )
                df_filtered = df_harian[df_harian["ICAO"].isin(selected_stations)]

                # Filter Status Lengkap
                status_filter = st.selectbox(
                    "Filter Status Ketersediaan", ["Semua", "Lengkap", "Tidak Lengkap"], key="filter_metar_status"
                )
                if status_filter == "Lengkap":
                    df_filtered = df_filtered[df_filtered["Status Lengkap"] == True]
                elif status_filter == "Tidak Lengkap":
                    df_filtered = df_filtered[df_filtered["Status Lengkap"] == False]

                # Filter Jam Operasional
                jam_opsi = sorted(df_filtered["Jam Operasional"].unique())
                selected_ops = st.multiselect(
                    "Pilih Jam Operasional", options=jam_opsi, default=jam_opsi, key="filter_metar_jam"
                )
                df_filtered = df_filtered[df_filtered["Jam Operasional"].isin(selected_ops)]

                st.session_state["df_harian"] = df_filtered

        # ================= TAMPILKAN TABEL HARlAN =================
            df_harian_display = df_filtered.drop(columns=["Status Lengkap"], errors="ignore")
            st.markdown('<h4 style="color:#000000;">Rekap Harian</h4>', unsafe_allow_html=True)
            st.dataframe(df_harian_display, use_container_width=True)

            # Tombol download CSV Harian
            df_harian_dl = df_harian_display.copy()
            df_harian_dl["Catatan"] = df_harian_dl["Catatan"].apply(
                lambda x: re.sub(r"[^0-9A-Za-z\s\-]", "", str(x))
            )
            csv_harian = df_harian_dl.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV METAR Harian",
                data=csv_harian,
                file_name=f"metar_harian_{tahun}_{bulan}.csv",
                mime="text/csv"
            )

            # ================= TAMPILKAN TABEL BULANAN =================
            st.markdown("<br>", unsafe_allow_html=True)  # beri jarak
            st.markdown('<h4 style="color:#000000;">Rekap Bulanan</h4>', unsafe_allow_html=True)
            st.dataframe(df_bulanan, use_container_width=True)

            # Tombol download CSV Bulanan
            df_bulanan_dl = df_bulanan.copy()
            df_bulanan_dl["Catatan"] = df_bulanan_dl["Catatan"].apply(
                lambda x: re.sub(r"[^0-9A-Za-z\s\-]", "", str(x))
            )
            csv_bulanan = df_bulanan_dl.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV METAR Bulanan",
                data=csv_bulanan,
                file_name=f"metar_bulanan_{tahun}_{bulan}.csv",
                mime="text/csv"
            )


        # ================= TAB VISUALISASI =================
        with metar_subtabs[1]:
            df_filtered = st.session_state["df_harian"]
            df_harian_filtered = st.session_state["df_harian"]
            df_bulanan_filtered = st.session_state["df_metar_raw"][1]  # ambil df_bulanan dari session_state
            figs = show_metar_visualizations(df_harian_filtered, df_bulanan_filtered, return_figs=True)

            # Buat ZIP grafik
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for filename, fig in figs:
                    fig.update_layout(template="plotly_white", 
                                      paper_bgcolor="white", 
                                      plot_bgcolor="white")

                    html_bytes = fig.to_html(full_html=False).encode("utf-8")
                    zf.writestr(f"{filename}.html", html_bytes)

            zip_buffer.seek(0)
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
    tahun = col1.selectbox("Pilih Tahun", options=list(range(2020, 2026)), index=5, key="rason_tahun")
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
            
                
            # Tampilkan KPI
            kpi_card(col1, "📡 Jumlah Stasiun", total_stasiun)
            kpi_card(col2, "📑 Total Record Harian", total_laporan)
            kpi_card(col3, "📆 Hari Ada Data", total_hari_data)
            kpi_card(col4, "⚠️ Hari Tanpa Data", hari_tanpa_data)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # === FILTER WMO ===
            with st.expander("Filter WMO"):
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
                    html_bytes = fig.to_html(full_html=False).encode("utf-8")
                    zf.writestr(f"{filename}.html", html_bytes)

          
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
    tahun = col1.selectbox("Pilih Tahun",  options=list(range(2020, 2026)), index=5, key="speci_tahun")
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
                total_record = len(df_speci_harian)
                total_laporan = df_speci_harian["Jumlah SPECI Harian"].sum()

                with st.container():    
                    st.markdown('<h4 style="color:#000000;">📊 Ringkasan SPECI</h4>', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns(3)

                    # Tampilkan KPI SPECI
                    kpi_card(col1, "📡 Jumlah Stasiun", total_stasiun_aktif, "#1565C0")  # biru tegas
                    kpi_card(col2, "📑 Total Record Harian", total_record, "#1565C0")
                    kpi_card(col3, "📑 Total Laporan Masuk", total_laporan, "#1565C0")
                
                st.markdown("<br>", unsafe_allow_html=True) 
                st.markdown("<br>", unsafe_allow_html=True) 
                
                # === FILTER cccc ===
                with st.expander("Filter ICAO"):
                    valid_cccc = set(station_info_map.keys())
                    cccc_options = sorted([cccc for cccc in df_speci_harian["ICAO"].unique() if cccc in valid_cccc])
                    selected_cccc_speci = st.multiselect(
                        "Pilih Stasiun (ICAO)",
                        options=cccc_options,
                        default=cccc_options,
                        key="filter_cccc_speci"
                    )
                if selected_cccc_speci:
                    df_speci_harian = df_speci_harian[df_speci_harian["ICAO"].isin(selected_cccc_speci)]
                    df_speci_bulanan = df_speci_bulanan[df_speci_bulanan["ICAO"].isin(selected_cccc_speci)]

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
                    html_bytes = fig.to_html(full_html=False).encode("utf-8")
                    zf.writestr(f"{filename}.html", html_bytes)

            zip_buffer.seek(0)
            st.download_button(
                label="📥 Download Semua Grafik (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"speci_grafik_{tahun}_{bulan}.zip",
                mime="application/zip"
            )
    else:
        st.warning("Lakukan analisis SPECI terlebih dahulu.")
        

# ================= TAB TAF =================
# ================= TAB TAF =================
# ================= TAB TAF =================


if menu == "TAF":
    show_penjelasan("TAF")
    st.markdown("<br>", unsafe_allow_html=True)

    # === INPUT ===
    col1, col2 = st.columns(2)
    tahun = col1.selectbox("Pilih Tahun", options=list(range(2020, 2026)), index=5, key="TAF_tahun")
    bulan = col2.selectbox("Pilih Bulan", list(range(1, 13)), index=0, key="TAF_bulan")

    if st.button("Analisis TAF"):
        with st.spinner("Mengambil dan menganalisis data TAF..."):
            try:
                df_harian, df_bulanan = run_async(
                    fetch_and_analyze_TAF_wrapper, tahun, bulan, station_info_map
                )
                st.session_state["df_TAF"] = (df_harian, df_bulanan)
                st.session_state["TAF_analisis_selesai"] = True

            except Exception as e:
                st.error(f"Gagal analisis TAF: {e}")
                        
    # === JIKA ANALISIS SELESAI ===       
    if st.session_state.get("TAF_analisis_selesai", False):        
        TAF_subtabs = st.tabs(["📄 Tabel Analisis", "📊 Visualisasi"])
            
        # ================= TAB TABEL ===============   
        with TAF_subtabs[0]:   
            df_harian, df_bulanan = st.session_state["df_TAF"]   
            
            # === KPI TAF ===
            total_stasiun_aktif = df_harian["ICAO"].nunique()
            total_laporan_TAF = df_harian["Jumlah TAF Harian"].sum()
            total_target_laporan = df_harian["Target Harian"].sum()
            total_record = len(df_harian)

            persentase_total = round((total_laporan_TAF / total_target_laporan) * 100, 1) \
                if total_target_laporan > 0 else 0

            jumlah_hari_bulan = calendar.monthrange(tahun, bulan)[1]
            rata2_TAF_per_hari = round(total_laporan_TAF / (total_stasiun_aktif * jumlah_hari_bulan), 2) \
                if total_stasiun_aktif > 0 else 0
                    
            with st.container():    
                st.markdown('<h4 style="color:#000000;">📊 Ringkasan TAF</h4>', unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns(4)

                kpi_card(col1, "📡 Jumlah Stasiun", total_stasiun_aktif, "#1565C0")
                kpi_card(col2, "📑 Total Record Harian", total_record, "#1565C0")
                kpi_card(col3, "✅ Persentase Tersedia (%)", f"{persentase_total:.1f}%", "#43A047")
                kpi_card(col4, "📑 Total Laporan Masuk", total_laporan_TAF, "#1565C0")

            st.markdown("<br>", unsafe_allow_html=True) 
            
            
            # --- Filter berdasarkan ICAO ---
            with st.expander("Filter ICAO"):
                stasiun_opsi = sorted(df_harian["ICAO"].unique())
                selected_stations = st.multiselect(
                            "Pilih Stasiun (ICAO)",
                            options=stasiun_opsi,
                            default=stasiun_opsi, # default semua terpilih
                            key="filter_taf_ICAO" 
                        )
            if selected_stations:
                df_harian = df_harian[df_harian["ICAO"].isin(selected_stations)]
                df_bulanan = df_bulanan[df_bulanan["ICAO"].isin(selected_stations)]
            
                    
            # -berishkan emoji
            df_taf_harian = df_harian.copy()
            df_taf_harian["Catatan"] = df_taf_harian["Catatan"].apply(
                    lambda x: re.sub(r"[^0-9A-Za-z\s\-]", "", str(x))
                )  
            
            df_taf_bulanan = df_bulanan.copy()
            df_taf_bulanan["Catatan"] = df_taf_bulanan["Catatan"].apply(
                    lambda x: re.sub(r"[^0-9A-Za-z\s\-]", "", str(x))
                )  
        
            # === TABEL HARIAN ===
            st.markdown('<h4 style="color:#000000;">Rekap Harian</h4>', unsafe_allow_html=True)
            st.dataframe(df_harian, use_container_width=True)
            st.download_button(
                label="📥 Download CSV TAF Harian",
                data=df_taf_harian.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"TAF_harian_{tahun}_{bulan}.csv",
                mime="text/csv"
            )
                
            # === TABEL BULANAN ===
            st.markdown('<h4 style="color:#000000;">Rekap Bulanan</h4>', unsafe_allow_html=True)
            st.dataframe(df_bulanan, use_container_width=True)
            st.download_button(
                label="📥 Download CSV TAF Bulanan",
                data=df_taf_bulanan.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"TAF_bulanan_{tahun}_{bulan}.csv",
                mime="text/csv"
            )

        # ================= TAB VISUALISASI =================
        with TAF_subtabs[1]:
            df_TAF_harian, df_TAF_bulanan = st.session_state["df_TAF"]

            tahun = st.session_state["TAF_tahun"]
            bulan = st.session_state["TAF_bulan"]

            figs = show_TAF_visualizations(df_TAF_harian, df_TAF_bulanan, return_figs=True)

            # === BUAT ZIP GRAFIK ===
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for filename, fig in figs:
                    fig.update_layout(
                        template="plotly_white",
                        paper_bgcolor="white",
                        plot_bgcolor="white"
                    )
                    html_bytes = fig.to_html(full_html=False).encode("utf-8")
                    zf.writestr(f"{filename}.html", html_bytes)

            zip_buffer.seek(0)
            st.download_button(
                label="📥 Download Semua Grafik (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"TAF_grafik_{tahun}_{bulan}.zip",
                mime="application/zip"
            )
    else:
        st.warning("Lakukan analisis TAF terlebih dahulu.")





import asyncio
from analyzerMetar import analyze_metar
from analyzerRason import analyze_rason
from analyzerSpeci import analyze_speci

# ==== FULL ANALYSIS RUNNER ====

# berguna untuk sekali panggil --> dapat semua jenis data

# async def run_full_analysis(tahun, bulan, interval_mode, token, session, fetch_func, station_info_map):
#     """
#     Ambil data METAR, RASON (TEMP), dan SPECI, lalu analisis lengkap.
#     """

#     metar_data, rason_data, speci_data = await asyncio.gather(
#         fetch_func(token, session, tahun, bulan, 4),  # METAR (type_message=4)
#         fetch_func(token, session, tahun, bulan, 3),  # TEMP/RASON (type_message=3)
#         fetch_func(token, session, tahun, bulan, 5),  # SPECI (type_message=5)
#     )

#     df_metar = analyze_metar(metar_data, station_info_map, tahun, bulan, interval_mode)
#     df_rason_harian, df_rason_bulanan = analyze_rason(rason_data, station_info_map, tahun, bulan)
#     df_speci_harian, df_speci_bulanan = analyze_speci(speci_data, station_info_map, tahun, bulan)

#     return df_metar, df_rason_harian, df_rason_bulanan, df_speci_harian, df_speci_bulanan


# fetch & analyze per jenis → ambil + analisis hanya jenis tertentu sesuai kebutuhan.
# cocok untuk per tab

async def fetch_and_analyze_metar (token, session, tahun, bulan, interval_mode,station_info_map, fetch_func):
    metar_data = await fetch_func(token, session, tahun, bulan, 4)
    df_metar = analyze_metar(metar_data, station_info_map, tahun, bulan, interval_mode)
    return df_metar

async def fetch_and_analyze_rason(token, session, tahun, bulan, station_info_map, fetch_func):
    rason_data = await fetch_func(token, session, tahun, bulan, 3)
    df_rason_harian, df_rason_bulanan = analyze_rason(rason_data, station_info_map, tahun, bulan)
    return df_rason_harian, df_rason_bulanan

async def fetch_and_analyze_speci(token, session, tahun, bulan, station_info_map, fetch_func):
    speci_data = await fetch_func(token, session, tahun, bulan, 5)
    df_speci_harian, df_speci_bulanan = analyze_speci(speci_data, station_info_map, tahun, bulan)
    return df_speci_harian, df_speci_bulanan


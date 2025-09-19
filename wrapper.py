from analyzermetar import analyze_metar
from analyzerrason import analyze_rason
from analyzerspeci import analyze_speci
from analyzertaf import analyze_taf


async def fetch_and_analyze_metar (token, session, tahun, bulan, interval_mode,station_info_map, fetch_func):
    metar_data = await fetch_func(token, session, tahun, bulan, 4)
    df_harian, df_bulanan = analyze_metar(metar_data, station_info_map, tahun, bulan, interval_mode)
    return df_harian, df_bulanan

async def fetch_and_analyze_rason(token, session, tahun, bulan, station_info_map, fetch_func):
    rason_data = await fetch_func(token, session, tahun, bulan, 3)
    df_rason_harian, df_rason_bulanan = analyze_rason(rason_data, station_info_map, tahun, bulan)
    return df_rason_harian, df_rason_bulanan

async def fetch_and_analyze_speci(token, session, tahun, bulan, station_info_map, fetch_func):
    speci_data = await fetch_func(token, session, tahun, bulan, 5)
    df_speci_harian, df_speci_bulanan = analyze_speci(speci_data, station_info_map, tahun, bulan)
    return df_speci_harian, df_speci_bulanan

async def fetch_and_analyze_TAF(token, session, tahun, bulan, station_info_map, fetch_func):
    taf_data = await fetch_func(token, session, tahun, bulan, 6)
    df_harian, df_bulanan = analyze_taf(taf_data, station_info_map, tahun, bulan)
    return df_harian, df_bulanan


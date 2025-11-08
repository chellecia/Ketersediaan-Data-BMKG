from collections import defaultdict
from datetime import datetime
import pandas as pd

def analyze_speci(speci_data, station_info_map, tahun, bulan):
    """
    Analisis SPECI: menghasilkan DataFrame harian dan bulanan.
    """
    if not speci_data:
        print("[WARNING] Data SPECI kosong.")
        return pd.DataFrame(), pd.DataFrame()

    jumlah_per_stasiun_harian = defaultdict(lambda: defaultdict(int))
    jumlah_per_stasiun_bulanan = defaultdict(int)

    for item in speci_data:
        cccc = (item.get("cccc") or "").strip().upper()
        ts = item.get("timestamp_data")

        if not cccc or not ts:
            continue

        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.year == tahun and dt.month == bulan:
                tanggal = dt.strftime("%Y-%m-%d")
                jumlah_per_stasiun_harian[cccc][tanggal] += 1
                jumlah_per_stasiun_bulanan[cccc] += 1
        except Exception:
            continue

    # DataFrame Harian
    harian_records = []
    for cccc, tanggal_counts in jumlah_per_stasiun_harian.items():
        info = station_info_map.get(cccc, {})
        for tanggal, jumlah in tanggal_counts.items():
            harian_records.append({
                "WMO ID": str(info.get("wmo") or info.get("wmo_id") or "-"),
                "ICAO": cccc,
                "Nama Stasiun": info.get("stasiun") or info.get("name") or f"Stasiun {cccc}",
                "Tanggal": tanggal,
                "Jumlah SPECI Harian": jumlah,
            })

    df_harian = pd.DataFrame(harian_records).sort_values(["ICAO", "Tanggal"]).reset_index(drop=True)

    # DataFrame Bulanan
    bulanan_records = []
    for cccc, jumlah in jumlah_per_stasiun_bulanan.items():
        info = station_info_map.get(cccc, {})
        bulanan_records.append({
            "WMO ID": str(info.get("wmo") or info.get("wmo_id") or "-"),
            "ICAO": cccc,
            "Nama Stasiun": info.get("stasiun") or info.get("name") or f"Stasiun {cccc}",
            "Jumlah SPECI Bulanan": jumlah,
        })

    df_bulanan = pd.DataFrame(bulanan_records).sort_values("ICAO").reset_index(drop=True)

    return df_harian, df_bulanan


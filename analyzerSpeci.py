from collections import defaultdict # mirip dict tpi klo key blm ada, otomatis buat nilai default
from datetime import datetime
import pandas as pd

# ==== ANALYZE SPECI ====
def analyze_speci(speci_data, station_info_map, tahun, bulan):
    """
    Analisis SPECI: menghasilkan DataFrame harian dan bulanan.
    Fallback mapping digunakan agar nama stasiun tetap muncul walaupun WMO ID atau ICAO kosong.
    """
    if not speci_data:
        print("[WARNING] Data SPECI kosong.")
        return pd.DataFrame(), pd.DataFrame()

    # Hitung jumlah laporan harian dan bulanan
    jumlah_per_stasiun_harian = defaultdict(lambda: defaultdict(int)) #menyimpan jumlah laporan per stasiun per tanggal
    jumlah_per_stasiun_bulanan = defaultdict(int) #menyimpan total laporan per stasiun untuk bulan itu


# loop record speci
    for item in speci_data:
        cccc = (item.get("cccc") or "").strip().upper()
        # sid = item.get("station_id") or item.get("wmo_id")

        # skip kalau ICAO tidak valid
        if not cccc or cccc not in station_info_map:
            continue

        ts = item.get("timestamp_data")
        if not cccc or not ts:
            continue
        #Kalau ICAO kosong atau tidak ada di mapping stasiun,
        #Maka lewatkan record ini dan langsung ke record SPECI berikutnya.

        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.year == tahun and dt.month == bulan:
                tanggal = dt.strftime("%Y-%m-%d")
                jumlah_per_stasiun_harian[cccc][tanggal] += 1 #dictionary bertingkat
                jumlah_per_stasiun_bulanan[cccc] += 1 #dictionary biasa
        except Exception:
            continue

    # DataFrame Harian
    harian_records = [] #membuat list kosong yang nanti berisi list of dict
    for cccc, tanggal_counts in jumlah_per_stasiun_harian.items():
        info = station_info_map.get(cccc, {})
        for tanggal, jumlah in tanggal_counts.items():
            harian_records.append({
                "WMO ID": str(info.get("wmo_id", "-")),
                "ICAO": cccc,
                "Nama Stasiun": info.get("stasiun", "-"),
                "Tanggal": tanggal,
                "Jumlah SPECI Harian": jumlah,
            })

    df_harian = pd.DataFrame(harian_records).sort_values(["ICAO", "Tanggal"]).reset_index(drop=True)

    # DataFrame Bulanan
    bulanan_records = []
    for cccc, jumlah in jumlah_per_stasiun_bulanan.items():
        info = station_info_map.get(cccc, {})
        bulanan_records.append({
            "WMO ID": str(info.get("wmo_id", "-")),
            "ICAO": cccc,
            "Nama Stasiun": info.get("stasiun", "-"),
            "Jumlah SPECI Bulanan": jumlah,
        })

    df_bulanan = pd.DataFrame(bulanan_records).sort_values("ICAO").reset_index(drop=True)

    return df_harian, df_bulanan



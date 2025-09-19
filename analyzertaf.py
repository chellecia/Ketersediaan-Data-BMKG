from collections import defaultdict
import pandas as pd

# Daftar stasiun khusus dengan target 5 TAF
special_stations = {"WIII", "WADD", "WAAA", "WABB"}

def get_daily_target(station_list):
    """
    Menghasilkan target jumlah TAF harian per stasiun.
    - Stasiun normal: 4 TAF
    - Stasiun khusus: 5 TAF
    """
    target_dict = {}
    for icao in station_list:
        if icao in special_stations:
            target_dict[icao] = 5
        else:
            target_dict[icao] = 4
    return target_dict


def analyze_taf(taf_data, station_info_map, tahun, bulan):
    """
    Analisis TAF: menghasilkan DataFrame harian (jumlah per tanggal)
    dan bulanan (total per stasiun) beserta target, ketersediaan (%), dan catatan dengan emotikon.
    """
    if not taf_data:
        print("[WARNING] Data TAF kosong.")
        return pd.DataFrame(), pd.DataFrame()

    # Semua stasiun dari station_info_map
    all_stations = list(station_info_map.keys())
    target_dict = get_daily_target(all_stations)

    # Dictionary bertingkat: stasiun -> tanggal -> jumlah TAF
    jumlah_per_stasiun_harian = defaultdict(lambda: defaultdict(int))
    jumlah_per_stasiun_bulanan = defaultdict(int)

    for item in taf_data:
        cccc = (item.get("cccc") or "").strip().upper()
        ts = item.get("timestamp_sent_data")
        if not cccc or not ts:
            continue

        try:
            dt = pd.to_datetime(ts.strip(), utc=True)
        except Exception as e:
            print("Skip parsing error:", ts, e)
            continue

        if dt.year != tahun or dt.month != bulan:
            continue

        tanggal = dt.strftime("%Y-%m-%d")
        jumlah_per_stasiun_harian[cccc][tanggal] += 1
        jumlah_per_stasiun_bulanan[cccc] += 1

    # DataFrame harian: satu row per stasiun per tanggal
    harian_records = []
    for cccc, tanggal_counts in jumlah_per_stasiun_harian.items():
        info = station_info_map.get(cccc, {})
        wmo_id = str(info.get("wmo") or info.get("wmo_id") or "-")
        nama_stasiun = info.get("name") or info.get("stasiun") or f"Stasiun {cccc}"
        target_harian = target_dict.get(cccc, 4)

        for tanggal, jumlah in tanggal_counts.items():
            persentase = round(jumlah / target_harian * 100, 2)
            if jumlah < target_harian:
                catatan = "⚠️ Tidak Lengkap"
            elif jumlah == target_harian:
                catatan = "✅ Lengkap"
            else:
                catatan = "⚠️ Ada AMD/CORR"

            harian_records.append({
                "WMO ID": wmo_id,
                "ICAO": cccc,
                "Nama Stasiun": nama_stasiun,
                "Tanggal": tanggal,
                "Jumlah TAF Harian": jumlah,
                "Target Harian": target_harian,
                "Ketersediaan %": persentase,
                "Catatan": catatan
            })

    df_harian = pd.DataFrame(harian_records).sort_values(["ICAO", "Tanggal"]).reset_index(drop=True)

    # DataFrame bulanan: total TAF per stasiun
    bulanan_records = []
    for cccc, tanggal_counts in jumlah_per_stasiun_harian.items():
        info = station_info_map.get(cccc, {})
        wmo_id = str(info.get("wmo") or info.get("wmo_id") or "-")
        nama_stasiun = info.get("name") or info.get("stasiun") or f"Stasiun {cccc}"
        target_harian = target_dict.get(cccc, 4)
        jumlah = jumlah_per_stasiun_bulanan.get(cccc, 0)    

        # target bulanan = target harian * jumlah hari unik yg tercatat
        target_bulanan = target_harian * len(tanggal_counts)

        if target_bulanan == 0:
            persentase = 0
            catatan = "❌ Tidak ada data"
        else:
            persentase = round(jumlah / target_bulanan * 100, 2)
            
            if jumlah < target_bulanan:
                catatan = "⚠️ Tidak Lengkap"
            elif jumlah == target_bulanan:
                catatan = "✅ Lengkap"
            else:  # jumlah > target_bulanan
                catatan = "⚠️ Ada AMD/CORR"

        bulanan_records.append({
            "WMO ID": wmo_id,
            "ICAO": cccc,
            "Nama Stasiun": nama_stasiun,
            "Jumlah TAF Bulanan": jumlah,
            "Target Bulanan": target_bulanan,
            "Ketersediaan %": persentase,
            "Catatan": catatan
        })

    df_bulanan = pd.DataFrame(bulanan_records).sort_values("ICAO").reset_index(drop=True)

    return df_harian, df_bulanan
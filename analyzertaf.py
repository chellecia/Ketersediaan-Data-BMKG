from collections import defaultdict
import pandas as pd
import calendar

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
        target_dict[icao] = 5 if icao in special_stations else 4
    return target_dict

def analyze_taf(taf_data, station_info_map, tahun, bulan):

    if not taf_data:
        print("[WARNING] Data TAF kosong.")
        return pd.DataFrame(), pd.DataFrame()

    # Hitung jumlah TAF per stasiun per tanggal dan bulanan
    jumlah_per_stasiun_harian = defaultdict(lambda: defaultdict(int))
    jumlah_per_stasiun_bulanan = defaultdict(int)

    for item in taf_data:
        cccc = (item.get("cccc") or "").strip().upper()
        ts = item.get("timestamp_sent_data")
        if not cccc or not ts:
            continue
        try:
            dt = pd.to_datetime(ts.strip(), utc=True)
        except Exception:
            continue
        if dt.year != tahun or dt.month != bulan:
            continue
        tanggal = dt.strftime("%Y-%m-%d")
        jumlah_per_stasiun_harian[cccc][tanggal] += 1
        jumlah_per_stasiun_bulanan[cccc] += 1


    # Target harian hanya untuk stasiun yang muncul di data
    stasiun_aktif = list(jumlah_per_stasiun_harian.keys())
    target_dict = get_daily_target(stasiun_aktif)

    # Daftar semua tanggal dalam bulan
    jumlah_hari_bulan = calendar.monthrange(tahun, bulan)[1]
    all_dates = [pd.Timestamp(year=tahun, month=bulan, day=d).strftime("%Y-%m-%d")
                 for d in range(1, jumlah_hari_bulan + 1)]

    # --- DataFrame harian ---
    harian_records = []
    for cccc in stasiun_aktif:
        info = station_info_map.get(cccc, {})
        wmo_id = str(info.get("wmo") or info.get("wmo_id") or "-")
        nama_stasiun = info.get("name") or info.get("stasiun") or f"Stasiun {cccc}"
        target_harian = target_dict.get(cccc, 4)

        for tanggal in all_dates:
            jumlah = jumlah_per_stasiun_harian[cccc].get(tanggal, 0)
            persentase = round(jumlah / target_harian * 100, 2) if target_harian else 0

            if jumlah == 0:
                catatan = "❌ Tidak Ada Data"
            elif jumlah < target_harian:
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

    # --- DataFrame bulanan ---
    bulanan_records = []
    for cccc in stasiun_aktif:
        info = station_info_map.get(cccc, {})
        wmo_id = str(info.get("wmo") or info.get("wmo_id") or "-")
        nama_stasiun = info.get("name") or info.get("stasiun") or f"Stasiun {cccc}"
        target_harian = target_dict.get(cccc, 4)
        jumlah = jumlah_per_stasiun_bulanan.get(cccc, 0)
        target_bulanan = target_harian * jumlah_hari_bulan
        persentase = round(jumlah / target_bulanan * 100, 2) if target_bulanan else 0

        if jumlah == 0:
            catatan = "❌ Tidak Ada Data"
        elif jumlah < target_bulanan:
            catatan = "⚠️ Tidak Lengkap"
        elif jumlah == target_bulanan:
            catatan = "✅ Lengkap"
        else:
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


from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import calendar

def analyze_metar(metar_data, station_info_map, tahun, bulan, mode_interval="Otomatis"):
    """
    Analisis ketersediaan laporan METAR per stasiun.

    Parameters:
    - metar_data: list of dict, data METAR mentah
    - station_info_map: dict, informasi stasiun
    - tahun: int
    - bulan: int
    - mode_interval: "Otomatis" atau "Interval 1 Jam"/"30 Menit"

    Returns:
    - df_harian: DataFrame harian per stasiun
    - df_bulanan: DataFrame bulanan summary per stasiun
    """

    # ========== 1. Inisialisasi dasar ==========
    harian_record = []
    start_date = datetime(tahun, bulan, 1)
    end_date = start_date + relativedelta(months=1)
    num_days = (end_date - start_date).days

    # Struktur harian[tanggal][cccc] = set(waktu)
    harian = defaultdict(lambda: defaultdict(set))
    for item in metar_data:
        cccc = item.get("cccc")
        ts = item.get("timestamp_data")
        if not cccc or not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            tanggal = dt.strftime("%Y-%m-%d")
            waktu = dt.strftime("%H:%M")
            harian[tanggal][cccc].add(waktu)
        except ValueError:
            continue

    # ========== 2. Loop per tanggal dan stasiun ==========
    for day_offset in range(num_days):
        tanggal_str = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        for cccc, info in station_info_map.items():
            if not cccc.isalpha():
                continue

            jam_operasi = info.get("operating_hours", 24)
            is_half_hourly = info.get("is_metar_half_hourly", False)
            nama_stasiun = (info.get("name") or "").strip().upper()

            # --- Tentukan interval final ---
            if mode_interval.lower() == "otomatis":
                interval = "30 Menit" if is_half_hourly else "1 Jam"
            else:
                interval = mode_interval.strip()

            # --- Skip AWOS jika mode 1 jam (karena otomatis biasanya 30 menit) ---
            if mode_interval.lower() == "interval 1 jam" and nama_stasiun.startswith("AWOS"):
                continue


            # --- Tentukan laporan per jam berdasarkan interval ---
            laporan_per_jam = 2 if "30" in interval else 1
            maksimal = int(jam_operasi * laporan_per_jam)

            # --- Ambil waktu laporan aktual ---
            waktu_lapor = harian[tanggal_str].get(cccc, set())

            # --- Normalisasi waktu sesuai interval ---
            slot = set()
            for w in waktu_lapor:
                try:
                    jam, menit = map(int, w.split(":"))
                    if "30" in interval:
                        menit_slot = "00" if menit < 30 else "30"
                        slot.add(f"{jam:02d}:{menit_slot}")
                    else:
                        slot.add(f"{jam:02d}:00")
                except:
                    continue

            jumlah = int(len(slot))
            persen = round((jumlah / maksimal) * 100, 2) if maksimal else 0

            # --- Tentukan catatan ---
            if maksimal == 0:
                catatan = "⚠️ Target tidak tersedia"
            elif jumlah == 0:
                catatan = "❌ Tidak ada data"
            elif jumlah > maksimal:
                catatan = "⚠️ Data anomali, melebihi ekspektasi"
            elif jumlah == maksimal:
                catatan = "✅ Lengkap"
            else:
                catatan =  "⚠️ Tidak Lengkap"
            # if 90 <= persen < 100:
            #     print(f"[DEBUG] {cccc} {tanggal_str} => jumlah={jumlah}, maksimal={maksimal}, persen={persen}, status={catatan}")


            harian_record.append({
                "WMO ID": str(info.get("wmo", "-")),
                "ICAO": cccc,
                "Tanggal": tanggal_str,
                "Nama Stasiun": info.get("name", "-"),
                "Jam Operasional": jam_operasi,
                "Interval Pengiriman": interval,
                "Laporan Diharapkan": maksimal,
                "Laporan Masuk": jumlah,
                "Ketersediaan (%)": persen,
                "Catatan": catatan
            })

    # ========== 3. Buat DataFrame Harian ==========
    df_harian = pd.DataFrame(harian_record).sort_values(["ICAO", "Tanggal"])
    df_harian["Status Lengkap"] = df_harian["Catatan"].apply(lambda x: "✅ Lengkap" in str(x))

    # ========== 4. Buat Rekap Bulanan ==========
    bulanan_records = []
    for icao, group in df_harian.groupby("ICAO"):
        wmo_id = group["WMO ID"].iloc[0]
        nama_stasiun = group["Nama Stasiun"].iloc[0]
        laporan_masuk = group["Laporan Masuk"].sum()
        jumlah_hari_bulan = calendar.monthrange(tahun, bulan)[1]
        target_harian = group["Laporan Diharapkan"].iloc[0]  # target harian per stasiun
        target_bulanan = target_harian * jumlah_hari_bulan

        if target_bulanan == 0:
            persentase = 0
            catatan = "⚠️ Target tidak tersedia"
        elif laporan_masuk == 0:
            persentase = 0
            catatan = "❌ Tidak ada data"
        elif laporan_masuk > target_bulanan:
            persentase = round((laporan_masuk / target_bulanan) * 100, 2)
            catatan = "⚠️ Data anomali, melebihi ekspektasi"
        elif laporan_masuk < target_bulanan:
            persentase = round((laporan_masuk / target_bulanan) * 100, 2)
            catatan = "⚠️ Tidak Lengkap"
        else:
            persentase = 100.0
            catatan = "✅ Lengkap"

        bulanan_records.append({
            "WMO ID": wmo_id,
            "ICAO": icao,
            "Nama Stasiun": nama_stasiun,
            "Laporan Masuk Bulanan": laporan_masuk,
            "Target Bulanan": target_bulanan,
            "Ketersediaan %": persentase,
            "Catatan": catatan
        })

    df_bulanan = pd.DataFrame(bulanan_records).sort_values("ICAO").reset_index(drop=True)

    return df_harian, df_bulanan

from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd

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
    
    # Inisialisasi
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
    
    # Loop per tanggal dan stasiun
    for day_offset in range(num_days):
        tanggal_str = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        
        for cccc, info in station_info_map.items():
            if not cccc.isalpha():
                continue

            jam_operasi = info.get("operating_hours", 24)
            is_half_hourly = info.get("is_metar_half_hourly", False)
            
            # Tentukan interval
            if mode_interval.lower() == "otomatis":
                interval = "30 Menit" if is_half_hourly else "1 Jam"
            else:
                interval = mode_interval.strip()
            
            nama_stasiun = (info.get("name") or "").strip().upper()
            if interval == "Interval 1 Jam" and nama_stasiun.startswith("AWOS"):
                continue
            
            laporan_per_jam = 2 if is_half_hourly else 1
            maksimal = jam_operasi * laporan_per_jam
            
            waktu_lapor = harian[tanggal_str].get(cccc, set())
            
            if laporan_per_jam == 2:
                slot = set()
                for w in waktu_lapor:
                    try:
                        jam, menit = map(int, w.split(":"))
                        menit_slot = "00" if menit < 30 else "30"
                        slot.add(f"{jam:02d}:{menit_slot}")
                    except:
                        continue
                jumlah = len(slot)
            else:
                jumlah = len(waktu_lapor)
            
            persen = round((jumlah / maksimal) * 100, 1) if maksimal else 0
            
            catatan = []
            if jumlah == 0:
                catatan.append("❌ Tidak ada data")
            elif jumlah < maksimal * 0.5:
                catatan.append("⚠️ Kurang dari 50%")
            if jumlah > maksimal:
                catatan.append("⚠️ Data anomali, melebihi ekspektasi")
            
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
                "Catatan": "; ".join(catatan) if catatan else "✅ Lengkap"
            })
    
    # Buat dataframe harian
    df_harian = pd.DataFrame(harian_record).sort_values(["ICAO","Tanggal"])
    df_harian["Status Lengkap"] = df_harian["Catatan"].apply(lambda x: "✅ Lengkap" in str(x))
    
 
    # ================== BUAT DF BULANAN ==================
    bulanan_records = []
    for icao, group in df_harian.groupby("ICAO"):
        wmo_id = group["WMO ID"].iloc[0]
        nama_stasiun = group["Nama Stasiun"].iloc[0]
        laporan_masuk = group["Laporan Masuk"].sum()
        target_bulanan = group["Laporan Diharapkan"].sum()
        
        if target_bulanan == 0:
            persentase = 0
            catatan = "❌ Tidak ada data"
        else:
            persentase = round(laporan_masuk / target_bulanan * 100, 2)
            if laporan_masuk < target_bulanan:
                catatan = "⚠️ Tidak Lengkap"
            elif laporan_masuk == target_bulanan:
                catatan = "✅ Lengkap"
            else:
                catatan = "⚠️ Data anomali, melebihi ekspektasi"
        
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

    # ==========================
    # TEST METAR
    # ==========================
    
# import aiohttp
# import asyncio
# from auth import get_bmkg_token
# from fetcher import fetch_gts_data

# async def main():
#     token = await get_bmkg_token()
    
#     async with aiohttp.ClientSession() as session:
#         # Ambil data METAR bulan tertentu
#         metar_data = await fetch_gts_data(token, session, 2025, 9, type_message=4)
        
#         # ===== CEK CEPAT =====
#         total_metar = len(metar_data)
#         print(f"Total METAR record: {total_metar}")
#         total_stasiun = len(set(r.get('cccc') for r in metar_data if r.get('cccc')))
#         print(f"Total stasiun METAR: {total_stasiun}")

#         wiii_records = [r for r in metar_data if r.get("cccc") == "WIII"]
#         if wiii_records:
#             print(f"Ada {len(wiii_records)} record METAR untuk WIII")
#             print("Contoh 1 record WIII:")
#             print(wiii_records[0])
#         else:
#             print("Tidak ada record METAR untuk WIII")

# # Jalankan async main
# if __name__ == "__main__":
#     asyncio.run(main())

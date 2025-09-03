from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd

# ==== ANALYZE METAR (PERBAIKAN) ====
def analyze_metar(metar_data, station_info_map, tahun, bulan, mode_interval):
    """
    Analisis ketersediaan laporan METAR berdasarkan frekuensi asli stasiun.
    Mode interval bisa 'Otomatis' atau 'Interval 1 Jam' / '30 Menit'.
    Stasiun half-hourly tetap dihitung 2 laporan per jam, meski paksa 1 jam.
    """
    
    #Menyiapkan tanggal & wadah hasil
    hasil, nomor = [], 1

    start_date = datetime(tahun, bulan, 1)
    end_date = start_date + relativedelta(months=1)
    num_days = (end_date - start_date).days

    #Mengelompokkan data mentah ke struktur harian
    # Struktur data: harian[tanggal][cccc] = set(waktu)
    harian = defaultdict(lambda: defaultdict(set)) # dict bertingkat
    for item in metar_data:
        cccc = item.get("cccc") # key level 2
        ts = item.get("timestamp_data") # waktu asli dri data
        if not cccc or not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            tanggal = dt.strftime("%Y-%m-%d") # key level 1
            waktu = dt.strftime("%H:%M")  # nilai dalam set #value waktu "HH:MM" disimpan unik di dalam set.
            harian[tanggal][cccc].add(waktu) 
        except ValueError:
            continue

        #Loop tiap hari dan tiap stasiun
    for day_offset in range(num_days):
        tanggal_str = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        for cccc, info in station_info_map.items():
            jam_operasi = info.get("jam_operasi", 24) # jam operasi default 24
            is_half_hourly = info.get("sends_half_hourly", False) # apakah half -hourly

            # Tentukan interval yang dipakai untuk analisis
            if mode_interval == "Otomatis":
                interval = "30 Menit" if is_half_hourly else "Interval 1 Jam"
            else:
                interval = mode_interval

            # Skip AWOS jika interval 1 Jam
            nama_stasiun = (info.get("stasiun") or "").strip().upper()
            if interval == "Interval 1 Jam" and nama_stasiun.startswith("AWOS"):
                continue

            # Frekuensi asli stasiun menentukan laporan per jam
            laporan_per_jam = 2 if is_half_hourly else 1
            # Stasiun half-hourly → 2 laporan per jam (mis. menit 00 dan 30).
            # Stasiun hourly → 1 laporan per jam.
            
            # Sehari ada jam_operasi jam → target harian = jam_operasi * laporan_per_jam.
            maksimal = jam_operasi * laporan_per_jam

            # Menghitung jumlah laporan yang masuk
            waktu_lapor = harian[tanggal_str].get(cccc, set())

            # Hitung jumlah laporan sesuai interval
            if laporan_per_jam == 2:  # half-hourly
                slot = set() # agar tdk duplikat
                for w in waktu_lapor:
                    try:
                        jam, menit = map(int, w.split(":")) 
                        # w.split(":") --> Memisahkan string waktu seperti "15:14" menjadi dua bagian: ["15","14"].
                        # map(int, ...) → Mengubah "15" dan "14" menjadi integer: jam = 15, menit = 14.
                       
                        menit_slot = "00" if menit < 30 else "30"                        
                       # Menentukan slot waktu setengah jam:
                       # menit < 30 → masuk ke slot :00
                       # menit >= 30 → masuk ke slot :30

                        slot.add(f"{jam:02d}:{menit_slot}")
                        # Menambahkan slot ke set bernama slot.
                        # f"{jam:02d}" memastikan jam selalu 2 digit, misal "05" bukan "5".
                    
                    except:
                        continue #Jika parsing gagal (misal w bukan string waktu yang valid), abaikan saja.
               
                jumlah = len(slot) #Menghitung jumlah slot unik dalam satu hari
           
           # waktu_lapor kemungkinan adalah list yang berisi semua laporan yang masuk per jam.
            else:  # hourly
                jumlah = len(waktu_lapor) # len(waktu_lapor) → menghitung total laporan, tanpa mengelompokkan atau menyaring duplikasi.

            # Persentase ketersediaan
            persen = round((jumlah / maksimal) * 100, 1) if maksimal else 0
            # if maksimal else 0, cek divisi 0 (ZeroDivisionError), jika max 0 artinya tidak ada target laporan sama sekali
            
            catatan = []
            if jumlah == 0:
                catatan.append("❌ Tidak ada data")
            elif jumlah < maksimal * 0.5:
                catatan.append("⚠️ Kurang dari 50%")
            if jumlah > maksimal:
                catatan.append("⚠️ Data anomali, melebihi ekspektasi")
            if jam_operasi < 24:
                catatan.append(f"🕒 Op: {jam_operasi} jam")

            hasil.append({
                "Nomor": nomor,
                "WMO ID": str(info.get("wmo_id", "-")),
                "Tanggal": tanggal_str,
                "ICAO": cccc,
                "Nama Stasiun": info.get("stasiun", "-"),
                "Jam Operasional": jam_operasi,
                "Interval Pengiriman": interval,
                "Laporan Diharapkan": maksimal,
                "Laporan Masuk": jumlah,
                "Ketersediaan (%)": persen,
                "Catatan": "; ".join(catatan) if catatan else "✅ Lengkap"
            })
            nomor += 1
            
    
    df = pd.DataFrame(hasil)
    
    # Tambahkan kolom Status Lengkap
    df["Status Lengkap"] = df["Catatan"].apply(
        lambda x: True if "✅ Lengkap" in str(x) else False
    )
    
    return df





# from collections import defaultdict
# from datetime import datetime, timedelta
# from dateutil.relativedelta import relativedelta
# import pandas as pd


# # ==== ANALYZE METAR ====
# def analyze_metar(metar_data, station_info_map, tahun, bulan, mode_interval):
#     """
#     Analisis ketersediaan laporan METAR berdasarkan jam atau 30 menit.
#     Jika interval 1 Jam -> data AWOS dilewati (tidak dihitung).
#     """

#     hasil, nomor = [], 1

#     start_date = datetime(tahun, bulan, 1)
#     end_date = start_date + relativedelta(months=1)
#     num_days = (end_date - start_date).days

#     harian = defaultdict(lambda: defaultdict(set))

#     for item in metar_data:
#         cccc = item.get("cccc")
#         ts = item.get("timestamp_data")
#         if not cccc or not ts:
#             continue
#         try:
#             dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
#             tanggal = dt.strftime("%Y-%m-%d")
#             waktu = dt.strftime("%H:%M")
#             harian[tanggal][cccc].add(waktu)
#         except ValueError:
#             continue

#     for day_offset in range(num_days):
#         tanggal_str = (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

#         for cccc, info in station_info_map.items():
#             jam_operasi = info.get("jam_operasi", 24)
#             is_half_hourly = info.get("sends_half_hourly", False)

#             interval = mode_interval if mode_interval != "Otomatis" else ("30 Menit" if is_half_hourly else " Interval 1 Jam")
            
#             # 🚫 Skip AWOS kalau interval 1 Jam
#             nama_stasiun = (info.get("stasiun") or "").strip().upper()
#             if interval == "Interval 1 Jam" and nama_stasiun.startswith("AWOS"):
#                 continue

#             waktu_lapor = harian[tanggal_str].get(cccc, set())
#             laporan_per_jam = 2 if interval == "30 Menit" else 1
#             maksimal = jam_operasi * laporan_per_jam

#             if interval == "30 Menit":
#                 slot = set()
#                 for w in waktu_lapor:
#                     try:
#                         jam, menit = map(int, w.split(":"))
#                         menit_slot = "00" if menit < 30 else "30"
#                         slot.add(f"{jam:02d}:{menit_slot}")
#                     except:
#                         continue
#                 jumlah = len(slot)
#             else:
#                 jumlah = len(waktu_lapor)

#             # Hitung Persentase
#             persen = round((jumlah / maksimal) * 100, 2) if maksimal else 0

#             status_lengkap = (jumlah == maksimal)
#             catatan = []
#             if jumlah == 0:
#                 catatan.append("❌ Tidak ada data")
#             elif jumlah < maksimal * 0.5:
#                 catatan.append("⚠️ Kurang dari 50%")
#             if jumlah > maksimal:
#                 catatan.append("⚠️ Data anomali, melebihi ekspektasi")
#             if jam_operasi < 24:
#                 catatan.append(f"🕒 Op: {jam_operasi} jam")

#             hasil.append({
#                 "Nomor": nomor,
#                 "WMO ID": str(info.get("wmo_id", "-")),
#                 "Tanggal": tanggal_str,
#                 "ICAO": cccc,
#                 "Nama Stasiun": info.get("stasiun", "-"),
#                 "Jam Operasional": jam_operasi,
#                 "Interval Pengiriman": interval,
#                 "Laporan Diharapkan": maksimal,
#                 "Laporan Masuk": jumlah,
#                 "Ketersediaan (%)": persen,
#                 "Status Lengkap": status_lengkap,
#                 "Catatan": "; ".join(catatan) if catatan else "✅ Lengkap"
#             })
#             nomor += 1

#     df = pd.DataFrame(hasil)
#     return df

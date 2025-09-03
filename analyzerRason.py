from datetime import datetime
import pandas as pd
import calendar

# ==== Helper Functions ====
def kv_list_to_dict(items):
    """Flatten list of key-value dicts to a single dict."""
    out = {}
    for el in items:
        if isinstance(el, dict):
            if "key" in el and "value" in el:
                k = el["key"]
                out[k] = el.get("value")
                if "status" in el:
                    out[f"{k}__status"] = el.get("status")
            else:
                for k, v in el.items():
                    out[k] = v
    return out

def has_obs_for(flat, hour):
    """Cek apakah ada observasi untuk jam tertentu (00Z / 12Z)."""
    hh = f"{hour:02d}:00"
    cells = [f"{hh} A", f"{hh} B", f"{hh} C", f"{hh} D"]
    vals = [flat.get(k) for k in cells]
    stats = [flat.get(f"{k}__status") for k in cells]

    valid_flags = [
        (v is not None and v not in ("", "-", "M"))
        and (s not in ("missing", "no observation") if s else True)
        for v, s in zip(vals, stats)
    ]
    n_valid = sum(valid_flags)

    if n_valid == 0:
        return False, "Tidak Ada"
    elif n_valid < len(cells):
        return True, "Parsial"
    else:
        return True, "Lengkap"

# ==== Record generator ====
def iter_records(raw, tahun, bulan):
    """Generator untuk membaca semua record RASON."""
    if not raw:
        return # klo data ksoong, langsung berhenti
    
    #normalisasi data --> suapaya bs selalu di looping
    # dict dengan key items --> ambil list nya
    # list --> pakai langsung
    # 1 object --> ubah jdi list 1 elemen
    rlist = raw.get("items", [raw]) if isinstance(raw, dict) else raw if isinstance(raw, list) else [raw]
   
    seen_global = set() # mencegah duplikat dengan mengingat record yg sdh diproses

   
    
    # jika item adalah dict langsung
    for item in rlist:  # loop tiap item di data
        if isinstance(item, dict):
            ts = item.get("timestamp_data")
            dt = pd.to_datetime(ts, errors="coerce")
            if pd.isna(dt) or dt.year != tahun or dt.month != bulan:
                continue

            wmo_id = str(item.get("station_wmo_id") or item.get("station_id") or "").strip()
            if not wmo_id:
                continue
            name = item.get("station_name") or ""

            for jam, hour in [("00Z", 0), ("12Z", 12)]:
                if dt.hour == hour:
                    key = (wmo_id, dt.date(), jam)
                    if key in seen_global:
                        continue
                    seen_global.add(key)
                    yield {
                        "date": dt.date(),
                        "wmo_id": wmo_id,
                        "station_name": name,
                        "jam": jam,
                        "status": "Lengkap",
                    }
        # jika item adalah list key value
        elif isinstance(item, list):
            flat = kv_list_to_dict(item)
            dt = pd.to_datetime(flat.get("periode"), errors="coerce")
            if pd.isna(dt) or dt.year != tahun or dt.month != bulan:
                continue

            wmo_id = str(flat.get("station_wmo_id") or flat.get("station_id") or "").strip()
            if not wmo_id:
                continue
            name = flat.get("station_name") or ""

            for jam, hour in [("00Z", 0), ("12Z", 12)]:
                has_obs, status = has_obs_for(flat, hour)
                key = (wmo_id, dt.date(), jam)
                if has_obs and key not in seen_global: #“Kalau ada data observasi dan record ini belum tercatat, lanjut proses.”
                    seen_global.add(key)
                    yield { #Menghasilkan satu record RASON berupa dictionary:
                        "date": dt.date(),
                        "wmo_id": wmo_id,
                        "station_name": name,
                        "jam": jam,
                        "status": status,
                    }

# ==== Manual mapping WMO → Nama Stasiun (fallback) ====
station_map_manual = {
    "96035": "Stasiun Meteorologi Kualanamu",
    "96147": "Stasiun Meteorologi Ranai",
    "96237": "Stasiun Meteorologi Depati Amir",
    "96253": "Stasiun Meteorologi Fatmawati Soekarno",
    "96509": "Stasiun Meteorologi Juwata",
    "96581": "Stasiun Meteorologi Supadio",
    "96633": "Stasiun Meteorologi Sultan Aji Muhammad Sulaiman Sepinggan",
    "96645": "Stasiun Meteorologi Iskandar",

    "96685": "Stasiun Meteorologi Syamsudin Noor",
    "96749": "Stasiun Meteorologi Soekarno Hatta",
    "96805": "Stasiun Meteorologi Tunggul wulung",
    
    "96935": "Stasiun Meteorologi Juanda",
    "97230": "Stasiun Meteorologi I Gusti Ngurah Rai",
    "97372": "Stasiun Meteorologi Eltari",
    
    "97502": "Stasiun Meteorologi Domine Eduard Osok",
    "97560": "Stasiun Meteorologi Frans Kaisiepo",
    "97690": "Stasiun Meteorologi Sentani",
    "97980": "Stasiun Meteorologi Mopah",
    "97686": "Stasiun Meteorologi Wamena",
    "97300": "Stasiun Meteorologi Fransiskus Xaverius Seda"
  
    
}

def get_station_name_combined(wmo_id, station_info_map):
    # Cek di mapping otomatis (BMKG)
    if station_info_map:
        for icao, info in station_info_map.items():
            if str(info.get("wmo_id")) == str(wmo_id):
                return info.get("stasiun") or info.get("station_name") or f"Stasiun {wmo_id}"
    # Fallback manual
    return station_map_manual.get(wmo_id, f"Stasiun {wmo_id or 'Unknown'}")


# Tambahkan catatan status
def status_bulanan(row):
    if row["Jumlah Laporan"] == row["Target Bulanan"]:
        return "✅ Lengkap"
    elif row["Jumlah Laporan"] > row["Target Bulanan"]:
        return "⚠️ Anomali"
    elif 0 < row["Jumlah Laporan"] < row["Target Bulanan"]:
        return "⚠️ Parsial"
    else:
        return "❌ Tidak Ada Data"
        
# ==== Main Analysis Function ====
def analyze_rason(rason_data, station_info_map, tahun, bulan):
    # membuat list record
    rows = [] # membuat list kosong, nnti list akan di isi dengan record, setiap record itu dictionary {}
    for rec in iter_records(rason_data, tahun, bulan):
        wmo_id = rec["wmo_id"] #Ambil kode stasiun dari record
        nama = rec.get("station_name") or get_station_name_combined(wmo_id, station_info_map) 
        # ambil nama stasiun dari record, klo ga ada akan fallback mapping otomatis atau manual
        
        #membuat dict baru berisi info penting dari record, kemudian ditambahkan ke list rows
        # jadi rows = list dari dict
        # rows = kumpulan semua record siap pakai untuk dianalisis
        rows.append({
            "WMO ID": wmo_id,
            "Nama Stasiun": nama,
            "Tanggal": rec["date"],
            "Jam": rec["jam"],
            "Status Jam": rec["status"],
        })

    #jika data tidak ada, buat df kosong dengan kolom yg sesuai, agar aplikasi atau analisis selanjutnya tetap berjalan tanpa error
    if not rows:
        empty_harian = pd.DataFrame(columns=["WMO ID","Nama Stasiun","Tanggal","00Z","12Z","Jumlah Laporan"])
        empty_bulanan = pd.DataFrame(columns=["WMO ID","Nama Stasiun","Bulan","Jumlah Laporan","Target Bulanan","Ketersediaan (%)","Catatan"])
        return empty_harian, empty_bulanan

    df_rason_detail = pd.DataFrame(rows)

    # ==== Rekap Harian ====
    # df_rason_detail → tabel berisi semua record harian 
    df_rason_harian = df_rason_detail.pivot_table(
        index=["WMO ID","Nama Stasiun","Tanggal"],
        columns="Jam",
        values="Status Jam",
        aggfunc="first"
    ).reset_index()
    df_rason_harian = df_rason_harian.rename_axis(None, axis=1)

    # Pastikan kolom 00Z dan 12Z ada
    for jam in ["00Z","12Z"]: # jika salah satu jam tidak ada karena data kosong
        if jam not in df_rason_harian.columns:
            df_rason_harian[jam] = None # buat kolom baru dengan isi NONE, agar tdk error

    # Hitung jumlah laporan harian
    df_rason_harian["Jumlah Laporan"] = df_rason_harian[["00Z","12Z"]].apply(
        lambda x: sum(v in ["Lengkap","Parsial"] for v in x), axis=1
    )
    # df_rason_harian["Status Lengkap"] = (df_rason_harian["Jumlah Laporan"] == 2)

    # ==== Rekap Bulanan ====
    jumlah_hari_bulan = calendar.monthrange(tahun, bulan)[1]
    target_bulanan = jumlah_hari_bulan * 2

    df_rason_bulanan = df_rason_harian.groupby(["WMO ID","Nama Stasiun"]).agg(
        Jumlah_Laporan=("Jumlah Laporan","sum"),
    ).reset_index()
    df_rason_bulanan["Target Bulanan"] = target_bulanan
    df_rason_bulanan["Ketersediaan (%)"] = (df_rason_bulanan["Jumlah_Laporan"] / target_bulanan * 100).round(1).clip(upper=100)
    # df_rason_bulanan["Status Lengkap"] = df_rason_bulanan["Jumlah_Laporan"] >= target_bulanan
    df_rason_bulanan = df_rason_bulanan.rename(columns={"Jumlah_Laporan":"Jumlah Laporan"})

        
    df_rason_bulanan["Catatan"] = df_rason_bulanan.apply(status_bulanan, axis=1)
    # Pastikan tipe kolom string agar emoji tampil
    df_rason_bulanan["Catatan"] = df_rason_bulanan["Catatan"].astype(str)
    
    return df_rason_harian, df_rason_bulanan


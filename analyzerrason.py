import asyncio
import aiohttp
import calendar
from datetime import datetime
import pandas as pd
from auth import get_bmkg_token
from station import fetch_all_stations_info
from fetcher import fetch_gts_data  # pastikan ini ada di project-mu
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
        return True, "Tidak Lengkap"
    else:
        return True, "Lengkap"


# ==== Record generator ====
def iter_records(raw, tahun, bulan):
    """Generator untuk membaca semua record RASON."""
    if not raw:
        return

    # Normalisasi data supaya selalu bisa di-loop
    rlist = raw.get("items", [raw]) if isinstance(raw, dict) else raw if isinstance(raw, list) else [raw]
    seen_global = set()  # mencegah duplikat

    for item in rlist:
        if isinstance(item, dict):
            ts = item.get("timestamp_data")
            dt = pd.to_datetime(ts, errors="coerce")
            if pd.isna(dt) or dt.year != tahun or dt.month != bulan:
                continue

            wmo_id = str(item.get("station_wmo_id") or item.get("station_id") or "").strip()
            if not wmo_id:
                continue

            for jam, hour in [("00Z", 0), ("12Z", 12)]:
                if dt.hour == hour:
                    key = (wmo_id, dt.date(), jam)
                    if key in seen_global:
                        continue
                    seen_global.add(key)
                    yield {
                        "date": dt.date(),
                        "wmo_id": wmo_id,
                        "jam": jam,
                        "status": "Lengkap",
                    }

        elif isinstance(item, list):
            flat = kv_list_to_dict(item)
            dt = pd.to_datetime(flat.get("timestamp_data"), errors="coerce")  # pakai timestamp_data, bukan periode
            if pd.isna(dt) or dt.year != tahun or dt.month != bulan:
                continue

            wmo_id = str(flat.get("station_wmo_id") or flat.get("station_id") or "").strip()
            if not wmo_id:
                continue

            for jam, hour in [("00Z", 0), ("12Z", 12)]:
                has_obs, status = has_obs_for(flat, hour)
                key = (wmo_id, dt.date(), jam)
                if has_obs and key not in seen_global:
                    seen_global.add(key)
                    yield {
                        "date": dt.date(),
                        "wmo_id": wmo_id,
                        "jam": jam,
                        "status": status,
                    }

def get_station_name_combined(wmo_id, station_info_map):
    # Langsung cek pakai WMO sebagai key (string)
    if str(wmo_id) in station_info_map:
        return station_info_map[str(wmo_id)].get("name", f"Stasiun {wmo_id}")
    
    # Kalau tidak ada, coba cari manual di value
    for info in station_info_map.values():
        if str(info.get("wmo")) == str(wmo_id):
            return info.get("name", f"Stasiun {wmo_id}")
    
    return f"Stasiun {wmo_id}"


def status_bulanan(row):
    if row["Jumlah Laporan"] == row["Target Bulanan"]:
        return "✅ Lengkap"
    elif row["Jumlah Laporan"] > row["Target Bulanan"]:
        return "⚠️ Anomali"
    elif 0 < row["Jumlah Laporan"] < row["Target Bulanan"]:
        return "⚠️ Tidak Lengkap"
    else:
        return "❌ Tidak Ada Data"


def analyze_rason(rason_data, station_info_map, tahun, bulan):
    rows = []
    seen_global = set()

    for rec in iter_records(rason_data, tahun, bulan):
        wmo_id = rec["wmo_id"]
        nama = get_station_name_combined(wmo_id, station_info_map)
        key = (wmo_id, rec["date"], rec["jam"])
        if key in seen_global:
            continue
        seen_global.add(key)

        rows.append({
            "WMO ID": wmo_id,
            "Nama Stasiun": nama,
            "Tanggal": rec["date"],
            "Jam": rec["jam"],
            "Status Jam": rec["status"],
        })

    if not rows:
        empty_harian = pd.DataFrame(columns=["WMO ID","Nama Stasiun","Tanggal","00Z","12Z","Jumlah Laporan"])
        empty_bulanan = pd.DataFrame(columns=["WMO ID","Nama Stasiun","Bulan","Jumlah Laporan","Target Bulanan","Ketersediaan (%)","Catatan"])
        return empty_harian, empty_bulanan

    df_rason_detail = pd.DataFrame(rows)

    # ==== Rekap Harian (pivot dulu) ====
    df_rason_harian = df_rason_detail.pivot_table(
        index=["WMO ID","Nama Stasiun","Tanggal"],
        columns="Jam",
        values="Status Jam",
        aggfunc="first"
    ).reset_index()
    df_rason_harian = df_rason_harian.rename_axis(None, axis=1)

    for jam in ["00Z","12Z"]:
        if jam not in df_rason_harian.columns:
            df_rason_harian[jam] = "Tidak Ada"

    df_rason_harian["Jumlah Laporan"] = df_rason_harian[["00Z","12Z"]].apply(
        lambda x: sum(v in ["Lengkap","Tidak Lengkap"] for v in x), axis=1
    )

    # ==== Tambahkan semua tanggal dalam bulan ====
    all_dates = pd.date_range(
        start=f"{tahun}-{bulan:02d}-01",
        end=f"{tahun}-{bulan:02d}-{calendar.monthrange(tahun, bulan)[1]}"
    )
    stations = df_rason_detail[["WMO ID", "Nama Stasiun"]].drop_duplicates()
    complete_index = (
        stations.assign(key=1)
        .merge(pd.DataFrame({"Tanggal": all_dates, "key": 1}), on="key")
        .drop("key", axis=1)
    )

    df_rason_harian["Tanggal"] = pd.to_datetime(df_rason_harian["Tanggal"])
    complete_index["Tanggal"] = pd.to_datetime(complete_index["Tanggal"])

    # Gabungkan supaya semua tanggal muncul
    df_rason_harian = complete_index.merge(
        df_rason_harian,
        on=["WMO ID", "Nama Stasiun", "Tanggal"],
        how="left"
    ).fillna({"00Z": "None", "12Z": "None", "Jumlah Laporan": 0})

   # Ubah Tanggal kembali jadi tipe date saja (tanpa jam)
    df_rason_harian["Tanggal"] = df_rason_harian["Tanggal"].dt.date

    # ==== Rekap Bulanan ====
    jumlah_hari_bulan = calendar.monthrange(tahun, bulan)[1]
    target_bulanan = jumlah_hari_bulan * 2

    df_rason_bulanan = df_rason_harian.groupby(["WMO ID","Nama Stasiun"]).agg(
        Jumlah_Laporan=("Jumlah Laporan","sum"),
    ).reset_index()

    df_rason_bulanan["Target Bulanan"] = target_bulanan
    df_rason_bulanan["Ketersediaan (%)"] = (
        (df_rason_bulanan["Jumlah_Laporan"] / target_bulanan * 100)
        .round(2)
    )
    df_rason_bulanan = df_rason_bulanan.rename(columns={"Jumlah_Laporan":"Jumlah Laporan"})
    df_rason_bulanan["Catatan"] = df_rason_bulanan.apply(status_bulanan, axis=1).astype(str)

    return df_rason_harian, df_rason_bulanan



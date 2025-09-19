import asyncio
import aiohttp
import calendar
import time
from datetime import datetime, timedelta
from auth import get_bmkg_token
from station import fetch_all_stations_info

BASE_URL = "https://bmkgsatu.bmkg.go.id/db/bmkgsatu//@search"
SEMAPHORE = asyncio.Semaphore(6)


async def fetch_range_with_paging(session, headers, type_message, start, end, metadata=None, use_sent_timestamp=False):
    """Ambil data GTSMessage dalam range waktu tertentu, dengan paging."""
    all_items = []
    offset = 0
    size = 10000
    if metadata is None:
        metadata = "type_message,timestamp_data,timestamp_sent_data,cccc,station_wmo_id,sandi_gts"

    range_start = time.perf_counter()
    timestamp_field = "timestamp_sent_data" if use_sent_timestamp else "timestamp_data"

    while True:
        params = {
            "type_name": "GTSMessage",
            "_metadata": metadata,
            "type_message": type_message,
            "_size": size,
            "_from": offset,
            f"{timestamp_field}__gte": start.strftime("%Y-%m-%dT%H:%M:%S"),
            f"{timestamp_field}__lte": end.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        try:
            async with SEMAPHORE:
                async with session.get(
                    BASE_URL, headers=headers, params=params,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status != 200:
                        print(f"⚠️ Error {resp.status} [{start} – {end}]")
                        break

                    result = await resp.json()
                    items = result.get("items", [])
                    if not items:
                        break

                    all_items.extend(items)
                    offset += len(items)

                    if len(items) < size:
                        break
        except Exception as e:
            print(f"❌ Error range {start}–{end}: {e}")
            break

    elapsed = time.perf_counter() - range_start
    print(f"📦 {type_message} [{start:%d %b} – {end:%d %b}] {len(all_items)} record asli dalam {elapsed:.2f} detik")
    return all_items


async def fetch_gts_data(token, session, tahun, bulan, type_message, metadata=None):
    """Fetch data GTS untuk 1 bulan penuh."""
    headers = {"Authorization": f"Bearer {token}"}
    last_day = calendar.monthrange(tahun, bulan)[1]
    start_date = datetime(tahun, bulan, 1, 0, 0, 0)
    end_date = datetime(tahun, bulan, last_day, 23, 59, 59)

    ranges = []
    cur = start_date
    while cur <= end_date:
        nxt = min(cur + timedelta(days=6, hours=23, minutes=59, seconds=59), end_date)
        ranges.append((cur, nxt))
        cur = nxt + timedelta(seconds=1)

    total_start = time.perf_counter()
    use_sent_timestamp = (type_message == 6)  # khusus TAF

    tasks = [
        fetch_range_with_paging(session, headers, type_message, s, e, metadata, use_sent_timestamp)
        for (s, e) in ranges
    ]
    results = await asyncio.gather(*tasks)
    all_items = [item for sublist in results for item in sublist]

    # Sort berdasarkan timestamp
    sort_key = "timestamp_sent_data" if use_sent_timestamp else "timestamp_data"
    all_items.sort(key=lambda x: x.get(sort_key, ""))

    total_elapsed = time.perf_counter() - total_start
    print(f"✅ {type_message} bulan {bulan}-{tahun} selesai dalam {total_elapsed:.2f} detik, total {len(all_items)} record asli")
    return all_items

# import asyncio
# import aiohttp
# from auth import get_bmkg_token
# from fetcher import fetch_gts_data

# async def main():
#     token = await get_bmkg_token()
#     async with aiohttp.ClientSession() as session:
#         # Misal cek type_message 1 (METAR) atau 6 (TAF)
#         type_message = 6
#         tahun = 2025
#         bulan = 9

#         items = await fetch_gts_data(token, session, tahun, bulan, type_message)

#         if not items:
#             print("❌ Tidak ada data sama sekali")
#             return

#         # Print contoh 3 item pertama
#         for i, item in enumerate(items[:3], 1):
#             print(f"\nItem {i}:")
#             print(item)

#         # Cek apakah 'cccc' ada di keys
#         keys_set = set()
#         for item in items[:10]:  # cek 10 item pertama
#             keys_set.update(item.keys())
#         print("\nKeys yang muncul di response:", keys_set)

#         if "cccc" in keys_set:
#             print("✅ Kolom 'cccc' ada")
#         else:
#             print("⚠️ Kolom 'cccc' TIDAK ADA di response")

# if __name__ == "__main__":
#     asyncio.run(main())


# async def main():
#     token = await get_bmkg_token()
#     async with aiohttp.ClientSession() as session:
#         # =======================
#         # Ambil semua metadata stasiun
#         # =======================
#         stations = await fetch_all_stations_info(token, session)

#         # Buat index lookup: ICAO dan WMO
#         station_by_icao = {s["icao"]: s for s in stations.values() if s.get("icao")}
#         station_by_wmo = {str(s["wmo"]): s for s in stations.values() if s.get("wmo")}

#         # Semua ICAO valid di metadata
#         stations_in_meta = set(station_by_icao.keys())

#         # =======================
#         # Ambil data TAF bulan tertentu
#         # =======================
#         taf_data = await fetch_gts_data(token, session, 2025, 8, 6)

#         # =======================
#         # Contoh 5 record TAF
#         # =======================
#         print("\nContoh 5 record TAF:")
#         for item in taf_data[:5]:
#             icao = item.get("station_icao") or item.get("cccc")
#             wmo = str(item.get("station_wmo_id"))
#             stasiun = None

#             if icao in station_by_icao:
#                 stasiun = station_by_icao[icao]["name"]
#             elif wmo in station_by_wmo:
#                 stasiun = station_by_wmo[wmo]["name"]

#             print({
#                 "timestamp_data": item.get("timestamp_data"),
#                 "timestamp_sent_data": item.get("timestamp_sent_data"),
#                 "icao": icao,
#                 "wmo": wmo,
#                 "station": stasiun,
#                 "sandi_gts": (item.get("sandi_gts") or "")[:80] + "..."
#             })

#         # =======================
#         # Statistik ICAO unik
#         # =======================
#         icao_set = {item.get("station_icao") or item.get("cccc") for item in taf_data if item.get("cccc")}
#         stations_with_name = {icao for icao in icao_set if icao in station_by_icao}
#         new_icao = {icao for icao in icao_set if icao not in station_by_icao}

#         print("\nJumlah ICAO unik dalam TAF:", len(icao_set))
#         print("Jumlah stasiun valid (ada di metadata):", len(stations_with_name))
#         print("Jumlah ICAO baru yang belum ada di metadata:", len(new_icao))
#         print("Contoh ICAO baru:", list(new_icao)[:10])

#         icao_to_check = "WIII"

#         # Cek apakah ada di TAF
#         if icao_to_check in icao_set:
#             print(f"{icao_to_check} ada di TAF")
#         else:
#             print(f"{icao_to_check} TIDAK ada di TAF")

#         # Cek apakah stasiun valid (ada di metadata)
#         if icao_to_check in stations_in_meta:
#             print(f"{icao_to_check} ada di metadata stasiun")
#         else:
#             print(f"{icao_to_check} TIDAK ada di metadata stasiun")


# if __name__ == "__main__":
#     asyncio.run(main())

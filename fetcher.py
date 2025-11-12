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


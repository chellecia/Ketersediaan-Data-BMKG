
import calendar
from datetime import datetime, timedelta
import aiohttp
import asyncio
import time

BASE_URL = "https://bmkgsatu.bmkg.go.id/db/bmkgsatu//@search"

# Semaphore global, batasi maksimal 6 request bersamaan
SEMAPHORE = asyncio.Semaphore(6)

async def fetch_range_with_paging(session, headers, type_message, start, end):
    """Ambil semua data untuk 1 range (mingguan) dengan paging sampai habis."""
    all_items = []
    offset = 0
    size = 10000

    range_start = time.perf_counter()

    while True:
        params = {
            "type_name": "GTSMessage",
            "_metadata": "timestamp_data,cccc,station_wmo_id",
            "type_message": type_message,
            "timestamp_data__gte": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "timestamp_data__lte": end.strftime("%Y-%m-%dT%H:%M:%S"),
            "_size": size,
            "_from": offset
        }

        try:
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
    print(f"📦 {type_message} [{start:%d %b} – {end:%d %b}] "
          f"{len(all_items)} record asli dalam {elapsed:.2f} detik")

    return all_items


async def fetch_gts_data(token, session, tahun, bulan, type_message):
    """Ambil data GTS 1 bulan penuh, dibagi per minggu, paging otomatis, paralel."""
    headers = {"Authorization": f"Bearer {token}"}
    

    last_day = calendar.monthrange(tahun, bulan)[1]
    start_date = datetime(tahun, bulan, 1, 0, 0, 0)
    end_date = datetime(tahun, bulan, last_day, 23, 59, 59)

    # Bagi per 7 hari
    ranges = []
    cur = start_date
    while cur <= end_date:
        nxt = min(cur + timedelta(days=6, hours=23, minutes=59, seconds=59), end_date)
        ranges.append((cur, nxt))
        cur = nxt + timedelta(seconds=1)

    total_start = time.perf_counter()

    # Jalankan semua minggu paralel
    tasks = [fetch_range_with_paging(session, headers, type_message, s, e) for (s, e) in ranges]
    results = await asyncio.gather(*tasks)

    all_items = [item for sublist in results for item in sublist]
    all_items.sort(key=lambda x: x.get("timestamp_data", ""))

    total_elapsed = time.perf_counter() - total_start
    print(f"✅ {type_message} bulan {bulan}-{tahun} selesai "
          f"dalam {total_elapsed:.2f} detik, total {len(all_items)} record asli")

    return all_items


import calendar
from datetime import datetime
import aiohttp
import asyncio

BASE_URL = "https://bmkgsatu.bmkg.go.id/db/bmkgsatu//@search"

async def fetch_gts_data(token, session, tahun, bulan, type_message):
    """
    Ambil data GTS dari BMKG SATU berdasarkan bulan, tahun, dan jenis pesan.
    type_message: 'METAR', 'SPECI', 'RASON'
    """
    headers = {"Authorization": f"Bearer {token}"}

    # Hitung awal dan akhir bulan
    last_day = calendar.monthrange(tahun, bulan)[1]
    start_date = datetime(tahun, bulan, 1, 0, 0, 0)
    end_date = datetime(tahun, bulan, last_day, 23, 59, 59)

    params_base = {
        "type_name": "GTSMessage",
        "_metadata": "timestamp_data,cccc,station_wmo_id",
        "type_message": type_message,
        "timestamp_data__gte": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "timestamp_data__lte": end_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "_size": 10000
    }

    all_data = []
    offset = 0

    while True:
        params = dict(params_base)
        params["_from"] = offset

        try:
            async with session.get(BASE_URL, 
                                   headers=headers, 
                                   params=params, 
                                   timeout=aiohttp.ClientTimeout(total=90)
                                   ) as response:
               
                if response.status != 200:
                    print(f"⚠️ Gagal ambil data {type_message} ({response.status})")
                    return[]
                
                try:  
                    result = await response.json()
                except Exception as e:
                    text = await response.text()
                    print(f"⚠️ Response bukan JSON untuk {type_message} ({e}): {text[:200]}")
                    return []  # hentikan fungsi
                
                items = result.get("items", [])

                if not items:
                    break

                all_data.extend(items)
                offset += len(items)

        except asyncio.TimeoutError:
            print(f"⏳ Timeout saat ambil {type_message} bulan {bulan} {tahun}")
            break
        
        except Exception as e:
            print(f"❌ Error: {e}")
            break

    # Urutkan berdasarkan timestamp_data
    all_data.sort(key=lambda x: x.get("timestamp_data", ""))
    return all_data

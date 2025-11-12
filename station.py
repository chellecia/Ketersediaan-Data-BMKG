# station.py
import aiohttp
import asyncio

BMKG_STATION_URL = "https://bmkgsatu.bmkg.go.id/db/bmkgsatu/@search"


async def fetch_all_stations_info(token: str, session: aiohttp.ClientSession) -> dict:
    """
    Ambil semua stasiun BMKG (~6000) dalam 1 request besar.
    Bisa lookup ICAO & WMO.
    Session dipakai dari luar agar bisa paralel dengan fetcher GTS.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "type_name": "BmkgStation",
        "_metadata": "station_name,station_icao,station_wmo_id,station_operating_hours,is_metar_half_hourly",
        "_size": 10000  # cukup untuk semua stasiun
    }

    async with session.get(BMKG_STATION_URL, headers=headers, params=params) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Gagal fetch stations, status={resp.status}")
        data = await resp.json()

    stations = {}
    for item in data.get("items", []):
        icao = item.get("station_icao")
        wmo = item.get("station_wmo_id")
        if not icao or not wmo:
            continue

        # Ambil jam operasi, fallback ke 24 jam jika tidak valid
        op_hours = item.get("station_operating_hours", 24)
        if not isinstance(op_hours, int) or not (0 < op_hours <= 24):
            op_hours = 24
                    
        station_data = {
            "icao": icao.upper(),
            "wmo": wmo,
            "name": item.get("station_name"),
            "operating_hours": op_hours,
            "is_metar_half_hourly": bool(item.get("is_metar_half_hourly", False))
        }

        # keyed by ICAO
        stations[icao.upper()] = station_data
        # keyed by WMO juga
        stations[str(wmo)] = station_data

    return stations



import aiohttp

# Endpoint API BMKG SATU untuk data stasiun
BMKG_STATION_URL = "https://bmkgsatu.bmkg.go.id/db/bmkgsatu/@search"

async def fetch_all_stations_info(token: str, session: aiohttp.ClientSession) -> dict:
    """
    Ambil metadata semua stasiun BMKG dalam bentuk dict keyed by ICAO code.
    
    Args:
        token (str): JWT token BMKG SATU
        session (aiohttp.ClientSession): Session HTTP untuk request async
        
    Returns:
        dict: { ICAO: {stasiun, wmo_id, jam_operasi, sends_half_hourly} }
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "type_name": "BmkgStation",
        "_metadata": (
            "station_name,station_operating_hours,"
            "station_icao,station_wmo_id,is_metar_half_hourly"
        ),
        "_size": 2000
    }

    station_map = {}

    try:
        async with session.get(BMKG_STATION_URL, headers=headers, params=params, timeout=30) as response:
            response.raise_for_status()

            # Pastikan respon JSON valid
            try:
                data = await response.json()
            except aiohttp.ContentTypeError:
                raise RuntimeError("Respon dari BMKG bukan JSON yang valid.")

            items = data.get("items", [])
            for item in items:
                icao = item.get("station_icao")
                if not icao:
                    continue  # skip jika tidak ada kode ICAO

                # Ambil jam operasi, fallback ke 24 jam jika tidak valid
                op_hours = item.get("station_operating_hours", 24)
                if not isinstance(op_hours, int) or not (0 < op_hours <= 24):
                    op_hours = 24

                station_map[icao] = {
                
                    "stasiun": item.get("station_name", "-"),
                    "wmo_id": str(item.get("station_wmo_id", "-")).strip(),
                    "jam_operasi": op_hours,
                    "sends_half_hourly": bool(item.get("is_metar_half_hourly", False))
                }

        return station_map

    except aiohttp.ClientResponseError as e:
        print(f"HTTP Error saat mengambil data stasiun: {e.status} - {e.message}")
        return {}

    except aiohttp.ClientError as e:
        print(f"Kesalahan koneksi saat mengambil data stasiun: {e}")
        return {}

    except Exception as e:
        print(f"Kesalahan tidak terduga saat mengambil data stasiun: {e}")
        return {}
    
    


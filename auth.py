import aiohttp 
# untuk ambil data dari internet tanpa nunggu satu persatu, 
# jadi prosesnya bisa jalan bareng dan lebih cepat bila ambil data dari banyak endpoint secara paralel


LOGIN_URL = "https://bmkgsatu.bmkg.go.id/db/bmkgsatu/@login"
USERNAME = "aksesdata"
PASSWORD = "@ksesData"

async def get_bmkg_token():
    """
    Login ke BMKG SATU dan mengembalikan JWT token.
    """ # # Fungsi async untuk login ke API BMKG dan ambil token
    
    payload = {"username": USERNAME, "password": PASSWORD} # Data login yang dikirim ke server (isi username & password)
    try:
        async with aiohttp.ClientSession() as session:# Buka sesi koneksi HTTP secara async (tidak nunggu satu-satu)
            async with session.post(LOGIN_URL, json=payload, timeout=10) as response: # Kirim data login ke API dengan metode POST
                # POST = kirim data dari client ke server
                response.raise_for_status() 
                # fungsi ini untuk ngecek status kode HTTP dari response, kalau diantara 200 - 299 artinya sukses, diluar itu artinya eror
                data = await response.json() # jadi kan data dari server berupa string json, kita ubah ke objek python
                return data.get("token") # mengambil nilai dari kunci "token" hasil login
    
    except aiohttp.ClientResponseError as e:  # Kalau server BMKG balas dengan error (misalnya 401, 500, dll)
        raise RuntimeError(f"HTTP Error saat login BMKG: {e.status} - {e.message}")

    except aiohttp.ClientError as e:  # Kalau ada masalah jaringan, koneksi gagal, dll
        raise RuntimeError(f"Kesalahan koneksi ke BMKG: {e}")

    except Exception as e:  # Untuk semua jenis error lain yang tak terduga
        raise RuntimeError(f"Error tidak terduga saat login BMKG: {e}")

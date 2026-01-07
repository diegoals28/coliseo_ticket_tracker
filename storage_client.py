"""
Cliente de almacenamiento usando Supabase Storage.
Maneja la subida y descarga de archivos Excel e históricos.
"""

import os
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de Supabase desde variables de entorno
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
BUCKET_NAME = 'colosseo-files'


def get_supabase_client() -> Client:
    """Obtiene el cliente de Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL y SUPABASE_KEY deben estar configurados")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def ensure_bucket_exists(supabase: Client):
    """Crea el bucket si no existe"""
    try:
        supabase.storage.get_bucket(BUCKET_NAME)
    except:
        supabase.storage.create_bucket(BUCKET_NAME, options={
            'public': False
        })


def upload_file(file_bytes: bytes, filename: str, folder: str = '') -> dict:
    """
    Sube un archivo a Supabase Storage.

    Args:
        file_bytes: Contenido del archivo en bytes
        filename: Nombre del archivo
        folder: Carpeta opcional (ej: 'historico', 'exports')

    Returns:
        dict con 'success', 'path' y 'url' o 'error'
    """
    try:
        supabase = get_supabase_client()
        ensure_bucket_exists(supabase)

        # Construir path
        if folder:
            path = f"{folder}/{filename}"
        else:
            path = filename

        # Subir archivo
        result = supabase.storage.from_(BUCKET_NAME).upload(
            path,
            file_bytes,
            file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        )

        # Obtener URL pública temporal (1 hora)
        url = supabase.storage.from_(BUCKET_NAME).create_signed_url(path, 3600)

        return {
            'success': True,
            'path': path,
            'url': url.get('signedURL', '')
        }

    except ValueError as e:
        return {'success': False, 'error': str(e)}
    except Exception as e:
        return {'success': False, 'error': f"Error subiendo archivo: {str(e)}"}


def download_file(path: str) -> dict:
    """
    Descarga un archivo de Supabase Storage.

    Args:
        path: Ruta del archivo en el bucket

    Returns:
        dict con 'success', 'data' (bytes) o 'error'
    """
    try:
        supabase = get_supabase_client()

        result = supabase.storage.from_(BUCKET_NAME).download(path)

        return {
            'success': True,
            'data': result
        }

    except Exception as e:
        return {'success': False, 'error': f"Error descargando archivo: {str(e)}"}


def list_files(folder: str = '') -> dict:
    """
    Lista archivos en una carpeta.

    Args:
        folder: Carpeta a listar

    Returns:
        dict con 'success', 'files' o 'error'
    """
    try:
        supabase = get_supabase_client()

        result = supabase.storage.from_(BUCKET_NAME).list(folder)

        return {
            'success': True,
            'files': result
        }

    except Exception as e:
        return {'success': False, 'error': f"Error listando archivos: {str(e)}"}


def get_historico_url() -> dict:
    """
    Obtiene URL del archivo histórico actual.

    Returns:
        dict con 'success', 'url' o 'error'
    """
    try:
        supabase = get_supabase_client()

        # Buscar el archivo histórico
        path = 'historico/historico_disponibilidad.xlsx'

        url = supabase.storage.from_(BUCKET_NAME).create_signed_url(path, 3600)

        return {
            'success': True,
            'url': url.get('signedURL', '')
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def is_configured() -> bool:
    """Verifica si Supabase está configurado"""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def get_auto_cookies() -> dict:
    """
    Obtiene las cookies automáticas guardadas por GitHub Actions.

    Returns:
        dict con 'success', 'cookies', 'timestamp' o 'error'
    """
    try:
        if not is_configured():
            return {'success': False, 'error': 'Supabase no configurado'}

        supabase = get_supabase_client()

        # Descargar archivo de cookies
        path = 'cookies/cookies_auto.json'

        try:
            result = supabase.storage.from_(BUCKET_NAME).download(path)

            import json
            data = json.loads(result.decode('utf-8'))

            return {
                'success': True,
                'cookies': data.get('cookies', []),
                'timestamp': data.get('timestamp', ''),
                'source': data.get('source', 'unknown'),
                'proxy': data.get('proxy')  # Incluir proxy si está disponible
            }

        except Exception as e:
            error_msg = str(e)
            if 'not found' in error_msg.lower() or '404' in error_msg:
                return {'success': False, 'error': 'Cookies no encontradas en Supabase. Ejecuta el job de Railway para generarlas.'}
            return {'success': False, 'error': f'Error descargando cookies de Supabase: {error_msg}'}

    except Exception as e:
        return {'success': False, 'error': f'Error conectando con Supabase: {str(e)}'}


def get_cached_availability() -> dict:
    """
    Obtiene la disponibilidad cacheada desde Supabase (consultada por Railway).

    Returns:
        dict con 'success', 'availability', 'timestamp' o 'error'
    """
    try:
        if not is_configured():
            return {'success': False, 'error': 'Supabase no configurado'}

        supabase = get_supabase_client()

        path = 'availability/availability_cache.json'

        try:
            result = supabase.storage.from_(BUCKET_NAME).download(path)

            import json
            data = json.loads(result.decode('utf-8'))

            return {
                'success': True,
                'availability': data.get('availability', {}),
                'timestamp': data.get('timestamp', ''),
                'source': data.get('source', 'unknown')
            }

        except Exception as e:
            return {'success': False, 'error': f'Archivo no encontrado: {str(e)}'}

    except Exception as e:
        return {'success': False, 'error': f'Error obteniendo disponibilidad: {str(e)}'}


def save_auto_cookies(cookies: list) -> dict:
    """
    Guarda cookies en Supabase Storage.

    Args:
        cookies: Lista de cookies

    Returns:
        dict con 'success' o 'error'
    """
    try:
        if not is_configured():
            return {'success': False, 'error': 'Supabase no configurado'}

        import json
        from datetime import datetime

        supabase = get_supabase_client()
        ensure_bucket_exists(supabase)

        cookies_data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "source": "web_app"
        }

        cookies_json = json.dumps(cookies_data, indent=2).encode('utf-8')

        path = 'cookies/cookies_auto.json'

        # Eliminar archivo anterior
        try:
            supabase.storage.from_(BUCKET_NAME).remove([path])
        except:
            pass

        # Subir nuevo archivo
        supabase.storage.from_(BUCKET_NAME).upload(
            path,
            cookies_json,
            file_options={"content-type": "application/json", "upsert": "true"}
        )

        return {'success': True, 'message': 'Cookies guardadas en Supabase'}

    except Exception as e:
        return {'success': False, 'error': f'Error guardando cookies: {str(e)}'}

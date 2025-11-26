"""
Cliente de almacenamiento usando Supabase Storage.
Maneja la subida y descarga de archivos Excel e históricos.
"""

import os
from io import BytesIO
from datetime import datetime
from supabase import create_client, Client

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

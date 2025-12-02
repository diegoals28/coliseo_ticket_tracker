"""
Script para obtener cookies automáticamente del sitio del Colosseo.
Usa ScrapingBee para bypass de anti-bot (Octofence).

Flujo:
1. Usar ScrapingBee para cargar la página con JavaScript rendering
2. Extraer cookies de sesión
3. Guardar en Supabase
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from urllib.parse import urlencode, quote

# Configurar encoding UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


SCRAPINGBEE_API_KEY = os.environ.get('SCRAPINGBEE_API_KEY', '')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

# URL del tour
TOUR_URL = "https://ticketing.colosseo.it/en/eventi/24h-colosseo-foro-romano-palatino-gruppi/"


def fetch_with_scrapingbee(url, wait_time=10000, js_scenario=None):
    """
    Usa ScrapingBee para cargar una página con JavaScript rendering.

    Args:
        url: URL a cargar
        wait_time: Tiempo de espera para JavaScript (ms)
        js_scenario: Escenario de JavaScript a ejecutar

    Returns:
        dict con 'success', 'html', 'cookies' o 'error'
    """
    if not SCRAPINGBEE_API_KEY:
        return {'success': False, 'error': 'SCRAPINGBEE_API_KEY no configurada'}

    print(f"[ScrapingBee] Cargando: {url[:60]}...")

    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'true',
        'premium_proxy': 'true',  # Mejor para sitios con anti-bot
        'country_code': 'it',     # Proxy italiano para sitio italiano
        'wait': wait_time,        # Esperar JS
        'block_resources': 'false',  # No bloquear recursos
        'json_response': 'true',  # Obtener cookies y metadata
    }

    if js_scenario:
        params['js_scenario'] = json.dumps(js_scenario)

    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=300  # 5 minutos
        )

        print(f"[ScrapingBee] Status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                return {
                    'success': True,
                    'html': data.get('body', ''),
                    'cookies': data.get('cookies', {}),
                    'headers': data.get('headers', {}),
                    'status': data.get('status_code', 200)
                }
            except:
                # Respuesta no es JSON, es HTML directo
                return {
                    'success': True,
                    'html': response.text,
                    'cookies': {},
                    'headers': dict(response.headers)
                }
        else:
            error_msg = response.text[:500] if response.text else f"HTTP {response.status_code}"
            print(f"[ScrapingBee] Error: {error_msg}")
            return {'success': False, 'error': error_msg}

    except Exception as e:
        print(f"[ScrapingBee] Exception: {e}")
        return {'success': False, 'error': str(e)}


def extract_cookies_from_page():
    """
    Extrae cookies del sitio usando ScrapingBee.
    Primero intenta carga simple, luego con interacción.
    """
    print("\n[Step 1] Cargando página inicial (sin JS scenario)...")

    # Primero intentar sin js_scenario para ver si pasa Octofence
    result = fetch_with_scrapingbee(TOUR_URL, wait_time=10000)

    if not result['success']:
        print(f"[Error] {result.get('error', 'Unknown error')}")
        return None

    html = result.get('html', '')
    cookies = result.get('cookies', {})

    print(f"[Result] HTML length: {len(html)} chars")
    print(f"[Result] Cookies: {len(cookies)}")

    # Debug: verificar contenido
    html_lower = html.lower()
    indicators = {
        'calendar': 'calendar' in html_lower or 'datepicker' in html_lower,
        'tariff': 'tariff' in html_lower,
        'slot': 'slot' in html_lower,
        'octofence': 'octofence' in html_lower or 'waiting' in html_lower[:2000]
    }

    print(f"[Debug] Indicadores: {indicators}")

    if indicators['octofence'] and not indicators['calendar']:
        print("[Warning] Posible bloqueo de Octofence")

    if cookies:
        print(f"[Success] Cookies obtenidas: {list(cookies.keys())}")
        cookies_list = [
            {'name': k, 'value': v, 'domain': '.colosseo.it'}
            for k, v in cookies.items()
        ]
        return cookies_list

    print("[Info] No se encontraron cookies en respuesta")
    return None


def fetch_simple_page():
    """
    Método más simple: sin premium_proxy, solo stealth_proxy.
    """
    print("\n[Simple] Cargando página con stealth proxy...")

    # Intentar con stealth_proxy en lugar de premium_proxy
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': TOUR_URL,
        'render_js': 'true',
        'stealth_proxy': 'true',  # Alternativa a premium
        'wait': 15000,
        'block_resources': 'false',
        'json_response': 'true',
    }

    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=300
        )

        print(f"[Simple] Status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                html = data.get('body', '')
                cookies = data.get('cookies', {})

                # Guardar HTML para debug
                try:
                    with open('debug_scrapingbee.html', 'w', encoding='utf-8') as f:
                        f.write(html)
                    print("[Debug] HTML guardado")
                except:
                    pass

                print(f"[Simple] HTML: {len(html)} chars, Cookies: {len(cookies)}")

                if cookies:
                    cookies_list = [
                        {'name': k, 'value': v, 'domain': '.colosseo.it'}
                        for k, v in cookies.items()
                    ]
                    return cookies_list

            except:
                pass

        else:
            print(f"[Simple] Error: {response.text[:300]}")

    except Exception as e:
        print(f"[Simple] Exception: {e}")

    return None


def fetch_basic_page():
    """
    Método básico: sin proxies especiales, solo render_js.
    """
    print("\n[Basic] Cargando página sin proxies especiales...")

    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': TOUR_URL,
        'render_js': 'true',
        'wait': 8000,
        'json_response': 'true',
    }

    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=180
        )

        print(f"[Basic] Status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                html = data.get('body', '')
                cookies = data.get('cookies', {})

                print(f"[Basic] HTML: {len(html)} chars, Cookies: {len(cookies)}")

                # Verificar si pasó Octofence
                html_lower = html.lower()
                if 'tariff' in html_lower or 'calendar' in html_lower:
                    print("[Basic] Contenido real detectado!")

                if cookies:
                    cookies_list = [
                        {'name': k, 'value': v, 'domain': '.colosseo.it'}
                        for k, v in cookies.items()
                    ]
                    return cookies_list

            except:
                pass

        else:
            print(f"[Basic] Error: {response.text[:200]}")

    except Exception as e:
        print(f"[Basic] Exception: {e}")

    return None


def fetch_simple_page_old():
    """
    Método legacy.
    """
    print("\n[Legacy] Cargando...")

    result = fetch_with_scrapingbee(TOUR_URL, wait_time=15000)

    if not result['success']:
        print(f"[Error] {result.get('error', 'Unknown error')}")
        return None

    cookies = result.get('cookies', {})
    html = result.get('html', '')

    print(f"[Simple] HTML: {len(html)} chars, Cookies: {len(cookies)}")

    # Guardar HTML para debug
    try:
        with open('debug_scrapingbee.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("[Debug] HTML guardado en debug_scrapingbee.html")
    except:
        pass

    if cookies:
        cookies_list = [
            {'name': k, 'value': v, 'domain': '.colosseo.it'}
            for k, v in cookies.items()
        ]
        return cookies_list

    return None


def save_cookies_to_supabase(cookies):
    """Guarda las cookies en Supabase Storage"""
    from supabase import create_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[Supabase] ERROR: Variables no configuradas")
        return False

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        cookies_data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "source": "scrapingbee"
        }

        cookies_json = json.dumps(cookies_data, indent=2).encode('utf-8')

        bucket_name = 'colosseo-files'
        file_path = 'cookies/cookies_auto.json'

        # Crear bucket si no existe
        try:
            supabase.storage.get_bucket(bucket_name)
        except:
            try:
                supabase.storage.create_bucket(bucket_name, options={'public': False})
            except:
                pass

        # Eliminar archivo anterior
        try:
            supabase.storage.from_(bucket_name).remove([file_path])
        except:
            pass

        # Subir nuevo archivo
        supabase.storage.from_(bucket_name).upload(
            file_path,
            cookies_json,
            file_options={"content-type": "application/json", "upsert": "true"}
        )

        print(f"[Supabase] Cookies guardadas exitosamente")
        return True

    except Exception as e:
        print(f"[Supabase] Error: {e}")
        return False


def save_cookies_local(cookies, filename="cookies_colosseo.json"):
    """Guarda cookies en archivo local"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2)
        print(f"[Local] Cookies guardadas en {filename}")
        return True
    except Exception as e:
        print(f"[Local] Error: {e}")
        return False


def main():
    """Función principal"""
    print("=" * 60)
    print("COLOSSEO AUTO-COOKIES (ScrapingBee)")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    if not SCRAPINGBEE_API_KEY:
        print("[ERROR] SCRAPINGBEE_API_KEY no está configurada")
        return 1

    print(f"[Config] API Key: {SCRAPINGBEE_API_KEY[:10]}...")

    cookies = None

    # Método 1: Básico sin proxies especiales
    print("\n" + "=" * 40)
    print("Método 1: Básico")
    print("=" * 40)
    cookies = fetch_basic_page()

    # Método 2: Con stealth proxy
    if not cookies:
        print("\n" + "=" * 40)
        print("Método 2: Stealth Proxy")
        print("=" * 40)
        cookies = fetch_simple_page()

    # Método 3: Con premium proxy
    if not cookies:
        print("\n" + "=" * 40)
        print("Método 3: Premium Proxy")
        print("=" * 40)
        cookies = extract_cookies_from_page()

    # Guardar cookies si se obtuvieron
    if cookies and len(cookies) > 0:
        print(f"\n[SUCCESS] Cookies obtenidas: {len(cookies)}")
        for c in cookies:
            print(f"  - {c.get('name', 'unknown')}")

        if SUPABASE_URL:
            save_cookies_to_supabase(cookies)
        save_cookies_local(cookies)

        print("\n" + "=" * 60)
        print("RESULTADO: EXITO")
        print(f"Cookies obtenidas: {len(cookies)}")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("RESULTADO: FALLO")
        print("No se pudieron obtener cookies")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

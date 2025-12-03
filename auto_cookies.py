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

# URLs
TOUR_URL = "https://ticketing.colosseo.it/en/eventi/24h-colosseo-foro-romano-palatino-gruppi/"
CART_URL = "https://ticketing.colosseo.it/en/cart/"
BASE_URL = "https://ticketing.colosseo.it"


def fetch_with_scrapingbee(url, wait_time=10000, js_scenario=None, custom_cookies=None, session_id=None):
    """
    Usa ScrapingBee para cargar una página con JavaScript rendering.

    Args:
        url: URL a cargar
        wait_time: Tiempo de espera para JavaScript (ms)
        js_scenario: Escenario de JavaScript a ejecutar
        custom_cookies: Cookies a enviar con la peticion
        session_id: ID de sesion para mantener cookies entre peticiones

    Returns:
        dict con 'success', 'html', 'cookies', 'headers' o 'error'
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

    # Mantener sesion entre peticiones
    if session_id:
        params['session_id'] = session_id

    if js_scenario:
        params['js_scenario'] = json.dumps(js_scenario)

    # Headers personalizados
    headers = {}
    if custom_cookies:
        cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in custom_cookies])
        headers['Spb-Cookie'] = cookie_str
        params['forward_headers'] = 'true'

    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            headers=headers if headers else None,
            timeout=300  # 5 minutos
        )

        print(f"[ScrapingBee] Status: {response.status_code}")

        # Capturar cookies de headers de respuesta (prefijo Spb-)
        response_cookies = {}
        for header_name, header_value in response.headers.items():
            if header_name.lower().startswith('spb-set-cookie'):
                # Parsear Set-Cookie header
                cookie_parts = header_value.split(';')[0].split('=', 1)
                if len(cookie_parts) == 2:
                    response_cookies[cookie_parts[0].strip()] = cookie_parts[1].strip()

        if response.status_code == 200:
            try:
                data = response.json()

                # Combinar cookies del body JSON con las de headers
                body_cookies = data.get('cookies', {})
                all_cookies = {**body_cookies, **response_cookies} if isinstance(body_cookies, dict) else body_cookies

                # Debug: mostrar headers de respuesta
                print(f"[ScrapingBee] Response headers con Spb-: {[h for h in response.headers.keys() if 'spb' in h.lower()]}")

                return {
                    'success': True,
                    'html': data.get('body', ''),
                    'cookies': all_cookies,
                    'headers': data.get('headers', {}),
                    'status': data.get('status_code', 200),
                    'response_headers': dict(response.headers)
                }
            except:
                # Respuesta no es JSON, es HTML directo
                return {
                    'success': True,
                    'html': response.text,
                    'cookies': response_cookies,
                    'headers': dict(response.headers),
                    'response_headers': dict(response.headers)
                }
        else:
            error_msg = response.text[:500] if response.text else f"HTTP {response.status_code}"
            print(f"[ScrapingBee] Error: {error_msg}")
            return {'success': False, 'error': error_msg}

    except Exception as e:
        print(f"[ScrapingBee] Exception: {e}")
        return {'success': False, 'error': str(e)}


def extract_cookies_with_cart_flow():
    """
    Extrae cookies completando el flujo de reserva con un solo evaluate
    que ejecuta todo el flujo de una vez.
    """
    print("\n[Flow] Ejecutando flujo completo de reserva...")

    # Un solo evaluate que hace todo el flujo secuencialmente
    js_scenario = {
        "instructions": [
            {"wait": 5000},
            # Ejecutar todo el flujo en un solo script
            {"evaluate": """
                (async function() {
                    // Click en día disponible
                    const day = document.querySelector('.ui-datepicker-calendar td:not(.ui-datepicker-unselectable) a');
                    if (day) day.click();
                    await new Promise(r => setTimeout(r, 3000));

                    // Click en horario
                    const slot = document.querySelector('input[name="slot"]');
                    if (slot) slot.click();
                    await new Promise(r => setTimeout(r, 2000));

                    // Click en + dos veces
                    const plus = document.querySelector('button[data-dir="up"]');
                    if (plus) { plus.click(); await new Promise(r => setTimeout(r, 500)); plus.click(); }
                    await new Promise(r => setTimeout(r, 2000));

                    // Submit
                    const submit = document.querySelector('button[type="submit"]');
                    if (submit) submit.click();
                    await new Promise(r => setTimeout(r, 5000));

                    return 'done';
                })();
            """},
            {"wait": 3000},
        ]
    }

    result = fetch_with_scrapingbee(TOUR_URL, wait_time=8000, js_scenario=js_scenario)

    if not result['success']:
        print(f"[Error] {result.get('error', 'Unknown error')}")
        return None

    html = result.get('html', '')
    cookies = result.get('cookies', {})

    print(f"[Result] HTML length: {len(html)} chars")
    print(f"[Result] Cookies: {len(cookies)}")

    # Verificar si tenemos las cookies críticas
    cookie_names = list(cookies.keys()) if isinstance(cookies, dict) else [c.get('name', '') for c in cookies]
    critical_cookies = ['octofence-waap-id', 'octofence-waap-sessid', 'PHPSESSID']
    has_critical = any(c in str(cookie_names) for c in critical_cookies)

    print(f"[Debug] Cookie names: {cookie_names}")
    print(f"[Debug] Has critical cookies: {has_critical}")

    if cookies:
        if isinstance(cookies, dict):
            cookies_list = [
                {'name': k, 'value': v, 'domain': '.colosseo.it'}
                for k, v in cookies.items()
            ]
        else:
            cookies_list = cookies
        return cookies_list

    return None


def extract_cookies_from_page():
    """
    Extrae cookies del sitio usando ScrapingBee.
    Primero intenta con flujo de carrito, luego simple.
    """
    print("\n[Step 1] Intentando flujo con carrito...")

    # Primero intentar con el flujo completo de carrito
    cookies = extract_cookies_with_cart_flow()
    if cookies and len(cookies) >= 10:
        return cookies

    print("\n[Step 2] Flujo de carrito no obtuvo suficientes cookies, intentando carga simple...")
    result = fetch_with_scrapingbee(TOUR_URL, wait_time=15000)

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
        # Convertir a lista si es diccionario
        if isinstance(cookies, dict):
            print(f"[Success] Cookies obtenidas: {list(cookies.keys())}")
            cookies_list = [
                {'name': k, 'value': v, 'domain': '.colosseo.it'}
                for k, v in cookies.items()
            ]
            return cookies_list
        elif isinstance(cookies, list):
            print(f"[Success] Cookies obtenidas: {len(cookies)}")
            return cookies

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


def extract_with_session_flow():
    """
    Usa una sesion de ScrapingBee para mantener cookies entre peticiones.
    Esto simula mejor el comportamiento de un usuario real.
    """
    import random

    print("\n[Session] Iniciando flujo con sesion persistente...")

    # Generar ID de sesion unico (debe ser entero para ScrapingBee)
    session_id = random.randint(100000, 999999)
    print(f"[Session] ID: {session_id}")

    all_cookies = {}

    # Paso 1: Visitar la pagina principal para obtener cookies iniciales
    print("\n[Session] Paso 1: Visitando pagina principal...")
    result1 = fetch_with_scrapingbee(
        BASE_URL,
        wait_time=8000,
        session_id=session_id
    )

    if result1['success']:
        cookies1 = result1.get('cookies', {})
        if isinstance(cookies1, dict):
            all_cookies.update(cookies1)
        print(f"[Session] Cookies paso 1: {len(cookies1) if isinstance(cookies1, dict) else 'N/A'}")

        # Verificar si pasamos Octofence
        html = result1.get('html', '')
        if 'waiting' in html.lower()[:2000] or 'block' in result1.get('html', '').lower()[:500]:
            print("[Session] Octofence detectado, esperando...")
            time.sleep(5)

    # Paso 2: Visitar el carrito para iniciar sesion PHP
    print("\n[Session] Paso 2: Visitando carrito...")
    result2 = fetch_with_scrapingbee(
        CART_URL,
        wait_time=10000,
        session_id=session_id
    )

    if result2['success']:
        cookies2 = result2.get('cookies', {})
        if isinstance(cookies2, dict):
            all_cookies.update(cookies2)
        print(f"[Session] Cookies paso 2: {len(cookies2) if isinstance(cookies2, dict) else 'N/A'}")

        # Debug: mostrar headers
        headers2 = result2.get('headers', {})
        print(f"[Session] Headers del servidor: {list(headers2.keys())[:10]}")

    # Paso 3: Visitar la pagina del tour con JS scenario
    print("\n[Session] Paso 3: Visitando tour con interaccion...")
    js_scenario = {
        "instructions": [
            {"wait": 3000},
            {"evaluate": """
                // Aceptar cookies
                var acceptBtn = document.querySelector('[data-cli_action="accept_all"], .cli-accept-all-btn, #cookie_action_close_header');
                if (acceptBtn) acceptBtn.click();
            """},
            {"wait": 2000},
            {"evaluate": """
                // Click en dia disponible
                var day = document.querySelector('.ui-datepicker-calendar td:not(.ui-datepicker-unselectable) a');
                if (day) {
                    day.click();
                    return 'Day clicked: ' + day.textContent;
                }
                return 'No day found';
            """},
            {"wait": 4000},
            {"evaluate": """
                // Click en horario
                var slot = document.querySelector('input[name="slot"]');
                if (slot) {
                    slot.click();
                    return 'Slot clicked';
                }
                return 'No slot found';
            """},
            {"wait": 3000},
            {"evaluate": """
                // Incrementar cantidad
                var plus = document.querySelector('button[data-dir="up"]');
                if (plus) {
                    plus.click();
                    return 'Quantity incremented';
                }
                return 'No plus button';
            """},
            {"wait": 2000},
            {"evaluate": """
                // Obtener cookies del documento
                return document.cookie;
            """},
            {"wait": 2000}
        ]
    }

    result3 = fetch_with_scrapingbee(
        TOUR_URL,
        wait_time=15000,
        js_scenario=js_scenario,
        session_id=session_id
    )

    if result3['success']:
        cookies3 = result3.get('cookies', {})
        if isinstance(cookies3, dict):
            all_cookies.update(cookies3)
        print(f"[Session] Cookies paso 3: {len(cookies3) if isinstance(cookies3, dict) else 'N/A'}")

        # Verificar contenido
        html = result3.get('html', '')
        indicators = {
            'calendar': 'datepicker' in html.lower(),
            'tariff': 'tariff' in html.lower(),
            'cart_ref': 'cart' in html.lower()
        }
        print(f"[Session] Indicadores pagina: {indicators}")

    # Paso 4: Volver al carrito para capturar cookies de sesion
    print("\n[Session] Paso 4: Volviendo al carrito...")
    result4 = fetch_with_scrapingbee(
        CART_URL,
        wait_time=8000,
        session_id=session_id
    )

    if result4['success']:
        cookies4 = result4.get('cookies', {})
        if isinstance(cookies4, dict):
            all_cookies.update(cookies4)
        print(f"[Session] Cookies paso 4: {len(cookies4) if isinstance(cookies4, dict) else 'N/A'}")

    # Mostrar todas las cookies recolectadas
    print(f"\n[Session] Total cookies recolectadas: {len(all_cookies)}")
    for name in all_cookies.keys():
        print(f"  - {name}")

    # Verificar cookies criticas
    critical = ['PHPSESSID', 'octofence-waap-id', 'octofence-waap-sessid']
    has_critical = any(c in all_cookies for c in critical)
    print(f"[Session] Tiene cookies criticas: {has_critical}")

    if all_cookies:
        cookies_list = [
            {'name': k, 'value': v, 'domain': '.colosseo.it'}
            for k, v in all_cookies.items()
        ]
        return cookies_list

    return None


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

    # Método 0: Flujo con sesion persistente (NUEVO)
    print("\n" + "=" * 40)
    print("Método 0: Sesion Persistente")
    print("=" * 40)
    cookies = extract_with_session_flow()

    # Verificar cookies criticas
    if cookies:
        cookie_names = [c.get('name', '') for c in cookies]
        critical = ['PHPSESSID', 'octofence-waap-id', 'octofence-waap-sessid']
        has_critical = any(c in cookie_names for c in critical)
        if not has_critical:
            print(f"[Warning] Faltan cookies criticas, intentando otro metodo...")
            cookies = None

    # Método 1: Flujo completo con carrito (premium proxy)
    if not cookies:
        print("\n" + "=" * 40)
        print("Método 1: Flujo con carrito (Premium)")
        print("=" * 40)
        cookies = extract_cookies_from_page()

        # Verificar si tenemos las cookies críticas
        if cookies:
            cookie_names = [c.get('name', '') for c in cookies]
            has_critical = any('octofence-waap' in str(cookie_names) or 'PHPSESSID' in str(cookie_names) for _ in [1])
            if not has_critical and len(cookies) < 10:
                print(f"[Warning] Solo {len(cookies)} cookies, faltan cookies críticas")
                cookies = None

    # Método 2: Stealth proxy con carrito
    if not cookies:
        print("\n" + "=" * 40)
        print("Método 2: Stealth Proxy")
        print("=" * 40)
        cookies = fetch_simple_page()

    # Método 3: Básico
    if not cookies:
        print("\n" + "=" * 40)
        print("Método 3: Básico")
        print("=" * 40)
        cookies = fetch_basic_page()

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

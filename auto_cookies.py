"""
Script para obtener cookies automáticamente del sitio del Colosseo.
Diseñado para ejecutarse en GitHub Actions con soporte de proxy.
"""

import os
import sys
import json
import time
import random
from datetime import datetime

# Configurar encoding UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_proxy_config():
    """Obtiene configuración de proxy desde variables de entorno"""
    proxy_list = os.environ.get('PROXY_LIST', '')
    if proxy_list:
        proxies = [p.strip() for p in proxy_list.split(',') if p.strip()]
        if proxies:
            # Seleccionar proxy aleatorio
            proxy = random.choice(proxies)
            print(f"[Proxy] Usando: {proxy[:40]}...")
            return proxy
    return None


def setup_driver_with_proxy(proxy=None):
    """Configura el driver de Chrome con proxy y anti-detección"""

    # Intentar undetected-chromedriver primero
    try:
        import undetected_chromedriver as uc

        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")

        if proxy:
            proxy_clean = proxy.replace("http://", "").replace("https://", "")
            options.add_argument(f"--proxy-server=http://{proxy_clean}")

        driver = uc.Chrome(options=options, version_main=None)
        print("[Driver] undetected-chromedriver iniciado")
        return driver

    except ImportError:
        print("[Driver] undetected-chromedriver no disponible, usando Selenium")
    except Exception as e:
        print(f"[Driver] Error con undetected-chromedriver: {e}")

    # Fallback a Selenium estándar
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # User agent realista
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    if proxy:
        proxy_clean = proxy.replace("http://", "").replace("https://", "")
        options.add_argument(f"--proxy-server=http://{proxy_clean}")

    driver = webdriver.Chrome(options=options)

    # Inyectar scripts anti-detección
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.navigator.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """
    })

    print("[Driver] Selenium Chrome iniciado")
    return driver


def wait_for_page_load(driver, timeout=180):
    """
    Espera a que la página cargue correctamente, pasando Octofence.

    Returns:
        True si la página cargó exitosamente, False si fue bloqueada
    """
    print(f"[Wait] Esperando carga de página (timeout: {timeout}s)...")

    start_time = time.time()
    check_interval = 5

    while time.time() - start_time < timeout:
        try:
            title = driver.title.lower()
            url = driver.current_url.lower()
            page_source = driver.page_source.lower()[:5000]  # Solo primeros 5000 chars

            # Detectar bloqueo
            if "automation" in page_source and "detected" in page_source:
                print("[Wait] BLOQUEADO: Automatización detectada")
                return False

            if "blocked" in page_source and "access" in page_source:
                print("[Wait] BLOQUEADO: Acceso denegado")
                return False

            # Detectar página de espera Octofence
            if "waiting" in title or "octofence" in page_source:
                elapsed = int(time.time() - start_time)
                print(f"[Wait] Octofence verificando... ({elapsed}s)")
                time.sleep(check_interval)
                continue

            # Detectar página exitosa
            if "colosseo" in title or "colosseo" in url:
                if "eventi" in page_source or "biglietti" in page_source or "ticket" in page_source:
                    print("[Wait] Pagina cargada exitosamente!")
                    return True

            # Esperar antes del siguiente check
            time.sleep(check_interval)

        except Exception as e:
            print(f"[Wait] Error durante espera: {e}")
            time.sleep(check_interval)

    print(f"[Wait] Timeout alcanzado ({timeout}s)")
    return False


def wait_for_cookies(driver, timeout=30):
    """
    Espera a que se generen cookies en el navegador.

    Returns:
        Lista de cookies o lista vacía
    """
    print(f"[Cookies] Esperando generación de cookies...")

    start_time = time.time()

    while time.time() - start_time < timeout:
        cookies = driver.get_cookies()
        if cookies and len(cookies) > 0:
            print(f"[Cookies] Encontradas {len(cookies)} cookies")
            return cookies

        # Hacer scroll para activar JavaScript
        try:
            driver.execute_script("window.scrollBy(0, 300);")
        except:
            pass

        time.sleep(2)

    print("[Cookies] No se generaron cookies en el tiempo esperado")
    return []


def extract_cookies(driver):
    """Extrae cookies del navegador"""
    cookies = driver.get_cookies()
    print(f"[Cookies] Extraídas {len(cookies)} cookies")
    return cookies


def save_cookies_to_supabase(cookies):
    """Guarda las cookies en Supabase Storage"""
    from supabase import create_client

    supabase_url = os.environ.get('SUPABASE_URL', '')
    supabase_key = os.environ.get('SUPABASE_KEY', '')

    if not supabase_url or not supabase_key:
        print("[Supabase] ERROR: Variables SUPABASE_URL y SUPABASE_KEY no configuradas")
        return False

    try:
        supabase = create_client(supabase_url, supabase_key)

        # Crear contenido JSON con timestamp
        cookies_data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "source": "github_actions"
        }

        cookies_json = json.dumps(cookies_data, indent=2).encode('utf-8')

        # Subir a Supabase Storage
        bucket_name = 'colosseo-files'
        file_path = 'cookies/cookies_auto.json'

        # Intentar crear bucket si no existe
        try:
            supabase.storage.get_bucket(bucket_name)
        except:
            try:
                supabase.storage.create_bucket(bucket_name, options={'public': False})
            except:
                pass

        # Eliminar archivo anterior si existe
        try:
            supabase.storage.from_(bucket_name).remove([file_path])
        except:
            pass

        # Subir nuevo archivo
        result = supabase.storage.from_(bucket_name).upload(
            file_path,
            cookies_json,
            file_options={"content-type": "application/json", "upsert": "true"}
        )

        print(f"[Supabase] Cookies guardadas exitosamente en {file_path}")
        return True

    except Exception as e:
        print(f"[Supabase] Error guardando cookies: {e}")
        return False


def save_cookies_local(cookies, filename="cookies_colosseo.json"):
    """Guarda cookies en archivo local (fallback)"""
    try:
        cookies_data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "source": "auto_script"
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cookies_data, f, indent=2)

        print(f"[Local] Cookies guardadas en {filename}")
        return True
    except Exception as e:
        print(f"[Local] Error guardando cookies: {e}")
        return False


def main():
    """Función principal"""
    print("=" * 60)
    print("COLOSSEO AUTO-COOKIES")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    # URLs a intentar
    urls = [
        "https://ticketing.colosseo.it/en/eventi/24h-colosseo-foro-romano-palatino-gruppi/",
        "https://ticketing.colosseo.it/",
    ]

    # Obtener proxy
    proxy = get_proxy_config()

    # Inicializar driver
    driver = None
    success = False
    cookies = []

    try:
        driver = setup_driver_with_proxy(proxy)

        for url in urls:
            print(f"\n[Navigate] Intentando: {url}")

            try:
                driver.get(url)

                # Simular comportamiento humano
                time.sleep(random.uniform(3, 5))

                # Esperar a que pase Octofence
                if wait_for_page_load(driver, timeout=180):
                    # Esperar un poco más para que JS genere cookies
                    print("[Wait] Esperando generación de cookies por JavaScript...")
                    time.sleep(5)

                    # Hacer algunas interacciones para activar cookies
                    try:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                        time.sleep(2)
                        driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(2)
                    except:
                        pass

                    # Esperar y extraer cookies
                    cookies = wait_for_cookies(driver, timeout=30)

                    if not cookies:
                        # Intentar extraer directamente
                        cookies = extract_cookies(driver)

                    if cookies and len(cookies) > 0:
                        success = True
                        print(f"[Success] Cookies obtenidas: {len(cookies)}")

                        # Mostrar nombres de cookies para debug
                        cookie_names = [c.get('name', 'unknown') for c in cookies]
                        print(f"[Debug] Cookies: {', '.join(cookie_names[:10])}")
                        break
                    else:
                        print("[Warning] Página cargada pero sin cookies útiles")

                        # Debug: mostrar info de la página
                        print(f"[Debug] URL actual: {driver.current_url}")
                        print(f"[Debug] Título: {driver.title}")
                else:
                    print(f"[Failed] No se pudo cargar: {url}")

            except Exception as e:
                print(f"[Error] Error navegando a {url}: {e}")
                continue

    except Exception as e:
        print(f"[Fatal] Error crítico: {e}")

    finally:
        if driver:
            try:
                driver.quit()
                print("[Driver] Cerrado correctamente")
            except:
                pass

    # Guardar cookies si se obtuvieron
    if success and cookies:
        # Intentar guardar en Supabase
        if os.environ.get('SUPABASE_URL'):
            save_cookies_to_supabase(cookies)

        # También guardar local como backup
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

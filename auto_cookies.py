"""
Script para obtener cookies automáticamente del sitio del Colosseo.
Diseñado para ejecutarse en GitHub Actions con soporte de proxy.
Simula agregar un ticket al carrito y luego eliminarlo para generar cookies de sesión.
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
            proxy = random.choice(proxies)
            print(f"[Proxy] Usando: {proxy[:40]}...")
            return proxy
    return None


def setup_driver_with_proxy(proxy=None):
    """Configura el driver de Chrome con proxy y anti-detección"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    if proxy:
        proxy_clean = proxy.replace("http://", "").replace("https://", "")
        options.add_argument(f"--proxy-server=http://{proxy_clean}")

    driver = webdriver.Chrome(options=options)

    # Scripts anti-detección
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.navigator.chrome = {runtime: {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """
    })

    print("[Driver] Chrome iniciado")
    return driver


def wait_for_page_load(driver, timeout=180):
    """Espera a que la página cargue, pasando Octofence"""
    print(f"[Wait] Esperando carga de página (timeout: {timeout}s)...")

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            title = driver.title.lower()
            url = driver.current_url.lower()
            page_source = driver.page_source.lower()[:5000]

            # Detectar bloqueo
            if "automation" in page_source and "detected" in page_source:
                print("[Wait] BLOQUEADO: Automatización detectada")
                return False

            # Detectar página de espera Octofence
            if "waiting" in title or "octofence" in page_source:
                elapsed = int(time.time() - start_time)
                print(f"[Wait] Octofence verificando... ({elapsed}s)")
                time.sleep(5)
                continue

            # Detectar página exitosa
            if "colosseo" in title or "colosseo" in url:
                if "eventi" in page_source or "biglietti" in page_source or "ticket" in page_source:
                    print("[Wait] Página cargada exitosamente!")
                    return True

            time.sleep(5)

        except Exception as e:
            print(f"[Wait] Error: {e}")
            time.sleep(5)

    print(f"[Wait] Timeout alcanzado ({timeout}s)")
    return False


def simulate_add_to_cart(driver):
    """
    Simula el proceso de agregar al carrito y eliminar para generar cookies.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print("[Cart] Iniciando simulación de carrito...")

    try:
        # Esperar a que cargue el calendario
        print("[Cart] Esperando calendario...")
        time.sleep(5)

        # Buscar y hacer clic en una fecha disponible del calendario
        try:
            # Buscar días disponibles (generalmente tienen clase específica)
            available_days = driver.find_elements(By.CSS_SELECTOR, ".calendar-day.available, .day-available, td.available, .fc-day:not(.fc-day-disabled)")

            if not available_days:
                # Intentar encontrar cualquier día clickeable
                available_days = driver.find_elements(By.CSS_SELECTOR, "[data-date], .calendar td[class*='avail']")

            if available_days:
                # Hacer clic en el primer día disponible
                day = available_days[0]
                print(f"[Cart] Encontrado día disponible, haciendo clic...")
                driver.execute_script("arguments[0].click();", day)
                time.sleep(3)
            else:
                print("[Cart] No se encontraron días disponibles en el calendario")
        except Exception as e:
            print(f"[Cart] Error buscando calendario: {e}")

        # Buscar botón de agregar al carrito
        print("[Cart] Buscando botón de agregar...")
        add_buttons = driver.find_elements(By.CSS_SELECTOR,
            "button[class*='add'], button[class*='cart'], .add-to-cart, .btn-add, "
            "input[type='submit'][value*='Add'], button[type='submit'], "
            "[class*='aggiungi'], [class*='prenota']"
        )

        if add_buttons:
            print(f"[Cart] Encontrados {len(add_buttons)} botones, intentando clic...")
            for btn in add_buttons[:3]:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    break
                except:
                    continue

        # Esperar un momento para que se generen las cookies
        print("[Cart] Esperando generación de cookies de sesión...")
        time.sleep(5)

        # Hacer scroll y otras interacciones
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Extraer cookies
        cookies = driver.get_cookies()
        print(f"[Cart] Cookies obtenidas: {len(cookies)}")

        # Mostrar las cookies encontradas
        if cookies:
            cookie_names = [c.get('name', '') for c in cookies]
            print(f"[Cart] Nombres: {', '.join(cookie_names)}")

        # Intentar limpiar el carrito (opcional, para no dejar items)
        try:
            remove_buttons = driver.find_elements(By.CSS_SELECTOR,
                ".remove, .delete, [class*='remove'], [class*='delete'], .cart-remove"
            )
            for btn in remove_buttons[:1]:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
        except:
            pass

        return cookies

    except Exception as e:
        print(f"[Cart] Error en simulación: {e}")
        # Aún así intentar obtener cookies
        return driver.get_cookies()


def save_cookies_to_supabase(cookies):
    """Guarda las cookies en Supabase Storage"""
    from supabase import create_client

    supabase_url = os.environ.get('SUPABASE_URL', '')
    supabase_key = os.environ.get('SUPABASE_KEY', '')

    if not supabase_url or not supabase_key:
        print("[Supabase] ERROR: Variables no configuradas")
        return False

    try:
        supabase = create_client(supabase_url, supabase_key)

        cookies_data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "source": "github_actions"
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
    print("COLOSSEO AUTO-COOKIES")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    proxy = get_proxy_config()
    driver = None
    success = False
    cookies = []

    try:
        driver = setup_driver_with_proxy(proxy)

        # Navegar a la página del tour
        tour_url = "https://ticketing.colosseo.it/en/eventi/24h-colosseo-foro-romano-palatino-gruppi/"
        print(f"\n[Navigate] Abriendo: {tour_url}")

        driver.get(tour_url)
        time.sleep(random.uniform(3, 5))

        # Esperar a que pase Octofence
        if not wait_for_page_load(driver, timeout=180):
            print("[Failed] No se pudo pasar Octofence")
        else:
            print("[Success] Página del tour cargada")
            time.sleep(3)

            # Simular agregar al carrito para generar cookies
            cookies = simulate_add_to_cart(driver)

            if cookies and len(cookies) > 0:
                success = True
                print(f"\n[Success] Cookies obtenidas: {len(cookies)}")

    except Exception as e:
        print(f"[Fatal] Error crítico: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            try:
                driver.quit()
                print("[Driver] Cerrado")
            except:
                pass

    # Guardar cookies
    if success and cookies:
        if os.environ.get('SUPABASE_URL'):
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

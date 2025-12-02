"""
Script para obtener cookies automáticamente del sitio del Colosseo.
Diseñado para ejecutarse en GitHub Actions con soporte de proxy.

Flujo:
1. Entrar al sitio y pasar Octofence
2. Seleccionar un día en el calendario
3. Seleccionar un horario
4. Incrementar cantidad con botón +
5. Agregar al carrito
6. Extraer cookies de sesión
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


def wait_for_element(driver, selectors, timeout=15, description="elemento"):
    """Espera a que aparezca un elemento"""
    from selenium.webdriver.common.by import By

    print(f"[Wait] Buscando {description}...")
    start = time.time()

    while time.time() - start < timeout:
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    print(f"  Encontrado con '{selector}' ({len(visible)} visibles)")
                    return visible
            except:
                continue
        time.sleep(1)

    print(f"  No encontrado después de {timeout}s")
    return []


def debug_page(driver, step_name):
    """Muestra información de debug de la página actual"""
    print(f"\n[Debug {step_name}]")
    print(f"  URL: {driver.current_url}")
    print(f"  Title: {driver.title}")
    cookies = driver.get_cookies()
    print(f"  Cookies: {len(cookies)}")
    if cookies:
        names = [c.get('name', '')[:20] for c in cookies[:5]]
        print(f"  Cookie names: {names}")

    # Mostrar elementos clave encontrados
    from selenium.webdriver.common.by import By
    try:
        tariffs = driver.find_elements(By.CSS_SELECTOR, ".tariff-option")
        print(f"  Tarifas encontradas: {len(tariffs)}")
        calendars = driver.find_elements(By.CSS_SELECTOR, "[class*='calendar'], .fc-view")
        print(f"  Calendarios encontrados: {len(calendars)}")
    except:
        pass


def complete_booking_flow(driver):
    """
    Completa el flujo de reserva para generar cookies de sesión.
    Basado en la estructura real del sitio:
    - .tariff-option para tarifas
    - button[data-dir="up"] para incrementar
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains

    print("\n[Flow] Iniciando flujo de reserva...")

    try:
        # Esperar a que cargue el contenido dinámico
        print("\n[Step 0] Esperando carga de contenido dinámico...")
        time.sleep(8)

        # Scroll para cargar contenido lazy
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        debug_page(driver, "inicial")

        # ============ PASO 1: Buscar y clickear en el calendario ============
        print("\n[Step 1] Buscando calendario y día disponible...")

        calendar_selectors = [
            ".fc-day-future:not(.fc-day-disabled)",  # FullCalendar días futuros
            ".fc-daygrid-day:not(.fc-day-disabled)",
            "td.fc-day:not(.fc-day-past):not(.fc-day-disabled)",
            "[data-date]:not(.disabled)",
            ".calendar td.available",
            ".day-cell.available",
            "td[class*='available']"
        ]

        day_elements = wait_for_element(driver, calendar_selectors, timeout=10, description="día en calendario")

        if day_elements:
            for day in day_elements[:5]:
                try:
                    # Intentar obtener la fecha
                    date_attr = day.get_attribute("data-date") or day.text.strip()
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", day)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", day)
                    print(f"  Click en día: {date_attr[:15] if date_attr else 'unknown'}")
                    time.sleep(3)
                    break
                except Exception as e:
                    print(f"  Error en día: {e}")
                    continue
        else:
            print("  No se encontró calendario, continuando...")

        debug_page(driver, "después de calendario")

        # ============ PASO 2: Seleccionar horario ============
        print("\n[Step 2] Buscando horarios...")

        time_selectors = [
            ".timeslot",
            ".time-slot",
            "[class*='timeslot']",
            ".slot-time",
            ".hour-slot",
            "button[class*='time']",
            ".schedule-item",
            "[data-time]"
        ]

        time_elements = wait_for_element(driver, time_selectors, timeout=10, description="horario")

        if time_elements:
            for t in time_elements[:3]:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", t)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", t)
                    print(f"  Click en horario: {t.text.strip()[:20] if t.text else 'slot'}")
                    time.sleep(3)
                    break
                except:
                    continue

        debug_page(driver, "después de horario")

        # ============ PASO 3: Seleccionar tarifa e incrementar cantidad ============
        print("\n[Step 3] Buscando tarifas (.tariff-option)...")

        tariff_selectors = [
            ".tariff-option",
            "[class*='tariff']",
            ".ticket-type",
            ".price-option"
        ]

        tariff_elements = wait_for_element(driver, tariff_selectors, timeout=10, description="tarifa")

        if tariff_elements:
            print(f"  Encontradas {len(tariff_elements)} tarifas")

            # Buscar el botón + dentro de la tarifa
            for tariff in tariff_elements[:2]:
                try:
                    # Buscar botón de incremento (data-dir="up" o clase plus)
                    plus_btn = None
                    try:
                        plus_btn = tariff.find_element(By.CSS_SELECTOR, "button[data-dir='up']")
                    except:
                        try:
                            plus_btn = tariff.find_element(By.CSS_SELECTOR, "button.plus, .btn-plus, [class*='plus']")
                        except:
                            try:
                                plus_btn = tariff.find_element(By.CSS_SELECTOR, "button:last-of-type")
                            except:
                                pass

                    if plus_btn:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", plus_btn)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", plus_btn)
                        print(f"  Click en botón + para agregar 1 entrada")
                        time.sleep(3)
                        break
                    else:
                        print(f"  No se encontró botón + en esta tarifa")
                except Exception as e:
                    print(f"  Error en tarifa: {e}")
                    continue

        debug_page(driver, "después de tarifa")

        # ============ PASO 4: Buscar y click en agregar al carrito ============
        print("\n[Step 4] Buscando botón de agregar al carrito...")

        cart_selectors = [
            "button[class*='cart']",
            "button[class*='add']",
            ".add-to-cart",
            ".btn-cart",
            "[class*='aggiungi']",
            "[class*='acquista']",
            "button.btn-primary",
            "input[type='submit']",
            "button[type='submit']"
        ]

        cart_buttons = wait_for_element(driver, cart_selectors, timeout=10, description="botón carrito")

        if cart_buttons:
            for btn in cart_buttons:
                try:
                    btn_text = btn.text.strip().lower()
                    # Evitar botones negativos
                    if any(x in btn_text for x in ['cancel', 'close', 'annulla', 'rimuovi']):
                        continue
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"  Click en: {btn.text.strip()[:30] if btn.text else 'botón'}")
                    time.sleep(5)
                    break
                except:
                    continue

        debug_page(driver, "después de carrito")

        # ============ PASO 5: Esperar cookies ============
        print("\n[Step 5] Esperando generación de cookies...")

        # Esperar más tiempo para que se procese
        time.sleep(5)

        # Interacciones adicionales
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)

        # Verificar cookies periódicamente
        for i in range(5):
            cookies = driver.get_cookies()
            if cookies:
                print(f"  Intento {i+1}: {len(cookies)} cookies encontradas")
                break
            time.sleep(2)

        # Extraer cookies finales
        cookies = driver.get_cookies()
        print(f"\n[Result] Cookies obtenidas: {len(cookies)}")

        if cookies:
            cookie_names = [c.get('name', '') for c in cookies]
            print(f"[Result] Nombres: {', '.join(cookie_names)}")

        return cookies

    except Exception as e:
        print(f"[Flow] Error: {e}")
        import traceback
        traceback.print_exc()
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

            # Completar flujo de reserva
            cookies = complete_booking_flow(driver)

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

"""
Script para obtener cookies automáticamente del sitio del Colosseo.
Diseñado para ejecutarse en GitHub Actions con soporte de proxy.

Flujo:
1. Entrar al sitio y pasar Octofence
2. Seleccionar un tipo de tour
3. Ver el calendario y entrar a un día disponible
4. Escoger un horario
5. Agregar al carrito una entrada
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


def complete_booking_flow(driver):
    """
    Completa el flujo de reserva para generar cookies de sesión:
    1. Seleccionar tipo de tour
    2. Ver calendario
    3. Seleccionar día
    4. Seleccionar horario
    5. Agregar al carrito
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print("\n[Flow] Iniciando flujo de reserva...")

    try:
        # ============ PASO 1: Seleccionar tipo de tour ============
        print("\n[Step 1] Buscando tipos de tour/entradas...")
        time.sleep(3)

        # Buscar opciones de tour/entrada
        tour_selectors = [
            ".ticket-type", ".tour-option", ".product-item",
            "[class*='ticket']", "[class*='tour']", "[class*='product']",
            ".entrance-type", ".visit-type", "input[type='radio']",
            ".card", ".option", "button[class*='select']",
            "a[href*='ticket']", "a[href*='tour']"
        ]

        tour_found = False
        for selector in tour_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"  Encontrados {len(elements)} elementos con '{selector}'")
                    # Intentar hacer clic en el primero que sea visible
                    for elem in elements[:3]:
                        try:
                            if elem.is_displayed():
                                driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", elem)
                                print(f"  Click en elemento de tour")
                                tour_found = True
                                time.sleep(3)
                                break
                        except:
                            continue
                    if tour_found:
                        break
            except:
                continue

        debug_page(driver, "después de tour")

        # ============ PASO 2: Ver calendario y seleccionar día ============
        print("\n[Step 2] Buscando calendario y día disponible...")
        time.sleep(3)

        # Buscar días en el calendario
        day_selectors = [
            "td.available", "td[class*='available']",
            ".day.available", ".day[class*='available']",
            ".calendar-day:not(.disabled)", "[data-date]:not(.disabled)",
            ".fc-day:not(.fc-day-disabled)", "td:not(.disabled) a",
            ".datepicker td:not(.disabled)", "[class*='selectable']"
        ]

        day_found = False
        for selector in day_selectors:
            try:
                days = driver.find_elements(By.CSS_SELECTOR, selector)
                if days:
                    print(f"  Encontrados {len(days)} días con '{selector}'")
                    for day in days:
                        try:
                            text = day.text.strip()
                            if text and text.isdigit() and int(text) > 0:
                                driver.execute_script("arguments[0].scrollIntoView(true);", day)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", day)
                                print(f"  Click en día: {text}")
                                day_found = True
                                time.sleep(3)
                                break
                        except:
                            continue
                    if day_found:
                        break
            except:
                continue

        if not day_found:
            # Intentar buscar cualquier elemento clickeable en el calendario
            print("  Intentando método alternativo para calendario...")
            try:
                calendar = driver.find_element(By.CSS_SELECTOR, ".calendar, .datepicker, [class*='calendar']")
                clickable = calendar.find_elements(By.CSS_SELECTOR, "td, .day, a")
                for elem in clickable:
                    try:
                        if elem.is_displayed() and elem.text.strip():
                            driver.execute_script("arguments[0].click();", elem)
                            print(f"  Click alternativo en: {elem.text.strip()[:10]}")
                            time.sleep(3)
                            break
                    except:
                        continue
            except:
                pass

        debug_page(driver, "después de día")

        # ============ PASO 3: Seleccionar horario ============
        print("\n[Step 3] Buscando horarios disponibles...")
        time.sleep(3)

        time_selectors = [
            ".time-slot", ".timeslot", "[class*='time']",
            ".hour", ".schedule", "input[type='radio'][name*='time']",
            "button[class*='time']", "a[class*='time']",
            ".slot", "[class*='slot']", "[class*='hour']"
        ]

        time_found = False
        for selector in time_selectors:
            try:
                times = driver.find_elements(By.CSS_SELECTOR, selector)
                if times:
                    print(f"  Encontrados {len(times)} horarios con '{selector}'")
                    for t in times:
                        try:
                            if t.is_displayed():
                                driver.execute_script("arguments[0].scrollIntoView(true);", t)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", t)
                                print(f"  Click en horario: {t.text.strip()[:20]}")
                                time_found = True
                                time.sleep(3)
                                break
                        except:
                            continue
                    if time_found:
                        break
            except:
                continue

        debug_page(driver, "después de horario")

        # ============ PASO 4: Agregar al carrito ============
        print("\n[Step 4] Buscando botón de agregar al carrito...")
        time.sleep(2)

        # Primero, buscar selector de cantidad si existe
        qty_selectors = [
            "input[type='number']", "select[class*='qty']",
            ".quantity input", "[class*='quantity'] input",
            "input[name*='qty']", "input[name*='quantity']"
        ]

        for selector in qty_selectors:
            try:
                qty_inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                for qty in qty_inputs:
                    if qty.is_displayed():
                        qty.clear()
                        qty.send_keys("1")
                        print(f"  Cantidad establecida a 1")
                        time.sleep(1)
                        break
            except:
                continue

        # Buscar botón de agregar
        add_selectors = [
            "button[class*='add']", "button[class*='cart']",
            "input[type='submit']", "button[type='submit']",
            ".add-to-cart", ".btn-add", "[class*='aggiungi']",
            "[class*='prenota']", "[class*='book']", "[class*='compra']",
            "button.btn-primary", "button.btn", "a.btn[href*='cart']"
        ]

        add_found = False
        for selector in add_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                if buttons:
                    print(f"  Encontrados {len(buttons)} botones con '{selector}'")
                    for btn in buttons:
                        try:
                            if btn.is_displayed():
                                btn_text = btn.text.strip().lower()
                                # Evitar botones de cancelar/cerrar
                                if any(x in btn_text for x in ['cancel', 'close', 'cerrar', 'annulla']):
                                    continue
                                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                time.sleep(1)
                                driver.execute_script("arguments[0].click();", btn)
                                print(f"  Click en botón: {btn.text.strip()[:30]}")
                                add_found = True
                                time.sleep(5)
                                break
                        except:
                            continue
                    if add_found:
                        break
            except:
                continue

        debug_page(driver, "después de agregar")

        # ============ PASO 5: Esperar y extraer cookies ============
        print("\n[Step 5] Esperando generación de cookies...")
        time.sleep(5)

        # Hacer algunas interacciones adicionales
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
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

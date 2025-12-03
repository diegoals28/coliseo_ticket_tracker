"""
Cookie Fetcher para Railway usando undetected-chromedriver.
Obtiene cookies del Colosseo pasando Octofence y las sube a Supabase.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime

# Iniciar Xvfb para display virtual
def start_xvfb():
    try:
        subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1920x1080x24'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        os.environ['DISPLAY'] = ':99'
        print("[Xvfb] Display virtual iniciado")
    except Exception as e:
        print(f"[Xvfb] Error: {e}")

# Configuracion
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
TOUR_URL = "https://ticketing.colosseo.it/en/eventi/24h-colosseo-foro-romano-palatino-gruppi/"


def setup_driver():
    """Configura undetected-chromedriver"""
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')

    # NO usar headless - usar Xvfb en su lugar
    driver = uc.Chrome(options=options, use_subprocess=True)

    print("[Driver] undetected-chromedriver iniciado")
    return driver


def wait_for_octofence(driver, timeout=120):
    """Espera a que Octofence termine de verificar"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print(f"[Wait] Esperando Octofence (max {timeout}s)...")
    start = time.time()

    while time.time() - start < timeout:
        try:
            # Verificar si pasamos Octofence
            title = driver.title.lower()
            url = driver.current_url

            # Si el titulo tiene el nombre del tour, pasamos
            if 'colosseo' in title and 'waiting' not in title:
                # Verificar elementos de la pagina
                try:
                    driver.find_element(By.CSS_SELECTOR, '.ui-datepicker, .tariff-option, input[name="slot"]')
                    print(f"[Wait] Octofence pasado en {int(time.time()-start)}s")
                    return True
                except:
                    pass

            # Mostrar progreso
            elapsed = int(time.time() - start)
            if elapsed % 10 == 0:
                print(f"[Wait] Verificando... ({elapsed}s) - Title: {title[:50]}")

            time.sleep(2)

        except Exception as e:
            print(f"[Wait] Error: {e}")
            time.sleep(2)

    print("[Wait] Timeout esperando Octofence")
    return False


def accept_cookies_banner(driver):
    """Acepta el banner de cookies si aparece"""
    from selenium.webdriver.common.by import By

    print("[Banner] Buscando banner de cookies...")
    try:
        # Buscar boton de aceptar cookies
        accept_selectors = [
            "button#cookie_action_close_header",
            "a.cli_action_button.cli-accept-all-btn",
            "button.cli-accept-btn",
            "[data-cli_action='accept_all']",
            ".cookie-law-info-accept"
        ]

        for selector in accept_selectors:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, selector)
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"[Banner] Cookies aceptadas con: {selector}")
                    time.sleep(1)
                    return True
            except:
                continue

        # Intentar con JavaScript directo
        driver.execute_script("""
            var btns = document.querySelectorAll('button, a');
            for (var b of btns) {
                var txt = b.textContent.toLowerCase();
                if (txt.includes('accept') || txt.includes('aceptar') || txt.includes('accetta')) {
                    b.click();
                    return;
                }
            }
        """)
        print("[Banner] Intentado aceptar via JS")
        time.sleep(1)
        return True

    except Exception as e:
        print(f"[Banner] No encontrado o error: {e}")
        return False


def complete_booking_flow(driver):
    """Completa el flujo de reserva para generar cookies de sesion"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print("[Flow] Iniciando flujo de reserva...")

    try:
        # Primero aceptar banner de cookies
        accept_cookies_banner(driver)
        time.sleep(2)

        wait = WebDriverWait(driver, 15)

        # 1. Click en dia disponible del calendario usando JavaScript
        print("[Flow] Buscando dia en calendario...")
        try:
            # Scroll al calendario primero
            driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(1)

            day = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".ui-datepicker-calendar td:not(.ui-datepicker-unselectable) a")))

            # Scroll al elemento y click con JS
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", day)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", day)
            print("[Flow] Dia seleccionado")
            time.sleep(3)
        except Exception as e:
            print(f"[Flow] No se pudo seleccionar dia: {e}")

        # 2. Click en horario usando JavaScript
        print("[Flow] Buscando horario...")
        try:
            slot = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='slot']")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", slot)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", slot)
            print("[Flow] Horario seleccionado")
            time.sleep(2)
        except Exception as e:
            print(f"[Flow] No se pudo seleccionar horario: {e}")

        # 3. Incrementar cantidad usando JavaScript
        print("[Flow] Incrementando cantidad...")
        try:
            plus_btn = driver.find_element(By.CSS_SELECTOR, "button[data-dir='up']")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", plus_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", plus_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", plus_btn)
            print("[Flow] Cantidad incrementada")
            time.sleep(2)
        except Exception as e:
            print(f"[Flow] No se pudo incrementar: {e}")

        # 4. Agregar al carrito usando JavaScript
        print("[Flow] Agregando al carrito...")
        try:
            submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", submit)
            print("[Flow] Agregado al carrito")
            time.sleep(8)  # Esperar mas tiempo para la navegacion
        except Exception as e:
            print(f"[Flow] No se pudo agregar al carrito: {e}")

        # 5. Verificar si navegamos al carrito y obtener mas cookies
        print("[Flow] Verificando navegacion al carrito...")
        try:
            current_url = driver.current_url
            print(f"[Flow] URL actual: {current_url}")

            # Si no estamos en el carrito, navegar directamente
            if 'cart' not in current_url and 'carrello' not in current_url:
                print("[Flow] Navegando al carrito directamente...")
                driver.get("https://ticketing.colosseo.it/en/cart/")
                time.sleep(5)
                print(f"[Flow] Nueva URL: {driver.current_url}")
        except Exception as e:
            print(f"[Flow] Error verificando carrito: {e}")

        return True

    except Exception as e:
        print(f"[Flow] Error general: {e}")
        return False


def get_cookies(driver):
    """Obtiene todas las cookies del navegador"""
    cookies = driver.get_cookies()
    print(f"[Cookies] Obtenidas {len(cookies)} cookies totales")

    # Debug: mostrar TODAS las cookies
    print("[Debug] Todas las cookies:")
    for c in cookies:
        print(f"  - {c['name']} (domain: {c.get('domain', 'N/A')})")

    # Filtrar cookies relevantes (incluir PHPSESSID y otras importantes)
    relevant = []
    important_names = ['PHPSESSID', 'octofence', 'waap']

    for c in cookies:
        domain = c.get('domain', '')
        name = c.get('name', '')

        # Incluir si: dominio colosseo, o nombre contiene octofence/waap, o es PHPSESSID
        is_relevant = (
            'colosseo' in domain or
            'ticketing' in domain or
            any(imp in name.lower() for imp in important_names)
        )

        if is_relevant:
            relevant.append({
                'name': c['name'],
                'value': c['value'],
                'domain': c.get('domain', '.colosseo.it'),
                'path': c.get('path', '/'),
                'secure': c.get('secure', False),
                'httpOnly': c.get('httpOnly', False)
            })

    print(f"[Cookies] Relevantes: {len(relevant)}")
    for c in relevant:
        print(f"  - {c['name']}")

    return relevant


def save_to_supabase(cookies):
    """Guarda cookies en Supabase Storage"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[Supabase] No configurado")
        return False

    try:
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        data = {
            "cookies": cookies,
            "timestamp": datetime.now().isoformat(),
            "source": "railway-uc"
        }

        cookies_json = json.dumps(data, indent=2).encode('utf-8')

        bucket = 'colosseo-files'
        path = 'cookies/cookies_auto.json'

        # Crear bucket si no existe
        try:
            supabase.storage.get_bucket(bucket)
        except:
            try:
                supabase.storage.create_bucket(bucket, options={'public': False})
            except:
                pass

        # Eliminar archivo anterior
        try:
            supabase.storage.from_(bucket).remove([path])
        except:
            pass

        # Subir
        supabase.storage.from_(bucket).upload(
            path, cookies_json,
            file_options={"content-type": "application/json", "upsert": "true"}
        )

        print("[Supabase] Cookies guardadas exitosamente")
        return True

    except Exception as e:
        print(f"[Supabase] Error: {e}")
        return False


def main():
    print("=" * 60)
    print("COOKIE FETCHER - Railway + undetected-chromedriver")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    # Iniciar display virtual
    start_xvfb()

    driver = None
    try:
        # Configurar driver
        driver = setup_driver()

        # Navegar a la pagina
        print(f"\n[Navigate] Abriendo {TOUR_URL[:50]}...")
        driver.get(TOUR_URL)

        # Esperar Octofence
        if not wait_for_octofence(driver):
            print("[Error] No se pudo pasar Octofence")
            return 1

        # Completar flujo de reserva
        time.sleep(3)
        complete_booking_flow(driver)

        # Esperar a que se generen cookies de sesion
        print("\n[Wait] Esperando generacion de cookies...")
        time.sleep(5)

        # Obtener cookies
        cookies = get_cookies(driver)

        if len(cookies) >= 5:
            print(f"\n[Success] {len(cookies)} cookies obtenidas")

            # Verificar cookies criticas
            names = [c['name'] for c in cookies]
            critical = ['PHPSESSID', 'octofence-waap-id', 'octofence-waap-sessid']
            has_critical = any(c in names for c in critical)

            if has_critical:
                print("[Success] Cookies criticas encontradas!")
            else:
                print("[Warning] Faltan algunas cookies criticas, pero intentando guardar...")

            # Guardar en Supabase
            save_to_supabase(cookies)

            # Guardar local como backup
            with open('cookies_colosseo.json', 'w') as f:
                json.dump(cookies, f, indent=2)
            print("[Local] Backup guardado")

            print("\n" + "=" * 60)
            print("RESULTADO: EXITO")
            print("=" * 60)
            return 0
        else:
            print(f"\n[Error] Solo {len(cookies)} cookies obtenidas")
            return 1

    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
            print("[Driver] Cerrado")


if __name__ == "__main__":
    sys.exit(main())

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

        # 2. Esperar a que carguen los horarios
        print("[Flow] Esperando horarios...")
        time.sleep(4)

        # 3. Click en horario usando JavaScript
        print("[Flow] Buscando horario...")
        try:
            # Buscar el primer slot disponible
            slots = driver.find_elements(By.CSS_SELECTOR, "input[name='slot']")
            print(f"[Flow] Encontrados {len(slots)} slots")
            if slots:
                slot = slots[0]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", slot)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", slot)
                print("[Flow] Horario seleccionado")
                time.sleep(3)
        except Exception as e:
            print(f"[Flow] No se pudo seleccionar horario: {e}")

        # 4. Seleccionar tarifa si existe
        print("[Flow] Buscando tarifas...")
        try:
            tariffs = driver.find_elements(By.CSS_SELECTOR, "input[name='tariff'], .tariff-option input[type='radio']")
            print(f"[Flow] Encontradas {len(tariffs)} tarifas")
            if tariffs:
                tariff = tariffs[0]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tariff)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", tariff)
                print("[Flow] Tarifa seleccionada")
                time.sleep(2)
        except Exception as e:
            print(f"[Flow] No se encontraron tarifas: {e}")

        # 5. Incrementar cantidad usando JavaScript
        print("[Flow] Incrementando cantidad...")
        try:
            plus_btns = driver.find_elements(By.CSS_SELECTOR, "button[data-dir='up'], .qty-btn-plus, button.plus")
            print(f"[Flow] Encontrados {len(plus_btns)} botones +")
            if plus_btns:
                plus_btn = plus_btns[0]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", plus_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", plus_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", plus_btn)
                print("[Flow] Cantidad incrementada")
                time.sleep(2)
        except Exception as e:
            print(f"[Flow] No se pudo incrementar: {e}")

        # 6. Debug: ver todos los formularios
        print("[Flow] Analizando formularios en la pagina...")
        try:
            forms_info = driver.execute_script("""
                var forms = document.querySelectorAll('form');
                var info = [];
                forms.forEach(function(form, idx) {
                    var action = form.action || 'no-action';
                    var id = form.id || 'no-id';
                    var inputs = form.querySelectorAll('input, select, button').length;
                    info.push('Form' + idx + ': id=' + id + ', action=' + action.substring(0,50) + ', inputs=' + inputs);
                });
                return info.join(' | ');
            """)
            print(f"[Flow] Forms: {forms_info[:300] if forms_info else 'None'}")
        except Exception as e:
            print(f"[Flow] Error analizando forms: {e}")

        # 7. Explorar estructura de la pagina para encontrar como agregar al carrito
        print("[Flow] Explorando estructura de la pagina...")
        try:
            page_structure = driver.execute_script("""
                var result = {};

                // Buscar secciones de tarifa
                var tariffSections = document.querySelectorAll('.tariff, .tariff-row, .ticket-type, [class*="tariff"], [class*="ticket"]');
                result.tariffSections = tariffSections.length;

                // Buscar inputs de cantidad
                var qtyInputs = document.querySelectorAll('input[type="number"], input[name*="qty"], input[name*="quantity"]');
                result.qtyInputs = qtyInputs.length;

                // Buscar todos los elementos con data attributes relacionados
                var dataElements = document.querySelectorAll('[data-product], [data-item], [data-ticket], [data-tariff]');
                result.dataElements = dataElements.length;

                // Buscar la seccion activa despues de seleccionar slot
                var activeSection = document.querySelector('.slot-selected, .time-selected, .active-slot, [class*="selected"]');
                result.hasActiveSection = !!activeSection;

                // Buscar botones dentro de secciones de tarifa
                if (tariffSections.length > 0) {
                    var btnsInTariff = tariffSections[0].querySelectorAll('button');
                    result.btnsInFirstTariff = btnsInTariff.length;
                }

                // Buscar el HTML de la seccion principal
                var mainContent = document.querySelector('.event-content, .booking-section, main, #content');
                if (mainContent) {
                    result.mainContentPreview = mainContent.innerHTML.substring(0, 500);
                }

                return JSON.stringify(result, null, 2);
            """)
            print(f"[Flow] Page structure: {page_structure[:400] if page_structure else 'None'}")
        except Exception as e:
            print(f"[Flow] Error explorando pagina: {e}")

        # 7b. Intentar agregar al carrito de varias formas
        print("[Flow] Intentando agregar al carrito...")
        try:
            add_cart_result = driver.execute_script("""
                // Metodo 1: Buscar boton con icono de carrito o plus
                var iconButtons = document.querySelectorAll('button i, a i');
                for (var icon of iconButtons) {
                    var classes = icon.className || '';
                    if (classes.includes('cart') || classes.includes('plus') || classes.includes('add') || classes.includes('shopping')) {
                        var btn = icon.closest('button') || icon.closest('a');
                        if (btn && btn.offsetParent !== null) {
                            btn.click();
                            return 'Method1: Clicked icon button with class: ' + classes;
                        }
                    }
                }

                // Metodo 2: Buscar en la seccion de slots seleccionados
                var selectedSlot = document.querySelector('input[name="slot"]:checked');
                if (selectedSlot) {
                    var container = selectedSlot.closest('.slot-container, .time-slot, tr, .row, div');
                    if (container) {
                        var btn = container.querySelector('button:not([type="button"][data-dir])');
                        if (btn) {
                            btn.click();
                            return 'Method2: Clicked button near selected slot';
                        }
                    }
                }

                // Metodo 3: Buscar boton despues de los controles de cantidad
                var qtyControls = document.querySelector('button[data-dir="up"]');
                if (qtyControls) {
                    var parent = qtyControls.closest('.qty-wrapper, .quantity-controls, .tariff-row, div');
                    if (parent) {
                        // Buscar siguiente boton que no sea de cantidad
                        var allBtns = parent.querySelectorAll('button');
                        for (var btn of allBtns) {
                            if (!btn.hasAttribute('data-dir')) {
                                btn.click();
                                return 'Method3: Clicked non-qty button in same container';
                            }
                        }
                    }
                }

                // Metodo 4: Buscar submit button que no sea de busqueda
                var submits = document.querySelectorAll('button[type="submit"]');
                for (var btn of submits) {
                    if (btn.getAttribute('alt') !== 'Search' && btn.offsetParent !== null) {
                        var text = btn.textContent || '';
                        if (!text.toLowerCase().includes('search')) {
                            btn.click();
                            return 'Method4: Clicked submit: ' + text.substring(0, 20);
                        }
                    }
                }

                return 'No method worked';
            """)
            print(f"[Flow] Add to cart result: {add_cart_result}")
            time.sleep(10)
        except Exception as e:
            print(f"[Flow] No se pudo agregar al carrito: {e}")

        # 8. Manejar posibles alerts
        print("[Flow] Verificando alerts...")
        try:
            from selenium.webdriver.common.alert import Alert
            alert = Alert(driver)
            alert_text = alert.text
            print(f"[Flow] Alert encontrado: {alert_text}")
            alert.dismiss()  # Cancelar para no vaciar el carrito
            print("[Flow] Alert cancelado")
            time.sleep(2)
        except:
            print("[Flow] No hay alerts pendientes")

        # 9. Verificar si navegamos al carrito y obtener mas cookies
        print("[Flow] Verificando navegacion al carrito...")
        try:
            current_url = driver.current_url
            print(f"[Flow] URL actual: {current_url}")

            # Si estamos en el carrito, bien! Si no, NO navegar para no perder sesion
            if 'cart' in current_url or 'carrello' in current_url:
                print("[Flow] Ya estamos en el carrito!")
            else:
                print("[Flow] No estamos en carrito, verificando si hay items...")
                # Verificar si hay indicador de carrito con items
                cart_count = driver.execute_script("""
                    var cartBadge = document.querySelector('.cart-count, .badge, .cart-items-count');
                    return cartBadge ? cartBadge.textContent : '0';
                """)
                print(f"[Flow] Items en carrito: {cart_count}")
        except Exception as e:
            print(f"[Flow] Error verificando carrito: {e}")

        # 6. Forzar peticion AJAX al calendario para generar cookies de sesion
        print("[Flow] Forzando peticion AJAX al calendario...")
        try:
            ajax_result = driver.execute_script("""
                return new Promise((resolve) => {
                    var formData = new FormData();
                    formData.append('action', 'mtajax_calendars_month');
                    formData.append('guids[entranceEvent_guid][]', 'a9a4b0f8-bf3c-4f22-afcd-196a27be04b9');
                    formData.append('singleDaySession', 'false');
                    formData.append('month', new Date().getMonth() + 1);
                    formData.append('year', new Date().getFullYear());

                    fetch('/mtajax/calendars_month', {
                        method: 'POST',
                        body: formData,
                        credentials: 'include'
                    })
                    .then(r => r.text())
                    .then(t => resolve('OK: ' + t.substring(0, 100)))
                    .catch(e => resolve('Error: ' + e.message));
                });
            """)
            print(f"[Flow] AJAX result: {ajax_result[:100] if ajax_result else 'None'}")
            time.sleep(3)
        except Exception as e:
            print(f"[Flow] Error AJAX: {e}")

        return True

    except Exception as e:
        print(f"[Flow] Error general: {e}")
        return False


def get_cookies(driver):
    """Obtiene todas las cookies del navegador"""
    # Verificar contenido de la pagina actual
    try:
        page_source = driver.page_source
        print(f"[Debug] Page length: {len(page_source)}")
        if 'empty' in page_source.lower() or 'vacío' in page_source.lower() or 'vuoto' in page_source.lower():
            print("[Debug] El carrito parece estar vacio")
        if 'cart' in page_source.lower() or 'carrello' in page_source.lower():
            print("[Debug] Pagina contiene referencia a carrito")
    except:
        pass

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

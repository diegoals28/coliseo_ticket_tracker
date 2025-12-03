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

# Proxy residencial (Webshare)
# Formato: PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS
PROXY_HOST = os.environ.get('PROXY_HOST', '')
PROXY_PORT = os.environ.get('PROXY_PORT', '')
PROXY_USER = os.environ.get('PROXY_USER', '')
PROXY_PASS = os.environ.get('PROXY_PASS', '')


def create_proxy_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    """Crea una extension de Chrome para autenticacion de proxy"""
    import zipfile
    import tempfile

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {urls: ["<all_urls>"]},
        ['blocking']
    );
    """ % (proxy_host, proxy_port, proxy_user, proxy_pass)

    # Crear extension temporal
    ext_dir = tempfile.mkdtemp()
    ext_path = os.path.join(ext_dir, 'proxy_auth.zip')

    with zipfile.ZipFile(ext_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return ext_path


def setup_driver():
    """Configura undetected-chromedriver con network logging y proxy"""
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')

    # Configurar proxy residencial si esta disponible
    if PROXY_HOST and PROXY_PORT:
        print(f"[Proxy] Configurando proxy residencial: {PROXY_HOST}:{PROXY_PORT}")

        if PROXY_USER and PROXY_PASS:
            # Crear extension para autenticacion
            print(f"[Proxy] Creando extension de autenticacion...")
            ext_path = create_proxy_extension(PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)
            options.add_extension(ext_path)
            print(f"[Proxy] Extension cargada")
        else:
            # Sin autenticacion
            options.add_argument(f'--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}')
    else:
        print("[Proxy] Sin proxy configurado - usando IP directa (puede ser bloqueado)")

    # Habilitar logging de red para capturar cookies HttpOnly
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # NO usar headless - usar Xvfb en su lugar
    driver = uc.Chrome(options=options, use_subprocess=True)

    print("[Driver] undetected-chromedriver iniciado con network logging")
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

        # ESTRATEGIA 1: Ir directamente al carrito para forzar sesion
        print("[Flow] Estrategia 1: Visitar carrito para crear sesion...")
        try:
            driver.get("https://ticketing.colosseo.it/en/cart/")
            time.sleep(5)
            print(f"[Flow] URL carrito: {driver.current_url}")
        except Exception as e:
            print(f"[Flow] Error visitando carrito: {e}")

        # Volver a la pagina del tour
        print("[Flow] Volviendo a pagina del tour...")
        driver.get("https://ticketing.colosseo.it/en/eventi/24h-colosseo-foro-romano-palatino-gruppi/")
        time.sleep(5)

        # Esperar a que el calendario este visible
        print("[Flow] Esperando calendario...")
        wait = WebDriverWait(driver, 30)

        # 1. Click en dia disponible del calendario usando JavaScript
        print("[Flow] Buscando dia en calendario...")
        try:
            # Esperar a que el calendario se cargue completamente
            time.sleep(3)

            # Scroll al calendario primero
            driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(2)

            # Intentar encontrar un dia disponible con multiples selectores
            day_selectors = [
                ".ui-datepicker-calendar td:not(.ui-datepicker-unselectable) a",
                ".ui-datepicker-calendar td.available a",
                ".ui-datepicker-calendar td a.ui-state-default",
                "td.abc-availability-available a"
            ]

            day = None
            for selector in day_selectors:
                try:
                    day = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if day:
                        print(f"[Flow] Dia encontrado con selector: {selector}")
                        break
                except:
                    continue

            if day:
                # Scroll al elemento y click con JS
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", day)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", day)
                print("[Flow] Dia seleccionado")
                time.sleep(4)
            else:
                # Intentar con JavaScript directo
                print("[Flow] Intentando seleccionar dia via JS...")
                result = driver.execute_script("""
                    var days = document.querySelectorAll('.ui-datepicker-calendar td:not(.ui-datepicker-unselectable) a');
                    if (days.length > 0) {
                        days[0].click();
                        return 'Clicked day ' + days[0].textContent;
                    }
                    return 'No days found';
                """)
                print(f"[Flow] JS result: {result}")
                time.sleep(4)
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

        # 5b. CRITICO: Hacer click en boton "Add to Cart" / "Book"
        print("[Flow] Buscando boton ADD TO CART...")
        try:
            add_to_cart_result = driver.execute_script("""
                // Textos a buscar (orden de prioridad)
                var targetTexts = ['add to cart', 'add to basket', 'book now', 'checkout',
                                   'aggiungi al carrello', 'prenota ora', 'proceed to checkout'];
                // Textos a EVITAR
                var excludeTexts = ['continue shopping', 'keep shopping', 'seguir comprando'];

                var buttons = document.querySelectorAll('button, input[type="submit"], a.btn, a.button');

                for (var btn of buttons) {
                    var text = (btn.textContent || btn.value || '').toLowerCase().trim();

                    // Saltar si contiene texto a excluir
                    var shouldExclude = false;
                    for (var ex of excludeTexts) {
                        if (text.includes(ex)) {
                            shouldExclude = true;
                            break;
                        }
                    }
                    if (shouldExclude) continue;

                    for (var target of targetTexts) {
                        if (text.includes(target)) {
                            btn.scrollIntoView({block: 'center'});
                            btn.click();
                            return 'Clicked: ' + text;
                        }
                    }
                }

                // Buscar por clase especifica de ABC (el sistema de booking del sitio)
                var abcButtons = document.querySelectorAll('.abc-book-btn, .abc-add-to-cart, [class*="abc-"][class*="btn"]');
                for (var btn of abcButtons) {
                    if (btn.offsetParent !== null && !btn.hasAttribute('data-dir')) {
                        var text = btn.textContent.toLowerCase();
                        if (!text.includes('shopping')) {
                            btn.click();
                            return 'Clicked ABC button: ' + btn.className;
                        }
                    }
                }

                // Buscar el modal del carrito y su boton de checkout
                var cartModal = document.querySelector('.cart-modal, #cart-modal, [class*="cart"][class*="modal"]');
                if (cartModal) {
                    var checkoutBtn = cartModal.querySelector('a[href*="checkout"], a[href*="cart"], button');
                    if (checkoutBtn && checkoutBtn.offsetParent !== null) {
                        checkoutBtn.click();
                        return 'Clicked cart modal button';
                    }
                }

                // Buscar link directo al carrito
                var cartLinks = document.querySelectorAll('a[href*="/cart"], a[href*="/checkout"]');
                for (var link of cartLinks) {
                    var text = link.textContent.toLowerCase();
                    if (text.includes('checkout') || text.includes('view cart') || text.includes('cart')) {
                        if (!text.includes('shopping')) {
                            link.click();
                            return 'Clicked cart link: ' + text;
                        }
                    }
                }

                // Listar todos los botones visibles para debug
                var visibleBtns = [];
                var allBtns = document.querySelectorAll('button:not([data-dir])');
                for (var btn of allBtns) {
                    if (btn.offsetParent !== null && btn.offsetWidth > 40) {
                        var text = (btn.textContent || '').trim().substring(0, 30);
                        if (text) visibleBtns.push(text);
                    }
                }
                return 'No cart button. Visible buttons: ' + visibleBtns.slice(0, 5).join(', ');
            """)
            print(f"[Flow] Add to cart result: {add_to_cart_result}")
            time.sleep(5)  # Esperar a que procese

            # Verificar si hubo navegacion
            current_url = driver.current_url
            print(f"[Flow] URL despues de add-to-cart: {current_url}")

        except Exception as e:
            print(f"[Flow] Error en add-to-cart: {e}")

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

        # 7b. Analizar la estructura de tarifas en detalle
        print("[Flow] Analizando estructura de tarifas...")
        try:
            tariff_analysis = driver.execute_script("""
                // Buscar la primera tarifa con cantidad > 0
                var qtyInputs = document.querySelectorAll('input[type="number"]');
                for (var input of qtyInputs) {
                    var val = parseInt(input.value) || 0;
                    if (val > 0) {
                        // Encontramos una tarifa con cantidad
                        var row = input.closest('tr, .row, .tariff-row, div[class*="tariff"]');
                        if (row) {
                            return 'Found qty=' + val + ' in: ' + row.className + ' | HTML: ' + row.innerHTML.substring(0, 300);
                        }
                    }
                }

                // Si no hay cantidad > 0, mostrar el primer input
                if (qtyInputs.length > 0) {
                    var first = qtyInputs[0];
                    var row = first.closest('tr, .row, div');
                    return 'First qty input value=' + first.value + ' | Row HTML: ' + (row ? row.innerHTML.substring(0, 300) : 'no row');
                }

                return 'No qty inputs found';
            """)
            print(f"[Flow] Tariff analysis: {tariff_analysis[:400] if tariff_analysis else 'None'}")
        except Exception as e:
            print(f"[Flow] Error analizando tarifas: {e}")

        # 7c. Buscar boton de agregar especifico del sitio
        print("[Flow] Buscando boton agregar especifico...")
        try:
            add_cart_result = driver.execute_script("""
                // El sitio probablemente usa un boton con clase especifica o data attribute
                // Buscar todos los botones y mostrar sus atributos
                var allButtons = document.querySelectorAll('button');
                var buttonInfo = [];

                for (var i = 0; i < Math.min(allButtons.length, 50); i++) {
                    var btn = allButtons[i];
                    if (btn.offsetParent === null) continue; // Skip hidden

                    var info = {
                        idx: i,
                        text: (btn.textContent || '').trim().substring(0, 20),
                        class: (btn.className || '').substring(0, 30),
                        type: btn.type || '',
                        onclick: btn.getAttribute('onclick') ? 'yes' : 'no',
                        dataAttrs: []
                    };

                    // Capturar data attributes
                    for (var attr of btn.attributes) {
                        if (attr.name.startsWith('data-')) {
                            info.dataAttrs.push(attr.name + '=' + attr.value.substring(0, 20));
                        }
                    }

                    if (info.dataAttrs.length > 0 || info.onclick === 'yes' || info.text.length > 0) {
                        buttonInfo.push(info);
                    }
                }

                return JSON.stringify(buttonInfo.slice(0, 10));
            """)
            print(f"[Flow] Button analysis: {add_cart_result[:500] if add_cart_result else 'None'}")
        except Exception as e:
            print(f"[Flow] Error analizando botones: {e}")

        # 7d. Intentar click en boton con data-action o similar
        print("[Flow] Intentando click en boton de accion...")
        try:
            click_result = driver.execute_script("""
                // Buscar botones con data attributes de accion
                var actionButtons = document.querySelectorAll('button[data-action], button[data-add], button[data-submit], a[data-action]');
                if (actionButtons.length > 0) {
                    actionButtons[0].click();
                    return 'Clicked data-action button';
                }

                // Buscar por clase que contenga 'add' o 'submit' o 'buy'
                var classButtons = document.querySelectorAll('button[class*="add"], button[class*="submit"], button[class*="buy"], button[class*="cart"]');
                for (var btn of classButtons) {
                    if (btn.offsetParent !== null && !btn.hasAttribute('data-dir')) {
                        btn.click();
                        return 'Clicked class button: ' + btn.className;
                    }
                }

                // Buscar el boton principal de la pagina (generalmente el mas grande o con estilo primario)
                var primaryBtns = document.querySelectorAll('.btn-primary, .primary-button, button.main, button.submit');
                for (var btn of primaryBtns) {
                    if (btn.offsetParent !== null) {
                        btn.click();
                        return 'Clicked primary button';
                    }
                }

                return 'No action button found';
            """)
            print(f"[Flow] Click result: {click_result}")
            time.sleep(10)
        except Exception as e:
            print(f"[Flow] Error clicking: {e}")

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

        # 6. Forzar multiples peticiones AJAX para generar cookies de sesion
        print("[Flow] Forzando peticiones AJAX...")
        try:
            # Llamada al calendario
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
                    .then(t => resolve('Calendar: ' + t.substring(0, 50)))
                    .catch(e => resolve('Error: ' + e.message));
                });
            """)
            print(f"[Flow] AJAX calendar: {ajax_result[:80] if ajax_result else 'None'}")
            time.sleep(2)

            # Llamada al carrito
            cart_result = driver.execute_script("""
                return new Promise((resolve) => {
                    fetch('/en/cart/', {
                        method: 'GET',
                        credentials: 'include'
                    })
                    .then(r => r.text())
                    .then(t => resolve('Cart loaded: ' + t.length + ' chars'))
                    .catch(e => resolve('Error: ' + e.message));
                });
            """)
            print(f"[Flow] AJAX cart: {cart_result[:80] if cart_result else 'None'}")
            time.sleep(2)

            # Llamada a wp-admin/admin-ajax.php (endpoint comun de WordPress)
            wp_result = driver.execute_script("""
                return new Promise((resolve) => {
                    var formData = new FormData();
                    formData.append('action', 'abc_get_cart');

                    fetch('/wp-admin/admin-ajax.php', {
                        method: 'POST',
                        body: formData,
                        credentials: 'include'
                    })
                    .then(r => r.text())
                    .then(t => resolve('WP: ' + t.substring(0, 50)))
                    .catch(e => resolve('Error: ' + e.message));
                });
            """)
            print(f"[Flow] AJAX wp: {wp_result[:80] if wp_result else 'None'}")
            time.sleep(2)

        except Exception as e:
            print(f"[Flow] Error AJAX: {e}")

        return True

    except Exception as e:
        print(f"[Flow] Error general: {e}")
        return False


def get_cookies_via_cdp(driver):
    """Obtiene TODAS las cookies usando Chrome DevTools Protocol"""
    print("[CDP] Obteniendo cookies via DevTools Protocol...")
    cookies_found = []

    try:
        # Metodo 1: Network.getAllCookies (obtiene todas las cookies del navegador)
        try:
            result = driver.execute_cdp_cmd('Network.getAllCookies', {})
            cdp_cookies = result.get('cookies', [])
            print(f"[CDP] Network.getAllCookies: {len(cdp_cookies)} cookies")

            for c in cdp_cookies:
                cookies_found.append({
                    'name': c.get('name'),
                    'value': c.get('value'),
                    'domain': c.get('domain', '.colosseo.it'),
                    'path': c.get('path', '/'),
                    'secure': c.get('secure', False),
                    'httpOnly': c.get('httpOnly', False)
                })
                print(f"  - {c.get('name')} (httpOnly: {c.get('httpOnly', False)})")
        except Exception as e:
            print(f"[CDP] Error Network.getAllCookies: {e}")

        # Metodo 2: Storage.getCookies para dominio especifico
        try:
            result = driver.execute_cdp_cmd('Storage.getCookies', {
                'browserContextId': None
            })
            storage_cookies = result.get('cookies', [])
            print(f"[CDP] Storage.getCookies: {len(storage_cookies)} cookies")
        except Exception as e:
            print(f"[CDP] Storage.getCookies no disponible: {e}")

        # Metodo 3: Page.getCookies (cookies de la pagina actual)
        try:
            result = driver.execute_cdp_cmd('Page.getCookies', {})
            page_cookies = result.get('cookies', [])
            print(f"[CDP] Page.getCookies: {len(page_cookies)} cookies")

            # Agregar las que no tengamos
            existing_names = {c['name'] for c in cookies_found}
            for c in page_cookies:
                if c.get('name') not in existing_names:
                    cookies_found.append({
                        'name': c.get('name'),
                        'value': c.get('value'),
                        'domain': c.get('domain', '.colosseo.it'),
                        'path': c.get('path', '/'),
                        'secure': c.get('secure', False),
                        'httpOnly': c.get('httpOnly', False)
                    })
                    print(f"  + {c.get('name')} (from Page.getCookies)")
        except Exception as e:
            print(f"[CDP] Page.getCookies no disponible: {e}")

    except Exception as e:
        print(f"[CDP] Error general: {e}")

    return cookies_found


def get_cookies_from_network_logs(driver):
    """Extrae cookies HttpOnly de los logs de red de Chrome"""
    import json as json_module

    print("[Network] Analizando logs de red para cookies HttpOnly...")
    cookies_found = {}
    set_cookie_count = 0

    try:
        logs = driver.get_log('performance')
        print(f"[Network] Procesando {len(logs)} entradas de log...")

        for entry in logs:
            try:
                log = json_module.loads(entry['message'])['message']
                method = log.get('method', '')

                # Buscar respuestas con Set-Cookie
                if method == 'Network.responseReceivedExtraInfo':
                    headers = log.get('params', {}).get('headers', {})
                    for key, value in headers.items():
                        if key.lower() == 'set-cookie':
                            set_cookie_count += 1
                            # Parsear la cookie
                            cookie_parts = value.split(';')[0].split('=', 1)
                            if len(cookie_parts) == 2:
                                name, val = cookie_parts
                                cookies_found[name.strip()] = val.strip()
                                # Debug: mostrar cookies importantes
                                if 'php' in name.lower() or 'octofence' in name.lower() or 'waap' in name.lower():
                                    print(f"[Network] IMPORTANTE encontrada: {name}")

                # Buscar cookies en requests salientes
                if method == 'Network.requestWillBeSentExtraInfo':
                    headers = log.get('params', {}).get('headers', {})
                    cookie_header = headers.get('Cookie', headers.get('cookie', ''))
                    if cookie_header:
                        for cookie_pair in cookie_header.split(';'):
                            if '=' in cookie_pair:
                                name, val = cookie_pair.split('=', 1)
                                name = name.strip()
                                if name not in cookies_found:
                                    cookies_found[name] = val.strip()

                # Buscar tambien en Network.responseReceived para headers
                if method == 'Network.responseReceived':
                    response = log.get('params', {}).get('response', {})
                    headers = response.get('headers', {})
                    for key, value in headers.items():
                        if key.lower() == 'set-cookie':
                            cookie_parts = value.split(';')[0].split('=', 1)
                            if len(cookie_parts) == 2:
                                name, val = cookie_parts
                                cookies_found[name.strip()] = val.strip()

            except Exception as e:
                continue

        print(f"[Network] Set-Cookie headers encontrados: {set_cookie_count}")
        print(f"[Network] Cookies unicas extraidas: {len(cookies_found)}")
        for name in sorted(cookies_found.keys()):
            is_critical = 'php' in name.lower() or 'waap' in name.lower()
            print(f"  {'*' if is_critical else '-'} {name}")

    except Exception as e:
        print(f"[Network] Error procesando logs: {e}")

    return cookies_found


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

        # Verificar si hay items en el carrito
        if 'There\'s an item in your cart' in page_source or 'items in your cart' in page_source:
            print("[Debug] HAY ITEMS EN EL CARRITO!")
    except:
        pass

    # METODO 1: CDP - obtiene TODAS las cookies incluyendo HttpOnly
    cdp_cookies = get_cookies_via_cdp(driver)

    # METODO 2: Network logs (backup)
    network_cookies = get_cookies_from_network_logs(driver)

    # METODO 3: Selenium standard (backup)
    cookies = driver.get_cookies()
    print(f"[Cookies] Obtenidas {len(cookies)} cookies via driver.get_cookies()")

    # Debug: mostrar cookies del driver
    print("[Debug] Cookies de driver.get_cookies():")
    for c in cookies:
        print(f"  - {c['name']} (domain: {c.get('domain', 'N/A')})")

    # PRIORIDAD 1: Usar cookies de CDP (incluye HttpOnly)
    relevant = []
    important_names = ['PHPSESSID', 'octofence', 'waap']

    # Filtrar cookies CDP relevantes
    for c in cdp_cookies:
        domain = c.get('domain', '')
        name = c.get('name', '')

        is_relevant = (
            'colosseo' in domain or
            'ticketing' in domain or
            any(imp in name.lower() for imp in important_names)
        )

        if is_relevant:
            relevant.append(c)

    print(f"[Cookies] Relevantes de CDP: {len(relevant)}")

    # PRIORIDAD 2: Agregar cookies del driver que no esten en CDP
    existing_names = {c['name'] for c in relevant}
    for c in cookies:
        domain = c.get('domain', '')
        name = c.get('name', '')

        is_relevant = (
            'colosseo' in domain or
            'ticketing' in domain or
            any(imp in name.lower() for imp in important_names)
        )

        if is_relevant and name not in existing_names:
            relevant.append({
                'name': c['name'],
                'value': c['value'],
                'domain': c.get('domain', '.colosseo.it'),
                'path': c.get('path', '/'),
                'secure': c.get('secure', False),
                'httpOnly': c.get('httpOnly', False)
            })
            print(f"  + {name} (from driver)")

    # PRIORIDAD 3: Agregar cookies de network logs
    existing_names = {c['name'] for c in relevant}
    for name, value in network_cookies.items():
        if name not in existing_names:
            relevant.append({
                'name': name,
                'value': value,
                'domain': '.colosseo.it',
                'path': '/',
                'secure': True,
                'httpOnly': True
            })
            print(f"  + {name} (from network logs)")

    print(f"[Cookies] Total combinadas: {len(relevant)}")

    # Mostrar resumen de cookies criticas
    cookie_names = [c['name'] for c in relevant]
    critical = ['PHPSESSID', 'octofence-waap-id', 'octofence-waap-sessid']
    print("[Cookies] Cookies criticas:")
    for crit in critical:
        found = crit in cookie_names
        print(f"  - {crit}: {'SI' if found else 'NO'}")

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

"""
Railway API Service - Consultas al Colosseo con cookies válidas
Usa undetected-chromedriver para obtener cookies y hacer consultas
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from threading import Lock, Thread

app = Flask(__name__)

# Estado global
state = {
    "cookies": [],
    "cookies_timestamp": None,
    "driver": None,
    "last_query": None,
    "status": "initializing"
}
state_lock = Lock()

# Configuración
TOUR_URL = "https://ticketing.colosseo.it/en/eventi/24h-colosseo-foro-romano-palatino-gruppi/"
COOKIE_MAX_AGE = 3600  # 1 hora
PROXY_HOST = os.environ.get('PROXY_HOST', '')
PROXY_PORT = os.environ.get('PROXY_PORT', '')
PROXY_USER = os.environ.get('PROXY_USER', '')
PROXY_PASS = os.environ.get('PROXY_PASS', '')


def start_xvfb():
    """Inicia display virtual para el navegador"""
    try:
        subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1920x1080x24'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        os.environ['DISPLAY'] = ':99'
        print("[Xvfb] Display virtual iniciado")
        return True
    except Exception as e:
        print(f"[Xvfb] Error: {e}")
        return False


def create_proxy_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    """Crea extensión de Chrome para autenticación de proxy"""
    import zipfile
    import tempfile

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: { scheme: "http", host: "%s", port: parseInt(%s) },
            bypassList: ["localhost"]
        }
    };
    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
    function callbackFn(details) {
        return { authCredentials: { username: "%s", password: "%s" } };
    }
    chrome.webRequest.onAuthRequired.addListener(callbackFn, {urls: ["<all_urls>"]}, ['blocking']);
    """ % (proxy_host, proxy_port, proxy_user, proxy_pass)

    ext_dir = tempfile.mkdtemp()
    ext_path = os.path.join(ext_dir, 'proxy_auth.zip')

    with zipfile.ZipFile(ext_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return ext_path


def setup_driver():
    """Configura undetected-chromedriver"""
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')

    if PROXY_HOST and PROXY_PORT:
        print(f"[Driver] Configurando proxy: {PROXY_HOST}:{PROXY_PORT}")
        if PROXY_USER and PROXY_PASS:
            ext_path = create_proxy_extension(PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)
            options.add_extension(ext_path)

    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    driver = uc.Chrome(options=options, use_subprocess=True)
    print("[Driver] Chrome iniciado")
    return driver


def wait_for_octofence(driver, timeout=60):
    """Espera a que Octofence termine de verificar"""
    from selenium.webdriver.common.by import By

    start = time.time()
    while time.time() - start < timeout:
        try:
            title = driver.title.lower()
            if 'colosseo' in title and 'waiting' not in title:
                try:
                    driver.find_element(By.CSS_SELECTOR, '.ui-datepicker, .tariff-option, input[name="slot"]')
                    return True
                except:
                    pass
            time.sleep(2)
        except:
            time.sleep(2)
    return False


def refresh_cookies():
    """Obtiene cookies frescas navegando al sitio y completando flujo de reserva"""
    global state

    print("[Cookies] Iniciando refresh de cookies...")

    with state_lock:
        state["status"] = "refreshing_cookies"

    driver = None
    try:
        driver = setup_driver()

        # Navegar al tour
        print(f"[Cookies] Navegando a {TOUR_URL[:50]}...")
        driver.get(TOUR_URL)

        # Esperar Octofence
        if not wait_for_octofence(driver):
            print("[Cookies] Error: No se pudo pasar Octofence")
            with state_lock:
                state["status"] = "octofence_blocked"
            return False

        print("[Cookies] Octofence pasado!")

        # Aceptar banner de cookies
        try:
            driver.execute_script("""
                var btns = document.querySelectorAll('button, a');
                for (var b of btns) {
                    var txt = b.textContent.toLowerCase();
                    if (txt.includes('accept') || txt.includes('aceptar')) { b.click(); return; }
                }
            """)
            time.sleep(1)
        except:
            pass

        # Visitar carrito para iniciar sesión
        print("[Cookies] Visitando carrito...")
        driver.get("https://ticketing.colosseo.it/en/cart/")
        time.sleep(3)

        # Volver al tour
        print("[Cookies] Volviendo al tour...")
        driver.get(TOUR_URL)
        time.sleep(5)
        wait_for_octofence(driver, timeout=30)

        # Seleccionar día del calendario
        print("[Cookies] Seleccionando día...")
        day_result = driver.execute_script("""
            var days = document.querySelectorAll('.ui-datepicker-calendar td:not(.ui-datepicker-unselectable) a');
            if (days.length > 0) {
                days[0].scrollIntoView({block: 'center'});
                days[0].click();
                return 'clicked day ' + days[0].textContent;
            }
            return 'no days found';
        """)
        print(f"[Cookies] Day result: {day_result}")
        time.sleep(4)

        # Seleccionar horario
        print("[Cookies] Seleccionando horario...")
        slot_result = driver.execute_script("""
            var slots = document.querySelectorAll('input[name="slot"]');
            if (slots.length > 0) {
                slots[0].scrollIntoView({block: 'center'});
                slots[0].click();
                return 'clicked slot, total: ' + slots.length;
            }
            return 'no slots found';
        """)
        print(f"[Cookies] Slot result: {slot_result}")
        time.sleep(3)

        # Incrementar cantidad varias veces
        print("[Cookies] Incrementando cantidad...")
        for i in range(3):
            driver.execute_script("""
                var plusBtns = document.querySelectorAll('button[data-dir="up"]');
                if (plusBtns.length > 0) { plusBtns[0].click(); }
            """)
            time.sleep(0.5)

        qty_result = driver.execute_script("""
            var inputs = document.querySelectorAll('input[type="number"]');
            var total = 0;
            for (var inp of inputs) { total += parseInt(inp.value) || 0; }
            return total;
        """)
        print(f"[Cookies] Cantidad total: {qty_result}")
        time.sleep(2)

        # Click en Confirm - buscar más opciones
        print("[Cookies] Buscando Confirm...")
        confirm_result = driver.execute_script("""
            // Opción 1: input[type=submit] con value Confirm
            var submits = document.querySelectorAll('input[type="submit"]');
            for (var s of submits) {
                var val = (s.value || '').toLowerCase();
                if (val === 'confirm' || val === 'conferma') {
                    s.scrollIntoView({block: 'center'});
                    s.click();
                    return 'clicked submit: ' + s.value;
                }
            }

            // Opción 2: cualquier submit que no sea search
            for (var s of submits) {
                var val = (s.value || '').toLowerCase();
                if (val && val !== 'search' && val !== 'cerca' && s.offsetParent !== null) {
                    s.scrollIntoView({block: 'center'});
                    s.click();
                    return 'clicked other submit: ' + s.value;
                }
            }

            // Opción 3: botón con texto add/book/cart
            var buttons = document.querySelectorAll('button:not([data-dir])');
            for (var b of buttons) {
                var txt = (b.textContent || '').toLowerCase();
                if ((txt.includes('add') || txt.includes('book') || txt.includes('cart')) && b.offsetParent !== null) {
                    b.click();
                    return 'clicked button: ' + txt.substring(0, 20);
                }
            }

            // Debug: listar submits disponibles
            var info = [];
            for (var s of submits) {
                info.push(s.value + '|visible:' + (s.offsetParent !== null));
            }
            return 'not_found. submits: ' + info.join(', ');
        """)
        print(f"[Cookies] Confirm result: {confirm_result}")
        time.sleep(3)

        # Si no encontramos confirm, navegar al carrito de todas formas
        current_url = driver.current_url
        print(f"[Cookies] URL actual: {current_url}")

        # RETRY: Buscar link al carrito y clickearlo (esto genera las cookies!)
        if 'cart' not in current_url:
            print("[Cookies] RETRY: Buscando link al carrito...")
            time.sleep(2)
            retry_result = driver.execute_script("""
                // Buscar links al carrito/checkout
                var checkoutLinks = document.querySelectorAll('a[href*="checkout"], a[href*="cart"]');
                for (var link of checkoutLinks) {
                    var text = (link.textContent || '').toLowerCase();
                    if (!text.includes('empty') && !text.includes('shopping') && link.offsetParent !== null) {
                        link.click();
                        return 'Clicked cart link: ' + text.substring(0, 30);
                    }
                }
                return 'No cart link found';
            """)
            print(f"[Cookies] Retry result: {retry_result}")
            time.sleep(5)
            print(f"[Cookies] URL after retry: {driver.current_url}")

        # Navegar al carrito final
        print("[Cookies] Navegando al carrito...")
        driver.get("https://ticketing.colosseo.it/en/cart/")
        time.sleep(5)

        # Obtener cookies via CDP
        result = driver.execute_cdp_cmd('Network.getAllCookies', {})
        cdp_cookies = result.get('cookies', [])

        cookies = []
        critical = ['PHPSESSID', 'octofence-waap-id', 'octofence-waap-sessid']
        for c in cdp_cookies:
            domain = c.get('domain', '')
            if 'colosseo' in domain:
                cookies.append({
                    'name': c.get('name'),
                    'value': c.get('value'),
                    'domain': domain,
                    'path': c.get('path', '/'),
                    'secure': c.get('secure', False),
                    'httpOnly': c.get('httpOnly', False)
                })

        print(f"[Cookies] Obtenidas {len(cookies)} cookies:")
        for c in cookies:
            marker = '*' if c['name'] in critical else '-'
            print(f"  {marker} {c['name']}")

        # Verificar cookies críticas
        cookie_names = [c['name'] for c in cookies]
        has_all_critical = all(crit in cookie_names for crit in critical)
        if has_all_critical:
            print("[Cookies] TODAS las cookies críticas obtenidas!")
        else:
            missing = [c for c in critical if c not in cookie_names]
            print(f"[Cookies] Faltan: {missing}")

        # Guardar estado
        with state_lock:
            state["cookies"] = cookies
            state["cookies_timestamp"] = datetime.now()
            state["driver"] = driver
            state["status"] = "ready"

        return True

    except Exception as e:
        print(f"[Cookies] Error: {e}")
        import traceback
        traceback.print_exc()
        if driver:
            try:
                driver.quit()
            except:
                pass
        with state_lock:
            state["status"] = f"error: {str(e)}"
        return False


def ensure_valid_cookies():
    """Asegura que tenemos cookies válidas"""
    with state_lock:
        cookies_age = None
        if state["cookies_timestamp"]:
            cookies_age = (datetime.now() - state["cookies_timestamp"]).total_seconds()

        need_refresh = (
            not state["cookies"] or
            cookies_age is None or
            cookies_age > COOKIE_MAX_AGE
        )

    if need_refresh:
        return refresh_cookies()
    return True


def query_calendar(guid, month, year):
    """Hace una consulta al calendario usando el navegador"""
    global state

    print(f"[Query] Consultando {month}/{year} para {guid[:8]}...")

    with state_lock:
        driver = state.get("driver")
        if not driver:
            return None, "No hay driver disponible"

    try:
        # Asegurar que estamos en el dominio correcto
        current_url = driver.current_url
        if 'ticketing.colosseo.it' not in current_url:
            print("[Query] Navegando al sitio...")
            driver.get(TOUR_URL)
            time.sleep(3)

        # Hacer la consulta AJAX con URL absoluta
        result = driver.execute_script("""
            return new Promise((resolve) => {
                var formData = new FormData();
                formData.append('action', 'mtajax_calendars_month');
                formData.append('guids[entranceEvent_guid][]', arguments[0]);
                formData.append('singleDaySession', 'false');
                formData.append('month', arguments[1]);
                formData.append('year', arguments[2]);

                fetch('https://ticketing.colosseo.it/mtajax/calendars_month', {
                    method: 'POST',
                    body: formData,
                    credentials: 'include'
                })
                .then(r => r.json())
                .then(data => resolve({success: true, data: data}))
                .catch(e => resolve({success: false, error: e.message}));
            });
        """, guid, str(month), str(year))

        if result and result.get('success'):
            with state_lock:
                state["last_query"] = datetime.now().isoformat()
            return result.get('data'), None
        else:
            return None, result.get('error', 'Unknown error')

    except Exception as e:
        return None, str(e)


# ============== ENDPOINTS ==============

@app.route('/')
def home():
    """Estado del servicio"""
    with state_lock:
        cookies_count = len(state["cookies"])
        cookies_age = None
        if state["cookies_timestamp"]:
            cookies_age = int((datetime.now() - state["cookies_timestamp"]).total_seconds())

    return jsonify({
        "service": "Colosseo Railway API",
        "status": state["status"],
        "cookies_count": cookies_count,
        "cookies_age_seconds": cookies_age,
        "last_query": state.get("last_query"),
        "endpoints": {
            "/": "Este endpoint - estado del servicio",
            "/refresh": "POST - Refrescar cookies",
            "/query": "GET - Consultar disponibilidad (?guid=...&month=12&year=2025)",
            "/cookies": "GET - Ver cookies actuales"
        }
    })


@app.route('/refresh', methods=['POST'])
def refresh():
    """Refresca las cookies"""
    success = refresh_cookies()
    with state_lock:
        return jsonify({
            "success": success,
            "status": state["status"],
            "cookies_count": len(state["cookies"])
        })


@app.route('/query')
def query():
    """Consulta disponibilidad del calendario"""
    guid = request.args.get('guid', 'a9a4b0f8-bf3c-4f22-afcd-196a27be04b9')
    month = request.args.get('month', datetime.now().month)
    year = request.args.get('year', datetime.now().year)

    # Asegurar cookies válidas
    if not ensure_valid_cookies():
        return jsonify({
            "success": False,
            "error": "No se pudieron obtener cookies válidas",
            "status": state["status"]
        }), 503

    # Hacer consulta
    data, error = query_calendar(guid, month, year)

    if error:
        return jsonify({
            "success": False,
            "error": error
        }), 500

    return jsonify({
        "success": True,
        "guid": guid,
        "month": month,
        "year": year,
        "data": data
    })


@app.route('/cookies')
def get_cookies():
    """Devuelve las cookies actuales"""
    with state_lock:
        return jsonify({
            "cookies": state["cookies"],
            "timestamp": state["cookies_timestamp"].isoformat() if state["cookies_timestamp"] else None,
            "count": len(state["cookies"])
        })


def init_service():
    """Inicializa el servicio en background"""
    print("[Init] Iniciando servicio...")
    start_xvfb()
    time.sleep(2)
    refresh_cookies()
    print("[Init] Servicio listo")


if __name__ == "__main__":
    # Iniciar en background
    init_thread = Thread(target=init_service, daemon=True)
    init_thread.start()

    # Iniciar Flask
    port = int(os.environ.get('PORT', 8080))
    print(f"[Flask] Iniciando en puerto {port}...")
    app.run(host='0.0.0.0', port=port, threaded=True)

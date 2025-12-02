"""
Módulo de navegador stealth con técnicas avanzadas anti-detección.
Diseñado específicamente para evadir Octofence y otros sistemas anti-bot.
Soporta rotación de proxies para evitar bloqueos por IP.
"""

import time
import random
import signal
from threading import Event
from typing import Optional, Tuple
from colosseo_config import config
from proxy_manager import ProxyManager

# Control de parada global
stop_event = Event()


def signal_handler(sig, frame):
    """Maneja señales de interrupción (CTRL+C) para detener de forma segura"""
    print("\n\n⚠️  CTRL+C detectado - Deteniendo proceso de forma segura...")
    stop_event.set()


signal.signal(signal.SIGINT, signal_handler)


def check_for_stop() -> bool:
    """
    Verifica si el usuario ha solicitado detener el proceso.

    Returns:
        True si se debe detener, False en caso contrario
    """
    if stop_event.is_set():
        print("🛑 Proceso detenido por el usuario")
        return True
    return False


# Intentar importar undetected-chromedriver
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    print("⚠️  undetected-chromedriver no está instalado")
    print("📦 Instálalo con: pip install undetected-chromedriver")
    print("🔄 Usando método alternativo con Selenium estándar...\n")


class StealthBrowser:
    """Gestor de navegador con capacidades anti-detección"""

    # Scripts de evasión JavaScript
    EVASION_SCRIPT = """
        // Eliminar webdriver del navegador
        delete Object.getPrototypeOf(navigator).webdriver;

        // Simular Chrome real con plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                {name: 'Chrome PDF Plugin', description: 'Portable Document Format'},
                {name: 'Chrome PDF Viewer', description: 'Portable Document Format'},
                {name: 'Native Client', description: 'Native Client Executable'}
            ]
        });

        // Ocultar automation
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
            configurable: true
        });

        // Chrome object
        window.navigator.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        // MimeTypes realistas
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => [
                {type: "application/pdf", suffixes: "pdf"},
                {type: "application/x-google-chrome-pdf", suffixes: "pdf"},
                {type: "application/x-nacl", suffixes: ""},
                {type: "application/x-pnacl", suffixes: ""}
            ]
        });

        // Languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });

        // Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Silenciar console.debug
        window.console.debug = () => {};
    """

    @staticmethod
    def create_undetected_driver(proxy: str = None):
        """
        Crea un driver usando undetected-chromedriver (método más efectivo).

        Args:
            proxy: Proxy a usar en formato host:port o user:pass@host:port

        Returns:
            Driver de Chrome o None si falla
        """
        if not UNDETECTED_AVAILABLE:
            return None

        print("Iniciando navegador anti-detección...")

        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={config.USER_AGENT}")

        # Configurar proxy si se proporciona
        if proxy:
            # Limpiar formato de URL si viene con protocolo
            proxy_clean = proxy.replace("http://", "").replace("https://", "")
            options.add_argument(f"--proxy-server=http://{proxy_clean}")
            print(f"[Proxy] Configurado para navegador: {proxy_clean[:30]}...")

        # Deshabilitar características que delatan automatización
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)

        try:
            driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)

            # Inyectar scripts de evasión
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": StealthBrowser.EVASION_SCRIPT
            })

            print("✅ Navegador anti-detección iniciado correctamente")
            return driver

        except Exception as e:
            print(f"❌ Error creando driver undetected: {e}")
            return None

    @staticmethod
    def create_stealth_driver_fallback(proxy: str = None):
        """
        Método alternativo usando Selenium estándar con técnicas avanzadas.

        Args:
            proxy: Proxy a usar en formato host:port o user:pass@host:port

        Returns:
            Driver de Chrome
        """
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        print("Iniciando navegador con método alternativo...")

        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)

        # Configuraciones adicionales anti-detección
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--incognito")

        # Configurar proxy si se proporciona
        if proxy:
            proxy_clean = proxy.replace("http://", "").replace("https://", "")
            options.add_argument(f"--proxy-server=http://{proxy_clean}")
            print(f"[Proxy] Configurado para navegador: {proxy_clean[:30]}...")

        if config.HEADLESS:
            options.add_argument("--headless=new")

        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 1
        }
        options.add_experimental_option("prefs", prefs)
        options.add_argument(f"user-agent={config.USER_AGENT}")

        driver = webdriver.Chrome(options=options)

        # Inyectar scripts de evasión
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": StealthBrowser.EVASION_SCRIPT
        })

        print("✅ Navegador iniciado con técnicas anti-detección")
        return driver

    @staticmethod
    def create_driver(proxy: str = None, use_proxy_manager: bool = None):
        """
        Crea un driver con la mejor técnica disponible.

        Args:
            proxy: Proxy específico a usar (opcional)
            use_proxy_manager: Si usar ProxyManager para obtener proxy automáticamente

        Returns:
            Driver de Chrome o None si falla
        """
        # Determinar si usar proxy manager
        use_proxy_manager = use_proxy_manager if use_proxy_manager is not None else config.PROXY_ENABLED

        # Obtener proxy del manager si está habilitado y no se proporcionó uno específico
        if not proxy and use_proxy_manager:
            pm = ProxyManager(
                proxy_file=config.PROXY_FILE,
                rotation_mode=config.PROXY_ROTATION_MODE
            )
            if pm.enabled:
                proxy = pm.get_proxy_for_selenium()

        driver = None

        if UNDETECTED_AVAILABLE:
            driver = StealthBrowser.create_undetected_driver(proxy=proxy)

        if not driver:
            driver = StealthBrowser.create_stealth_driver_fallback(proxy=proxy)

        return driver

    @staticmethod
    def simulate_human_delay():
        """Simula delays humanos aleatorios"""
        time.sleep(random.uniform(config.HUMAN_DELAY_MIN, config.HUMAN_DELAY_MAX))

    @staticmethod
    def wait_for_page_load(driver, timeout: int = None, simulate_behavior: bool = True) -> bool:
        """
        Espera a que la página cargue correctamente, detectando bloqueos de Octofence.

        Args:
            driver: WebDriver de Selenium
            timeout: Tiempo máximo de espera en segundos
            simulate_behavior: Si True, simula comportamiento humano

        Returns:
            True si la página cargó exitosamente, False si fue bloqueada
        """
        if timeout is None:
            timeout = config.PAGE_LOAD_TIMEOUT

        print("\n" + "=" * 60)
        print("🌐 Intentando acceder al sitio...")
        print("⚠️  IMPORTANTE: Puedes presionar CTRL+C para detener")
        print("=" * 60 + "\n")

        # Importar comportamiento humano si está habilitado
        human_sim = None
        if simulate_behavior:
            try:
                from human_behavior import HumanBehaviorSimulator
                human_sim = HumanBehaviorSimulator(driver)
                print("🎭 Simulación de comportamiento humano activada")
            except Exception as e:
                print(f"⚠️  No se pudo activar comportamiento humano: {e}")

        end_time = time.time() + timeout
        attempts = 0
        last_check = ""
        last_behavior_time = time.time()

        while time.time() < end_time and not check_for_stop():
            attempts += 1

            try:
                title = driver.title.lower()
                url = driver.current_url
                page_source = driver.page_source.lower()

                # Detectar bloqueo de Octofence
                if any(keyword in page_source for keyword in config.BLOCKED_KEYWORDS):
                    print("\n" + "=" * 60)
                    print("❌ OCTOFENCE HA DETECTADO AUTOMATIZACIÓN")
                    print("=" * 60)
                    print("⚠️  El sitio ha bloqueado este intento")
                    print("💡 RECOMENDACIONES:")
                    print("   1. Espera 5-10 minutos antes de reintentar")
                    print("   2. Usa una VPN o cambia tu IP")
                    print("   3. Prueba desde otro dispositivo")
                    print("   4. Considera acceder manualmente al sitio")
                    print("=" * 60 + "\n")
                    stop_event.set()
                    return False

                # Detectar waiting page
                if any(keyword in title or keyword in page_source
                       for keyword in config.WAITING_KEYWORDS):
                    if last_check != "waiting":
                        print(f"⏳ Esperando verificación de seguridad...")
                        last_check = "waiting"
                    time.sleep(config.SECURITY_CHECK_INTERVAL)
                    continue

                # Detectar página exitosa
                if (any(keyword in title or keyword in url
                        for keyword in config.SUCCESS_KEYWORDS)
                        and "waiting" not in title):
                    print("✅ ¡Acceso exitoso! Verificando calendario...")
                    time.sleep(3)

                    # Verificar que no sea un bloqueo disfrazado
                    if not any(keyword in page_source
                               for keyword in config.BLOCKED_KEYWORDS):
                        print("✅ Página del calendario cargada correctamente")
                        return True
                    else:
                        print("⚠️ Posible bloqueo detectado en la página")
                        return False

                if attempts % 10 == 0:
                    print(f"⏳ Intento {attempts}... (CTRL+C para cancelar)")

            except Exception as e:
                if check_for_stop():
                    return False
                if attempts == 1:
                    print(f"⚠️ Error: {e}")

            time.sleep(2)

        if check_for_stop():
            print("\n🛑 Proceso detenido por el usuario")
            return False

        print("\n⏰ Tiempo de espera agotado")
        return False

    @staticmethod
    def extract_cookies(driver) -> list:
        """
        Extrae cookies del navegador.

        Args:
            driver: WebDriver de Selenium

        Returns:
            Lista de cookies
        """
        cookies = driver.get_cookies()
        print(f"💾 {len(cookies)} cookies extraídas")
        return cookies


# Función de conveniencia para uso rápido
def create_stealth_browser(proxy: str = None, use_proxy_manager: bool = None):
    """
    Crea y retorna un navegador stealth listo para usar.

    Args:
        proxy: Proxy específico a usar (opcional)
        use_proxy_manager: Si usar ProxyManager automáticamente

    Returns:
        WebDriver configurado con técnicas anti-detección
    """
    return StealthBrowser.create_driver(proxy=proxy, use_proxy_manager=use_proxy_manager)

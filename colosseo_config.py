"""
Configuración centralizada para el monitor de disponibilidad del Colosseo.
Maneja todas las URLs, GUIDs, fechas de interés y configuraciones del sistema.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()


class ColosseoConfig:
    """Configuración centralizada para el sistema de monitoreo"""

    # URLs principales
    BASE_URL = "https://ticketing.colosseo.it"
    TOUR_URL = "https://ticketing.colosseo.it/en/eventi/24h-colosseo-foro-romano-palatino-gruppi/"
    API_ENDPOINT = "https://ticketing.colosseo.it/mtajax/calendars_month"

    # GUID del tour (puede ser configurable)
    DEFAULT_GUID = "a9a4b0f8-bf3c-4f22-afcd-196a27be04b9"

    # Archivos de persistencia
    COOKIES_FILE = "cookies_colosseo.json"
    LOG_FILE = "colosseo_monitor.log"
    REPORT_FILE = "colosseo_report.txt"

    # Configuración de navegador
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Tiempos de espera y delays (más humanos)
    PAGE_LOAD_TIMEOUT = 300  # segundos (más paciencia)
    HUMAN_DELAY_MIN = 2.5    # segundos (más lento)
    HUMAN_DELAY_MAX = 6.0    # segundos (variabilidad alta)
    SECURITY_CHECK_INTERVAL = 8  # segundos entre checks (menos agresivo)
    MOUSE_MOVE_DELAY_MIN = 0.3  # delay mínimo entre movimientos de mouse
    MOUSE_MOVE_DELAY_MAX = 1.2  # delay máximo entre movimientos de mouse
    SCROLL_DELAY_MIN = 1.0      # delay mínimo para scroll
    SCROLL_DELAY_MAX = 3.0      # delay máximo para scroll

    # Detección de estado
    BLOCKED_KEYWORDS = ["automation detected", "automation", "blocked"]
    WAITING_KEYWORDS = ["waiting", "octofence"]
    SUCCESS_KEYWORDS = ["colosseo", "eventi"]

    # Configuración desde .env
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    HEADLESS = os.getenv("HEADLESS", "false").lower() in ('1', 'true', 'yes')

    @staticmethod
    def get_default_dates(days_ahead: int = 7) -> List[str]:
        """
        Genera lista de fechas de interés por defecto.

        Args:
            days_ahead: Número de días hacia adelante desde hoy

        Returns:
            Lista de fechas en formato YYYY-MM-DD
        """
        today = datetime.now().date()
        return [(today + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(days_ahead)]

    @staticmethod
    def get_current_month() -> str:
        """Retorna el mes actual en formato YYYY-MM"""
        return datetime.now().strftime("%Y-%m")

    @staticmethod
    def parse_dates_from_env(env_key: str = "FECHAS_INTERES") -> List[str]:
        """
        Lee fechas de interés desde variable de entorno.

        Args:
            env_key: Clave de la variable de entorno

        Returns:
            Lista de fechas o fechas por defecto si no existe la variable
        """
        fechas_str = os.getenv(env_key, "")
        if fechas_str:
            return [f.strip() for f in fechas_str.split(",") if f.strip()]
        return ColosseoConfig.get_default_dates()

    @staticmethod
    def get_headers(referer: str = None) -> Dict[str, str]:
        """
        Genera headers HTTP realistas.

        Args:
            referer: URL de referencia opcional

        Returns:
            Diccionario de headers
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": ColosseoConfig.USER_AGENT,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        if referer:
            headers["Referer"] = referer
        else:
            headers["Referer"] = ColosseoConfig.TOUR_URL

        return headers


# Instancia global de configuración
config = ColosseoConfig()

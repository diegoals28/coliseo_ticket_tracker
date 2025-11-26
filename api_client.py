"""
Cliente de API para consultar la disponibilidad del calendario del Colosseo.
Maneja cookies, sesiones y realiza peticiones HTTP con headers realistas.
"""

import json
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from colosseo_config import config


class ColosseoAPIClient:
    """Cliente para interactuar con la API del calendario del Colosseo"""

    def __init__(self, cookies_file: str = None):
        """
        Inicializa el cliente de API.

        Args:
            cookies_file: Ruta al archivo de cookies (opcional)
        """
        self.cookies_file = cookies_file or config.COOKIES_FILE
        self.session = None
        self.cookies = []

    def save_cookies(self, cookies: List[dict]) -> bool:
        """
        Guarda cookies en un archivo JSON.

        Args:
            cookies: Lista de cookies a guardar

        Returns:
            True si se guardaron exitosamente
        """
        try:
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            print(f"💾 {len(cookies)} cookies guardadas en {self.cookies_file}")
            return True
        except Exception as e:
            print(f"❌ Error guardando cookies: {e}")
            return False

    def load_cookies(self) -> bool:
        """
        Carga cookies desde un archivo JSON.

        Returns:
            True si se cargaron exitosamente
        """
        try:
            with open(self.cookies_file, "r", encoding="utf-8") as f:
                self.cookies = json.load(f)
            print(f"📂 {len(self.cookies)} cookies cargadas desde {self.cookies_file}")
            return True
        except FileNotFoundError:
            print(f"⚠️  Archivo de cookies no encontrado: {self.cookies_file}")
            return False
        except Exception as e:
            print(f"❌ Error cargando cookies: {e}")
            return False

    def create_session_from_cookies(self, cookies: List[dict] = None) -> requests.Session:
        """
        Crea una sesión de requests con las cookies proporcionadas.

        Args:
            cookies: Lista de cookies (usa las cargadas si no se proporciona)

        Returns:
            Sesión de requests configurada
        """
        if cookies is None:
            cookies = self.cookies

        session = requests.Session()

        # Agregar cookies a la sesión
        for cookie in cookies:
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain"),
                path=cookie.get("path", "/")
            )

        self.session = session
        return session

    def validate_cookies(self, cookies: List[dict] = None) -> Tuple[bool, str]:
        """
        Valida que las cookies sean funcionales haciendo una petición de prueba.

        Args:
            cookies: Cookies a validar (usa las cargadas si no se proporciona)

        Returns:
            Tupla (es_valida, mensaje)
        """
        if cookies is None:
            cookies = self.cookies

        if not cookies:
            return False, "No hay cookies para validar"

        # Crear sesión temporal
        temp_session = requests.Session()

        for cookie in cookies:
            temp_session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain"),
                path=cookie.get("path", "/")
            )

        try:
            # Hacer petición de prueba a la página principal
            headers = config.get_headers()
            response = temp_session.get(
                config.BASE_URL,
                headers=headers,
                timeout=10,
                allow_redirects=True
            )

            # Verificar respuesta
            if response.status_code == 403:
                return False, "Cookies bloqueadas (403 Forbidden)"

            # Verificar si devuelve HTML de Octofence
            if 'octofence' in response.text.lower() and 'waiting' in response.text.lower():
                return False, "Cookies detectadas por Octofence"

            # Si llegamos aquí, las cookies parecen válidas
            return True, "Cookies válidas"

        except requests.Timeout:
            return False, "Timeout en validación"
        except requests.RequestException as e:
            return False, f"Error en validación: {str(e)}"

    def fetch_calendar_data(
        self,
        guid: str = None,
        month: str = None,
        cookies: List[dict] = None
    ) -> Tuple[Optional[Dict], int, str]:
        """
        Consulta los datos del calendario.

        Args:
            guid: GUID del evento/tour
            month: Mes a consultar (formato YYYY-MM)
            cookies: Cookies a usar (usa las cargadas si no se proporciona)

        Returns:
            Tupla (datos_json, status_code, mensaje)
        """
        if guid is None:
            guid = config.DEFAULT_GUID

        if month is None:
            month = config.get_current_month()

        # Crear o actualizar sesión con cookies
        if cookies:
            self.create_session_from_cookies(cookies)
        elif not self.session:
            if not self.load_cookies():
                return None, 0, "No hay cookies disponibles"
            self.create_session_from_cookies()

        # Validar cookies antes de hacer la petición (opcional pero recomendado)
        # Comentado por defecto para evitar peticiones extra, pero útil para debugging
        # is_valid, validation_msg = self.validate_cookies()
        # if not is_valid:
        #     print(f"⚠️ Advertencia: {validation_msg}")

        # Preparar headers
        headers = config.get_headers()

        # Preparar payload con formato correcto
        # La API espera: action, guids[entranceEvent_guid][], year, month, day
        year, month_num = month.split("-")
        payload = (
            f"action=midaabc_calendars_month&"
            f"guids[entranceEvent_guid][]={guid}&"
            f"year={year}&"
            f"month={month_num}&"
            f"day="
        )

        try:
            print(f"🌐 Consultando calendario para {month}...")

            response = self.session.post(
                config.API_ENDPOINT,
                data=payload,
                headers=headers,
                timeout=10
            )

            status_code = response.status_code

            if status_code == 200:
                # Verificar si es HTML (Octofence) en lugar de JSON
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type:
                    print("🛡️ OCTOFENCE DETECTADO: La respuesta es HTML en lugar de JSON")
                    print("❌ Las cookies no son válidas o han expirado")
                    print("💡 Ejecuta: python extraer_cookies_directo.py")
                    return None, status_code, "Bloqueado por Octofence - cookies inválidas"

                # Verificar que el contenido parezca JSON
                response_text = response.text.strip()
                if response_text.startswith('<!DOCTYPE') or response_text.startswith('<html'):
                    print("🛡️ OCTOFENCE DETECTADO: Respuesta HTML detectada")
                    print("❌ Las cookies no son válidas o han expirado")
                    print("💡 Ejecuta: python extraer_cookies_directo.py")
                    return None, status_code, "Bloqueado por Octofence - HTML recibido"

                try:
                    data = response.json()

                    # Verificar si es un error encapsulado en JSON
                    if isinstance(data, list) and len(data) > 0:
                        if isinstance(data[0], dict) and 'code' in data[0]:
                            error_code = data[0].get('code')
                            error_msg = data[0].get('message', 'Sin mensaje')
                            print(f"❌ Error de API: Código {error_code} - {error_msg}")
                            return None, error_code, f"API Error {error_code}: {error_msg}"

                    if "data" in data:
                        print(f"✅ Datos recibidos correctamente")
                        return data.get("data", {}), status_code, "OK"
                    else:
                        print("⚠️ Respuesta sin campo 'data', usando datos directamente")
                        return data, status_code, "OK (formato alternativo)"
                except json.JSONDecodeError:
                    print("❌ Error: La respuesta no es JSON válido")
                    print(f"📄 Primeros 200 caracteres: {response_text[:200]}")
                    return None, status_code, "JSON inválido"
            else:
                print(f"⚠️ Status code: {status_code}")
                return None, status_code, f"HTTP {status_code}"

        except requests.Timeout:
            print("⏰ Timeout en la consulta")
            return None, 0, "Timeout"
        except requests.RequestException as e:
            print(f"❌ Error en la petición: {e}")
            return None, 0, str(e)

    def fetch_multiple_months(
        self,
        guid: str = None,
        months: List[str] = None,
        cookies: List[dict] = None
    ) -> Dict[str, Dict]:
        """
        Consulta múltiples meses del calendario.

        Args:
            guid: GUID del evento/tour
            months: Lista de meses (formato YYYY-MM)
            cookies: Cookies a usar

        Returns:
            Diccionario con datos por mes {mes: datos}
        """
        if months is None:
            months = [config.get_current_month()]

        results = {}

        for month in months:
            print(f"\n📅 Consultando mes: {month}")
            data, status, msg = self.fetch_calendar_data(guid, month, cookies)

            if data:
                results[month] = data
            else:
                print(f"⚠️ No se obtuvieron datos para {month}: {msg}")
                results[month] = {}

        return results


class AvailabilityChecker:
    """Analiza la disponibilidad de fechas en los datos del calendario"""

    STATUS_AVAILABLE = "available"
    STATUS_SOLDOUT = "soldout"
    STATUS_CLOSED = "closed"
    STATUS_UNKNOWN = "unknown"

    @staticmethod
    def normalize_data(data):
        """
        Convierte datos de lista a diccionario si es necesario.

        Args:
            data: Datos en formato dict o list

        Returns:
            Diccionario con fechas como keys
        """
        if isinstance(data, dict):
            return data

        if isinstance(data, list):
            result = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                # Intentar extraer fecha
                date = item.get("date") or item.get("startDateTime", "").split("T")[0]
                if date:
                    # Si la fecha ya existe, combinar capacidades
                    if date in result:
                        existing = result[date]
                        # Sumar capacidades de múltiples timeslots
                        if "capacity" in item and "capacity" in existing:
                            existing["capacity"] = existing.get("capacity", 0) + item.get("capacity", 0)
                        if "originalCapacity" in item and "originalCapacity" in existing:
                            existing["originalCapacity"] = existing.get("originalCapacity", 0) + item.get("originalCapacity", 0)
                    else:
                        result[date] = item
            return result

        return {}

    @staticmethod
    def extract_complete_info(item: Dict) -> Dict:
        """
        Extrae toda la información disponible de un elemento del calendario.

        Args:
            item: Elemento individual del calendario

        Returns:
            Diccionario con toda la información extraída
        """
        info = {
            # Información básica
            "fecha": item.get("date") or item.get("startDateTime", "").split("T")[0],
            "estado": item.get("status", AvailabilityChecker.STATUS_UNKNOWN),

            # Capacidad
            "capacidad": item.get("capacity"),
            "capacidad_original": item.get("originalCapacity"),
            "plazas_ocupadas": None,

            # Precios
            "precio": item.get("price"),
            "precio_formateado": item.get("formattedPrice"),
            "moneda": item.get("currency", "EUR"),

            # Horarios
            "hora_inicio": item.get("startTime") or item.get("startDateTime", "").split("T")[1] if "T" in item.get("startDateTime", "") else None,
            "hora_fin": item.get("endTime") or item.get("endDateTime", "").split("T")[1] if "T" in item.get("endDateTime", "") else None,
            "duracion": item.get("duration"),

            # Información del evento
            "titulo": item.get("title") or item.get("name"),
            "descripcion": item.get("description"),
            "tipo_evento": item.get("eventType") or item.get("type"),
            "categoria": item.get("category"),

            # IDs y referencias
            "guid": item.get("guid") or item.get("id"),
            "evento_id": item.get("eventId") or item.get("entranceEventId"),

            # Información adicional
            "idioma": item.get("language"),
            "guia_incluida": item.get("guidedTour") or item.get("withGuide"),
            "acceso_rapido": item.get("skipTheLine") or item.get("fastTrack"),
            "requisitos": item.get("requirements"),
            "restricciones": item.get("restrictions"),

            # Ubicación
            "ubicacion": item.get("location") or item.get("venue"),
            "punto_encuentro": item.get("meetingPoint"),

            # Estado del ticket
            "disponible_online": item.get("onlineBooking"),
            "requiere_confirmacion": item.get("requiresConfirmation"),
            "cancelable": item.get("cancellable") or item.get("refundable"),
            "politica_cancelacion": item.get("cancellationPolicy"),

            # URLs
            "url_reserva": item.get("bookingUrl") or item.get("url"),
            "url_imagen": item.get("imageUrl") or item.get("image"),

            # Metadata
            "ultima_actualizacion": item.get("lastUpdate") or item.get("updatedAt"),
            "fecha_creacion": item.get("createdAt"),
        }

        # Calcular plazas ocupadas si tenemos ambos datos
        if info["capacidad"] is not None and info["capacidad_original"] is not None:
            try:
                info["plazas_ocupadas"] = int(info["capacidad_original"]) - int(info["capacidad"])
            except (ValueError, TypeError):
                pass

        # Limpiar valores None para hacer el diccionario más compacto
        return {k: v for k, v in info.items() if v is not None}

    @staticmethod
    def extract_all_fields(data) -> Dict[str, set]:
        """
        Analiza todos los campos presentes en los datos para ver qué información está disponible.

        Args:
            data: Datos del calendario

        Returns:
            Diccionario con todos los campos encontrados y ejemplos
        """
        data = AvailabilityChecker.normalize_data(data)

        all_fields = {}

        for date, item in data.items():
            if isinstance(item, dict):
                for key, value in item.items():
                    if key not in all_fields:
                        all_fields[key] = {
                            "ejemplos": set(),
                            "tipo": type(value).__name__
                        }

                    # Agregar ejemplo si no es muy largo
                    if value is not None:
                        str_value = str(value)
                        if len(str_value) < 100:
                            all_fields[key]["ejemplos"].add(str_value)

        # Convertir sets a listas para JSON serializable
        for key in all_fields:
            all_fields[key]["ejemplos"] = list(all_fields[key]["ejemplos"])[:5]

        return all_fields

    @staticmethod
    def check_date_availability(data: Dict, date: str) -> Optional[Dict]:
        """
        Verifica la disponibilidad de una fecha específica con información completa.

        Args:
            data: Datos del calendario
            date: Fecha a verificar (formato YYYY-MM-DD)

        Returns:
            Diccionario con toda la información disponible o None
        """
        data = AvailabilityChecker.normalize_data(data)

        if not data or date not in data:
            return None

        date_info = data[date]

        # Usar la función de extracción completa
        if isinstance(date_info, dict):
            return AvailabilityChecker.extract_complete_info(date_info)

        return None

    @staticmethod
    def find_available_dates(data) -> List[Dict]:
        """
        Encuentra todas las fechas disponibles en los datos con información completa.

        Args:
            data: Datos del calendario (dict o list)

        Returns:
            Lista de fechas disponibles con toda su información
        """
        available = []

        # Normalizar datos
        data = AvailabilityChecker.normalize_data(data)

        for date, info in data.items():
            if isinstance(info, dict):
                # Determinar disponibilidad basándose en capacity
                capacity = info.get("capacity")
                status = info.get("status")

                # Considerar disponible si tiene capacity > 0 o status disponible
                is_available = False
                if status == AvailabilityChecker.STATUS_AVAILABLE:
                    is_available = True
                elif capacity is not None and capacity > 0:
                    is_available = True

                if is_available:
                    # Extraer información completa
                    complete_info = AvailabilityChecker.extract_complete_info(info)
                    available.append(complete_info)

        return sorted(available, key=lambda x: x["fecha"])

    @staticmethod
    def find_low_capacity_dates(data, threshold: int = 10) -> List[Dict]:
        """
        Encuentra fechas con baja capacidad (urgencia).

        Args:
            data: Datos del calendario (dict o list)
            threshold: Umbral de capacidad

        Returns:
            Lista de fechas con capacidad <= threshold
        """
        low_capacity = []

        # Normalizar datos
        data = AvailabilityChecker.normalize_data(data)

        for date, info in data.items():
            if isinstance(info, dict):
                capacity = info.get("capacity")
                if (capacity is not None
                        and capacity <= threshold
                        and info.get("status") == AvailabilityChecker.STATUS_AVAILABLE):
                    low_capacity.append({
                        "fecha": date,
                        "capacidad": capacity,
                        "precio": info.get("price"),
                        "urgencia": "ALTA" if capacity <= 5 else "MEDIA",
                    })

        return sorted(low_capacity, key=lambda x: (x["capacidad"], x["fecha"]))


# Funciones de conveniencia
def quick_check(dates: List[str], guid: str = None) -> Dict:
    """
    Realización rápida de chequeo de disponibilidad.

    Args:
        dates: Lista de fechas a verificar
        guid: GUID del tour (opcional)

    Returns:
        Diccionario con disponibilidad por fecha
    """
    client = ColosseoAPIClient()

    if not client.load_cookies():
        print("❌ No se pueden cargar las cookies. Ejecuta primero el navegador.")
        return {}

    data, status, msg = client.fetch_calendar_data(guid)

    if not data:
        print(f"❌ Error obteniendo datos: {msg}")
        return {}

    checker = AvailabilityChecker()
    results = {}

    for date in dates:
        availability = checker.check_date_availability(data, date)
        if availability:
            results[date] = availability

    return results

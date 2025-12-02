"""
Gestor de proxies rotativos para evitar bloqueos.
Soporta proxies HTTP/HTTPS y rotación automática.
"""

import os
import random
import time
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ProxyInfo:
    """Información sobre un proxy individual"""
    url: str
    protocol: str = "http"
    failures: int = 0
    successes: int = 0
    last_used: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    avg_response_time: float = 0.0
    is_active: bool = True

    @property
    def success_rate(self) -> float:
        """Calcula la tasa de éxito del proxy"""
        total = self.failures + self.successes
        if total == 0:
            return 1.0
        return self.successes / total

    def mark_success(self, response_time: float = 0.0):
        """Marca un uso exitoso del proxy"""
        self.successes += 1
        self.last_used = datetime.now()
        self.is_active = True
        # Actualizar tiempo de respuesta promedio
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time + response_time) / 2

    def mark_failure(self):
        """Marca un fallo del proxy"""
        self.failures += 1
        self.last_failure = datetime.now()
        # Desactivar después de 3 fallos consecutivos recientes
        if self.failures >= 3 and self.success_rate < 0.3:
            self.is_active = False


class ProxyManager:
    """
    Gestor de proxies con rotación y health checking.

    Soporta:
    - Carga desde archivo de texto
    - Carga desde variable de entorno
    - Rotación round-robin o aleatoria
    - Tracking de salud de cada proxy
    - Reactivación automática de proxies
    """

    def __init__(
        self,
        proxy_file: str = None,
        rotation_mode: str = "round_robin",
        max_failures: int = 3,
        reactivate_after_minutes: int = 30
    ):
        """
        Inicializa el gestor de proxies.

        Args:
            proxy_file: Archivo con lista de proxies (uno por línea)
            rotation_mode: "round_robin" o "random"
            max_failures: Fallos máximos antes de desactivar
            reactivate_after_minutes: Minutos para reintentar proxy fallido
        """
        self.proxies: List[ProxyInfo] = []
        self.current_index = 0
        self.rotation_mode = rotation_mode
        self.max_failures = max_failures
        self.reactivate_after = timedelta(minutes=reactivate_after_minutes)
        self.request_count = 0
        self.enabled = False

        # Cargar proxies
        self._load_proxies(proxy_file)

    def _load_proxies(self, proxy_file: str = None):
        """Carga proxies desde archivo o variable de entorno"""

        # Primero intentar desde variable de entorno
        env_proxies = os.getenv("PROXY_LIST", "")
        if env_proxies:
            for proxy_url in env_proxies.split(","):
                proxy_url = proxy_url.strip()
                if proxy_url:
                    self._add_proxy(proxy_url)

        # Luego cargar desde archivo
        file_path = proxy_file or os.getenv("PROXY_FILE", "proxies.txt")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            self._add_proxy(line)
                print(f"[ProxyManager] Cargados {len(self.proxies)} proxies desde {file_path}")
            except Exception as e:
                print(f"[ProxyManager] Error leyendo archivo de proxies: {e}")

        self.enabled = len(self.proxies) > 0

        if self.enabled:
            print(f"[ProxyManager] Sistema de proxies ACTIVADO con {len(self.proxies)} proxies")
        else:
            print("[ProxyManager] Sistema de proxies DESACTIVADO (sin proxies configurados)")

    def _add_proxy(self, proxy_url: str):
        """Agrega un proxy a la lista"""
        # Normalizar URL del proxy
        if not proxy_url.startswith(("http://", "https://", "socks4://", "socks5://")):
            proxy_url = f"http://{proxy_url}"

        # Determinar protocolo
        protocol = proxy_url.split("://")[0]

        # Evitar duplicados
        for p in self.proxies:
            if p.url == proxy_url:
                return

        self.proxies.append(ProxyInfo(url=proxy_url, protocol=protocol))

    def add_proxy(self, proxy_url: str):
        """API pública para agregar un proxy"""
        self._add_proxy(proxy_url)
        self.enabled = len(self.proxies) > 0

    def get_active_proxies(self) -> List[ProxyInfo]:
        """Obtiene lista de proxies activos"""
        # Reactivar proxies que hayan pasado el tiempo de espera
        now = datetime.now()
        for proxy in self.proxies:
            if not proxy.is_active and proxy.last_failure:
                if now - proxy.last_failure > self.reactivate_after:
                    proxy.is_active = True
                    proxy.failures = 0
                    print(f"[ProxyManager] Proxy reactivado: {proxy.url}")

        return [p for p in self.proxies if p.is_active]

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """
        Obtiene el siguiente proxy para usar.

        Returns:
            Diccionario con proxies para requests {"http": url, "https": url}
            o None si no hay proxies disponibles
        """
        if not self.enabled:
            return None

        active = self.get_active_proxies()

        if not active:
            print("[ProxyManager] No hay proxies activos disponibles")
            # Intentar reactivar todos
            for proxy in self.proxies:
                proxy.is_active = True
                proxy.failures = 0
            active = self.proxies
            if not active:
                return None

        # Seleccionar proxy según modo de rotación
        if self.rotation_mode == "random":
            proxy = random.choice(active)
        else:  # round_robin
            self.current_index = self.current_index % len(active)
            proxy = active[self.current_index]
            self.current_index += 1

        proxy.last_used = datetime.now()
        self.request_count += 1

        # Formato para requests
        proxy_dict = {
            "http": proxy.url,
            "https": proxy.url
        }

        return proxy_dict

    def get_proxy_for_selenium(self) -> Optional[str]:
        """
        Obtiene un proxy formateado para Selenium/Chrome.

        Returns:
            String con formato host:port para Chrome
        """
        proxy_dict = self.get_next_proxy()
        if not proxy_dict:
            return None

        # Extraer host:port de la URL
        url = proxy_dict["http"]
        # Quitar protocolo
        url = url.replace("http://", "").replace("https://", "")
        # Si tiene credenciales, devolverlas por separado
        if "@" in url:
            # formato: user:pass@host:port
            return url
        return url

    def mark_proxy_result(self, proxy_url: str, success: bool, response_time: float = 0.0):
        """
        Registra el resultado de usar un proxy.

        Args:
            proxy_url: URL del proxy usado
            success: Si la petición fue exitosa
            response_time: Tiempo de respuesta en segundos
        """
        for proxy in self.proxies:
            if proxy.url in proxy_url or proxy_url in proxy.url:
                if success:
                    proxy.mark_success(response_time)
                else:
                    proxy.mark_failure()
                return

    def test_proxy(self, proxy_url: str, test_url: str = "https://httpbin.org/ip", timeout: int = 10) -> Tuple[bool, float, str]:
        """
        Prueba un proxy individual.

        Args:
            proxy_url: URL del proxy a probar
            test_url: URL para hacer la prueba
            timeout: Timeout en segundos

        Returns:
            Tupla (éxito, tiempo_respuesta, mensaje)
        """
        proxies = {"http": proxy_url, "https": proxy_url}

        try:
            start = time.time()
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            elapsed = time.time() - start

            if response.status_code == 200:
                return True, elapsed, f"OK ({elapsed:.2f}s)"
            else:
                return False, elapsed, f"HTTP {response.status_code}"

        except requests.exceptions.ProxyError as e:
            return False, 0, f"Proxy error: {str(e)[:50]}"
        except requests.exceptions.Timeout:
            return False, timeout, "Timeout"
        except Exception as e:
            return False, 0, f"Error: {str(e)[:50]}"

    def test_all_proxies(self, test_url: str = "https://httpbin.org/ip") -> Dict[str, dict]:
        """
        Prueba todos los proxies configurados.

        Returns:
            Diccionario con resultados por proxy
        """
        results = {}

        for proxy in self.proxies:
            print(f"Probando {proxy.url}...", end=" ")
            success, time_taken, msg = self.test_proxy(proxy.url, test_url)

            if success:
                proxy.mark_success(time_taken)
                print(f"OK ({time_taken:.2f}s)")
            else:
                proxy.mark_failure()
                print(f"FALLO: {msg}")

            results[proxy.url] = {
                "success": success,
                "time": time_taken,
                "message": msg
            }

        return results

    def get_stats(self) -> Dict:
        """Obtiene estadísticas de uso de proxies"""
        active = len([p for p in self.proxies if p.is_active])
        total = len(self.proxies)

        return {
            "enabled": self.enabled,
            "total_proxies": total,
            "active_proxies": active,
            "inactive_proxies": total - active,
            "total_requests": self.request_count,
            "rotation_mode": self.rotation_mode,
            "proxies": [
                {
                    "url": p.url[:30] + "..." if len(p.url) > 30 else p.url,
                    "active": p.is_active,
                    "success_rate": f"{p.success_rate*100:.1f}%",
                    "successes": p.successes,
                    "failures": p.failures,
                    "avg_response_time": f"{p.avg_response_time:.2f}s"
                }
                for p in self.proxies
            ]
        }

    def clear_stats(self):
        """Reinicia las estadísticas de todos los proxies"""
        for proxy in self.proxies:
            proxy.failures = 0
            proxy.successes = 0
            proxy.avg_response_time = 0.0
            proxy.is_active = True
        self.request_count = 0


# Instancia global del proxy manager
proxy_manager = ProxyManager()


def get_proxy() -> Optional[Dict[str, str]]:
    """Función de conveniencia para obtener el siguiente proxy"""
    return proxy_manager.get_next_proxy()


def mark_result(proxy_url: str, success: bool, response_time: float = 0.0):
    """Función de conveniencia para marcar resultado"""
    proxy_manager.mark_proxy_result(proxy_url, success, response_time)

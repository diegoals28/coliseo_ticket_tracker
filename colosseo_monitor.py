"""
Aplicación principal de monitoreo de disponibilidad del Colosseo.
Orquesta el navegador stealth, la API y la generación de informes.
"""

import sys
import io
import argparse
from typing import Optional, List

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from colosseo_config import config
from stealth_browser import StealthBrowser, check_for_stop, stop_event
from api_client import ColosseoAPIClient, AvailabilityChecker
from report_generator import ReportGenerator


class ColosseoMonitor:
    """Aplicación principal de monitoreo"""

    def __init__(self, dates_of_interest: List[str] = None, guid: str = None):
        """
        Inicializa el monitor.

        Args:
            dates_of_interest: Fechas a monitorear
            guid: GUID del tour
        """
        self.dates_of_interest = dates_of_interest or config.parse_dates_from_env()
        self.guid = guid or config.DEFAULT_GUID
        self.browser = StealthBrowser()
        self.api_client = ColosseoAPIClient()
        self.report_gen = ReportGenerator()

    def obtain_cookies_via_browser(self) -> Optional[list]:
        """
        Obtiene cookies accediendo al sitio con el navegador stealth.

        Returns:
            Lista de cookies o None si falla
        """
        print("\n" + "=" * 70)
        print("🏛️  COLOSSEO MONITOR - FASE 1: OBTENCIÓN DE COOKIES")
        print("=" * 70)
        print("⚠️  Presiona CTRL+C en cualquier momento para detener")
        print("=" * 70 + "\n")

        # Crear driver
        driver = self.browser.create_driver()

        if not driver:
            print("❌ No se pudo crear el navegador")
            return None

        cookies = None

        try:
            if check_for_stop():
                return None

            print("🌐 Accediendo al sitio del Colosseo...")
            driver.get(config.TOUR_URL)

            self.browser.simulate_human_delay()

            if check_for_stop():
                return None

            # Intentar carga automática
            if self.browser.wait_for_page_load(driver):
                cookies = self.browser.extract_cookies(driver)
            else:
                # Modo manual
                print("\n💡 MODO MANUAL ACTIVADO")
                print("=" * 70)
                print("👉 El navegador permanece abierto para intervención manual")
                print("📋 INSTRUCCIONES:")
                print("   1. Resuelve cualquier verificación de seguridad")
                print("   2. Espera a que el calendario aparezca completamente")
                print("   3. Cuando veas el calendario, presiona ENTER aquí")
                print("=" * 70)

                try:
                    input("\n[Presiona ENTER cuando estés listo o CTRL+C para cancelar]\n")
                    if not check_for_stop():
                        cookies = self.browser.extract_cookies(driver)
                except KeyboardInterrupt:
                    print("\n🛑 Cancelado por el usuario")
                    stop_event.set()

        except Exception as e:
            if not check_for_stop():
                print(f"❌ Error: {e}")

        finally:
            if not check_for_stop():
                print("\n🔒 Cerrando navegador...")
            driver.quit()

        if check_for_stop():
            print("\n✅ Proceso terminado de forma segura")
            return None

        return cookies

    def fetch_and_report(self, cookies: list = None, save_report: bool = False) -> bool:
        """
        Consulta la API y genera el informe.

        Args:
            cookies: Cookies a usar (intenta cargar si no se proporciona)
            save_report: Si True, guarda el informe en archivo

        Returns:
            True si fue exitoso
        """
        print("\n" + "=" * 70)
        print("🏛️  COLOSSEO MONITOR - FASE 2: CONSULTA Y REPORTE")
        print("=" * 70 + "\n")

        # Obtener datos del calendario
        data, status, msg = self.api_client.fetch_calendar_data(
            guid=self.guid,
            cookies=cookies
        )

        if not data:
            print(f"\n❌ No se pudieron obtener datos del calendario: {msg}")
            return False

        # Generar alertas urgentes
        self.report_gen.print_urgent_alerts(data, threshold=10)

        # Generar informe principal
        self.report_gen.generate_console_report(
            data,
            dates_of_interest=self.dates_of_interest
        )

        # Guardar informe si se solicita
        if save_report:
            self.report_gen.save_report_to_file(
                data,
                dates_of_interest=self.dates_of_interest
            )

        # Mostrar fechas disponibles
        checker = AvailabilityChecker()
        available_dates = checker.find_available_dates(data)

        if available_dates:
            print("📌 TODAS LAS FECHAS DISPONIBLES:")
            print("-" * 70)
            for item in available_dates[:10]:  # Mostrar máximo 10
                capacidad = item.get('capacidad', 'N/A')
                precio = item.get('precio')
                if precio:
                    print(f"  ✅ {item['fecha']}: {capacidad} plazas | €{precio}")
                else:
                    print(f"  ✅ {item['fecha']}: {capacidad} plazas")
            if len(available_dates) > 10:
                print(f"  ... y {len(available_dates) - 10} fechas más")
            print("=" * 70 + "\n")

        return True

    def run_full_check(self, use_existing_cookies: bool = False, save_report: bool = False) -> bool:
        """
        Ejecuta el chequeo completo: obtiene cookies y genera informe.

        Args:
            use_existing_cookies: Si True, intenta usar cookies guardadas
            save_report: Si True, guarda el informe en archivo

        Returns:
            True si fue exitoso
        """
        cookies = None

        # Fase 1: Obtener cookies
        if use_existing_cookies and self.api_client.load_cookies():
            print("✅ Usando cookies existentes")
            cookies = self.api_client.cookies
        else:
            cookies = self.obtain_cookies_via_browser()

            if not cookies:
                print("\n❌ No se obtuvieron cookies")
                return False

            # Guardar cookies
            self.api_client.save_cookies(cookies)

        # Fase 2: Consultar y reportar
        return self.fetch_and_report(cookies, save_report)


def main():
    """Función principal con argumentos de línea de comandos"""

    parser = argparse.ArgumentParser(
        description="Monitor de disponibilidad del Colosseo con evasión de Octofence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python colosseo_monitor.py
  python colosseo_monitor.py --dates 2025-12-20 2025-12-21 2025-12-22
  python colosseo_monitor.py --use-cookies --save
  python colosseo_monitor.py --only-report
        """
    )

    parser.add_argument(
        "--dates",
        nargs="+",
        help="Fechas específicas a monitorear (formato YYYY-MM-DD)"
    )

    parser.add_argument(
        "--guid",
        help="GUID del tour/evento a monitorear"
    )

    parser.add_argument(
        "--use-cookies",
        action="store_true",
        help="Usar cookies existentes sin abrir navegador"
    )

    parser.add_argument(
        "--save",
        action="store_true",
        help="Guardar informe en archivo"
    )

    parser.add_argument(
        "--only-report",
        action="store_true",
        help="Solo generar informe con cookies existentes"
    )

    args = parser.parse_args()

    # Crear monitor
    monitor = ColosseoMonitor(
        dates_of_interest=args.dates,
        guid=args.guid
    )

    # Ejecutar según modo
    if args.only_report:
        if not monitor.api_client.load_cookies():
            print("❌ No hay cookies guardadas. Ejecuta sin --only-report primero.")
            return 1

        success = monitor.fetch_and_report(
            cookies=monitor.api_client.cookies,
            save_report=args.save
        )
    else:
        success = monitor.run_full_check(
            use_existing_cookies=args.use_cookies,
            save_report=args.save
        )

    if success:
        print("✅ Proceso completado exitosamente")
        return 0
    else:
        print("❌ Proceso completado con errores")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Programa interrumpido por el usuario")
        sys.exit(130)

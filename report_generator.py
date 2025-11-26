"""
Generador de informes de disponibilidad del calendario del Colosseo.
Produce informes visuales en consola y archivos de texto.
"""

from typing import Dict, List, Optional
from datetime import datetime
from colosseo_config import config


class ReportGenerator:
    """Generador de informes de disponibilidad"""

    # Emojis para estados
    EMOJI_AVAILABLE = "✅"
    EMOJI_SOLDOUT = "❌"
    EMOJI_CLOSED = "🔒"
    EMOJI_UNKNOWN = "⚪"
    EMOJI_LOW_CAPACITY = "⚠️"

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
                    result[date] = item
            return result

        return {}

    @staticmethod
    def get_status_emoji(status: str) -> str:
        """
        Retorna el emoji correspondiente al estado.

        Args:
            status: Estado de la fecha

        Returns:
            Emoji representativo
        """
        status_map = {
            "available": ReportGenerator.EMOJI_AVAILABLE,
            "soldout": ReportGenerator.EMOJI_SOLDOUT,
            "closed": ReportGenerator.EMOJI_CLOSED,
        }
        return status_map.get(status, ReportGenerator.EMOJI_UNKNOWN)

    @staticmethod
    def format_date(date_str: str) -> str:
        """
        Formatea una fecha para mostrar de forma legible.

        Args:
            date_str: Fecha en formato YYYY-MM-DD

        Returns:
            Fecha formateada con día de la semana
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            days_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            day_name = days_es[date_obj.weekday()]
            return f"{date_str} ({day_name})"
        except:
            return date_str

    @staticmethod
    def generate_console_report(
        data,
        dates_of_interest: List[str] = None,
        show_all: bool = False
    ) -> None:
        """
        Genera un informe visual en consola.

        Args:
            data: Datos del calendario
            dates_of_interest: Fechas específicas a reportar
            show_all: Si True, muestra todas las fechas
        """
        print("\n" + "=" * 70)
        print("📊 INFORME DE DISPONIBILIDAD - COLOSSEO GRUPPI")
        print("=" * 70)
        print(f"🕐 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        if not data:
            print("\n⚠️  No hay datos disponibles para mostrar")
            print("=" * 70 + "\n")
            return

        # Normalizar datos (convertir lista a dict si es necesario)
        data = ReportGenerator.normalize_data(data)

        # Si no hay fechas específicas y no se pide mostrar todo, usar fechas configuradas
        if dates_of_interest is None and not show_all:
            dates_of_interest = config.parse_dates_from_env()

        # Determinar qué fechas mostrar
        if show_all:
            dates_to_show = sorted(data.keys())
        elif dates_of_interest:
            dates_to_show = dates_of_interest
        else:
            dates_to_show = sorted(data.keys())

        # Contadores
        available_count = 0
        soldout_count = 0
        closed_count = 0

        print("\n📅 DISPONIBILIDAD POR FECHA:")
        print("-" * 70)

        for date in dates_to_show:
            info = data.get(date)

            if not info:
                print(f"  {date}: Sin datos")
                continue

            status = info.get("status", "unknown")
            emoji = ReportGenerator.get_status_emoji(status)
            formatted_date = ReportGenerator.format_date(date)

            if status == "available":
                available_count += 1
                capacity = info.get("capacity", "?")
                original = info.get("originalCapacity", "?")
                price = info.get("price", "?")

                # Detectar baja capacidad
                if isinstance(capacity, int) and capacity <= 10:
                    emoji = ReportGenerator.EMOJI_LOW_CAPACITY

                print(f"  {emoji} {formatted_date}")
                print(f"     └─ DISPONIBLE | Plazas: {capacity}/{original} | Precio: €{price}")

                # Mostrar información adicional si está disponible
                hora_inicio = info.get("hora_inicio") or info.get("startTime")
                hora_fin = info.get("hora_fin") or info.get("endTime")
                duracion = info.get("duracion") or info.get("duration")
                titulo = info.get("titulo") or info.get("title")
                tipo_evento = info.get("tipo_evento") or info.get("eventType") or info.get("type")
                idioma = info.get("idioma") or info.get("language")
                guia = info.get("guia_incluida") or info.get("guidedTour")
                acceso_rapido = info.get("acceso_rapido") or info.get("skipTheLine")

                # Línea de horario
                if hora_inicio or duracion:
                    horario_str = "     ├─"
                    if hora_inicio:
                        horario_str += f" Hora: {hora_inicio}"
                        if hora_fin:
                            horario_str += f" - {hora_fin}"
                    if duracion:
                        horario_str += f" | Duración: {duracion}"
                    print(horario_str)

                # Línea de detalles del evento
                detalles = []
                if titulo:
                    detalles.append(f"Tipo: {titulo}")
                elif tipo_evento:
                    detalles.append(f"Tipo: {tipo_evento}")
                if idioma:
                    detalles.append(f"Idioma: {idioma}")
                if guia:
                    detalles.append("Con guía" if guia else "Sin guía")
                if acceso_rapido:
                    detalles.append("Acceso rápido")

                if detalles:
                    print(f"     ├─ {' | '.join(detalles)}")

                # Mostrar plazas ocupadas si está disponible
                plazas_ocupadas = info.get("plazas_ocupadas")
                if plazas_ocupadas is not None:
                    try:
                        ocupacion_pct = (int(plazas_ocupadas) / int(original)) * 100
                        print(f"     └─ Ocupación: {ocupacion_pct:.1f}% ({plazas_ocupadas} plazas vendidas)")
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass

            elif status == "soldout":
                soldout_count += 1
                print(f"  {emoji} {formatted_date}")
                print(f"     └─ AGOTADO")

            elif status == "closed":
                closed_count += 1
                print(f"  {emoji} {formatted_date}")
                print(f"     └─ CERRADO")

            else:
                print(f"  {emoji} {formatted_date}")
                print(f"     └─ Estado: {status}")

        # Resumen
        print("\n" + "-" * 70)
        print("📈 RESUMEN:")
        print(f"  {ReportGenerator.EMOJI_AVAILABLE} Disponibles: {available_count}")
        print(f"  {ReportGenerator.EMOJI_SOLDOUT} Agotadas: {soldout_count}")
        print(f"  {ReportGenerator.EMOJI_CLOSED} Cerradas: {closed_count}")
        print("=" * 70 + "\n")

    @staticmethod
    def generate_availability_summary(data: Dict) -> Dict:
        """
        Genera un resumen estadístico de disponibilidad.

        Args:
            data: Datos del calendario

        Returns:
            Diccionario con estadísticas
        """
        summary = {
            "total_fechas": len(data),
            "disponibles": 0,
            "agotadas": 0,
            "cerradas": 0,
            "total_plazas": 0,
            "fechas_urgentes": [],
        }

        for date, info in data.items():
            if not isinstance(info, dict):
                continue

            status = info.get("status")

            if status == "available":
                summary["disponibles"] += 1
                capacity = info.get("capacity", 0)
                summary["total_plazas"] += capacity if isinstance(capacity, int) else 0

                # Detectar urgencia
                if isinstance(capacity, int) and capacity <= 5:
                    summary["fechas_urgentes"].append({
                        "fecha": date,
                        "capacidad": capacity
                    })

            elif status == "soldout":
                summary["agotadas"] += 1

            elif status == "closed":
                summary["cerradas"] += 1

        return summary

    @staticmethod
    def generate_urgent_alerts(data, threshold: int = 10) -> List[str]:
        """
        Genera alertas para fechas con baja disponibilidad.

        Args:
            data: Datos del calendario (dict o list)
            threshold: Umbral de capacidad para alerta

        Returns:
            Lista de mensajes de alerta
        """
        alerts = []

        # Normalizar datos
        data = ReportGenerator.normalize_data(data)

        for date, info in data.items():
            if not isinstance(info, dict):
                continue

            status = info.get("status")
            capacity = info.get("capacity")

            if status == "available" and isinstance(capacity, int) and capacity <= threshold:
                urgency = "¡URGENTE!" if capacity <= 5 else "¡ATENCIÓN!"
                alerts.append(
                    f"{urgency} {date}: Solo {capacity} plazas disponibles"
                )

        return sorted(alerts)

    @staticmethod
    def print_urgent_alerts(data: Dict, threshold: int = 10) -> None:
        """
        Imprime alertas urgentes en consola.

        Args:
            data: Datos del calendario
            threshold: Umbral de capacidad
        """
        alerts = ReportGenerator.generate_urgent_alerts(data, threshold)

        if alerts:
            print("\n" + "=" * 70)
            print("🚨 ALERTAS URGENTES")
            print("=" * 70)
            for alert in alerts:
                print(f"  {alert}")
            print("=" * 70 + "\n")

    @staticmethod
    def save_report_to_file(
        data: Dict,
        filename: str = None,
        dates_of_interest: List[str] = None
    ) -> bool:
        """
        Guarda el informe en un archivo de texto.

        Args:
            data: Datos del calendario
            filename: Nombre del archivo (usa default si no se proporciona)
            dates_of_interest: Fechas específicas a incluir

        Returns:
            True si se guardó exitosamente
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"colosseo_report_{timestamp}.txt"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write("INFORME DE DISPONIBILIDAD - COLOSSEO GRUPPI\n")
                f.write("=" * 70 + "\n")
                f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")

                if dates_of_interest is None:
                    dates_of_interest = config.parse_dates_from_env()

                for date in dates_of_interest:
                    info = data.get(date)

                    if not info:
                        f.write(f"{date}: Sin datos\n")
                        continue

                    status = info.get("status", "unknown")
                    formatted_date = ReportGenerator.format_date(date)

                    if status == "available":
                        capacity = info.get("capacity", "?")
                        original = info.get("originalCapacity", "?")
                        price = info.get("price", "?")
                        f.write(f"{formatted_date}: DISPONIBLE\n")
                        f.write(f"  Plazas: {capacity}/{original}\n")
                        f.write(f"  Precio: €{price}\n")

                        # Información adicional
                        hora_inicio = info.get("hora_inicio") or info.get("startTime")
                        hora_fin = info.get("hora_fin") or info.get("endTime")
                        duracion = info.get("duracion") or info.get("duration")
                        titulo = info.get("titulo") or info.get("title")
                        tipo_evento = info.get("tipo_evento") or info.get("eventType")
                        idioma = info.get("idioma") or info.get("language")

                        if hora_inicio:
                            f.write(f"  Horario: {hora_inicio}")
                            if hora_fin:
                                f.write(f" - {hora_fin}")
                            f.write("\n")

                        if duracion:
                            f.write(f"  Duración: {duracion}\n")

                        if titulo:
                            f.write(f"  Tipo: {titulo}\n")
                        elif tipo_evento:
                            f.write(f"  Tipo: {tipo_evento}\n")

                        if idioma:
                            f.write(f"  Idioma: {idioma}\n")

                        plazas_ocupadas = info.get("plazas_ocupadas")
                        if plazas_ocupadas is not None and isinstance(original, int) and original > 0:
                            try:
                                ocupacion_pct = (int(plazas_ocupadas) / int(original)) * 100
                                f.write(f"  Ocupación: {ocupacion_pct:.1f}% ({plazas_ocupadas} plazas vendidas)\n")
                            except (ValueError, TypeError, ZeroDivisionError):
                                pass

                        f.write("\n")

                    elif status == "soldout":
                        f.write(f"{formatted_date}: AGOTADO\n\n")

                    elif status == "closed":
                        f.write(f"{formatted_date}: CERRADO\n\n")

                    else:
                        f.write(f"{formatted_date}: {status}\n\n")

                # Agregar resumen
                summary = ReportGenerator.generate_availability_summary(data)
                f.write("=" * 70 + "\n")
                f.write("RESUMEN\n")
                f.write("=" * 70 + "\n")
                f.write(f"Fechas disponibles: {summary['disponibles']}\n")
                f.write(f"Fechas agotadas: {summary['agotadas']}\n")
                f.write(f"Fechas cerradas: {summary['cerradas']}\n")
                f.write(f"Total de plazas: {summary['total_plazas']}\n")

                if summary['fechas_urgentes']:
                    f.write("\nFECHAS URGENTES (≤5 plazas):\n")
                    for urgente in summary['fechas_urgentes']:
                        f.write(f"  - {urgente['fecha']}: {urgente['capacidad']} plazas\n")

            print(f"💾 Informe guardado en: {filename}")
            return True

        except Exception as e:
            print(f"❌ Error guardando informe: {e}")
            return False


# Funciones de conveniencia
def quick_report(data: Dict, dates: List[str] = None, save: bool = False) -> None:
    """
    Genera un informe rápido en consola.

    Args:
        data: Datos del calendario
        dates: Fechas específicas (opcional)
        save: Si True, también guarda en archivo
    """
    report = ReportGenerator()

    # Mostrar alertas urgentes primero
    report.print_urgent_alerts(data)

    # Mostrar informe principal
    report.generate_console_report(data, dates)

    # Guardar si se solicita
    if save:
        report.save_report_to_file(data, dates_of_interest=dates)

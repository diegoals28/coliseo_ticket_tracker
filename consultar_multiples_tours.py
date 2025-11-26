"""
Consulta múltiples tipos de tours del Colosseo
"""

import sys
import io
from datetime import datetime

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from api_client import ColosseoAPIClient, AvailabilityChecker

# Configuración de tours
TOURS = {
    "24h-grupos": {
        "nombre": "24h Colosseo, Foro Romano y Palatino - GRUPOS",
        "guid": "a9a4b0f8-bf3c-4f22-afcd-196a27be04b9"
    },
    "arena": {
        "nombre": "Colosseo con ACCESO A LA ARENA",
        "guid": "8d1c991c-a15f-42bc-8cb5-bd738aa19c70"
    }
}


def consultar_tour(client, tour_key, tour_info, month="2025-12"):
    """Consulta disponibilidad para un tour específico"""

    print(f"\n{'=' * 70}")
    print(f"🎫 {tour_info['nombre']}")
    print(f"{'=' * 70}")
    print(f"🔑 GUID: {tour_info['guid']}")

    if tour_info['guid'] == "GUID_PENDIENTE":
        print("⚠️  GUID no configurado - sigue las instrucciones para obtenerlo")
        return None

    # Consultar API
    data, status, msg = client.fetch_calendar_data(
        guid=tour_info['guid'],
        month=month
    )

    if not data:
        print(f"❌ Error: {msg}")
        return None

    print(f"✅ Timeslots recibidos: {len(data)}")

    # Normalizar
    checker = AvailabilityChecker()
    normalized = checker.normalize_data(data)

    print(f"📊 Fechas únicas: {len(normalized)}")

    if len(normalized) == 0:
        print("⚠️  No hay fechas disponibles")
        return None

    # Mostrar primeras fechas
    print(f"\n{'─' * 70}")
    print(f"{'FECHA':<22} | {'PLAZAS':>12} | {'OCUPACIÓN':>12}")
    print(f"{'─' * 70}")

    fechas_ordenadas = sorted(normalized.items())

    for fecha, info in fechas_ordenadas[:10]:
        capacidad = info.get('capacity', 0)
        capacidad_orig = info.get('originalCapacity', 0)
        ocupadas = capacidad_orig - capacidad if capacidad_orig else 0
        porcentaje_ocupado = (ocupadas / capacidad_orig * 100) if capacidad_orig > 0 else 0

        # Emoji
        if capacidad == 0:
            emoji = "❌"
        elif porcentaje_ocupado < 30:
            emoji = "🟢"
        elif porcentaje_ocupado < 70:
            emoji = "🟡"
        else:
            emoji = "🔴"

        # Formatear fecha
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
            dia_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][fecha_obj.weekday()]
            fecha_str = f"{fecha} ({dia_semana})"
        except:
            fecha_str = fecha

        print(f"{emoji} {fecha_str:<20} | {capacidad:>5,} plazas | {porcentaje_ocupado:>6.1f}%")

    if len(fechas_ordenadas) > 10:
        print(f"   ... y {len(fechas_ordenadas) - 10} fechas más")

    # Resumen del tour
    total_plazas = sum(info.get('capacity', 0) for info in normalized.values())
    print(f"\n📈 RESUMEN: {len(normalized)} fechas | {total_plazas:,} plazas totales")

    return normalized


def main():
    print("\n" + "=" * 70)
    print("🏛️  COMPARADOR DE TOURS - COLOSSEO")
    print("=" * 70)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Cargar cookies
    client = ColosseoAPIClient()
    if not client.load_cookies():
        print("\n❌ No se pueden cargar las cookies")
        sys.exit(1)

    # Determinar meses a consultar (mes actual + próximos 5)
    from datetime import timedelta
    hoy = datetime.now()
    meses_a_consultar = []

    for i in range(6):  # 6 meses: actual + 5 siguientes
        fecha = hoy + timedelta(days=30*i)
        mes_str = f"{fecha.year}-{fecha.month:02d}"
        if mes_str not in meses_a_consultar:
            meses_a_consultar.append(mes_str)

    print(f"\n📅 Consultando {len(meses_a_consultar)} meses: {', '.join(meses_a_consultar)}")

    # Consultar cada tour en todos los meses
    resultados = {}

    for tour_key, tour_info in TOURS.items():
        print(f"\n{'=' * 70}")
        print(f"🎫 {tour_info['nombre']}")
        print(f"{'=' * 70}")
        print(f"🔑 GUID: {tour_info['guid']}")

        if tour_info['guid'] == "GUID_PENDIENTE":
            print("⚠️  GUID no configurado - sigue las instrucciones para obtenerlo")
            continue

        # Acumular datos de todos los meses
        datos_totales = {}

        for month in meses_a_consultar:
            print(f"\n  📅 Consultando {month}...", end=" ")

            # Consultar API
            data, status, msg = client.fetch_calendar_data(
                guid=tour_info['guid'],
                month=month
            )

            if not data:
                print(f"❌ Error")
                continue

            print(f"✅ {len(data)} timeslots")

            # Normalizar
            checker = AvailabilityChecker()
            normalized = checker.normalize_data(data)

            # Agregar al total
            datos_totales.update(normalized)

        if len(datos_totales) == 0:
            print(f"\n⚠️  No hay fechas disponibles")
            continue

        print(f"\n📊 Total de fechas únicas: {len(datos_totales)}")

        # Mostrar primeras fechas
        print(f"\n{'─' * 70}")
        print(f"{'FECHA':<22} | {'PLAZAS':>12} | {'OCUPACIÓN':>12}")
        print(f"{'─' * 70}")

        fechas_ordenadas = sorted(datos_totales.items())

        for fecha, info in fechas_ordenadas[:15]:
            capacidad = info.get('capacity', 0)
            capacidad_orig = info.get('originalCapacity', 0)
            ocupadas = capacidad_orig - capacidad if capacidad_orig else 0
            porcentaje_ocupado = (ocupadas / capacidad_orig * 100) if capacidad_orig > 0 else 0

            # Emoji
            if capacidad == 0:
                emoji = "❌"
            elif porcentaje_ocupado < 30:
                emoji = "🟢"
            elif porcentaje_ocupado < 70:
                emoji = "🟡"
            else:
                emoji = "🔴"

            # Formatear fecha
            try:
                fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
                dia_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][fecha_obj.weekday()]
                fecha_str = f"{fecha} ({dia_semana})"
            except:
                fecha_str = fecha

            print(f"{emoji} {fecha_str:<20} | {capacidad:>5,} plazas | {porcentaje_ocupado:>6.1f}%")

        if len(fechas_ordenadas) > 15:
            print(f"   ... y {len(fechas_ordenadas) - 15} fechas más")

        # Resumen del tour
        total_plazas = sum(info.get('capacity', 0) for info in datos_totales.values())
        print(f"\n📈 RESUMEN: {len(datos_totales)} fechas | {total_plazas:,} plazas totales")

        # Guardar en resultados
        resultados[tour_key] = {
            "info": tour_info,
            "datos": datos_totales
        }

    # Comparación final
    if len(resultados) > 1:
        print(f"\n{'=' * 70}")
        print("📊 COMPARACIÓN DE TOURS")
        print(f"{'=' * 70}")

        for tour_key, resultado in resultados.items():
            tour_info = resultado['info']
            datos = resultado['datos']
            total_plazas = sum(info.get('capacity', 0) for info in datos.values())

            print(f"\n🎫 {tour_info['nombre']}")
            print(f"   Fechas disponibles: {len(datos)}")
            print(f"   Plazas totales: {total_plazas:,}")

    print(f"\n{'=' * 70}")
    print("✅ Consulta completada")
    print(f"{'=' * 70}\n")

    # Instrucciones si falta configurar algún GUID
    tours_pendientes = [k for k, v in TOURS.items() if v['guid'] == "GUID_PENDIENTE"]
    if tours_pendientes:
        print("\n" + "=" * 70)
        print("⚠️  CONFIGURACIÓN PENDIENTE")
        print("=" * 70)
        print("\nPara consultar todos los tours, necesitas obtener los GUIDs faltantes:")
        print("\n1. Abre Chrome y ve a la página del tour")
        print("2. F12 → Network → Filtra 'calendars_month'")
        print("3. Haz click en el calendario")
        print("4. Copia el valor de: guids[entranceEvent_guid][]")
        print("5. Edita este archivo y reemplaza 'GUID_PENDIENTE' con el valor real")
        print("\nArchivo a editar: consultar_multiples_tours.py")
        print(f"Línea: TOURS['{tours_pendientes[0]}']['guid'] = 'TU_GUID_AQUI'")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

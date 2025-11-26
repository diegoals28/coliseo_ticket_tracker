# # 🏛️ Colosseo Monitor - Aplicación de Monitoreo

Monitor de disponibilidad de entradas para el Colosseo en Roma.

## 📋 Archivos Incluidos

### Scripts Principales
- **`consultar_multiples_tours.py`** - Compara múltiples tipos de tours (RECOMENDADO)
- **`colosseo_monitor.py`** - Monitor completo con navegador y generación de informes

### Módulos Core
- **`api_client.py`** - Cliente de API y analizador de disponibilidad
- **`stealth_browser.py`** - Navegador con evasión de detección de bots
- **`report_generator.py`** - Generador de informes
- **`colosseo_config.py`** - Configuración del sistema

### Archivos de Datos
- **`cookies_colosseo.json`** - Cookies de autenticación (REQUERIDO)
- **`chromedriver.exe`** - Driver de Chrome para automatización
- **`requirements.txt`** - Dependencias de Python

## 🚀 Uso Rápido

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Consultar múltiples tours (RECOMENDADO)
```bash
python consultar_multiples_tours.py
```

Este script:
- ✅ Consulta automáticamente 6 meses de disponibilidad
- ✅ Compara diferentes tipos de tours simultáneamente
- ✅ Muestra ocupación y plazas disponibles
- ✅ Genera un resumen comparativo

**Tours configurados:**
- 24h Colosseo, Foro Romano y Palatino - GRUPOS
- Colosseo con ACCESO A LA ARENA

### 3. Monitor completo con navegador
```bash
# Chequeo completo (obtiene cookies + consulta)
python colosseo_monitor.py

# Solo consulta (usa cookies existentes)
python colosseo_monitor.py --only-report

# Guardar informe en archivo
python colosseo_monitor.py --only-report --save
```

## 🔧 Configuración de Tours

Para agregar o modificar tours, edita `consultar_multiples_tours.py`:

```python
TOURS = {
    "clave-tour": {
        "nombre": "Nombre del Tour",
        "guid": "GUID_DEL_TOUR"
    }
}
```

### Cómo obtener el GUID de un tour:
1. Abre Chrome y ve a la página del tour
2. Presiona F12 → Network
3. Filtra por: `calendars_month`
4. Haz click en el calendario
5. En la pestaña Payload, busca: `guids[entranceEvent_guid][]`
6. Copia ese valor como GUID

## 🍪 Actualizar Cookies

Las cookies tienen una validez limitada. Si empiezas a recibir errores:

1. **Extracción manual (recomendado)**:
   - Abre Chrome e ingresa a: https://ticketing.colosseo.it/
   - Presiona F12 → Application → Cookies
   - Copia todas las cookies en formato JSON
   - Reemplaza el contenido de `cookies_colosseo.json`

2. **Extracción automática con navegador**:
   ```bash
   python colosseo_monitor.py
   ```
   Esto abrirá Chrome y extraerá las cookies automáticamente.

## 📊 Interpretación de Resultados

**Indicadores de ocupación:**
- 🟢 Verde: < 30% ocupado (mucha disponibilidad)
- 🟡 Amarillo: 30-70% ocupado (disponibilidad moderada)
- 🔴 Rojo: > 70% ocupado (poca disponibilidad)
- ❌ Negro: 100% ocupado (agotado)

## 🔍 Solución de Problemas

### Error 400 en la API
→ Las cookies han expirado, actualízalas siguiendo la sección "Actualizar Cookies"

### Error "No se pueden cargar las cookies"
→ Verifica que `cookies_colosseo.json` existe y tiene el formato correcto

### ChromeDriver no funciona
→ Descarga la versión correcta desde: https://chromedriver.chromium.org/

## 📝 Notas

- El sistema consulta automáticamente 6 meses de disponibilidad
- Los meses futuros pueden dar error si las reservas aún no están abiertas
- Las cookies deben renovarse periódicamente para mantener el acceso

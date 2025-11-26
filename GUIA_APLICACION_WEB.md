# 🏛️ Colosseo Monitor - Guía de Aplicación Web

## 📋 Descripción

Aplicación web con interfaz gráfica moderna para consultar la disponibilidad de entradas del Colosseo en Roma.

### Características principales:
- ✅ Interfaz web moderna y fácil de usar
- 🍪 Carga de cookies mediante copiar/pegar o desde archivo
- 🎫 Selección de múltiples tours simultáneamente
- 📊 Visualización de resultados en tablas interactivas
- 📥 Exportación a Excel con múltiples hojas
- 📱 Diseño responsive (funciona en móviles y tablets)

## 🚀 Instalación

### 1. Instalar dependencias

Abre una terminal en la carpeta `colosseo_app` y ejecuta:

```bash
pip install -r requirements.txt
```

O manualmente:

```bash
pip install flask pandas openpyxl
```

### 2. Verificar que tienes las cookies

Asegúrate de que el archivo `cookies_colosseo.json` existe en esta carpeta o prepara tus cookies en formato JSON.

## 🎯 Cómo usar la aplicación

### Opción 1: Doble click en iniciar_app.bat (Windows)

1. Haz doble click en **`iniciar_app.bat`**
2. Se abrirá una ventana de terminal
3. El navegador se abrirá automáticamente en `http://localhost:5000`

### Opción 2: Comando manual

```bash
python app.py
```

Luego abre tu navegador en: **http://localhost:5000**

## 📝 Uso de la interfaz

### 1. Cargar cookies

**Opción A: Desde archivo**
- Click en el botón "📂 Cargar desde archivo"
- Se cargarán automáticamente las cookies de `cookies_colosseo.json`

**Opción B: Copiar y pegar**
- Copia tus cookies en formato JSON
- Pégalas en el área de texto

**Formato de cookies esperado:**

```json
[
  {
    "name": "octofence-waap-id",
    "value": "valor_de_tu_cookie",
    "domain": ".colosseo.it"
  },
  {
    "name": "octofence-waap-sessid",
    "value": "valor_de_tu_cookie",
    "domain": ".colosseo.it"
  }
]
```

### 2. Seleccionar tours

- Marca los checkboxes de los tours que quieres consultar
- Por defecto todos están seleccionados

**Tours disponibles:**
- 24h Colosseo, Foro Romano y Palatino - GRUPOS
- Colosseo con ACCESO A LA ARENA

### 3. Consultar disponibilidad

- Click en "🔍 Consultar Disponibilidad"
- Espera mientras se consultan los datos (puede tomar 10-30 segundos)
- Se consultarán automáticamente **6 meses** de disponibilidad

### 4. Ver resultados

Los resultados se muestran en:

**Tarjetas de resumen:**
- Número de tours consultados
- Número de meses consultados

**Tablas detalladas por tour:**
- Fecha
- Día de la semana
- Plazas disponibles / totales
- Porcentaje de ocupación
- Estado (con colores):
  - 🟢 Verde: Mucha disponibilidad (< 30% ocupado)
  - 🟡 Amarillo: Disponibilidad moderada (30-70% ocupado)
  - 🔴 Rojo: Poca disponibilidad (> 70% ocupado)
  - ⚫ Negro: Agotado (100% ocupado)

### 5. Exportar a Excel

- Click en "📥 Descargar Excel"
- Se descargará un archivo `.xlsx` con:
  - **Hoja "Resumen"**: Comparación de todos los tours
  - **Hojas individuales**: Una por cada tour con todos los detalles

**Formato del archivo:**
- Nombre: `colosseo_disponibilidad_YYYYMMDD_HHMMSS.xlsx`
- Compatible con Excel, Google Sheets, LibreOffice

## 🔧 Agregar nuevos tours

Edita el archivo `app.py` y modifica el diccionario `TOURS`:

```python
TOURS = {
    "clave-tour": {
        "nombre": "Nombre descriptivo del tour",
        "guid": "GUID_DEL_TOUR"
    }
}
```

### Cómo obtener el GUID:

1. Abre Chrome
2. Ve a la página del tour en ticketing.colosseo.it
3. Presiona F12 → Network
4. Filtra por: `calendars_month`
5. Haz click en el calendario
6. En Payload, busca: `guids[entranceEvent_guid][]`
7. Copia ese valor

## 🍪 Actualizar cookies

Las cookies expiran después de un tiempo. Si recibes errores:

### Método 1: Extracción manual (recomendado)

1. Abre Chrome
2. Ve a: https://ticketing.colosseo.it/
3. Presiona F12 → Application → Cookies
4. Selecciona el dominio `colosseo.it`
5. Copia todas las cookies
6. Formatéalas como JSON (ver ejemplo arriba)
7. Pégalas en la interfaz

### Método 2: Usar el monitor con navegador

```bash
python colosseo_monitor.py
```

Esto actualizará automáticamente `cookies_colosseo.json`

## 📊 Estructura del Excel exportado

### Hoja "Resumen"
| Tour | Fechas Disponibles | Plazas Totales |
|------|-------------------|----------------|
| Tour 1 | 30 | 62,059 |
| Tour 2 | 8 | 10,489 |

### Hojas individuales (una por tour)
| Fecha | Día | Plazas Disponibles | Plazas Totales | % Ocupado | Estado |
|-------|-----|-------------------|----------------|-----------|--------|
| 2025-11-24 | Lun | 515 | 1,300 | 60.4 | DISPONIBILIDAD MODERADA |
| 2025-11-25 | Mar | 7,008 | 12,850 | 45.5 | DISPONIBILIDAD MODERADA |

## 🔍 Solución de problemas

### Error: "No se pueden cargar las cookies"
→ Verifica que el formato JSON sea correcto
→ Asegúrate de incluir todas las cookies necesarias (octofence-waap-id, octofence-waap-sessid, etc.)

### Error 400 en la consulta
→ Las cookies han expirado, actualízalas

### Error: "Module not found"
→ Instala las dependencias: `pip install -r requirements.txt`

### La aplicación no inicia
→ Verifica que Python esté instalado
→ Verifica que estés en la carpeta correcta

### No se puede exportar a Excel
→ Verifica que openpyxl esté instalado: `pip install openpyxl`

## 🔒 Seguridad

- ⚠️ **NO compartas tus cookies** con nadie
- ⚠️ **NO subas el archivo cookies_colosseo.json** a repositorios públicos
- ⚠️ Las cookies tienen acceso a tu cuenta de ticketing.colosseo.it
- ✅ La aplicación solo se ejecuta localmente (localhost:5000)
- ✅ Los datos no se envían a ningún servidor externo

## 📱 Acceso desde otros dispositivos

La aplicación está configurada para escuchar en `0.0.0.0:5000`, lo que significa que puedes acceder desde otros dispositivos en tu red local:

1. Encuentra tu IP local (comando: `ipconfig` en Windows)
2. Desde otro dispositivo en la misma red: `http://TU_IP:5000`

Ejemplo: `http://192.168.1.100:5000`

## 🎨 Personalización

### Cambiar el puerto

Edita `app.py`, última línea:

```python
app.run(debug=True, host='0.0.0.0', port=5000)  # Cambia 5000 por el puerto deseado
```

### Cambiar el número de meses a consultar

En la interfaz, modifica la llamada a la API o edita el valor por defecto en `app.py`:

```python
num_meses = data.get('meses', 6)  # Cambia 6 por el número deseado
```

## 📞 Soporte

Si encuentras problemas:

1. Verifica los mensajes de error en la consola
2. Revisa que todas las dependencias estén instaladas
3. Asegúrate de que las cookies sean válidas y estén en el formato correcto

## 🎯 Resumen rápido

1. **Instalar**: `pip install -r requirements.txt`
2. **Iniciar**: Doble click en `iniciar_app.bat` o `python app.py`
3. **Abrir**: http://localhost:5000
4. **Usar**: Pegar cookies → Seleccionar tours → Consultar → Exportar Excel

¡Listo para monitorear el Colosseo! 🏛️

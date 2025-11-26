// Estado global
let currentResults = null;

// Mostrar alertas
function showAlert(type, message) {
    const errorAlert = document.getElementById('errorAlert');
    const successAlert = document.getElementById('successAlert');

    errorAlert.classList.remove('active');
    successAlert.classList.remove('active');

    if (type === 'error') {
        errorAlert.textContent = message;
        errorAlert.classList.add('active');
    } else {
        successAlert.textContent = message;
        successAlert.classList.add('active');
    }

    setTimeout(() => {
        errorAlert.classList.remove('active');
        successAlert.classList.remove('active');
    }, 5000);
}

// Convertir cookies de tabla a JSON
function convertirCookiesTabla() {
    const texto = document.getElementById('cookiesInput').value.trim();

    if (!texto) {
        showAlert('error', 'Por favor, pega las cookies primero');
        return;
    }

    // Si ya es JSON válido, no hacer nada
    try {
        JSON.parse(texto);
        showAlert('success', 'Las cookies ya están en formato JSON válido');
        return;
    } catch (e) {
        // No es JSON, continuar con conversión
    }

    try {
        const cookies = [];
        const lineas = texto.split('\n');

        for (const linea of lineas) {
            if (!linea.trim() || linea.includes('Name') || linea.includes('Domain')) {
                continue;
            }

            const partes = linea.split(/\t+|\s{2,}/);

            if (partes.length >= 3) {
                const name = partes[0].trim();
                const value = partes[1].trim();
                const domain = partes[2].trim();

                if (name && value && (domain.includes('colosseo') ||
                    name.includes('octofence') ||
                    name.includes('_ga') ||
                    name === 'PHPSESSID' ||
                    name === 'qtrans_front_language' ||
                    name.includes('cookielawinfo'))) {

                    cookies.push({
                        name: name,
                        value: value,
                        domain: domain,
                        path: "/",
                        secure: name.includes('octofence-waap-id') || name.includes('octofence-waap-sessid'),
                        httpOnly: name === 'octofence-waap-id' || name === 'octofence-waap-sessid' || name === 'qtrans_front_language',
                        sameSite: "Lax"
                    });
                }
            }
        }

        if (cookies.length === 0) {
            showAlert('error', 'No se encontraron cookies válidas. Asegúrate de copiar desde Chrome DevTools.');
            return;
        }

        const jsonCookies = JSON.stringify(cookies, null, 2);
        document.getElementById('cookiesInput').value = jsonCookies;

        showAlert('success', `✓ Convertidas ${cookies.length} cookies a formato JSON`);

    } catch (error) {
        showAlert('error', 'Error al convertir: ' + error.message);
    }
}

// Cargar cookies desde archivo
async function cargarCookiesArchivo() {
    try {
        const response = await fetch('/api/cargar-cookies-archivo', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('cookiesInput').value = data.cookies;
            showAlert('success', 'Cookies cargadas desde archivo correctamente');
        } else {
            showAlert('error', data.error || 'No se pudo cargar el archivo de cookies');
        }
    } catch (error) {
        showAlert('error', 'Error al cargar cookies: ' + error.message);
    }
}

// Guardar cookies en archivo
async function guardarCookies() {
    const cookiesText = document.getElementById('cookiesInput').value.trim();

    if (!cookiesText) {
        showAlert('error', 'Por favor, pega las cookies primero');
        return;
    }

    // Verificar que sea JSON válido
    try {
        JSON.parse(cookiesText);
    } catch (e) {
        showAlert('error', 'Las cookies deben estar en formato JSON. Usa "Auto-convertir formato" primero');
        return;
    }

    try {
        const response = await fetch('/api/guardar-cookies', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                cookies: cookiesText
            })
        });

        const data = await response.json();

        if (data.success) {
            showAlert('success', '✓ Cookies guardadas en cookies_colosseo.json');
        } else {
            showAlert('error', data.error || 'Error al guardar cookies');
        }
    } catch (error) {
        showAlert('error', 'Error al guardar: ' + error.message);
    }
}

// Consultar disponibilidad
async function consultarDisponibilidad() {
    const cookiesText = document.getElementById('cookiesInput').value.trim();

    if (!cookiesText) {
        showAlert('error', 'Por favor, ingresa las cookies');
        return;
    }

    // Consultar todos los tours siempre
    const toursSeleccionados = ['24h-grupos', 'arena'];

    document.getElementById('loading').classList.add('active');
    document.getElementById('results').classList.remove('active');

    try {
        const response = await fetch('/api/consultar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                cookies: cookiesText,
                tours: toursSeleccionados,
                meses: 6
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al consultar');
        }

        currentResults = data;
        mostrarResultados(data);
        document.getElementById('exportBtn').disabled = false;

        // Guardar automáticamente en histórico
        guardarHistoricoAutomatico(data);

        showAlert('success', 'Consulta completada exitosamente');

    } catch (error) {
        showAlert('error', error.message);
    } finally {
        document.getElementById('loading').classList.remove('active');
    }
}

// Guardar en histórico automáticamente
async function guardarHistoricoAutomatico(data) {
    try {
        const response = await fetch('/api/guardar-historico', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                resultados: data.resultados
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log('✓ Histórico guardado:', result.message);
            // Mostrar mensaje discreto
            setTimeout(() => {
                showAlert('success', `📊 ${result.message} en ${result.filename}`);
            }, 2000);
        }
    } catch (error) {
        console.error('Error guardando histórico:', error);
    }
}

// SVG Icons
const ICONS = {
    calendar: '<svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" /></svg>',
    chart: '<svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" /></svg>',
    clock: '<svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>',
    ticket: '<svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 6v.75m0 3v.75m0 3v.75m0 3V18m-9-5.25h5.25M7.5 15h3M3.375 5.25c-.621 0-1.125.504-1.125 1.125v3.026a2.999 2.999 0 0 1 0 5.198v3.026c0 .621.504 1.125 1.125 1.125h17.25c.621 0 1.125-.504 1.125-1.125v-3.026a2.999 2.999 0 0 1 0-5.198V6.375c0-.621-.504-1.125-1.125-1.125H3.375Z" /></svg>',
    chevronDown: '<svg class="icon-sm" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" /></svg>',
    calendarDays: '<svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-9-6h.008v.008H12v-.008ZM12 15h.008v.008H12V15Zm0 2.25h.008v.008H12v-.008ZM9.75 15h.008v.008H9.75V15Zm0 2.25h.008v.008H9.75v-.008ZM7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm6.75-4.5h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V15Zm0 2.25h.008v.008h-.008v-.008Zm2.25-4.5h.008v.008H16.5v-.008Zm0 2.25h.008v.008H16.5V15Z" /></svg>'
};

// Mostrar resultados con tabs
function mostrarResultados(data) {
    const summaryHtml = `
        <div class="summary-card">
            <p class="summary-card-label">Tours Consultados</p>
            <p class="summary-card-value">${Object.keys(data.resultados).length}</p>
        </div>
        <div class="summary-card">
            <p class="summary-card-label">Meses Consultados</p>
            <p class="summary-card-value">${data.meses_consultados.length}</p>
        </div>
    `;
    document.getElementById('summaryCards').innerHTML = summaryHtml;

    let toursHtml = '';

    for (const [tourKey, tourData] of Object.entries(data.resultados)) {
        const tourId = tourKey.replace(/[^a-z0-9]/gi, '_');

        toursHtml += `
            <div class="tour-section">
                <div class="tour-section-header">
                    <h3 class="tour-section-title">${tourData.nombre}</h3>
                    <div class="tour-section-stats">
                        <span><strong>${tourData.total_fechas}</strong> fechas disponibles</span>
                        <span><strong>${tourData.total_plazas.toLocaleString()}</strong> plazas totales</span>
                    </div>
                </div>

                <div class="tabs">
                    <button class="tab-btn active" onclick="cambiarTab('${tourId}', 'fechas', event)">
                        ${ICONS.calendar} Por Fechas
                    </button>
                    <button class="tab-btn" onclick="cambiarTab('${tourId}', 'estadisticas', event)">
                        ${ICONS.chart} Estadisticas
                    </button>
                </div>

                <div class="tab-content active" id="${tourId}_fechas">
                    ${generarTablaFechas(tourData)}
                </div>

                <div class="tab-content" id="${tourId}_estadisticas">
                    ${generarEstadisticas(tourData.estadisticas)}
                </div>
            </div>
        `;
    }

    document.getElementById('tourResults').innerHTML = toursHtml;
    document.getElementById('timestamp').textContent = `Ultima consulta: ${data.timestamp}`;
    document.getElementById('results').classList.add('active');
}

// Generar tabla de fechas con timeslots expandibles
function generarTablaFechas(tourData) {
    console.log('generarTablaFechas - Tour:', tourData.nombre);
    console.log('timeslots_por_fecha keys:', Object.keys(tourData.timeslots_por_fecha || {}));

    // Crear ID único para el tour
    const tourId = tourData.guid.substring(0, 8);

    let html = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Día</th>
                        <th>Plazas Disponibles</th>
                        <th>% Ocupado</th>
                        <th>Estado</th>
                        <th>Horarios</th>
                    </tr>
                </thead>
                <tbody>
    `;

    for (const fecha of tourData.fechas) {
        const timeslots = tourData.timeslots_por_fecha[fecha.fecha] || [];
        // ID único: tour_fecha (ej: a9a4b0f8_2025_11_25)
        const fechaId = tourId + '_' + fecha.fecha.replace(/[^a-z0-9]/gi, '_');
        console.log(`Fecha ${fecha.fecha}: ${timeslots.length} timeslots`);

        html += `
            <tr class="expandable-row" onclick="toggleTimeslots('${fechaId}')">
                <td>${fecha.fecha}</td>
                <td>${fecha.dia_semana}</td>
                <td><strong>${fecha.plazas_disponibles.toLocaleString()}</strong> / ${fecha.plazas_totales.toLocaleString()}</td>
                <td>${fecha.porcentaje_ocupado}%</td>
                <td><span class="badge badge-${fecha.nivel}">${fecha.estado}</span></td>
                <td class="expand-hint">${ICONS.chevronDown} ${timeslots.length} horarios</td>
            </tr>
            <tr>
                <td colspan="6" class="timeslots-detail" id="timeslots_${fechaId}">
                    ${generarTimeslotsGrid(timeslots)}
                </td>
            </tr>
        `;
    }

    html += `
                </tbody>
            </table>
        </div>
    `;

    return html;
}

// Generar grid de timeslots
function generarTimeslotsGrid(timeslots) {
    console.log('generarTimeslotsGrid llamado con:', timeslots ? timeslots.length : 'null', 'timeslots');

    if (!timeslots || timeslots.length === 0) {
        console.log('No hay timeslots disponibles');
        return '<p style="padding: 15px; color: #666;">No hay horarios detallados disponibles</p>';
    }

    let html = '<div class="timeslots-grid">';

    // Ordenar por hora
    const timeslotsSorted = [...timeslots].sort((a, b) => {
        const horaA = a.hora || '00:00';
        const horaB = b.hora || '00:00';
        return horaA.localeCompare(horaB);
    });

    console.log('Primeros 3 timeslots ordenados:', timeslotsSorted.slice(0, 3));

    for (const ts of timeslotsSorted) {
        let clase = 'disponible';
        if (ts.capacidad === 0) {
            clase = 'agotado';
        } else if (ts.porcentaje_ocupado > 70) {
            clase = 'parcial';
        }

        html += `
            <div class="timeslot-card ${clase}">
                <div class="timeslot-hora">${ts.hora || 'N/A'}</div>
                <div class="timeslot-plazas">${ts.capacidad || 0} / ${ts.capacidad_original || 0}</div>
                <div class="timeslot-plazas">${ts.porcentaje_ocupado || 0}%</div>
            </div>
        `;
    }

    html += '</div>';
    return html;
}

// Generar estadísticas
function generarEstadisticas(stats) {
    return `
        <div class="stats-grid">
            <div class="stats-card">
                <h4>${ICONS.clock} Horarios Mas Demandados</h4>
                <p class="stats-card-hint">
                    Horarios que mas se agotan (% de dias agotados)
                </p>
                ${stats.por_hora.map(h => `
                    <div class="stats-row">
                        <span class="stats-label">${h.hora}</span>
                        <span class="stats-value">${h.porcentaje_agotado}% agotado</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${h.porcentaje_agotado}%"></div>
                    </div>
                    <p class="stats-detail">${h.timeslots_agotados} de ${h.total_timeslots} dias | Ocupacion promedio: ${h.ocupacion_promedio}%</p>
                `).join('')}
            </div>

            <div class="stats-card">
                <h4>${ICONS.calendarDays} Dias de Anticipacion</h4>
                <p class="stats-card-hint">
                    Fechas lejanas que ya tienen horarios agotados
                </p>
                ${stats.dias_agotamiento.slice(0, 10).map(d => `
                    <div class="stats-row">
                        <span class="stats-label">${d.fecha}</span>
                        <span class="stats-value">${d.dias_adelantados} dias</span>
                    </div>
                    <p class="stats-detail">${d.timeslots_agotados} de ${d.total_timeslots} horarios agotados (${d.porcentaje_agotado}%)</p>
                `).join('')}
            </div>
        </div>
    `;
}

// Toggle timeslots visibility
function toggleTimeslots(fechaId) {
    const element = document.getElementById('timeslots_' + fechaId);
    element.classList.toggle('active');
}

// Cambiar tab
function cambiarTab(tourId, tabName, event) {
    // Desactivar todos los tabs del tour
    const container = event.target.closest('.tour-section');
    container.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    container.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Activar tab seleccionado
    event.target.classList.add('active');
    document.getElementById(`${tourId}_${tabName}`).classList.add('active');
}

// Exportar a Excel
async function exportarExcel() {
    if (!currentResults) {
        showAlert('error', 'No hay datos para exportar');
        return;
    }

    try {
        const response = await fetch('/api/exportar-excel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                resultados: currentResults.resultados
            })
        });

        if (!response.ok) {
            throw new Error('Error al exportar');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `colosseo_disponibilidad_${new Date().getTime()}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showAlert('success', 'Archivo Excel descargado correctamente');

    } catch (error) {
        showAlert('error', 'Error al exportar: ' + error.message);
    }
}

// Exponer funciones globalmente para que funcionen con onclick en HTML
window.convertirCookiesTabla = convertirCookiesTabla;
window.cargarCookiesArchivo = cargarCookiesArchivo;
window.guardarCookies = guardarCookies;
window.consultarDisponibilidad = consultarDisponibilidad;
window.toggleTimeslots = toggleTimeslots;
window.cambiarTab = cambiarTab;
window.exportarExcel = exportarExcel;

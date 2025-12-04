// Estado global
let currentResults = null;
let currentCookies = null;
let usingCachedData = false;

// Auto-cargar al iniciar: primero intentar cache, luego cookies
document.addEventListener('DOMContentLoaded', async function() {
    // Intentar cargar disponibilidad cacheada primero (de Railway)
    const cachedLoaded = await cargarDisponibilidadCacheada();

    if (!cachedLoaded) {
        // Si no hay cache, cargar cookies y consultar directamente
        await cargarCookiesAutomaticas();
    }
});

// Cargar disponibilidad cacheada desde Supabase (guardada por Railway)
async function cargarDisponibilidadCacheada() {
    actualizarEstadoCookies('loading', 'Cargando datos...', 'Buscando disponibilidad en cache');

    try {
        const response = await fetch('/api/availability/cached');
        const data = await response.json();

        if (response.ok && data.resultados && Object.keys(data.resultados).length > 0) {
            usingCachedData = true;

            const timestamp = data.timestamp ? new Date(data.timestamp).toLocaleString() : 'desconocido';
            actualizarEstadoCookies('success',
                'Datos cacheados disponibles',
                `Actualizado: ${timestamp} | Fuente: ${data.source || 'Railway'}`
            );

            // Mostrar los resultados cacheados
            currentResults = data;
            mostrarResultadosCacheados(data);

            return true;
        } else {
            console.log('[Cache] No hay datos cacheados:', data.error);
            return false;
        }
    } catch (error) {
        console.error('[Cache] Error cargando cache:', error);
        return false;
    }
}

// Mostrar resultados desde cache (formato ligeramente diferente)
function mostrarResultadosCacheados(data) {
    const summaryHtml = `
        <div class="summary-card">
            <p class="summary-card-label">Tours Disponibles</p>
            <p class="summary-card-value">${Object.keys(data.resultados).length}</p>
        </div>
        <div class="summary-card">
            <p class="summary-card-label">Fuente</p>
            <p class="summary-card-value" style="font-size: 1rem;">Cache (Railway)</p>
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
                </div>

                <div class="tab-content active" id="${tourId}_fechas">
                    ${generarTablaFechasCacheadas(tourData)}
                </div>
            </div>
        `;
    }

    document.getElementById('tourResults').innerHTML = toursHtml;
    document.getElementById('timestamp').textContent = `Datos cacheados: ${data.timestamp || 'desconocido'}`;
    document.getElementById('results').classList.add('active');
    document.getElementById('loading').classList.remove('active');
}

// Generar tabla de fechas desde datos cacheados
function generarTablaFechasCacheadas(tourData) {
    const tourId = (tourData.guid || 'tour').substring(0, 8);
    let html = '';

    for (const fecha of tourData.fechas) {
        const timeslots = fecha.timeslots || [];
        const fechaId = tourId + '_' + fecha.fecha.replace(/[^a-z0-9]/gi, '_');

        // Calcular estado
        const porcentajeOcupado = fecha.plazas_totales > 0
            ? ((fecha.plazas_totales - fecha.plazas_disponibles) / fecha.plazas_totales * 100).toFixed(1)
            : 0;

        let estado = 'DISPONIBLE';
        let nivel = 'alta';
        if (fecha.plazas_disponibles === 0) {
            estado = 'AGOTADO';
            nivel = 'agotado';
        } else if (porcentajeOcupado > 70) {
            estado = 'POCA DISPONIBILIDAD';
            nivel = 'baja';
        } else if (porcentajeOcupado > 30) {
            estado = 'DISPONIBILIDAD MODERADA';
            nivel = 'media';
        }

        // Obtener dia de la semana
        let diaSemana = '';
        try {
            const fechaObj = new Date(fecha.fecha + 'T00:00:00');
            diaSemana = ['Dom', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab'][fechaObj.getDay()];
        } catch (e) {}

        html += `
            <div class="fecha-row" onclick="toggleTimeslots('${fechaId}')">
                <div class="fecha-cell fecha-fecha">${fecha.fecha}</div>
                <div class="fecha-cell fecha-dia">${diaSemana}</div>
                <div class="fecha-cell fecha-plazas"><strong>${fecha.plazas_disponibles.toLocaleString()}</strong> / ${fecha.plazas_totales.toLocaleString()}</div>
                <div class="fecha-cell fecha-ocupado">${porcentajeOcupado}%</div>
                <div class="fecha-cell fecha-estado"><span class="badge badge-${nivel}">${estado}</span></div>
                <div class="fecha-cell fecha-horarios expand-hint">${ICONS.chevronDown} ${timeslots.length} horarios</div>
            </div>
            <div class="timeslots-panel" id="timeslots_${fechaId}">
                ${generarTimeslotsGridCacheados(timeslots)}
            </div>
        `;
    }

    return `
        <div class="fechas-container">
            <div class="fechas-header">
                <div class="fecha-cell fecha-fecha">Fecha</div>
                <div class="fecha-cell fecha-dia">Dia</div>
                <div class="fecha-cell fecha-plazas">Plazas Disponibles</div>
                <div class="fecha-cell fecha-ocupado">% Ocupado</div>
                <div class="fecha-cell fecha-estado">Estado</div>
                <div class="fecha-cell fecha-horarios">Horarios</div>
            </div>
            ${html}
        </div>
    `;
}

// Generar grid de timeslots desde cache
function generarTimeslotsGridCacheados(timeslots) {
    if (!timeslots || timeslots.length === 0) {
        return '<p style="padding: 15px; color: #666;">No hay horarios detallados disponibles</p>';
    }

    let html = '<div class="timeslots-grid">';

    const timeslotsSorted = [...timeslots].sort((a, b) => {
        const horaA = a.hora || '00:00';
        const horaB = b.hora || '00:00';
        return horaA.localeCompare(horaB);
    });

    for (const ts of timeslotsSorted) {
        const capacidad = ts.capacidad || 0;
        const capacidadOriginal = ts.capacidad_original || capacidad;
        const porcentajeOcupado = capacidadOriginal > 0
            ? ((capacidadOriginal - capacidad) / capacidadOriginal * 100)
            : 0;

        let clase = 'disponible';
        if (capacidad === 0) {
            clase = 'agotado';
        } else if (porcentajeOcupado > 70) {
            clase = 'parcial';
        }

        html += `
            <div class="timeslot-card ${clase}">
                <div class="timeslot-hora">${ts.hora || 'N/A'}</div>
                <div class="timeslot-plazas">${capacidad} / ${capacidadOriginal}</div>
                <div class="timeslot-plazas">${porcentajeOcupado.toFixed(0)}%</div>
            </div>
        `;
    }

    html += '</div>';
    return html;
}

// Actualizar estado visual de cookies
function actualizarEstadoCookies(estado, titulo, detalle) {
    const statusBox = document.getElementById('cookieStatus');
    statusBox.className = 'status-box ' + estado;
    statusBox.innerHTML = `
        <div class="status-title">${titulo}</div>
        <div class="status-detail">${detalle}</div>
    `;
}

// Cargar cookies automáticas desde Supabase
async function cargarCookiesAutomaticas() {
    actualizarEstadoCookies('loading', 'Cargando cookies...', 'Conectando con Supabase');

    try {
        const response = await fetch('/api/cookies/auto');
        const data = await response.json();

        if (data.success && data.cookies) {
            currentCookies = data.cookies;

            const timestamp = data.timestamp ? new Date(data.timestamp).toLocaleString() : 'desconocido';
            actualizarEstadoCookies('success',
                `Cookies activas (${data.count})`,
                `Actualizadas: ${timestamp} | Fuente: ${data.source || 'automatico'}`
            );

            // Auto-consultar disponibilidad
            await consultarDisponibilidad();
        } else {
            actualizarEstadoCookies('error',
                'Sin cookies disponibles',
                data.error || 'No se encontraron cookies en Supabase. Ejecuta el workflow de GitHub Actions.'
            );
        }
    } catch (error) {
        console.error('[Auto] Error cargando cookies:', error);
        actualizarEstadoCookies('error',
            'Error de conexion',
            'No se pudo conectar con el servidor: ' + error.message
        );
    }
}

// Refrescar datos - Triggea Railway para obtener datos frescos
async function refrescarCookies() {
    const btn = document.getElementById('refreshBtn');
    btn.disabled = true;
    btn.textContent = 'Actualizando...';

    try {
        // Triggear Railway para obtener datos frescos
        actualizarEstadoCookies('loading', 'Iniciando actualización...', 'Conectando con Railway');

        const response = await fetch('/api/railway/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showAlert('success', 'Actualización iniciada. Los datos estarán listos en 2-3 minutos.');
            actualizarEstadoCookies('loading',
                'Railway ejecutándose...',
                'Los datos se actualizarán automáticamente. Recarga la página en 2-3 minutos.'
            );

            // Programar recarga automática en 3 minutos
            setTimeout(async () => {
                await cargarDisponibilidadCacheada();
                showAlert('success', 'Datos actualizados');
            }, 180000);

        } else {
            // Si Railway no está configurado, solo recargar desde cache
            const loaded = await cargarDisponibilidadCacheada();
            if (loaded) {
                showAlert('success', 'Datos cargados desde cache');
            } else {
                showAlert('error', data.error || 'No se pudo actualizar');
            }
        }

    } catch (error) {
        console.error('[Refresh] Error:', error);
        // Fallback: recargar desde cache
        await cargarDisponibilidadCacheada();
        showAlert('error', 'Error conectando. Datos cargados desde cache.');
    }

    btn.disabled = false;
    btn.innerHTML = `${ICONS.refresh} Actualizar Datos`;
}

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

// Consultar disponibilidad
async function consultarDisponibilidad() {
    if (!currentCookies) {
        showAlert('error', 'No hay cookies disponibles');
        return;
    }

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
                cookies: currentCookies,
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

        // Guardar automáticamente en histórico
        guardarHistoricoAutomatico(data);

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
            console.log('Historico guardado:', result.message);
        }
    } catch (error) {
        console.error('Error guardando historico:', error);
    }
}

// SVG Icons
const ICONS = {
    calendar: '<svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" /></svg>',
    chart: '<svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" /></svg>',
    clock: '<svg class="icon" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>',
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
    const tourId = tourData.guid.substring(0, 8);
    let html = '';

    for (const fecha of tourData.fechas) {
        const timeslots = tourData.timeslots_por_fecha[fecha.fecha] || [];
        const fechaId = tourId + '_' + fecha.fecha.replace(/[^a-z0-9]/gi, '_');

        html += `
            <div class="fecha-row" onclick="toggleTimeslots('${fechaId}')">
                <div class="fecha-cell fecha-fecha">${fecha.fecha}</div>
                <div class="fecha-cell fecha-dia">${fecha.dia_semana}</div>
                <div class="fecha-cell fecha-plazas"><strong>${fecha.plazas_disponibles.toLocaleString()}</strong> / ${fecha.plazas_totales.toLocaleString()}</div>
                <div class="fecha-cell fecha-ocupado">${fecha.porcentaje_ocupado}%</div>
                <div class="fecha-cell fecha-estado"><span class="badge badge-${fecha.nivel}">${fecha.estado}</span></div>
                <div class="fecha-cell fecha-horarios expand-hint">${ICONS.chevronDown} ${timeslots.length} horarios</div>
            </div>
            <div class="timeslots-panel" id="timeslots_${fechaId}">
                ${generarTimeslotsGrid(timeslots)}
            </div>
        `;
    }

    return `
        <div class="fechas-container">
            <div class="fechas-header">
                <div class="fecha-cell fecha-fecha">Fecha</div>
                <div class="fecha-cell fecha-dia">Dia</div>
                <div class="fecha-cell fecha-plazas">Plazas Disponibles</div>
                <div class="fecha-cell fecha-ocupado">% Ocupado</div>
                <div class="fecha-cell fecha-estado">Estado</div>
                <div class="fecha-cell fecha-horarios">Horarios</div>
            </div>
            ${html}
        </div>
    `;
}

// Generar grid de timeslots
function generarTimeslotsGrid(timeslots) {
    if (!timeslots || timeslots.length === 0) {
        return '<p style="padding: 15px; color: #666;">No hay horarios detallados disponibles</p>';
    }

    let html = '<div class="timeslots-grid">';

    const timeslotsSorted = [...timeslots].sort((a, b) => {
        const horaA = a.hora || '00:00';
        const horaB = b.hora || '00:00';
        return horaA.localeCompare(horaB);
    });

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
    const panel = document.getElementById('timeslots_' + fechaId);
    panel.classList.toggle('active');
}

// Cambiar tab
function cambiarTab(tourId, tabName, event) {
    const container = event.target.closest('.tour-section');
    container.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    container.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(`${tourId}_${tabName}`).classList.add('active');
}

// Descargar histórico desde Supabase
async function descargarHistorico() {
    try {
        showAlert('success', 'Descargando historico...');

        const response = await fetch('/api/descargar-historico');

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error al descargar');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `historico_disponibilidad_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showAlert('success', 'Historico descargado correctamente');

    } catch (error) {
        showAlert('error', 'Error al descargar historico: ' + error.message);
    }
}

// Exponer funciones globalmente
window.refrescarCookies = refrescarCookies;
window.toggleTimeslots = toggleTimeslots;
window.cambiarTab = cambiarTab;
window.descargarHistorico = descargarHistorico;

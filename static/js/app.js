// Estado global
let currentResults = null;
let currentCookies = null;
let usingCachedData = false;

// Convert UTC timestamp to Rome time (automatically handles CET/CEST)
function formatTimestampRome(isoString) {
    if (!isoString) return 'unknown';
    try {
        const date = new Date(isoString);
        // toLocaleString with Europe/Rome automatically handles daylight saving time
        return date.toLocaleString('en-GB', {timeZone: 'Europe/Rome'});
    } catch (e) {
        return isoString;
    }
}

// Auto-cargar al iniciar: primero intentar cache, luego cookies
document.addEventListener('DOMContentLoaded', async function() {
    // Intentar cargar disponibilidad cacheada primero (de Railway)
    const cachedLoaded = await cargarDisponibilidadCacheada();

    if (!cachedLoaded) {
        // Si no hay cache, cargar cookies y consultar directamente
        await cargarCookiesAutomaticas();
    }
});

// Load cached availability from Supabase (saved by Railway)
async function cargarDisponibilidadCacheada() {
    actualizarEstadoCookies('loading', 'Loading data...', 'Searching availability in cache');

    try {
        // Add cache-busting parameter to force fresh data
        const cacheBuster = Date.now();
        const response = await fetch(`/api/availability/cached?_=${cacheBuster}`, {
            cache: 'no-store'
        });
        const data = await response.json();

        if (response.ok && data.resultados && Object.keys(data.resultados).length > 0) {
            usingCachedData = true;

            const timestamp = data.timestamp ? new Date(data.timestamp).toLocaleString('en-GB', {timeZone: 'Europe/Rome'}) : 'unknown';
            actualizarEstadoCookies('success',
                'Cached data available',
                `Updated: ${timestamp}`
            );

            // Show cached results
            currentResults = data;
            mostrarResultadosCacheados(data);

            return true;
        } else {
            console.log('[Cache] No cached data:', data.error);
            return false;
        }
    } catch (error) {
        console.error('[Cache] Error loading cache:', error);
        return false;
    }
}

// Show results from cache
function mostrarResultadosCacheados(data) {
    // No summary cards - removed Tours Disponibles and Fuente
    document.getElementById('summaryCards').innerHTML = '';

    let toursHtml = '';

    for (const [tourKey, tourData] of Object.entries(data.resultados)) {
        const tourId = tourKey.replace(/[^a-z0-9]/gi, '_');

        toursHtml += `
            <div class="tour-section">
                <div class="tour-section-header">
                    <h3 class="tour-section-title">${tourData.nombre}</h3>
                    <div class="tour-section-stats">
                        <span><strong>${tourData.total_fechas}</strong> available dates</span>
                        <span><strong>${tourData.total_plazas.toLocaleString()}</strong> total spots</span>
                    </div>
                </div>

                <div class="tabs">
                    <button class="tab-btn active" onclick="cambiarTab('${tourId}', 'fechas', event)">
                        ${ICONS.calendar} By Date
                    </button>
                </div>

                <div class="tab-content active" id="${tourId}_fechas">
                    ${generarTablaFechasCacheadas(tourData)}
                </div>
            </div>
        `;
    }

    document.getElementById('tourResults').innerHTML = toursHtml;
    const cachedTimestamp = data.timestamp ? new Date(data.timestamp).toLocaleString('en-GB', {timeZone: 'Europe/Rome'}) : 'unknown';
    document.getElementById('timestamp').textContent = `Cached data: ${cachedTimestamp}`;
    document.getElementById('results').classList.add('active');
    document.getElementById('loading').classList.remove('active');
}

// Generate date table from cached data
function generarTablaFechasCacheadas(tourData) {
    const tourId = (tourData.guid || 'tour').substring(0, 8);
    let html = '';

    for (const fecha of tourData.fechas) {
        const timeslots = fecha.timeslots || [];
        const fechaId = tourId + '_' + fecha.fecha.replace(/[^a-z0-9]/gi, '_');

        // Calculate status
        const porcentajeOcupado = fecha.plazas_totales > 0
            ? ((fecha.plazas_totales - fecha.plazas_disponibles) / fecha.plazas_totales * 100).toFixed(1)
            : 0;

        let estado = 'AVAILABLE';
        let nivel = 'alta';
        if (fecha.plazas_disponibles === 0) {
            estado = 'SOLD OUT';
            nivel = 'agotado';
        } else if (porcentajeOcupado > 70) {
            estado = 'LOW AVAILABILITY';
            nivel = 'baja';
        } else if (porcentajeOcupado > 30) {
            estado = 'MODERATE';
            nivel = 'media';
        }

        // Get day of week
        let diaSemana = '';
        try {
            const fechaObj = new Date(fecha.fecha + 'T00:00:00');
            diaSemana = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][fechaObj.getDay()];
        } catch (e) {}

        html += `
            <div class="fecha-row" onclick="toggleTimeslots('${fechaId}')">
                <div class="fecha-cell fecha-fecha">${fecha.fecha}</div>
                <div class="fecha-cell fecha-dia">${diaSemana}</div>
                <div class="fecha-cell fecha-plazas"><strong>${fecha.plazas_disponibles.toLocaleString()}</strong> / ${fecha.plazas_totales.toLocaleString()}</div>
                <div class="fecha-cell fecha-ocupado">${porcentajeOcupado}%</div>
                <div class="fecha-cell fecha-estado"><span class="badge badge-${nivel}">${estado}</span></div>
                <div class="fecha-cell fecha-horarios expand-hint">${ICONS.chevronDown} ${timeslots.length} timeslots</div>
            </div>
            <div class="timeslots-panel" id="timeslots_${fechaId}">
                ${generarTimeslotsGridCacheados(timeslots)}
            </div>
        `;
    }

    return `
        <div class="fechas-container">
            <div class="fechas-header">
                <div class="fecha-cell fecha-fecha">Date</div>
                <div class="fecha-cell fecha-dia">Day</div>
                <div class="fecha-cell fecha-plazas">Available Spots</div>
                <div class="fecha-cell fecha-ocupado">% Occupied</div>
                <div class="fecha-cell fecha-estado">Status</div>
                <div class="fecha-cell fecha-horarios">Timeslots</div>
            </div>
            ${html}
        </div>
    `;
}

// Generate timeslots grid from cache
function generarTimeslotsGridCacheados(timeslots) {
    if (!timeslots || timeslots.length === 0) {
        return '<p style="padding: 15px; color: #666;">No detailed timeslots available</p>';
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

// Update visual status of cookies
function actualizarEstadoCookies(estado, titulo, detalle) {
    const statusBox = document.getElementById('cookieStatus');
    statusBox.className = 'status-box ' + estado;
    statusBox.innerHTML = `
        <div class="status-title">${titulo}</div>
        <div class="status-detail">${detalle}</div>
    `;
}

// Load automatic cookies from Supabase
async function cargarCookiesAutomaticas() {
    actualizarEstadoCookies('loading', 'Loading cookies...', 'Connecting to Supabase');

    try {
        const response = await fetch('/api/cookies/auto');
        const data = await response.json();

        if (data.success && data.cookies) {
            currentCookies = data.cookies;

            const timestamp = data.timestamp ? new Date(data.timestamp).toLocaleString('en-GB', {timeZone: 'Europe/Rome'}) : 'unknown';
            actualizarEstadoCookies('success',
                `Active cookies (${data.count})`,
                `Updated: ${timestamp}`
            );

            // Auto-query availability
            await consultarDisponibilidad();
        } else {
            actualizarEstadoCookies('error',
                'No cookies available',
                data.error || 'No cookies found in Supabase. Run the GitHub Actions workflow.'
            );
        }
    } catch (error) {
        console.error('[Auto] Error loading cookies:', error);
        actualizarEstadoCookies('error',
            'Connection error',
            'Could not connect to server: ' + error.message
        );
    }
}

// Refresh data - Triggers Railway to get fresh data
async function refrescarCookies() {
    const btn = document.getElementById('refreshBtn');
    const originalHtml = btn.innerHTML;

    // Disable button and show loading state with grey style
    btn.disabled = true;
    btn.style.backgroundColor = '#9ca3af';
    btn.style.cursor = 'not-allowed';
    btn.innerHTML = `
        <svg class="icon" style="animation: spin 1s linear infinite;" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
        </svg>
        Updating...
    `;

    try {
        // Trigger Railway to get fresh data
        actualizarEstadoCookies('loading', 'Starting update...', 'Connecting to Railway');

        const response = await fetch('/api/railway/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showAlert('success', 'Update started. Data will be ready in 2-3 minutes.');
            actualizarEstadoCookies('loading',
                'Railway running...',
                'Data will update automatically. Page will refresh in 2-3 minutes.'
            );

            // Schedule automatic reload in 3 minutes
            setTimeout(async () => {
                await cargarDisponibilidadCacheada();
                showAlert('success', 'Data updated');
                // Re-enable button after auto-refresh
                btn.disabled = false;
                btn.style.backgroundColor = '';
                btn.style.cursor = '';
                btn.innerHTML = originalHtml;
            }, 180000);

            // Keep button disabled while waiting for Railway
            return;

        } else {
            // If Railway is not configured, just reload from cache
            const loaded = await cargarDisponibilidadCacheada();
            if (loaded) {
                showAlert('success', 'Data loaded from cache');
            } else {
                showAlert('error', data.error || 'Could not update');
            }
        }

    } catch (error) {
        console.error('[Refresh] Error:', error);
        // Fallback: reload from cache
        await cargarDisponibilidadCacheada();
        showAlert('error', 'Connection error. Data loaded from cache.');
    }

    // Re-enable button
    btn.disabled = false;
    btn.style.backgroundColor = '';
    btn.style.cursor = '';
    btn.innerHTML = originalHtml;
}

// Show alerts
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

// Query availability
async function consultarDisponibilidad() {
    if (!currentCookies) {
        showAlert('error', 'No cookies available');
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

// Save to history automatically
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
            console.log('History saved:', result.message);
        }
    } catch (error) {
        console.error('Error saving history:', error);
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

// Show results with tabs
function mostrarResultados(data) {
    // No summary cards - removed
    document.getElementById('summaryCards').innerHTML = '';

    let toursHtml = '';

    for (const [tourKey, tourData] of Object.entries(data.resultados)) {
        const tourId = tourKey.replace(/[^a-z0-9]/gi, '_');

        toursHtml += `
            <div class="tour-section">
                <div class="tour-section-header">
                    <h3 class="tour-section-title">${tourData.nombre}</h3>
                    <div class="tour-section-stats">
                        <span><strong>${tourData.total_fechas}</strong> available dates</span>
                        <span><strong>${tourData.total_plazas.toLocaleString()}</strong> total spots</span>
                    </div>
                </div>

                <div class="tabs">
                    <button class="tab-btn active" onclick="cambiarTab('${tourId}', 'fechas', event)">
                        ${ICONS.calendar} By Date
                    </button>
                    <button class="tab-btn" onclick="cambiarTab('${tourId}', 'estadisticas', event)">
                        ${ICONS.chart} Statistics
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
    document.getElementById('timestamp').textContent = `Last query: ${data.timestamp}`;
    document.getElementById('results').classList.add('active');
}

// Generate date table with expandable timeslots
function generarTablaFechas(tourData) {
    const tourId = tourData.guid.substring(0, 8);
    let html = '';

    // Translate status to English
    const translateStatus = (estado) => {
        const translations = {
            'DISPONIBLE': 'AVAILABLE',
            'AGOTADO': 'SOLD OUT',
            'POCA DISPONIBILIDAD': 'LOW AVAILABILITY',
            'DISPONIBILIDAD MODERADA': 'MODERATE'
        };
        return translations[estado] || estado;
    };

    // Translate day names
    const translateDay = (dia) => {
        const translations = {
            'Dom': 'Sun', 'Lun': 'Mon', 'Mar': 'Tue', 'Mie': 'Wed',
            'Jue': 'Thu', 'Vie': 'Fri', 'Sab': 'Sat'
        };
        return translations[dia] || dia;
    };

    for (const fecha of tourData.fechas) {
        const timeslots = tourData.timeslots_por_fecha[fecha.fecha] || [];
        const fechaId = tourId + '_' + fecha.fecha.replace(/[^a-z0-9]/gi, '_');

        html += `
            <div class="fecha-row" onclick="toggleTimeslots('${fechaId}')">
                <div class="fecha-cell fecha-fecha">${fecha.fecha}</div>
                <div class="fecha-cell fecha-dia">${translateDay(fecha.dia_semana)}</div>
                <div class="fecha-cell fecha-plazas"><strong>${fecha.plazas_disponibles.toLocaleString()}</strong> / ${fecha.plazas_totales.toLocaleString()}</div>
                <div class="fecha-cell fecha-ocupado">${fecha.porcentaje_ocupado}%</div>
                <div class="fecha-cell fecha-estado"><span class="badge badge-${fecha.nivel}">${translateStatus(fecha.estado)}</span></div>
                <div class="fecha-cell fecha-horarios expand-hint">${ICONS.chevronDown} ${timeslots.length} timeslots</div>
            </div>
            <div class="timeslots-panel" id="timeslots_${fechaId}">
                ${generarTimeslotsGrid(timeslots)}
            </div>
        `;
    }

    return `
        <div class="fechas-container">
            <div class="fechas-header">
                <div class="fecha-cell fecha-fecha">Date</div>
                <div class="fecha-cell fecha-dia">Day</div>
                <div class="fecha-cell fecha-plazas">Available Spots</div>
                <div class="fecha-cell fecha-ocupado">% Occupied</div>
                <div class="fecha-cell fecha-estado">Status</div>
                <div class="fecha-cell fecha-horarios">Timeslots</div>
            </div>
            ${html}
        </div>
    `;
}

// Generate timeslots grid
function generarTimeslotsGrid(timeslots) {
    if (!timeslots || timeslots.length === 0) {
        return '<p style="padding: 15px; color: #666;">No detailed timeslots available</p>';
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

// Generate statistics
function generarEstadisticas(stats) {
    return `
        <div class="stats-grid">
            <div class="stats-card">
                <h4>${ICONS.clock} Most Demanded Timeslots</h4>
                <p class="stats-card-hint">
                    Timeslots that sell out most often (% of days sold out)
                </p>
                ${stats.por_hora.map(h => `
                    <div class="stats-row">
                        <span class="stats-label">${h.hora}</span>
                        <span class="stats-value">${h.porcentaje_agotado}% sold out</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${h.porcentaje_agotado}%"></div>
                    </div>
                    <p class="stats-detail">${h.timeslots_agotados} of ${h.total_timeslots} days | Average occupancy: ${h.ocupacion_promedio}%</p>
                `).join('')}
            </div>

            <div class="stats-card">
                <h4>${ICONS.calendarDays} Days in Advance</h4>
                <p class="stats-card-hint">
                    Future dates that already have sold out timeslots
                </p>
                ${stats.dias_agotamiento.slice(0, 10).map(d => `
                    <div class="stats-row">
                        <span class="stats-label">${d.fecha}</span>
                        <span class="stats-value">${d.dias_adelantados} days</span>
                    </div>
                    <p class="stats-detail">${d.timeslots_agotados} of ${d.total_timeslots} timeslots sold out (${d.porcentaje_agotado}%)</p>
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

// Download history from Supabase
async function descargarHistorico() {
    try {
        showAlert('success', 'Downloading history...');

        const response = await fetch('/api/descargar-historico');

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error downloading');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `availability_history_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showAlert('success', 'History downloaded successfully');

    } catch (error) {
        showAlert('error', 'Error downloading history: ' + error.message);
    }
}

// Expose functions globally
window.refrescarCookies = refrescarCookies;
window.toggleTimeslots = toggleTimeslots;
window.cambiarTab = cambiarTab;
window.descargarHistorico = descargarHistorico;

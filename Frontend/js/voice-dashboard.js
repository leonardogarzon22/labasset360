// js/voice-dashboard.js

document.addEventListener('DOMContentLoaded', () => {

    const comandosDashboard = [
        // 1. Navegación: Crear Equipo / Equipo Nuevo
        {
            regex: /(ir a |abrir |nuevo )?(crear equipo|equipo nuevo)/i,
            action: () => {
                VoiceEngine.feedback("Entendido, redireccionando a creación de equipo.");
                setTimeout(() => {
                    window.location.href = 'crear-equipo.html';
                }, 1200); // Pequeña pausa para que se escuche la voz de Siena antes del cambio de página
            }
        },
        // 2. Navegación: Histórico / Ver Histórico / Historial
        {
            regex: /(ir a |abrir |ver )?(histórico|historico|historial)/i,
            action: () => {
                VoiceEngine.feedback("Abriendo el historial de activos del laboratorio.");
                setTimeout(() => {
                    window.location.href = 'historico.html';
                }, 1200);
            }
        },
        // 3. Navegación: Reportes / Ver Reportes
        {
            regex: /(ir a |abrir |ver )?(reporte|reportes)/i,
            action: () => {
                VoiceEngine.feedback("Redireccionando a la sección de reportes oficiales.");
                setTimeout(() => {
                    window.location.href = 'reporte.html';
                }, 1200);
            }
        },
        // 4. Acción: Recargar / Actualizar Panel
        {
            regex: /(actualizar |recargar )(panel|dashboard|página|pagina)/i,
            action: () => {
                VoiceEngine.feedback("Actualizando los datos de la flota.");
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        },
        // 5. Lectura de KPIs por Voz (Lectura manos libres de los datos del Dashboard)
        {
            regex: /(leer |dame el |cuál es el )?resumen( general| del laboratorio)?/i,
            action: () => {
                // Captura segura de los datos directo de las cards de tu dashboard.html
                const elOperatividad = document.getElementById('kpi-op');
                const elMantenimientos = document.getElementById('kpi-mant');
                const elCalibraciones = document.getElementById('kpi-cal');
                const elSalud = document.getElementById('kpi-salud');
                const elActivos = document.getElementById('txt-activos-sum');
                const elFuera = document.getElementById('txt-no-operativos-sum');

                const operatividad = elOperatividad ? elOperatividad.innerText : "desconocida";
                const mantenimientos = elMantenimientos ? elMantenimientos.innerText : "0";
                const calibraciones = elCalibraciones ? elCalibraciones.innerText : "0";
                const salud = elSalud ? elSalud.innerText : "buena";
                const activos = elActivos ? elActivos.innerText : "0";
                const fuera = elFuera ? elFuera.innerText : "0";

                let reporteInformativo = `Reporte operativo del sistema. La operatividad actual de la flota es del ${operatividad}, ` +
                    `con un índice de salud general del ${salud}. ` +
                    `Actualmente posees ${activos} equipos activos en línea y ${fuera} fuera de servicio. ` +
                    `Hay registrados ${mantenimientos} mantenimientos programados y ${calibraciones} calibraciones pendientes.`;

                VoiceEngine.feedback(reporteInformativo);
            }
        }
    ];

    // Registramos los comandos de navegación en el core de Siena
    VoiceEngine.registerCommands(comandosDashboard);
});
// js/voice-historico.js

// Función de limpieza final: Elimina espacios residuales y asegura mayúsculas para la base de datos
function normalizarCodigoFinal(hablado) {
    if (!hablado) return '';

    // Como el motor central ya cambió "guion" por "-" y "cero" por "0",
    // aquí solo eliminamos cualquier espacio en blanco y pasamos a MAYÚSCULAS
    return hablado.replace(/\s+/g, '').toUpperCase();
}

const comandosHistorico = [
    // ==========================================
    // 1. NAVEGACIÓN GLOBAL
    // ==========================================
    {
        regex: /(ir a |abrir |volver a |ver )?(dashboard|inicio|panel)/i,
        action: () => {
            window.VoiceEngine.feedback("Regresando al panel principal.");
            setTimeout(() => window.location.href = 'dashboard.html', 1000);
        }
    },
    {
        regex: /(ir a |abrir |nuevo )?(crear equipo|equipo nuevo)/i,
        action: () => {
            window.VoiceEngine.feedback("Redireccionando a creación de equipo.");
            setTimeout(() => window.location.href = 'crear-equipo.html', 1000);
        }
    },
    {
        regex: /(ir a |abrir |ver )?(reporte|reportes)/i,
        action: () => {
            window.VoiceEngine.feedback("Abriendo la sección de reportes.");
            setTimeout(() => window.location.href = 'reporte.html', 1000);
        }
    },

    // ==========================================
    // 2. BUSCAR Y ABRIR EQUIPO POR CÓDIGO
    // ==========================================
    // Gracias al motor central, si dices: "abrir L punto CE guion ICP guion cero uno"
    // la frase llegará procesada aquí como: "abrir l.ce-icp-01"
    {
        regex: /^(abrir|ver|buscar|equipo)\s+(.*)/i,
        action: (match) => {
            const codigoHablado = match[2];

            // Exclusión de seguridad para navegación
            if (['dashboard', 'inicio', 'reporte', 'reportes', 'historial', 'crear equipo'].includes(codigoHablado.toLowerCase())) {
                return;
            }

            // Pasamos el fragmento por la limpieza final (Ej: "l.ce-icp-01" -> "L.CE-ICP-01")
            const codigoLimpio = normalizarCodigoFinal(codigoHablado);
            console.log("Siena procesó el código del histórico como:", codigoLimpio);

            // Verificamos en el array global 'todosLosEquipos' del HTML
            if (typeof todosLosEquipos !== 'undefined' && todosLosEquipos.length > 0) {

                // Buscamos coincidencia exacta del código en tu base de datos
                const equipoEncontrado = todosLosEquipos.find(eq => eq.codigo.toUpperCase() === codigoLimpio);

                if (equipoEncontrado) {
                    window.VoiceEngine.feedback(`Abriendo la ficha técnica del equipo ${codigoLimpio}`);
                    setTimeout(() => irADetalle(equipoEncontrado.id), 1500);
                } else {
                    window.VoiceEngine.feedback(`No encontré ningún equipo registrado con el código ${codigoLimpio}.`);
                }
            } else {
                window.VoiceEngine.feedback("La base de datos aún se está cargando, por favor intenta en un segundo.");
            }
        }
    }
];

// Registro INMEDIATO en el núcleo global sin esperar a que cargue el DOM
if (window.VoiceEngine && typeof window.VoiceEngine.registerCommands === 'function') {
    window.VoiceEngine.registerCommands(comandosHistorico);
} else {
    console.error("Siena Engine no estaba listo para recibir los comandos del histórico.");
}
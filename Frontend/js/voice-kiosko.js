// js/voice-kiosko.js

    const comandosKiosko = [
        // ==========================================
        // 1. SOLICITUD DE PRÉSTAMOS
        // ==========================================
        {
            regex: /^(?:solicitar|pedir|iniciar) (?:préstamo|prestamo|equipo)/i,
            action: () => {
                VoiceEngine.feedback("Iniciando solicitud de préstamo.");
                const btnSolicitar = document.querySelector('.btn-solicitar'); //
                
                // Prioriza el clic en el elemento del DOM, fallback a la función global
                if (btnSolicitar) {
                    btnSolicitar.click();
                } else if (typeof solicitarEquipo === 'function') {
                    solicitarEquipo(); //[cite: 5]
                }
            }
        },

        // ==========================================
        // 2. REPORTE DE FALLAS
        // ==========================================
        {
            regex: /^reportar (?:falla|error|problema|daño|dano|anomalía|anomalia)/i,
            action: () => {
                VoiceEngine.feedback("Abriendo formulario para reportar falla.");
                const btnFalla = document.querySelector('.btn-falla'); //[cite: 5]
                
                if (btnFalla) {
                    btnFalla.click();
                } else if (typeof reportarFalla === 'function') {
                    reportarFalla(); //[cite: 5]
                }
            }
        },

        // ==========================================
        // 3. REPORTE TÉCNICO E HISTORIAL
        // ==========================================
        {
            regex: /^(?:ver |abrir |generar |mostrar )?(?:reporte|reporte técnico|reporte tecnico|hoja de vida)/i,
            action: () => {
                VoiceEngine.feedback("Abriendo el reporte técnico y hoja de vida del equipo.");
                const btnReporte = document.querySelector('.btn-reporte'); //[cite: 5]
                
                if (btnReporte) {
                    btnReporte.click();
                } else {
                    // Extracción dinámica del código del equipo desde el DOM en caso de fallback
                    const h2Codigo = document.querySelector('.equipo-info h2'); //[cite: 5]
                    const codigo = h2Codigo ? h2Codigo.innerText : '';
                    if (typeof abrirReporte === 'function') {
                        abrirReporte(codigo); //[cite: 5]
                    }
                }
            }
        },

        // ==========================================
        // 4. GESTIÓN AVANZADA (Mantenimiento/Calibración)
        // ==========================================
        {
            regex: /^(?:abrir |ir a |ver )?(?:gestión avanzada|gestion avanzada|detalle|mantenimiento|calibración|calibracion)/i,
            action: () => {
                VoiceEngine.feedback("Accediendo al panel de gestión avanzada del activo.");
                const btnMantenimiento = document.querySelector('.btn-mantenimiento'); //[cite: 5]
                
                if (btnMantenimiento) {
                    btnMantenimiento.click();
                } else if (typeof abrirDetalleEquipo === 'function') {
                    abrirDetalleEquipo(); //[cite: 5]
                }
            }
        },

        // ==========================================
        // 5. NAVEGACIÓN GENERAL (Fallbacks de seguridad)
        // ==========================================
        {
            regex: /(ir a |volver a |volver al )?(dashboard|inicio|panel principal)/i,
            action: () => {
                VoiceEngine.feedback("Regresando al panel principal.");
                setTimeout(() => window.location.href = 'dashboard.html', 1000);
            }
        },
        {
            regex: /(volver |ir )?(atrás|atras|histórico|historico)/i,
            action: () => {
                VoiceEngine.feedback("Volviendo al historial de equipos.");
                setTimeout(() => window.location.href = 'historico.html', 1000);
            }
        }
    ];

    // Registro en el núcleo de procesamiento de voz
    if (window.VoiceEngine && typeof VoiceEngine.registerCommands === 'function') {
        VoiceEngine.registerCommands(comandosKiosko);
    } else {
        console.error("Sienna no estaba lista para recibir los comandos del kiosko");
    }

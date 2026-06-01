// js/voice-reporte.js

document.addEventListener('DOMContentLoaded', () => {

    /**
     * Traduce el dictado fonético continuo en la nomenclatura real del inventario.
     * Ejemplo: "CGGUIONCEROUNO" -> "CG-01"
     */
    function transformarCodigoHablado(texto) {
        let clean = texto.toUpperCase().replace(/\s+/g, '');

        // Reemplazo de palabras clave de puntuación
        clean = clean.replace(/GUIONBAJO/g, '_');
        clean = clean.replace(/GUION/g, '-');
        clean = clean.replace(/RAYA/g, '-');

        // Mapeo de números deletreados por voz
        const numerosMapeo = {
            'CERO': '0', 'UNO': '1', 'DOS': '2', 'TRES': '3', 'CUATRO': '4',
            'CINCO': '5', 'SEIS': '6', 'SIETE': '7', 'OCHO': '8', 'NUEVE': '9'
        };

        Object.keys(numerosMapeo).forEach(key => {
            const regex = new RegExp(key, 'g');
            clean = clean.replace(regex, numerosMapeo[key]);
        });

        return clean.trim();
    }

    const comandosReporte = [
        // ==========================================
        // 1. NAVEGACIÓN ENTRE SECCIONES
        // ==========================================
        {
            regex: /(ir a |volver a )?dashboard/i,
            action: () => {
                VoiceEngine.feedback("Redirigiendo al panel principal.");
                setTimeout(() => window.location.href = 'dashboard.html', 1000); //[cite: 4]
            }
        },
        {
            regex: /(ir a |crear )?crear equipo/i,
            action: () => {
                VoiceEngine.feedback("Abriendo el formulario de registro de equipos.");
                setTimeout(() => window.location.href = 'crear-equipo.html', 1000); //[cite: 4]
            }
        },
        {
            regex: /(ir a |volver al )?histórico|(ir a |volver al )?historico/i,
            action: () => {
                VoiceEngine.feedback("Abriendo el historial general de activos.");
                setTimeout(() => window.location.href = 'historico.html', 1000); //[cite: 4]
            }
        },

        // ==========================================
        // 2. SELECCIÓN DE ACTIVOS (RECONOCIMIENTO EXACTO)
        // ==========================================
        {
            regex: /^(?:seleccionar equipo|equipo|código|codigo) (.+)/i,
            action: async (match) => {
                const dictadoOriginal = match[1];
                const codigoProcesado = transformarCodigoHablado(dictadoOriginal);
                
                const select = document.getElementById('equipo-select'); //[cite: 4]
                if (!select) return;

                let indexEncontrado = -1;

                // Validación estricta para evitar falsos positivos (evita confundir CG-01 con CG-011)
                for (let i = 0; i < select.options.length; i++) {
                    const textoOpcion = select.options[i].text.toUpperCase();
                    
                    // Separamos usando el delimitador exacto " - " definido en la carga de tu base de datos
                    const partes = textoOpcion.split(' - ');
                    const codigoOpcionExacto = partes[0].trim();

                    // Comparación estricta uno a uno
                    if (codigoOpcionExacto === codigoProcesado) {
                        indexEncontrado = i;
                        break;
                    }
                }

                if (indexEncontrado !== -1) {
                    select.selectedIndex = indexEncontrado;
                    select.dispatchEvent(new Event('change')); 
                    VoiceEngine.feedback(`Equipo ${codigoProcesado} seleccionado en el listado.`);
                } else {
                    VoiceEngine.feedback(`No se encontró correspondencia exacta para el código ${codigoProcesado}.`);
                }
            }
        },

        // ==========================================
        // 3. ACCIONES DE REPORTE Y EXPORTACIÓN
        // ==========================================
        {
            regex: /^generar vista previa/i,
            action: () => {
                const select = document.getElementById('equipo-select'); //[cite: 4]
                if (!select || select.value === "") {
                    VoiceEngine.feedback("Por favor, seleccione un equipo antes de generar el reporte.");
                    return;
                }
                VoiceEngine.feedback("Procesando información y generando vista previa.");
                generarVistaPrevia(); //[cite: 4]
            }
        },
        {
            regex: /^descargar pdf/i,
            action: () => {
                const btnDownload = document.getElementById('btnDownload'); //[cite: 4]
                
                // Valida si la vista previa está visible antes de permitir la descarga
                if (btnDownload && window.getComputedStyle(btnDownload).display !== 'none') {
                    VoiceEngine.feedback("Descargando el documento PDF del reporte.");
                    descargarPDF(); //[cite: 4]
                } else {
                    VoiceEngine.feedback("El reporte no ha sido generado todavía. Diga: Generar Vista Previa.");
                }
            }
        }
    ];

    // Registro automático de los comandos en tu núcleo de reconocimiento de voz
    if (window.VoiceEngine && typeof VoiceEngine.registerCommands === 'function') {
        VoiceEngine.registerCommands(comandosReporte);
    }
});
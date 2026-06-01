// js/voice-reportar-falla.js

document.addEventListener('DOMContentLoaded', () => {

    const comandosFalla = [
        // ==========================================
        // 1. CONFIGURACIÓN DE CATEGORÍA
        // ==========================================
        {
            regex: /^(?:cambiar |asignar )?(?:categoría|categoria) (mecánica|mecanica|eléctrica|electrica|software|otra|otro)/i,
            action: (match) => {
                const select = document.getElementById('tipoFalla'); //
                if (!select) return;

                const opcionHablada = match[1].toLowerCase();
                
                // Normalización de términos fonéticos hacia los values nativos del select
                const mapeoCategorias = {
                    'mecánica': 'mecanica',
                    'mecanica': 'mecanica',
                    'eléctrica': 'electrica',
                    'electrica': 'electrica',
                    'software': 'software',
                    'otra': 'otro',
                    'otro': 'otro'
                };

                const valorFinal = mapeoCategorias[opcionHablada];
                if (valorFinal) {
                    select.value = valorFinal;
                    select.dispatchEvent(new Event('change'));
                    VoiceEngine.feedback(`Categoría configurada como ${opcionHablada}.`);
                }
            }
        },

        // ==========================================
        // 2. CONFIGURACIÓN DE IMPACTO / URGENCIA
        // ==========================================
        {
            regex: /^(?:cambiar |asignar )?(?:impacto|urgencia|nivel de urgencia) (baja|media|alta)/i,
            action: (match) => {
                const select = document.getElementById('nivelUrgencia'); //[cite: 6]
                if (!select) return;

                const valorFinal = match[1].toLowerCase();
                select.value = valorFinal;
                select.dispatchEvent(new Event('change'));
                VoiceEngine.feedback(`Impacto establecido en nivel ${valorFinal}.`);
            }
        },

        // ==========================================
        // 3. DICTADO DE DESCRIPCIÓN DETALLADA
        // ==========================================
        {
            // Permite decir "Descripción el equipo no enciende" o "Detalle falla en el sensor"
            regex: /^(?:descripción|descripcion|añadir descripción|detalle|dictar descripción) (.+)/i,
            action: (match) => {
                const textarea = document.getElementById('descripcionFalla'); //[cite: 6]
                if (!textarea) return;

                const textoDictado = match[1].trim();
                
                // Si el campo ya tiene texto, añade un espacio e integra el nuevo dictado de forma aditiva
                if (textarea.value) {
                    textarea.value += " " + textoDictado;
                } else {
                    textarea.value = textoDictado.charAt(0).toUpperCase() + textoDictado.slice(1);
                }
                
                textarea.dispatchEvent(new Event('input'));
                VoiceEngine.feedback("Descripción actualizada.");
            }
        },
        {
            regex: /^(?:borrar|limpiar|vaciar) (?:descripción|descripcion|texto)/i,
            action: () => {
                const textarea = document.getElementById('descripcionFalla'); //[cite: 6]
                if (textarea) {
                    textarea.value = "";
                    textarea.dispatchEvent(new Event('input'));
                    VoiceEngine.feedback("Descripción borrada.");
                }
            }
        },

        // ==========================================
        // 4. ACCIONES DE ENVÍO Y FORMULARIO
        // ==========================================
        {
            regex: /^(?:registrar reporte|enviar reporte|guardar reporte|registrar falla)/i,
            action: () => {
                const form = document.getElementById('fallaForm'); //[cite: 6]
                const textarea = document.getElementById('descripcionFalla'); //[cite: 6]

                // Validación de seguridad previa antes de disparar el submit por voz
                if (textarea && !textarea.value.trim()) {
                    VoiceEngine.feedback("No se puede enviar el reporte porque la descripción está vacía.");
                    textarea.focus();
                    return;
                }

                VoiceEngine.feedback("Procesando y registrando reporte de incidencia.");
                if (form) {
                    form.dispatchEvent(new Event('submit')); //[cite: 6]
                }
            }
        },

        // ==========================================
        // 5. NAVEGACIÓN Y CANCELACIÓN
        // ==========================================
        {
            regex: /^(?:volver atrás|volver atras|regresar|cancelar)/i,
            action: () => {
                VoiceEngine.feedback("Cancelando operación y regresando a la pantalla anterior.");
                setTimeout(() => history.back(), 1000); //[cite: 6]
            }
        },
        {
            regex: /(ir a |volver a )?dashboard/i,
            action: () => {
                VoiceEngine.feedback("Redirigiendo al panel de control.");
                setTimeout(() => window.location.href = 'dashboard.html', 1000);
            }
        }
    ];

    // Registro automático en el núcleo de comandos por voz
    if (window.VoiceEngine && typeof VoiceEngine.registerCommands === 'function') {
        VoiceEngine.registerCommands(comandosFalla);
    }
});
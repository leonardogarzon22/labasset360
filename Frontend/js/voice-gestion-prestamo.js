
document.addEventListener('DOMContentLoaded', () => {

    const comandosMovimiento = [
        // ==========================================
        // 1. RESPONSABLE DE LA CUSTODIA
        // ==========================================
        {
            regex: /^(?:responsable|custodio|asignar responsable) (.+)/i,
            action: (match) => {
                const inputResp = document.getElementById('responsable'); //
                if (!inputResp) return;

                if (inputResp.disabled) {
                    VoiceEngine.feedback("El responsable no se puede modificar en el modo de retorno."); //[cite: 7]
                    return;
                }

                const nombre = match[1].trim();
                inputResp.value = nombre.charAt(0).toUpperCase() + nombre.slice(1);
                inputResp.dispatchEvent(new Event('input'));
                VoiceEngine.feedback(`Responsable asignado: ${nombre}.`);
            }
        },

        // ==========================================
        // 2. LISTA DE VERIFICACIÓN TÉCNICA (CHECKLIST)
        // ==========================================
        {
            // Permite decir: "marcar limpieza", "marcar integridad", etc.
            regex: /^(?:marcar|seleccionar|chequear|revisado) (limpieza|integridad|accesorios|funcionalidad|encendido)/i,
            action: (match) => {
                const itemHablado = match[1].toLowerCase();
                const checkboxes = document.querySelectorAll('.check-item'); //[cite: 7]
                
                checkboxes.forEach(cb => {
                    const valor = cb.value.toLowerCase();
                    // Empareja el valor nativo ('limpieza', 'integridad', 'accesorios', 'funcionalidad')
                    if (valor.includes(itemHablado) || (itemHablado === 'encendido' && valor === 'funcionalidad')) {
                        if (!cb.checked) {
                            cb.checked = true;
                            cb.dispatchEvent(new Event('change'));
                            VoiceEngine.feedback(`Verificado: ${cb.value}.`);
                        }
                    }
                });
            }
        },
        {
            // Permite decir: "desmarcar limpieza", "quitar integridad", etc.
            regex: /^(?:desmarcar|quitar|remover) (limpieza|integridad|accesorios|funcionalidad|encendido)/i,
            action: (match) => {
                const itemHablado = match[1].toLowerCase();
                const checkboxes = document.querySelectorAll('.check-item'); //[cite: 7]
                
                checkboxes.forEach(cb => {
                    const valor = cb.value.toLowerCase();
                    if (valor.includes(itemHablado) || (itemHablado === 'encendido' && valor === 'funcionalidad')) {
                        if (cb.checked) {
                            cb.checked = false;
                            cb.dispatchEvent(new Event('change'));
                            VoiceEngine.feedback(`Removido: ${cb.value}.`);
                        }
                    }
                });
            }
        },
        {
            // Acción masiva para agilizar el flujo: "marcar todo", "todo ok"
            regex: /^(?:marcar todo|todo ok|todos los checks|verificación completa)/i,
            action: () => {
                const checkboxes = document.querySelectorAll('.check-item'); //[cite: 7]
                let marcados = 0;
                checkboxes.forEach(cb => {
                    if (!cb.checked) {
                        cb.checked = true;
                        cb.dispatchEvent(new Event('change'));
                        marcados++;
                    }
                });
                VoiceEngine.feedback("Se marcaron todos los puntos de la verificación técnica.");
            }
        },

        // ==========================================
        // 3. DICTADO DE OBSERVACIONES
        // ==========================================
        {
            regex: /^(?:observaciones|observación|añadir observación|dictar observaciones) (.+)/i,
            action: (match) => {
                const textarea = document.getElementById('observaciones'); //[cite: 7]
                if (!textarea) return;

                const textoDictado = match[1].trim();
                
                if (textarea.value) {
                    textarea.value += " " + textoDictado;
                } else {
                    textarea.value = textoDictado.charAt(0).toUpperCase() + textoDictado.slice(1);
                }
                
                textarea.dispatchEvent(new Event('input'));
                VoiceEngine.feedback("Observaciones actualizadas.");
            }
        },
        {
            regex: /^(?:borrar|limpiar|vaciar) observaciones/i,
            action: () => {
                const textarea = document.getElementById('observaciones'); //[cite: 7]
                if (textarea) {
                    textarea.value = "";
                    textarea.dispatchEvent(new Event('input'));
                    VoiceEngine.feedback("Campo de observaciones limpio.");
                }
            }
        },

        // ==========================================
        // 4. ENVÍO Y CONFIRMACIÓN DEL PROTOCOLO
        // ==========================================
        {
            regex: /^(?:confirmar registro|guardar registro|enviar protocolo|confirmar)/i,
            action: () => {
                const form = document.getElementById('formForm' || 'formPrestamo'); //[cite: 7]
                const inputResp = document.getElementById('responsable'); //[cite: 7]

                if (inputResp && !inputResp.value.trim()) {
                    VoiceEngine.feedback("No se puede confirmar. Falta definir el responsable de la custodia.");
                    inputResp.focus();
                    return;
                }

                VoiceEngine.feedback("Transmitiendo datos del protocolo de movimiento.");
                if (form) {
                    form.dispatchEvent(new Event('submit')); //[cite: 7]
                }
            }
        },

        // ==========================================
        // 5. NAVEGACIÓN Y RETORNO
        // ==========================================
        {
            regex: /^(?:cancelar|volver|regresar)/i,
            action: () => {
                VoiceEngine.feedback("Cancelando operación.");
                setTimeout(() => history.back(), 1000); //[cite: 7]
            }
        }
    ];

    // Auto-registro en el núcleo del motor de voz
    if (window.VoiceEngine && typeof VoiceEngine.registerCommands === 'function') {
        VoiceEngine.registerCommands(comandosMovimiento);
    }
});
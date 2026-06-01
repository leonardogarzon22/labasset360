// js/voice-detalle-equipo.js

document.addEventListener('DOMContentLoaded', () => {

    // Función auxiliar para parsear fechas dictadas de forma natural
    function parseSpokenDate(spokenText) {
        const meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08', 
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        };
        const cleanText = spokenText.toLowerCase().replace(/ del /g, ' de ');
        const match = cleanText.match(/(\d+)\s+de\s+([a-z]+)\s+de\s+(\d+)/);
        
        if (match) {
            let dia = match[1].padStart(2, '0');
            let mes = meses[match[2]];
            let anio = match[3];
            if (mes) return `${anio}-${mes}-${dia}`;
        }
        return null;
    }

    const comandosDetalle = [
        // ==========================================
        // 1. NAVEGACIÓN BÁSICA
        // ==========================================
        {
            regex: /(ir a |volver a )?(dashboard|inicio)/i,
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
        },

        // ==========================================
        // 2. GESTIÓN GENERAL
        // ==========================================
        {
            regex: /^ubicación (.*)|^asignar ubicación (.*)/i,
            action: (match) => {
                const valor = match[1] || match[2];
                document.getElementById('ubicacion').value = valor;
                VoiceEngine.feedback(`Ubicación general actualizada a ${valor}`);
            }
        },
        {
            regex: /^responsable (.*)|^asignar responsable (.*)/i,
            action: (match) => {
                const valor = match[1] || match[2];
                document.getElementById('responsable').value = valor;
                VoiceEngine.feedback(`Responsable asignado a ${valor}`);
            }
        },
        {
            regex: /^cambiar estado a (operativo|no operativo|en revisión|en prestamo|devolución)/i,
            action: (match) => {
                const estadoHablado = match[1].toLowerCase();
                const mapEstados = {
                    'operativo': 'Operativo',
                    'no operativo': 'No operativo',
                    'en revisión': 'En revisión',
                    'en prestamo': 'En prestamo',
                    'devolución': 'Devolucion'
                };
                document.getElementById('estado').value = mapEstados[estadoHablado];
                VoiceEngine.feedback(`Estado seleccionado: ${estadoHablado}`);
            }
        },
        {
            regex: /^guardar cambios generales/i,
            action: () => {
                VoiceEngine.feedback("Guardando gestión general del activo.");
                document.getElementById('detalleForm').dispatchEvent(new Event('submit'));
            }
        },

        // ==========================================
        // 3. MANTENIMIENTOS (Modales y Acciones)
        // ==========================================
        {
            regex: /^registrar mantenimiento/i,
            action: () => {
                abrirModalMantenimiento();
                VoiceEngine.feedback("Abriendo formulario para programar mantenimiento.");
            }
        },
        {
            regex: /^fecha de mantenimiento (.*)/i,
            action: (match) => {
                const fecha = parseSpokenDate(match[1]);
                if (fecha) {
                    document.getElementById('p_m_fecha').value = fecha;
                    VoiceEngine.feedback("Fecha de mantenimiento asignada.");
                } else {
                    VoiceEngine.feedback("No entendí la fecha. Ejemplo: dos de febrero de dos mil veintiséis.");
                }
            }
        },
        {
            regex: /^técnico responsable (.*)|^tecnico responsable (.*)/i,
            action: (match) => {
                document.getElementById('p_m_tecnico').value = match[1] || match[2];
                VoiceEngine.feedback("Técnico asignado.");
            }
        },
        {
            regex: /^tipo de mantenimiento (preventivo|correctivo)/i,
            action: (match) => {
                document.getElementById('p_m_tipo').value = match[1].toLowerCase();
                VoiceEngine.feedback(`Mantenimiento configurado como ${match[1]}`);
            }
        },
        {
            regex: /^confirmar programación de mantenimiento|^guardar programación/i,
            action: () => {
                VoiceEngine.feedback("Guardando programación de mantenimiento.");
                guardarProgramacion();
            }
        },
        {
            regex: /^ejecutar (el )?mantenimiento/i,
            action: () => {
                const btnEjecutar = document.querySelector('#tabla-mantenimientos button[title="Ejecutar"]');
                if (btnEjecutar) {
                    btnEjecutar.click();
                    VoiceEngine.feedback("Abriendo ventana de ejecución de mantenimiento.");
                } else {
                    VoiceEngine.feedback("No hay mantenimientos pendientes para ejecutar.");
                }
            }
        },
        {
            regex: /^fecha de ejecución (.*)|^fecha de ejecucion (.*)/i,
            action: (match) => {
                const fecha = parseSpokenDate(match[1] || match[2]);
                if (fecha) {
                    document.getElementById('e_m_fecha_real').value = fecha;
                    VoiceEngine.feedback("Fecha de ejecución asignada.");
                }
            }
        },
        {
            regex: /^días fuera de servicio (\d+)/i,
            action: (match) => {
                document.getElementById('e_m_dias_fuera').value = match[1];
                VoiceEngine.feedback(`${match[1]} días registrados.`);
            }
        },
        {
            regex: /^cerrar mantenimiento/i,
            action: () => {
                VoiceEngine.feedback("Finalizando mantenimiento.");
                guardarEjecucion();
            }
        },

        // ==========================================
        // 4. CALIBRACIONES (Modales y Acciones)
        // ==========================================
        {
            regex: /^programar calibración|^programar calibracion/i,
            action: () => {
                abrirModalCalibracion();
                VoiceEngine.feedback("Abriendo formulario de calibración.");
            }
        },
        {
            regex: /^fecha de calibración (.*)|^fecha de calibracion (.*)/i,
            action: (match) => {
                const fecha = parseSpokenDate(match[1] || match[2]);
                if (fecha) {
                    document.getElementById('c_fecha').value = fecha;
                    VoiceEngine.feedback("Fecha de calibración asignada.");
                }
            }
        },
        {
            regex: /^proveedor (.*)/i,
            action: (match) => {
                document.getElementById('c_proveedor').value = match[1];
                VoiceEngine.feedback("Proveedor asignado.");
            }
        },
        {
            regex: /^confirmar calibración|^guardar calibracion/i,
            action: () => {
                VoiceEngine.feedback("Programando calibración.");
                guardarCalibracion();
            }
        },
        {
            regex: /^ejecutar (la )?calibración/i,
            action: () => {
                const btnFinalizar = document.querySelector('#tabla-calibraciones button[title="Finalizar"]');
                if (btnFinalizar) {
                    btnFinalizar.click();
                    VoiceEngine.feedback("Abriendo ejecución de calibración.");
                } else {
                    VoiceEngine.feedback("No hay calibraciones pendientes.");
                }
            }
        },
        {
            regex: /^resultado (aprobado|rechazado)/i,
            action: (match) => {
                const res = match[1].charAt(0).toUpperCase() + match[1].slice(1).toLowerCase();
                document.getElementById('exec_cal_resultado').value = res;
                VoiceEngine.feedback(`Resultado marcado como ${res}.`);
            }
        },
        {
            regex: /^(cerrar|cancelar) (ventana|modal)/i,
            action: () => {
                document.querySelectorAll('.modal-overlay').forEach(m => m.style.display = 'none');
                VoiceEngine.feedback("Ventana cerrada.");
            }
        },

        // ==========================================
        // 5. CONFIRMACIÓN DE APTITUD (Motor Dinámico Universal)
        // ==========================================
        {
            // Captura de forma flexible cualquier frase que inicie con el nombre del parámetro (uno o varios términos)
            // seguido de palabras clave como valor, criterio, mínimo o máximo.
            regex: /^(?:prueba |parámetro |parametro )?(.+?)\s+(valor obtenido|valor|tipo de criterio|criterio|valor mínimo|valor minimo|mínimo|minimo|valor máximo|valor maximo|máximo|maximo)\s+(.+)/i,
            action: (match) => {
                const nombrePruebaHablada = match[1].toLowerCase().trim();
                // Consolidamos el texto restante para extraer las variables sin importar el orden del dictado
                const restoTexto = (match[2] + " " + match[3]).toLowerCase().trim();

                // Expresiones regulares internas para extracción semántica aditiva
                const rxValor = /(?:valor obtenido|valor)\s+([\d\.]+)/i;
                const rxCriterio = /(?:tipo de criterio|criterio)\s+(rango|máximo|maximo|mínimo|minimo|igual a|igual)/i;
                const rxMin = /(?:valor mínimo|valor minimo|mínimo|minimo)\s+([\d\.]+)/i;
                const rxMax = /(?:valor máximo|valor maximo|máximo|maximo)\s+([\d\.]+)/i;

                const mValor = restoTexto.match(rxValor);
                const mCriterio = restoTexto.match(rxCriterio);
                const mMin = restoTexto.match(rxMin);
                const mMax = restoTexto.match(rxMax);

                const valObtenido = mValor ? mValor[1] : null;
                let criterioHablado = mCriterio ? mCriterio[1] : null;
                const valMin = mMin ? mMin[1] : null;
                const valMax = mMax ? mMax[1] : null;

                // Homologación de criterios con los values reales de tus elementos <select>
                if (criterioHablado) {
                    if (criterioHablado.includes('rango')) criterioHablado = 'rango';
                    else if (criterioHablado.includes('max') || criterioHablado.includes('máx')) criterioHablado = 'max';
                    else if (criterioHablado.includes('min') || criterioHablado.includes('mín')) criterioHablado = 'min';
                    else if (criterioHablado.includes('igual')) criterioHablado = 'igual';
                }

                let encontrado = false;
                // Escaneo directo del DOM real del usuario utilizando la clase contenedora '.field'
                const items = document.querySelectorAll('#lista-parametros .field');

                items.forEach(item => {
                    const labelB = item.querySelector('label b');
                    if (labelB && labelB.innerText.toLowerCase().includes(nombrePruebaHablada)) {
                        encontrado = true;

                        // Localizamos el input de valor para aislar el ID dinámico numérico de la prueba actual
                        const inputValorBase = item.querySelector('input[id^="valor_"]');
                        if (!inputValorBase) return;
                        const idPrueba = inputValorBase.id.replace('valor_', '');

                        // Llenado dinámico y condicional de campos mapeando tu estructura de IDs reales
                        if (valObtenido !== null) {
                            inputValorBase.value = valObtenido;
                        }
                        if (criterioHablado !== null) {
                            const selCriterio = document.getElementById(`tipo_${idPrueba}`);
                            if (selCriterio) selCriterio.value = criterioHablado;
                        }
                        if (valMin !== null) {
                            const inputMin = document.getElementById(`min_${idPrueba}`);
                            if (inputMin) inputMin.value = valMin;
                        }
                        if (valMax !== null) {
                            const inputMax = document.getElementById(`max_${idPrueba}`);
                            if (inputMax) inputMax.value = valMax;
                        }

                        // Ejecución inmediata de tu lógica de cálculo nativa para recalcular el cumplimiento visual
                        if (typeof evaluarManual === 'function') {
                            evaluarManual(idPrueba);
                        }

                        VoiceEngine.feedback(`Parámetro ${labelB.innerText} actualizado.`);
                    }
                });

                if (!encontrado) {
                    VoiceEngine.feedback(`No encontré la prueba ${nombrePruebaHablada} en la lista.`);
                }
            }
        },
        {
            regex: /^guardar confirmación|^guardar confirmacion/i,
            action: () => {
                VoiceEngine.feedback("Evaluando y guardando aptitud del equipo.");
                guardarAptitud();
            }
        },
        {
            regex: /^editar (resultados|confirmación)/i,
            action: () => {
                activarEdicion();
                VoiceEngine.feedback("Modo edición de aptitud activado.");
            }
        },

        // ==========================================
        // 6. ETIQUETA QR
        // ==========================================
        {
            regex: /^generar etiqueta( qr)?/i,
            action: () => {
                VoiceEngine.feedback("Generando etiqueta inteligente para este activo.");
                generarEtiquetaQR();
            }
        }
    ];

    VoiceEngine.registerCommands(comandosDetalle);
});
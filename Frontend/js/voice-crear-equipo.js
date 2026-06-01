// js/voice-crear-equipo.js

document.addEventListener('DOMContentLoaded', () => {

    // Función auxiliar para parsear fechas dictadas de forma natural (Ej: "15 de junio de 2026")
    function parseSpokenDate(spokenText) {
        const meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08', 
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        };
        
        const cleanText = spokenText.toLowerCase().replace(/ del /g, ' de ');
        // Regex para capturar [dia] de [mes] de [año]
        const match = cleanText.match(/(\d+)\s+de\s+([a-z]+)\s+de\s+(\d+)/);
        
        if (match) {
            let dia = match[1].padStart(2, '0');
            let mes = meses[match[2]];
            let anio = match[3];
            if (mes) return `${anio}-${mes}-${dia}`;
        }
        return null;
    }

    const comandosCrearEquipo = [
        // 1. Campo: Código
        {
            regex: /^código (.*)|^codigo (.*)/i,
            action: (match) => {
                const valor = match[1] || match[2];
                // Quitar espacios por si dicta letras separadas (Ej: "L A B 1")
                const codigoLimpio = valor.replace(/\s/g, '').toUpperCase();
                document.getElementById('codigo').value = codigoLimpio;
                VoiceEngine.feedback(`Código asignado: ${codigoLimpio}`);
            }
        },
        // 2. Campo: Marca
        {
            regex: /^marca (.*)/i,
            action: (match) => {
                document.getElementById('marca').value = match[1];
                VoiceEngine.feedback(`Marca asignada: ${match[1]}`);
            }
        },
        // 3. Campo: Modelo
        {
            regex: /^modelo (.*)/i,
            action: (match) => {
                document.getElementById('modelo').value = match[1];
                VoiceEngine.feedback(`Modelo asignado: ${match[1]}`);
            }
        },
        // 4. Campo: Serial
        {
            regex: /^serial (.*)/i,
            action: (match) => {
                const serialLimpio = match[1].replace(/\s/g, '').toUpperCase();
                document.getElementById('serial').value = serialLinter;
                document.getElementById('serial').value = serialLimpio;
                VoiceEngine.feedback(`Serial asignado: ${serialLimpio}`);
            }
        },
        // 5. Campo: Ubicación
        {
            regex: /^ubicación (.*)|^ubicacion (.*)/i,
            action: (match) => {
                const valor = match[1] || match[2];
                document.getElementById('ubicacion').value = valor;
                VoiceEngine.feedback(`Ubicación asignada: ${valor}`);
            }
        },
        // 6. Campo Selector: Nivel de Uso (bajo, medio, alto)
        {
            regex: /^nivel de uso (bajo|medio|alto)/i,
            action: (match) => {
                const nivel = match[1].toLowerCase();
                document.getElementById('uso').value = nivel;
                VoiceEngine.feedback(`Nivel de uso configurado en ${nivel}`);
            }
        },
        // 7. Campo Selector Dinámico: Tipo de Equipo (Busca coincidencia de texto en las opciones de la API)
        {
            regex: /^tipo de equipo (.*)|^tipo (.*)/i,
            action: (match) => {
                const busqueda = (match[1] || match[2]).toLowerCase().trim();
                const selectTipo = document.getElementById('tipo');
                let encontrado = false;

                for (let option of selectTipo.options) {
                    if (option.text.toLowerCase().includes(busqueda)) {
                        selectTipo.value = option.value;
                        encontrado = true;
                        VoiceEngine.feedback(`Tipo de equipo seleccionado: ${option.text.split('-')[0]}`);
                        break;
                    }
                }
                if (!encontrado) {
                    VoiceEngine.feedback(`No encontré ningún tipo de equipo que coincida con ${busqueda}`);
                }
            }
        },
        // 8. Campo: Fecha de Inicio de Operación
        {
            regex: /^fecha de inicio (.*)|^fecha (.*)/i,
            action: (match) => {
                const textoFecha = match[1] || match[2];
                const fechaFormateada = parseSpokenDate(textoFecha);
                
                if (fechaFormateada) {
                    document.getElementById('fecha_inicio_operacion').value = fechaFormateada;
                    VoiceEngine.feedback(`Fecha establecida correctamente.`);
                } else {
                    VoiceEngine.feedback("No entendí la fecha. Intenta diciendo por ejemplo: veintidós de mayo de dos mil veintiséis");
                }
            }
        },
        // 9. Checkboxes de Auditoría e Inspección
        {
            regex: /^(marcar|desmarcar) estado físico|^(marcar|desmarcar) estado fisico/i,
            action: (match) => {
                const accion = (match[1] || match[2]).toLowerCase();
                document.getElementById('check_fisico').checked = (accion === 'marcar');
                VoiceEngine.feedback(`Estado físico ${accion === 'marcar' ? 'conforme' : 'removido'}`);
            }
        },
        {
            regex: /^(marcar|desmarcar) eléctrico|^(marcar|desmarcar) electrico/i,
            action: (match) => {
                const accion = (match[1] || match[2]).toLowerCase();
                document.getElementById('check_electrico').checked = (accion === 'marcar');
                VoiceEngine.feedback(`Estado eléctrico ${accion === 'marcar' ? 'conforme' : 'removido'}`);
            }
        },
        {
            regex: /^(marcar|desmarcar) funcional/i,
            action: (match) => {
                const accion = match[1].toLowerCase();
                document.getElementById('check_funcional').checked = (accion === 'marcar');
                VoiceEngine.feedback(`Funcionamiento ${accion === 'marcar' ? 'conforme' : 'removido'}`);
            }
        },
        // 10. Campo: Observaciones de Recepción
        {
            regex: /^observaciones (.*)|^notas (.*)/i,
            action: (match) => {
                const observacion = match[1] || match[2];
                document.getElementById('observaciones').value = observacion;
                VoiceEngine.feedback("Observaciones agregadas a la auditoría.");
            }
        },
        // 11. Acción: Enviar Formulario (Registrar)
        {
            regex: /^(registrar|guardar) equipo/i,
            action: () => {
                const form = document.getElementById('equipoForm');
                // Validar campos obligatorios nativos antes de enviar
                if (form.checkValidity()) {
                    VoiceEngine.feedback("Procesando registro del nuevo activo.");
                    form.dispatchEvent(new Event('submit'));
                } else {
                    VoiceEngine.feedback("Faltan campos obligatorios por llenar. Por favor verifica el código o tipo de equipo.");
                }
            }
        }
    ];

    // Inyectamos los comandos en Siena
    VoiceEngine.registerCommands(comandosCrearEquipo);
});
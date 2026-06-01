// js/voice-historico.js

document.addEventListener('DOMContentLoaded', () => {

    // Función crucial: Traduce el español natural a códigos técnicos (Ej: "CG guion cero dos" -> "CG-02")
    function normalizarCodigo(hablado) {
        let texto = hablado.toLowerCase();
        
        // Reemplazar palabras por símbolos
        texto = texto.replace(/guion|guión|raya|línea/g, '-');
        
        // Reemplazar palabras de números básicos a dígitos
        const numeros = {
            'cero': '0', 'uno': '1', 'dos': '2', 'tres': '3', 'cuatro': '4',
            'cinco': '5', 'seis': '6', 'siete': '7', 'ocho': '8', 'nueve': '9'
        };
        
        for (let num in numeros) {
            let regex = new RegExp('\\b' + num + '\\b', 'g');
            texto = texto.replace(regex, numeros[num]);
        }
        
        // Eliminar todos los espacios y pasar a mayúsculas (Ej: "c g - 0 2" -> "CG-02")
        return texto.replace(/\s+/g, '').toUpperCase();
    }

    const comandosHistorico = [
        // 1. NAVEGACIÓN GLOBAL
        {
            regex: /(ir a |abrir |volver a |ver )?(dashboard|inicio|panel)/i,
            action: () => {
                VoiceEngine.feedback("Regresando al panel principal.");
                setTimeout(() => window.location.href = 'dashboard.html', 1000);
            }
        },
        {
            regex: /(ir a |abrir |nuevo )?(crear equipo|equipo nuevo)/i,
            action: () => {
                VoiceEngine.feedback("Redireccionando a creación de equipo.");
                setTimeout(() => window.location.href = 'crear-equipo.html', 1000);
            }
        },
        {
            regex: /(ir a |abrir |ver )?(reporte|reportes)/i,
            action: () => {
                VoiceEngine.feedback("Abriendo la sección de reportes.");
                setTimeout(() => window.location.href = 'reporte.html', 1000);
            }
        },

        // 2. BUSCAR Y ABRIR EQUIPO POR CÓDIGO
        // Escucha frases como: "abrir CG guion cero dos", "buscar LAB raya 1", "equipo A 0 5"
        {
            regex: /^(abrir|ver|buscar|equipo)\s+(.*)/i,
            action: (match) => {
                const codigoHablado = match[2];
                
                // Exclusión de seguridad para que no confunda los comandos de navegación con un código
                if (['dashboard', 'inicio', 'reporte', 'reportes', 'historial', 'crear equipo'].includes(codigoHablado.toLowerCase())) {
                    return; 
                }

                const codigoLimpio = normalizarCodigo(codigoHablado);
                console.log("Siena interpretó el código hablado como:", codigoLimpio);

                // Verificamos en el array global 'todosLosEquipos' de tu historico.html
                if (typeof todosLosEquipos !== 'undefined' && todosLosEquipos.length > 0) {
                    
                    // Buscamos coincidencia exacta del código
                    const equipoEncontrado = todosLosEquipos.find(eq => eq.codigo.toUpperCase() === codigoLimpio);

                    if (equipoEncontrado) {
                        VoiceEngine.feedback(`Abriendo la ficha técnica del equipo ${codigoLimpio}`);
                        // Llamamos a la función que ya tienes programada en tu HTML
                        setTimeout(() => irADetalle(equipoEncontrado.id), 1500);
                    } else {
                        // Feedback en caso de no existir
                        VoiceEngine.feedback(`No encontré ningún equipo registrado con el código ${codigoLimpio}.`);
                    }
                } else {
                    VoiceEngine.feedback("La base de datos aún se está cargando, por favor intenta en un segundo.");
                }
            }
        }
    ];

    // Registramos los comandos en el core de Siena
    VoiceEngine.registerCommands(comandosHistorico);
});
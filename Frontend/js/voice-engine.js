// js/voice-engine.js

// Forzamos explícitamente a que pertenezca a window
window.VoiceEngine = (function () {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;
    let isListening = false;
    let isSienaAwake = localStorage.getItem('siena_estado') === 'despierta';
    let registeredCommands = [];
    let isSienaSpeaking = false; // <-- Control central: Bandera para saber si Siena está hablando

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.lang = 'es-CO';
        recognition.interimResults = false;
    } else {
        console.warn("La Web Speech API no es compatible.");
    }

    function speak(text) {
        if (!text) return;

        const synth = window.speechSynthesis;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'es-CO';
        utterance.rate = 1.0;

        // 1. CUANDO SIENA EMPIEZA A HABLAR
        utterance.onstart = () => {
            isSienaSpeaking = true;
            if (recognition && isListening) {
                try {
                    // .abort() detiene la escucha inmediatamente y vacía el búfer actual
                    // para que no guarde fragmentos residuales de lo que escuchó a medias.
                    recognition.abort();
                } catch (e) { }
            }
        };

        // 2. CUANDO SIENA TERMINA DE HABLAR
        utterance.onend = () => {
            // Añadimos un pequeño retraso de 400ms antes de encender el micro.
            // Esto evita que el micrófono capture el "eco" final que rebota en la habitación.
            setTimeout(() => {
                isSienaSpeaking = false;
                startPhysicalListening();
            }, 400);
        };

        // Seguro de vida en caso de que la síntesis de voz falle o se cancele
        utterance.onerror = () => {
            isSienaSpeaking = false;
            startPhysicalListening();
        };

        synth.speak(utterance);
    }

    function updateUI() {
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            if (isSienaAwake) {
                indicator.classList.add('active');
                indicator.style.background = '#e74c3c'; // Rojo (Despierta)
            } else {
                indicator.classList.remove('active');
                indicator.style.background = '#243B8F'; // Azul (Dormida)
            }
        }
    }

    function crearDepuradorPantalla() {
        if (document.getElementById('siena-debug-overlay')) return;
        const debugDiv = document.createElement('div');
        debugDiv.id = 'siena-debug-overlay';
        debugDiv.style.position = 'fixed';
        debugDiv.style.bottom = '15px';
        debugDiv.style.left = '50%';
        debugDiv.style.transform = 'translateX(-50%)';
        debugDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.85)';
        debugDiv.style.color = '#fff';
        debugDiv.style.padding = '10px 15px';
        debugDiv.style.borderRadius = '15px';
        debugDiv.style.fontSize = '13px';
        debugDiv.style.zIndex = '99999';
        debugDiv.style.fontFamily = 'sans-serif';
        debugDiv.style.textAlign = 'center';
        debugDiv.style.minWidth = '250px';
        debugDiv.innerHTML = `Siena: Esperando voz... <br><span style="color:#2ecc71; font-size:11px;">${registeredCommands.length} comandos listos</span>`;
        document.body.appendChild(debugDiv);
    }

    function actualizarDepurador(texto) {
        const debugDiv = document.getElementById('siena-debug-overlay');
        if (debugDiv) {
            debugDiv.innerHTML = `Siena escuchó: <b style="color:#f1c40f;">"${texto}"</b><br><span style="color:#aaa; font-size:11px;">${registeredCommands.length} comandos activos</span>`;
        }
    }

    function actualizarConteoInicial() {
        const debugDiv = document.getElementById('siena-debug-overlay');
        if (debugDiv) {
            debugDiv.innerHTML = `Siena: Esperando voz... <br><span style="color:#2ecc71; font-size:11px;">${registeredCommands.length} comandos listos</span>`;
        }
    }

    function normalizarTextoTecnico(texto) {
        let t = texto.toLowerCase().trim();

        // 1. Traducir palabras de puntuación dictadas a sus símbolos reales
        t = t.replace(/\bpunto\b/g, '.');
        t = t.replace(/\bguion\b|\bguión\b/g, '-');
        t = t.replace(/\bslash\b|\bbarra\b/g, '/');

        // 2. Corregir homófonos críticos de laboratorio (Si dices "CE", el celular suele escribir "se" o "sé")
        t = t.replace(/\bse\b|\bsé\b/g, 'ce');
        t = t.replace(/\bise\b/g, 'icp'); // Parche por si junta fonéticamente "ICP"

        // 3. Traducir números hablados comunes a dígitos individuales
        const mapaNumeros = {
            'cero': '0', 'uno': '1', 'dos': '2', 'tres': '3', 'cuatro': '4',
            'cinco': '5', 'seis': '6', 'siete': '7', 'ocho': '8', 'nueve': '9'
        };
        for (const [palabra, digito] of Object.entries(mapaNumeros)) {
            t = t.replace(new RegExp(`\\b${palabra}\\b`, 'g'), digito);
        }

        // 4. Eliminar espacios rebeldes alrededor de los símbolos para compactar el código
        // Ejemplo: "l . ce - icp - 01"  =>  "l.ce-icp-01"
        t = t.replace(/\s*([\.\-\/])\s*/g, '$1');

        // 5. Unir letras sueltas si el usuario las deletreó despacio (Ej: "i c p" => "icp")
        t = t.replace(/\b([a-z])\s+(?=[a-z]\b)/g, '$1');

        return t;
    }

    // =========================================================================
    // FUNCIÓN PROCESADORA ACTUALIZADA
    // =========================================================================
    function processTranscript(transcript) {
        if (isSienaSpeaking) return;

        // 1. Guardamos el texto original para comandos nativos de inicio/apagado
        const lowerTranscript = transcript.toLowerCase().trim();

        // 2. Pasamos el texto por el filtro técnico para los comandos de las pantallas
        const textoNormalizado = normalizarTextoTecnico(transcript);

        // Mostramos el código ya formateado en el recuadro negro para que valides qué entendió
        actualizarDepurador(textoNormalizado);

        // Control de encendido (Evaluamos con el texto original o normalizado)
        if (lowerTranscript.includes('siena iníciate') || lowerTranscript.includes('siena iniciate')) {
            if (!isSienaAwake) {
                isSienaAwake = true;
                localStorage.setItem('siena_estado', 'despierta');
                speak("Hola, soy Siena. Sistemas en línea.");
                updateUI();
            }
            return;
        }

        if (lowerTranscript.includes('hasta luego siena') || lowerTranscript.includes('adiós siena') || lowerTranscript.includes('adios siena')) {
            if (isSienaAwake) {
                isSienaAwake = false;
                localStorage.setItem('siena_estado', 'dormida');
                speak("Sistemas de voz en reposo.");
                updateUI();
            }
            return;
        }

        if (!isSienaAwake) return;

        // Limpieza de activadores usando la cadena ya normalizada y compactada
        let cleanTranscript = textoNormalizado
            .replace(/^(siena|por favor|oye siena|escucha siena)[,\s]*/, '')
            .trim();

        // Buscar coincidencia en los comandos registrados de la página
        for (let cmd of registeredCommands) {
            const match = cleanTranscript.match(cmd.regex);
            if (match) {
                cmd.action(match);
                return;
            }
        }
    }

    function startPhysicalListening() {
        // Si Siena está hablando, impedimos por completo reabrir el micrófono
        if (isSienaSpeaking) return;

        if (recognition && !isListening) {
            try {
                recognition.start();
                isListening = true;
                updateUI();
            } catch (e) { }
        }
    }

    if (recognition) {
        recognition.onresult = (event) => {
            if (isSienaSpeaking) return; // Doble filtro de protección

            const current = event.resultIndex;
            const transcript = event.results[current][0].transcript;
            processTranscript(transcript);
        };

        recognition.onend = () => {
            isListening = false;
            // El bucle de auto-arranque solo se ejecuta si Siena NO causó el cierre al hablar
            if (!isSienaSpeaking) {
                startPhysicalListening();
            }
        };
    }

    window.addEventListener('load', () => {
        crearDepuradorPantalla();
        startPhysicalListening();
        updateUI();
    });

    return {
        toggle: function () {
            isSienaAwake = !isSienaAwake;
            localStorage.setItem('siena_estado', isSienaAwake ? 'despierta' : 'dormida');
            speak(isSienaAwake ? "Siena activada." : "Siena desactivada.");
            updateUI();
        },
        registerCommands: function (commandsArray) {
            registeredCommands = registeredCommands.concat(commandsArray);
            actualizarConteoInicial();
        },
        feedback: speak
    };
})();
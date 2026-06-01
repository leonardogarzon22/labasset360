// js/voice-engine.js

const VoiceEngine = (function() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;
    let isListening = false; // Estado del micrófono físico
    
    // Leemos la memoria para saber si Siena viene despierta de la página anterior
    let isSienaAwake = localStorage.getItem('siena_estado') === 'despierta'; 
    let registeredCommands = []; 
    
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.lang = 'es-CO';
        recognition.interimResults = false;
    } else {
        console.warn("La Web Speech API no es compatible con este navegador.");
    }

    function speak(text) {
        const synth = window.speechSynthesis;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'es-CO';
        utterance.rate = 1.0; // Velocidad normal
        synth.speak(utterance);
    }

    function updateUI() {
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            if (isSienaAwake) {
                indicator.classList.add('active');
                indicator.style.background = '#e74c3c'; // Rojo (Despierta y escuchando comandos)
            } else {
                indicator.classList.remove('active');
                indicator.style.background = '#243B8F'; // Azul (Dormida, solo esperando su nombre)
            }
        }
    }

    function processTranscript(transcript) {
        const lowerTranscript = transcript.toLowerCase().trim();
        console.log("Voz detectada:", lowerTranscript);

        // 1. COMANDOS GLOBALES DE ACTIVACIÓN (Se escuchan siempre)
        if (lowerTranscript.includes('siena iníciate') || lowerTranscript.includes('siena iniciate')) {
            if (!isSienaAwake) {
                isSienaAwake = true;
                localStorage.setItem('siena_estado', 'despierta');
                speak("Hola, soy Siena. Sistemas en línea y lista para ayudarte.");
                updateUI();
            }
            return;
        }

        if (lowerTranscript.includes('hasta luego siena') || lowerTranscript.includes('adiós siena') || lowerTranscript.includes('adios siena')) {
            if (isSienaAwake) {
                isSienaAwake = false;
                localStorage.setItem('siena_estado', 'dormida');
                speak("Hasta luego. Sistemas de voz en reposo.");
                updateUI();
            }
            return;
        }

        // 2. FILTRO DE ESTADO
        // Si Siena está dormida, ignoramos cualquier otra cosa que se hable en el laboratorio
        if (!isSienaAwake) return;

        // 3. PROCESAMIENTO DE COMANDOS DE PANTALLA
        for (let cmd of registeredCommands) {
            const match = lowerTranscript.match(cmd.regex);
            if (match) {
                cmd.action(match);
                return; 
            }
        }
    }

    function startPhysicalListening() {
        if (recognition && !isListening) {
            try {
                recognition.start();
                isListening = true;
                updateUI();
            } catch (e) {
                console.error("Error iniciando micrófono:", e);
            }
        }
    }

    if (recognition) {
        recognition.onresult = (event) => {
            const current = event.resultIndex;
            const transcript = event.results[current][0].transcript;
            processTranscript(transcript);
        };

        recognition.onend = () => {
            isListening = false;
            // Bucle infinito: si el microfono se apaga (por silencio o cambio de página), lo forzamos a reiniciar
            startPhysicalListening();
        };
    }

    // Auto-arranque al cargar cualquier página
    window.addEventListener('load', () => {
        startPhysicalListening();
        updateUI();
    });

    return {
        // Mantenemos el toggle manual por si el navegador bloquea el micrófono inicialmente
        toggle: function() {
            if (isSienaAwake) {
                isSienaAwake = false;
                localStorage.setItem('siena_estado', 'dormida');
                speak("Siena desactivada manualmente.");
            } else {
                isSienaAwake = true;
                localStorage.setItem('siena_estado', 'despierta');
                speak("Siena activada manualmente.");
                startPhysicalListening();
            }
            updateUI();
        },
        registerCommands: function(commandsArray) {
            registeredCommands = registeredCommands.concat(commandsArray);
        },
        feedback: speak
    };
})();
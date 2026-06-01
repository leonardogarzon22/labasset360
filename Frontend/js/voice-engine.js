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
        // interimResults en false ayuda a procesar solo cuando la frase esté consolidada
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

    // Crea un panel flotante en el celular para ver qué está escuchando en tiempo real
    function crearDepuradorPantalla() {
        if (document.getElementById('siena-debug-overlay')) return;
        const debugDiv = document.createElement('div');
        debugDiv.id = 'siena-debug-overlay';
        debugDiv.style.position = 'fixed';
        debugDiv.style.bottom = '10px';
        debugDiv.style.left = '50%';
        debugDiv.style.transform = 'translateX(-50%)';
        debugDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        debugDiv.style.color = '#fff';
        debugDiv.style.padding = '8px 15px';
        debugDiv.style.borderRadius = '20px';
        debugDiv.style.fontSize = '12px';
        debugDiv.style.zIndex = '99999';
        debugDiv.style.fontFamily = 'sans-serif';
        debugDiv.style.pointerEvents = 'none';
        debugDiv.style.textAlign = 'center';
        debugDiv.style.minWidth = '200px';
        debugDiv.innerText = 'Siena: Esperando voz...';
        document.body.appendChild(debugDiv);
    }

    function actualizarDepurador(texto) {
        const debugDiv = document.getElementById('siena-debug-overlay');
        if (debugDiv) {
            debugDiv.innerText = `Siena escuchó: "${texto}"`;
            debugDiv.style.border = "1px solid #2ecc71";
            setTimeout(() => { debugDiv.style.border = "none"; }, 1000);
        }
    }

    function processTranscript(transcript) {
        const lowerTranscript = transcript.toLowerCase().trim();
        console.log("Voz detectada:", lowerTranscript);
        
        // Actualiza el texto en la pantalla del celular
        actualizarDepurador(lowerTranscript);

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
        if (!isSienaAwake) return;

        // =========================================================================
        // MEJORA DE SENSIBILIDAD: Limpieza del texto para compatibilidad con Regex ^
        // =========================================================================
        // Si el usuario dijo "Siena, reportar falla" o "Por favor reportar falla", 
        // eliminamos el prefijo para dejar solo "reportar falla" y que el regex funcione.
        let cleanTranscript = lowerTranscript
            .replace(/^(siena|por favor|oye siena|escucha siena)[,\s]*/, '')
            .trim();

        // 3. PROCESAMIENTO DE COMANDOS DE PANTALLA
        for (let cmd of registeredCommands) {
            const match = cleanTranscript.match(cmd.regex);
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
            // Bucle infinito corregido para móviles: si se corta, vuelve a enganchar de inmediato
            startPhysicalListening();
        };
    }

    // Auto-arranque al cargar cualquier página
    window.addEventListener('load', () => {
        crearDepuradorPantalla();
        startPhysicalListening();
        updateUI();
    });

    return {
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
// js/voice-engine.js

// Forzamos explícitamente a que pertenezca a window
window.VoiceEngine = (function() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;
    let isListening = false;
    let isSienaAwake = localStorage.getItem('siena_estado') === 'despierta'; 
    let registeredCommands = []; 
    
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.lang = 'es-CO';
        recognition.interimResults = false;
    } else {
        console.warn("La Web Speech API no es compatible.");
    }

    function speak(text) {
        const synth = window.speechSynthesis;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'es-CO';
        utterance.rate = 1.0;
        synth.speak(utterance);
    }

    function updateUI() {
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            if (isSienaAwake) {
                indicator.style.background = '#e74c3c'; // Rojo (Despierta)
            } else {
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

    function processTranscript(transcript) {
        const lowerTranscript = transcript.toLowerCase().trim();
        actualizarDepurador(lowerTranscript);

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

        // Limpieza de activadores
        let cleanTranscript = lowerTranscript
            .replace(/^(siena|por favor|oye siena|escucha siena)[,\s]*/, '')
            .trim();

        // Buscar comando
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
            } catch (e) {}
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
            startPhysicalListening();
        };
    }

    window.addEventListener('load', () => {
        crearDepuradorPantalla();
        startPhysicalListening();
        updateUI();
    });

    return {
        toggle: function() {
            isSienaAwake = !isSienaAwake;
            localStorage.setItem('siena_estado', isSienaAwake ? 'despierta' : 'dormida');
            speak(isSienaAwake ? "Siena activada." : "Siena desactivada.");
            updateUI();
        },
        registerCommands: function(commandsArray) {
            registeredCommands = registeredCommands.concat(commandsArray);
            // Actualiza el texto en el celular apenas se registren comandos
            actualizarConteoInicial();
        },
        feedback: speak
    };
})();
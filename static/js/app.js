let currentQuestions = [];
let currentIndex = 0;
let wrongQueue = []; // Pino johon väärin vastatut tehtävät siirretään uudelleen harjoiteltavaksi

function startLesson(lessonId) {
    let url = lessonId === 'practice' ? '/api/get_random_questions' : `/api/get_lesson_questions/${lessonId}`;
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.length === 0) {
                alert("Ei tehtäviä tässä oppitunnissa vielä!");
                return;
            }
            currentQuestions = data;
            currentIndex = 0;
            wrongQueue = [];
            document.getElementById('lesson-modal').classList.remove('hidden');
            renderQuestion();
        });
}

function renderQuestion() {
    const qArea = document.getElementById('question-area');
    qArea.innerHTML = '';
    
    let q = currentQuestions[currentIndex];
    
    let html = `<h3>${q.prompt}</h3>`;
    
    if (q.type === 'choice') {
        let options = (q.answer + ',' + q.choices).split(',').sort(() => Math.random() - 0.5);
        options.forEach(opt => {
            html += `<button class="btn" style="width:100%; margin:5px 0; background:white; color:#3c3c3c; border:2px solid #e5e5e5; box-shadow:none;" onclick="checkAnswer('${opt.trim()}', '${q.answer.trim()}')">${opt.trim()}</button>`;
        });
    } else if (q.type === 'input' || q.type === 'wordbank') {
        html += `<input type="text" id="user-input" style="width:100%; padding:12px; font-size:18px; border-radius:10px; border:2px solid #ccc; margin-bottom:15px;">`;
        html += `<button class="btn" onclick="checkAnswer(document.getElementById('user-input').value, '${q.answer.trim()}')">Tarkista</button>`;
    }
    
    qArea.innerHTML = html;
}

function checkAnswer(userAns, correctAns) {
    const feedback = document.getElementById('feedback-area');
    let q = currentQuestions[currentIndex];

    if (userAns.toLowerCase().trim() === correctAns.toLowerCase().trim()) {
        playAudio(true);
        feedback.innerHTML = `<h3 style="color:var(--duo-green);">Hienoa! Oikein menee!</h3>`;
    } else {
        playAudio(false);
        feedback.innerHTML = `<h3 style="color:var(--duo-red);">Väärin. Oikea vastaus: ${correctAns}</h3>`;
        // LISÄTÄÄN VÄÄRIN VASTATTU TEHTÄVÄ UUDELLEEN JONOON!
        wrongQueue.push(q);
    }
    
    setTimeout(() => {
        feedback.innerHTML = '';
        currentIndex++;
        
        // Jos varsinaiset tehtävät loppuivat, mutta virheitä tuli -> käydään ne läpi uudelleen!
        if (currentIndex >= currentQuestions.length) {
            if (wrongQueue.length > 0) {
                currentQuestions = [...wrongQueue];
                wrongQueue = [];
                currentIndex = 0;
                renderQuestion();
            } else {
                finishLesson();
            }
        } else {
            renderQuestion();
        }
    }, 1500);
}

function finishLesson() {
    fetch('/api/complete_lesson', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ xp: 15 })
    }).then(() => {
        alert("Oppitunti suoritettu! +15 XP");
        location.reload();
    });
}

// Synteettiset äänieffektit (Web Audio API)
function playAudio(isCorrect) {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    if (isCorrect) {
        osc.frequency.setValueAtTime(523.25, ctx.currentTime);
        osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.1);
    } else {
        osc.frequency.setValueAtTime(200, ctx.currentTime);
        osc.frequency.setValueAtTime(150, ctx.currentTime + 0.1);
    }
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
}

// --- TEEMAN VAIHTO (DARK / LIGHT MODE) ---
document.addEventListener("DOMContentLoaded", () => {
    const isDark = localStorage.getItem("theme") === "dark";
    if (isDark) {
        document.documentElement.classList.add("dark-theme");
        updateThemeIcon(true);
    }
});

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle("dark-theme");
    document.body.classList.toggle("dark-theme", isDark);
    localStorage.setItem("theme", isDark ? "dark" : "light");
    updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
    const btn = document.getElementById("theme-toggle");
    if (btn) {
        btn.textContent = isDark ? "☀" : "🌙";
    }
}
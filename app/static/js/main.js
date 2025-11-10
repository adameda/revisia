// app/static/js/main.js
document.addEventListener("DOMContentLoaded", () => {
  console.log("✨ Révis'IA front prêt !");

  // --- Upload ---
  const uploadForm = document.getElementById("uploadForm");
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(uploadForm);
      const status = document.getElementById("uploadStatus");
      status.textContent = "📤 Envoi en cours...";

      try {
        const res = await fetch("/api/documents/upload", { method: "POST", body: formData });
        const data = await res.json();

        if (res.ok) {
          status.textContent = "✅ Document importé avec succès !";
          setTimeout(() => (window.location.href = "/documents"), 1000);
        } else {
          status.textContent = "❌ " + (data.error || "Erreur d'importation.");
        }
      } catch (err) {
        status.textContent = "⚠️ Erreur réseau.";
      }
    });
  }

  // --- Delete document ---
  const deleteButtons = document.querySelectorAll("[data-delete]");
  deleteButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.delete;
      if (!confirm("Supprimer ce document ?")) return;

      try {
        const res = await fetch(`/api/documents/${id}`, { method: "DELETE" });
        const data = await res.json();

        if (res.ok) {
          btn.closest("div.bg-white, div.bg-white\\/50, div.bg-white\\/40")?.remove();
          alert("🗑️ Document supprimé !");
        } else {
          alert("❌ Erreur : " + (data.error || "Impossible de supprimer."));
        }
      } catch (err) {
        alert("⚠️ Erreur réseau ou serveur.");
      }
    });
  });

  // --- Génération de quiz ---
  const genButtons = document.querySelectorAll("[data-generate]");
  genButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const docId = btn.dataset.generate;
      btn.disabled = true;
      const oldText = btn.textContent;
      btn.textContent = "⏳ Génération...";

      try {
        const res = await fetch(`/api/quizzes/generate?document_id=${docId}`, { method: "POST" });
        const data = await res.json();

        if (res.ok) {
          alert(data.message || "✅ Quiz généré !");
        } else {
          alert("❌ " + (data.error || "Erreur pendant la génération."));
        }
      } catch (err) {
        alert("⚠️ Erreur de connexion au serveur.");
      }

      btn.textContent = oldText;
      btn.disabled = false;
    });
  });

  // --- Mode Quiz strict : une question à la fois ---
  const quizContainer = document.getElementById("quizContainer");
  if (quizContainer) {
    const questions = JSON.parse(quizContainer.dataset.questions);
    const questionBox = document.getElementById("questionBox");
    const nextBtn = document.getElementById("nextBtn");
    const resultBox = document.getElementById("result");
    const progressText = document.getElementById("progress");
    const scoreDisplay = document.getElementById("scoreDisplay");

    let current = 0;
    let score = 0;
    let answered = false;

    function renderQuestion() {
      const q = questions[current];
      answered = false;
      nextBtn.classList.add("hidden");
      progressText.textContent = `Question ${current + 1} / ${questions.length}`;

      questionBox.innerHTML = `
        <p class="font-semibold mb-4">${q.question}</p>
        ${
          q.type === "qcm" && q.choices
            ? q.choices
                .map(
                  (choice) => `
            <button class="choice-btn w-full border border-gray-300 rounded-lg py-2 my-1 hover:bg-gray-50 transition">
              ${choice}
            </button>`
                )
                .join("")
            : `<textarea id="openAnswer" rows="2" class="w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-primary" placeholder="Ta réponse..."></textarea>
              <button id="submitOpen" class="mt-3 bg-primary text-white px-4 py-2 rounded-lg shadow hover:bg-blue-600">Valider</button>`
        }
      `;

      if (q.type === "ouverte") {
        document.getElementById("submitOpen").addEventListener("click", () => {
          const answer = document.getElementById("openAnswer").value.trim();
          handleAnswer(answer);
        });
      } else {
        document.querySelectorAll(".choice-btn").forEach((btn) => {
          btn.addEventListener("click", () => handleAnswer(btn.textContent.trim(), btn));
        });
      }
    }

    function handleAnswer(answer, btn = null) {
      if (answered) return;
      answered = true;
      const q = questions[current];
      const correct = q.answer?.trim().toLowerCase();

      q.user_answer = answer;
      q.is_correct = answer.toLowerCase() === correct;

      if (q.is_correct) {
        score++;
        scoreDisplay.textContent = `Score : ${score}`;
        if (btn) btn.classList.add("bg-green-100", "border-green-500");
        showFeedback("✅ Bonne réponse !");
      } else {
        if (btn) btn.classList.add("bg-red-100", "border-red-500");
        showFeedback(`❌ Mauvaise réponse. Réponse correcte : <strong>${q.answer}</strong>`);
      }

      nextBtn.classList.remove("hidden");
    }

    function showFeedback(msg) {
      const fb = document.createElement("p");
      fb.innerHTML = msg;
      fb.className = "mt-4 text-sm text-gray-700";
      questionBox.appendChild(fb);
    }

    function handleNext() {
      current++;
      if (current < questions.length) renderQuestion();
      else showResult();
    }

    async function showResult() {
      questionBox.innerHTML = "";
      nextBtn.classList.add("hidden");
      resultBox.classList.remove("hidden");
      resultBox.innerHTML = `
        <h2 class="text-2xl font-bold mb-2">Quiz terminé</h2>
        <p class="text-lg">Score final : <strong>${score}/${questions.length}</strong></p>
      `;

      const answersData = questions.map((q) => ({
        question_id: q.id,
        user_answer: q.user_answer || "",
        is_correct: q.is_correct || false,
      }));

      try {
        const res = await fetch("/api/results/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            document_id: quizContainer.dataset.documentId || null,
            score: score,
            answers: answersData,
          }),
        });
        const data = await res.json();
        console.log("💾 Sauvegarde :", data);
      } catch (err) {
        console.error("❌ Erreur lors de la sauvegarde :", err);
      }
    }

    nextBtn.addEventListener("click", handleNext);
    renderQuestion();
  }

  // --- Visualisation des résultats (page /results) ---
  const docSelect = document.getElementById("documentSelect");
  const ctx = document.getElementById("resultsChart");
  const noDataMsg = document.getElementById("noDataMessage");

  if (docSelect && ctx) {
    let chart;

    async function fetchResults(documentId) {
      const res = await fetch(`/api/results/data?document_id=${documentId}`);
      return await res.json();
    }

    async function updateChart(documentId) {
      const data = await fetchResults(documentId);

      if (!data || data.length === 0) {
        if (chart) chart.destroy();
        noDataMsg.classList.remove("hidden");
        return;
      }

      noDataMsg.classList.add("hidden");

      const labels = data.map((d) => d.played_at);
      const scores = data.map((d) => d.score);

      if (chart) chart.destroy();

      // Gradient pastel pour la courbe
      const ctx2d = ctx.getContext("2d");
      const gradient = ctx2d.createLinearGradient(0, 0, 0, 300);
      gradient.addColorStop(0, "rgba(37,99,235,0.4)");
      gradient.addColorStop(1, "rgba(147,197,253,0.05)");

      chart = new Chart(ctx, {
        type: "line",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Note",
              data: data.map(d => d.score),
              borderColor: "#2563eb",
              backgroundColor: "rgba(37,99,235,0.15)",
              fill: true,
              tension: 0.35,
              pointRadius: 5,
              pointHoverRadius: 7,
              pointBackgroundColor: "#2563eb",
              pointBorderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              max: 10,
              ticks: {
                stepSize: 1,
                color: "#4b5563",
                font: { family: "Inter, sans-serif", size: 12, weight: 500 },
              },
              grid: { color: "rgba(0,0,0,0.05)" },
            },
            x: {
              ticks: {
                color: "#6b7280",
                font: { family: "Inter, sans-serif", size: 12 },
              },
              grid: { display: false },
            },
          },
          plugins: {
            legend: { display: false },
            title: { display: false },
            tooltip: {
              backgroundColor: "rgba(37,99,235,0.9)",
              titleColor: "#fff",
              bodyColor: "#fff",
              cornerRadius: 6,
              padding: 10,
              displayColors: false,
            },
          },
          elements: {
            line: { borderWidth: 3 },
          },
          animation: {
            duration: 700,
            easing: "easeOutCubic",
          },
        },
      });
    }

    // Initialisation
    if (docSelect.value) updateChart(docSelect.value);

    // Mise à jour dynamique
    docSelect.addEventListener("change", (e) => {
      updateChart(e.target.value);
    });
  }
});

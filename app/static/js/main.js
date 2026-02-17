// app/static/js/main.js
document.addEventListener("DOMContentLoaded", () => {
  console.log("✨ Révis'IA front prêt !");

  // === Token CSRF ===
  // On le lit depuis la balise <meta> dans base.html.
  // Il sera envoyé dans le header de chaque requête POST/PUT/DELETE
  // pour prouver que la requête vient bien de notre site.
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

  // Helper : construit les headers avec le token CSRF inclus
  function csrfHeaders(extra = {}) {
    return { "X-CSRFToken": csrfToken, ...extra };
  }

  // === Menu burger mobile ===
  const burgerBtn = document.getElementById("burgerBtn");
  const mobileMenu = document.getElementById("mobileMenu");
  const burgerIcon = document.getElementById("burgerIcon");
  const closeIcon = document.getElementById("closeIcon");

  if (burgerBtn && mobileMenu) {
    burgerBtn.addEventListener("click", () => {
      const isOpen = !mobileMenu.classList.contains("hidden");
      mobileMenu.classList.toggle("hidden");
      burgerIcon.classList.toggle("hidden");
      closeIcon.classList.toggle("hidden");
    });
  }

  // === Système de modal unifié ===
  const unifiedModal = document.getElementById("unified-modal");
  const unifiedModalTitle = document.getElementById("unified-modal-title");
  const unifiedModalMessage = document.getElementById("unified-modal-message");
  const unifiedModalActions = document.getElementById("unified-modal-actions");
  const unifiedModalIcon = document.getElementById("unified-modal-icon");

  // Helper pour afficher une modal
  window.showModal = function(options) {
    const {
      type = "info", // warning, error, info, success
      title = "",
      message = "",
      confirmText = "OK",
      cancelText = null,
      confirmClass = "btn-blue",
      onConfirm = null,
      onCancel = null
    } = options;

    // Définir l'icône selon le type
    const icons = {
      warning: '<svg class="w-8 h-8 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>',
      error: '<svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
      info: '<svg class="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
      success: '<svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
    };

    // Mettre à jour le contenu
    unifiedModalIcon.innerHTML = icons[type] || icons.info;
    unifiedModalTitle.textContent = title;
    unifiedModalMessage.textContent = message;

    // Créer les boutons
    unifiedModalActions.innerHTML = "";
    
    if (cancelText) {
      const cancelBtn = document.createElement("button");
      cancelBtn.textContent = cancelText;
      cancelBtn.className = "btn btn-gray";
      cancelBtn.onclick = () => {
        closeUnifiedModal();
        if (onCancel) onCancel();
      };
      unifiedModalActions.appendChild(cancelBtn);
    }

    const confirmBtn = document.createElement("button");
    confirmBtn.textContent = confirmText;
    confirmBtn.className = `btn ${confirmClass}`;
    confirmBtn.onclick = () => {
      closeUnifiedModal();
      if (onConfirm) onConfirm();
    };
    unifiedModalActions.appendChild(confirmBtn);

    // Afficher la modal
    unifiedModal.classList.remove("hidden");
    unifiedModal.classList.add("flex");
    document.body.style.overflow = "hidden";
  };

  // Helper pour fermer la modal
  function closeUnifiedModal() {
    unifiedModal.classList.add("hidden");
    unifiedModal.classList.remove("flex");
    document.body.style.overflow = "";
  }

  // Fermer avec Echap
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !unifiedModal.classList.contains("hidden")) {
      closeUnifiedModal();
    }
  });

  // Fermer en cliquant sur le backdrop
  unifiedModal.addEventListener("click", (e) => {
    if (e.target === unifiedModal) {
      closeUnifiedModal();
    }
  });

  // === Fonctions helper pour mise à jour dynamique ===
  
  // Mettre à jour le compteur d'une matière
  function updateSubjectCount(subjectId, delta) {
    // Cibler l'élément avec data-subject-id (peut être <a> pour "Tous" ou <div> pour les matières)
    // Exclure les boutons de suppression qui ont aussi ce data-attribute
    const pill = document.querySelector(`[data-subject-id="${subjectId}"]:not(button)`);
    if (pill) {
      const countElement = pill.querySelector('.count');
      if (countElement) {
        const currentCount = parseInt(countElement.textContent);
        const newCount = Math.max(0, currentCount + delta);
        countElement.textContent = newCount;
      }
    }
    
    // Mettre à jour TOUS les boutons de suppression avec ce subject_id
    // (important car le bouton peut être en dehors de la pill trouvée ci-dessus)
    const deleteButtons = document.querySelectorAll(`.delete-subject-btn[data-subject-id="${subjectId}"]`);
    deleteButtons.forEach(deleteBtn => {
      deleteBtn.dataset.subjectDocs = Math.max(0, parseInt(deleteBtn.dataset.subjectDocs || 0) + delta);
    });
    
    // Mettre à jour aussi le titre de la section (seulement si ce subjectId correspond au filtre actuel)
    const sectionTitle = document.querySelector('h2.text-2xl');
    if (sectionTitle) {
      // Déterminer le filtre actuel de la page
      const currentUrl = new URL(window.location.href);
      const currentFilter = currentUrl.searchParams.get('subject') || 'all';
      
      // Mettre à jour le titre seulement si on est sur la page correspondante
      if (subjectId === currentFilter) {
        const titleText = sectionTitle.textContent;
        const match = titleText.match(/\((\d+)\)/);
        if (match) {
          const currentCount = parseInt(match[1]);
          const newCount = Math.max(0, currentCount + delta);
          
          // Préserver la pastille colorée si elle existe
          const colorSpan = sectionTitle.querySelector('span.inline-block');
          if (colorSpan) {
            // Extraire le nom de la matière (tout sauf le compteur)
            const nameOnly = titleText.replace(/\s*\(\d+\)\s*$/, '').trim();
            // Reconstruire le HTML en préservant le span
            sectionTitle.innerHTML = colorSpan.outerHTML + ' ' + nameOnly + ` (${newCount})`;
          } else {
            // Pas de pastille, juste remplacer le texte
            const newTitleText = titleText.replace(/\(\d+\)/, `(${newCount})`);
            sectionTitle.textContent = newTitleText;
          }
        }
      }
    }
  }

  // Afficher le message "Aucun cours"
  function showEmptyMessage(subjectId, subjectName) {
    const container = document.getElementById('documents-container');
    if (!container) return;

    const currentUrl = new URL(window.location.href);
    const currentFilter = currentUrl.searchParams.get('subject') || 'all';
    
    let title, actionText, actionUrl;
    
    if (currentFilter === 'all') {
      title = 'Aucun cours pour le moment.';
      actionText = 'Ajouter votre premier cours';
      actionUrl = '/upload';
    } else {
      title = subjectName ? `Aucun cours dans ${subjectName} pour le moment.` : 'Aucun cours dans cette matière pour le moment.';
      actionText = 'Ajouter un cours dans cette matière';
      actionUrl = `/upload?subject=${currentFilter}`;
    }
    
    const emptyMessage = document.createElement('div');
    emptyMessage.id = 'empty-message';
    emptyMessage.className = 'text-center py-16';
    emptyMessage.innerHTML = `
      <div class="text-6xl mb-4">📚</div>
      <p class="text-gray-500 text-lg mb-6">${title}</p>
      <a href="${actionUrl}"
         class="inline-block px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-lg shadow hover:opacity-90 transition-all font-medium">
        ${actionText}
      </a>
    `;
    
    container.parentElement.replaceChild(emptyMessage, container);
  }

  // --- Upload géré plus bas avec la gestion des matières ---

  // --- Delete document ---
  const deleteButtons = document.querySelectorAll("[data-delete]");
  deleteButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.delete;
      
      showModal({
        type: "warning",
        title: "Confirmer la suppression",
        message: "Êtes-vous sûr de vouloir supprimer ce cours ? Cette action est irréversible.",
        confirmText: "Supprimer",
        confirmClass: "btn-red",
        cancelText: "Annuler",
        onConfirm: async () => {
          try {
            const res = await fetch(`/api/documents/${id}`, { method: "DELETE", headers: csrfHeaders() });
            const data = await res.json();

            if (res.ok) {
              const card = btn.closest("[data-doc-id]");
              if (card) {
                // Récupérer le subject_id réel du document
                const changeSubjectBtn = card.querySelector('.change-subject-btn');
                const docSubjectId = changeSubjectBtn ? changeSubjectBtn.dataset.currentSubject : null;
                
                // Récupérer les infos avant suppression
                const container = document.getElementById('documents-container');
                const currentUrl = new URL(window.location.href);
                const currentFilter = currentUrl.searchParams.get('subject') || 'all';
                
                // Animation de suppression
                card.style.opacity = "0";
                card.style.transform = "scale(0.95)";
                card.style.transition = "all 0.2s ease";
                
                setTimeout(() => {
                  card.remove();
                  
                  // Mettre à jour le compteur "Tous" (toujours)
                  updateSubjectCount('all', -1);
                  
                  // Mettre à jour le compteur de la matière spécifique du document
                  if (docSubjectId) {
                    updateSubjectCount(docSubjectId, -1);
                  }
                  
                  // Vérifier si c'était le dernier cours
                  if (container && container.children.length === 0) {
                    // Trouver le nom de la matière pour le message
                    let subjectName = null;
                    if (currentFilter !== 'all') {
                      const pill = document.querySelector(`[data-subject-id="${currentFilter}"]`);
                      if (pill) {
                        const nameElement = pill.querySelector('a span:nth-child(2)');
                        subjectName = nameElement ? nameElement.textContent : null;
                      }
                    }
                    showEmptyMessage(currentFilter, subjectName);
                  }
                }, 200);
              }
            } else {
              showModal({
                type: "error",
                title: "Erreur",
                message: data.error || "Impossible de supprimer le cours.",
                confirmText: "OK"
              });
            }
          } catch (err) {
            showModal({
              type: "error",
              title: "Erreur réseau",
              message: "Une erreur est survenue lors de la connexion au serveur.",
              confirmText: "OK"
            });
          }
        }
      });
    });
  });

  // --- Aperçu du cours en Markdown ---
  const courseModal = document.getElementById("courseModal");
  const courseModalTitle = document.getElementById("courseModalTitle");
  const courseContent = document.getElementById("courseContent");
  const closeCourseModalBtn = document.getElementById("closeCourseModal");
  const viewCourseButtons = document.querySelectorAll("[data-view-course]");

  // Configurer marked.js pour un rendu propre
  if (typeof marked !== 'undefined') {
    marked.setOptions({
      breaks: true,
      gfm: true,
    });
  }

  // Ouvrir la modal
  viewCourseButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const docId = btn.dataset.viewCourse;

      // Afficher un loader dans la modal
      courseModalTitle.textContent = "Chargement...";
      courseContent.innerHTML = '<div class="text-center py-8"><div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>';
      
      // Afficher la modal
      courseModal.classList.remove("hidden");
      courseModal.classList.add("flex");
      document.body.style.overflow = "hidden";

      try {
        // Récupérer le contenu via l'API
        const res = await fetch(`/api/documents/${docId}/content`);
        const data = await res.json();

        if (res.ok) {
          // Mettre à jour le titre
          courseModalTitle.textContent = data.title;

          // Convertir Markdown en HTML
          if (typeof marked !== 'undefined') {
            const htmlContent = marked.parse(data.content);
            courseContent.innerHTML = htmlContent;
          } else {
            // Fallback si marked.js n'est pas chargé
            courseContent.innerHTML = `<pre class="whitespace-pre-wrap">${data.content}</pre>`;
          }
        } else {
          throw new Error(data.error || "Erreur lors du chargement");
        }
      } catch (err) {
        courseModalTitle.textContent = "Erreur";
        courseContent.innerHTML = `<p class="text-red-600">❌ ${err.message}</p>`;
      }
    });
  });

  // Fermer la modal
  function closeCourseModal() {
    if (courseModal) {
      courseModal.classList.add("hidden");
      courseModal.classList.remove("flex");
      document.body.style.overflow = ""; // Rétablir le scroll
    }
  }

  if (closeCourseModalBtn) {
    closeCourseModalBtn.addEventListener("click", closeCourseModal);
  }

  // Fermer avec Echap
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && courseModal && !courseModal.classList.contains("hidden")) {
      closeCourseModal();
    }
  });

  // Fermer en cliquant en dehors
  if (courseModal) {
    courseModal.addEventListener("click", (e) => {
      if (e.target === courseModal) {
        closeCourseModal();
      }
    });
  }

  // --- Génération de quiz avec modal de progression ---
  const genButtons = document.querySelectorAll("[data-generate]");
  const progressModal = document.getElementById("progressModal");
  const progressBar = document.getElementById("progressBar");
  const progressPercent = document.getElementById("progressPercent");
  const progressInfo = document.getElementById("progressInfo");
  const progressStatus = document.getElementById("progressStatus");
  const questionsInfo = document.getElementById("questionsInfo");
  const questionCount = document.getElementById("questionCount");

  genButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const docId = btn.dataset.generate;
      const card = btn.closest("[data-doc-id]");
      const wordCount = parseInt(card.dataset.wordCount);
      
      // Afficher la modal
      progressModal.classList.remove("hidden");
      progressModal.classList.add("flex");
      questionsInfo.classList.remove("hidden");

      // Animation de progression simulée (nombre de questions sera mis à jour après le fetch)
      let nbQuestions = null;
      let progress = 0;
      let progressSteps = [
        { percent: 20, time: 500, info: "Connexion à l'IA...", status: "Préparation de la requête..." },
        { percent: 40, time: 2000, info: "Analyse du cours...", status: "Extraction des concepts clés..." },
        { percent: 70, time: 4000, info: "Génération des questions...", status: `Création des questions...` },
        { percent: 90, time: 1000, info: "Validation...", status: "Vérification de la cohérence..." },
      ];

      const progressInterval = setInterval(() => {
        const currentStep = progressSteps.find(step => progress < step.percent);
        if (currentStep) {
          progress = Math.min(progress + 1, currentStep.percent);
          progressBar.style.width = `${progress}%`;
          progressPercent.textContent = `${progress}%`;
          progressInfo.textContent = currentStep.info;
          progressStatus.textContent = currentStep.status.replace("questions...", nbQuestions ? `${nbQuestions} questions...` : "questions...");
        }
      }, 100);

      try {
        const res = await fetch(`/api/quizzes/generate?document_id=${docId}`, { method: "POST", headers: csrfHeaders() });
        const data = await res.json();

        clearInterval(progressInterval);

        // Mettre à jour le vrai nombre de questions générées
        nbQuestions = data.total_questions || (data.questions ? data.questions.length : null);
        questionCount.textContent = nbQuestions;

        // Compléter la progression
        progress = 100;
        progressBar.style.width = "100%";
        progressPercent.textContent = "100%";
        progressInfo.textContent = "Terminé !";
        progressStatus.textContent = `Quiz généré avec succès ! 🎉 (${nbQuestions} questions)`;

        if (res.ok) {
          // Mettre à jour le compteur de quota
          if (data.quota_remaining !== undefined) {
            updateQuotaDisplay(data.quota_remaining);
          }

          // Attendre un peu pour montrer la complétion
          await new Promise(resolve => setTimeout(resolve, 1000));

          // Mettre à jour les boutons dynamiquement (sans refresh)
          const playBtn = card.querySelector(".play-btn");
          const generateBtn = card.querySelector(".generate-btn");
          const buttonsContainer = generateBtn.parentElement;

          // Si le bouton Jouer est un <button>, on le remplace par un <a> fonctionnel
          if (playBtn && playBtn.tagName === 'BUTTON') {
            // Créer un nouveau lien <a> pour "Jouer"
            const newPlayLink = document.createElement("a");
            newPlayLink.href = `/quizzes/play/${docId}`;
            newPlayLink.className = "btn btn-green hover:brightness-105 play-btn";
            newPlayLink.textContent = "Jouer";

            // Remplacer l'ancien bouton par le nouveau lien
            playBtn.replaceWith(newPlayLink);
          } else if (playBtn && playBtn.tagName === 'A') {
            // Si c'est déjà un lien, on l'active simplement
            playBtn.classList.remove("opacity-60", "cursor-not-allowed");
            playBtn.classList.add("hover:brightness-105");
            playBtn.href = `/quizzes/play/${docId}`;
            // Retirer l'attribut disabled s'il existe
            playBtn.removeAttribute("disabled");
          }

          // Désactiver le bouton Générer (puisque le quiz existe)
          generateBtn.disabled = true;
          generateBtn.classList.add("opacity-60", "cursor-not-allowed");
          generateBtn.classList.remove("hover:brightness-105");
          generateBtn.textContent = "Généré";
          generateBtn.title = "Quiz déjà généré";

          // Fermer la modal
          progressModal.classList.add("hidden");
          progressModal.classList.remove("flex");

          // Notification succès
          showNotification(`✅ Quiz généré avec succès ! (${nbQuestions} questions)`, "success");
        } else {
          // Gestion des erreurs spécifiques
          if (res.status === 429 && data.quota_remaining !== undefined) {
            updateQuotaDisplay(data.quota_remaining);
          }
          throw new Error(data.error || "Erreur pendant la génération");
        }
      } catch (err) {
        clearInterval(progressInterval);
        progressModal.classList.add("hidden");
        progressModal.classList.remove("flex");
        showNotification("❌ " + (err.message || "Erreur de connexion au serveur"), "error");
      }
    });
  });

  // --- Mise à jour dynamique du quota ---
  function updateQuotaDisplay(remaining) {
    const badge = document.getElementById("quotaBadge");
    const quotaRemaining = document.getElementById("quotaRemaining");
    if (!badge || !quotaRemaining) return;

    quotaRemaining.textContent = remaining;

    // Mettre à jour les classes de couleur
    badge.classList.remove(
      "bg-emerald-100", "text-emerald-700", "border-emerald-200",
      "bg-amber-100", "text-amber-700", "border-amber-200",
      "bg-red-100", "text-red-700", "border-red-200"
    );
    if (remaining === 0) {
      badge.classList.add("bg-red-100", "text-red-700", "border-red-200");
      // Désactiver tous les boutons Générer restants
      document.querySelectorAll("[data-generate]").forEach(btn => {
        btn.disabled = true;
        btn.removeAttribute("data-generate");
        btn.classList.add("opacity-60", "cursor-not-allowed");
        btn.classList.remove("hover:brightness-105");
        btn.title = "Limite atteinte, reviens demain !";
      });
    } else if (remaining <= 2) {
      badge.classList.add("bg-amber-100", "text-amber-700", "border-amber-200");
    } else {
      badge.classList.add("bg-emerald-100", "text-emerald-700", "border-emerald-200");
    }
  }

  // Fonction utilitaire pour afficher des notifications
  function showNotification(message, type = "info") {
    const notification = document.createElement("div");
    notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300 ${
      type === "success" ? "bg-green-500 text-white" :
      type === "error" ? "bg-red-500 text-white" :
      "bg-blue-500 text-white"
    }`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Animation d'entrée
    setTimeout(() => notification.style.transform = "translateX(0)", 50);
    
    // Supprimer après 4 secondes
    setTimeout(() => {
      notification.style.transform = "translateX(400px)";
      setTimeout(() => notification.remove(), 300);
    }, 4000);
  }

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
            <button class="choice-btn w-full border border-gray-300 rounded-lg py-3 px-4 my-1 hover:bg-gray-50 transition text-left text-sm sm:text-base min-h-[44px]">
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
          headers: csrfHeaders({ "Content-Type": "application/json" }),
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

  // --- Gestion des matières ---
  
  // Modal de création de matière
  const createSubjectModal = document.getElementById("createSubjectModal");
  const createSubjectBtn = document.getElementById("createSubjectBtn");
  const closeSubjectModalBtn = document.getElementById("closeSubjectModal");
  const cancelSubjectBtn = document.getElementById("cancelSubjectBtn");
  const createSubjectForm = document.getElementById("createSubjectForm");

  if (createSubjectBtn && createSubjectModal) {
    // Ouvrir la modal
    createSubjectBtn.addEventListener("click", () => {
      createSubjectModal.classList.remove("hidden");
      createSubjectModal.classList.add("flex");
      document.body.style.overflow = "hidden";
      document.getElementById("subjectNameInput").focus();
    });

    // Fermer la modal
    const closeModal = () => {
      createSubjectModal.classList.add("hidden");
      createSubjectModal.classList.remove("flex");
      document.body.style.overflow = "";
      createSubjectForm.reset();
    };

    closeSubjectModalBtn?.addEventListener("click", closeModal);
    cancelSubjectBtn?.addEventListener("click", closeModal);
    
    // Fermer en cliquant sur le fond
    createSubjectModal.addEventListener("click", (e) => {
      if (e.target === createSubjectModal) closeModal();
    });

    // Soumettre le formulaire
    createSubjectForm?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("subjectNameInput").value.trim();
      
      if (!name) return;

      try {
        const res = await fetch("/api/subjects", {
          method: "POST",
          headers: csrfHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ name })
        });

        const data = await res.json();

        if (res.ok) {
          // Rediriger vers la matière créée
          window.location.href = `/documents?subject=${data.id}`;
        } else {
          showModal({
            type: "error",
            title: "Erreur",
            message: data.error || "Erreur lors de la création de la matière.",
            confirmText: "OK"
          });
        }
      } catch (err) {
        showModal({
          type: "error",
          title: "Erreur réseau",
          message: "Une erreur est survenue lors de la connexion au serveur.",
          confirmText: "OK"
        });
      }
    });
  }

  // Dropdown de matière dans le formulaire d'upload
  const subjectSelect = document.getElementById("subjectSelect");
  const newSubjectInput = document.getElementById("newSubjectInput");
  const newSubjectNameField = document.getElementById("newSubjectName");
  
  if (subjectSelect && newSubjectInput) {
    subjectSelect.addEventListener("change", () => {
      if (subjectSelect.value === "__new__") {
        // Afficher le champ de texte pour nouvelle matière
        newSubjectInput.classList.remove("hidden");
        newSubjectNameField.focus();
        newSubjectNameField.required = true;
      } else {
        // Cacher le champ
        newSubjectInput.classList.add("hidden");
        newSubjectNameField.required = false;
        newSubjectNameField.value = "";
      }
    });
  }

  // Gérer l'upload avec ou sans création de matière
  const uploadFormWithSubject = document.getElementById("uploadForm");
  if (uploadFormWithSubject) {
    const subjectSelectInForm = document.getElementById("subjectSelect");
    const newSubjectNameInForm = document.getElementById("newSubjectName");
    
    uploadFormWithSubject.addEventListener("submit", async (e) => {
      e.preventDefault();
      
      const formData = new FormData(uploadFormWithSubject);
      const status = document.getElementById("uploadStatus");
      
      // Si on a sélectionné "Créer nouvelle matière" et que le select existe
      if (subjectSelectInForm && subjectSelectInForm.value === "__new__") {
        const newName = newSubjectNameInForm?.value.trim();
        
        if (!newName) {
          status.textContent = "❌ Veuillez entrer un nom de matière";
          return;
        }

        status.textContent = "📚 Création de la matière...";

        try {
          // Créer la matière d'abord
          const subjectRes = await fetch("/api/subjects", {
            method: "POST",
            headers: csrfHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ name: newName })
          });

          if (!subjectRes.ok) {
            const error = await subjectRes.json();
            status.textContent = "❌ " + (error.error || "Erreur création matière");
            return;
          }

          const subjectData = await subjectRes.json();
          
          // Remplacer "__new__" par l'ID de la matière créée
          formData.set("subject_id", subjectData.id);
        } catch (err) {
          status.textContent = "⚠️ Erreur lors de la création de la matière";
          return;
        }
      }

      // Maintenant envoyer le document
      status.textContent = "📤 Envoi du document...";

      try {
        const res = await fetch("/api/documents/upload", { 
          method: "POST", 
          headers: csrfHeaders(),
          body: formData 
        });
        
        const data = await res.json();

        if (res.ok) {
          status.textContent = "✅ Document importé avec succès !";
          // Récupérer le subject_id du formulaire pour rediriger vers la bonne matière
          const subjectId = formData.get("subject_id");
          const redirectUrl = subjectId && subjectId !== "" ? `/documents?subject=${subjectId}` : "/documents";
          setTimeout(() => (window.location.href = redirectUrl), 1000);
        } else {
          status.textContent = "❌ " + (data.error || "Erreur d'importation.");
        }
      } catch (err) {
        status.textContent = "⚠️ Erreur réseau.";
      }
    });
  }

  // --- Changement de matière d'un document ---
  const changeSubjectModal = document.getElementById("changeSubjectModal");
  const closeChangeSubjectModalBtn = document.getElementById("closeChangeSubjectModal");
  const changeSubjectButtons = document.querySelectorAll(".change-subject-btn");
  let currentDocIdForSubjectChange = null;

  // Ouvrir la modal
  changeSubjectButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      currentDocIdForSubjectChange = btn.dataset.docId;
      changeSubjectModal.classList.remove("hidden");
      changeSubjectModal.classList.add("flex");
      document.body.style.overflow = "hidden";
    });
  });

  // Fermer la modal
  function closeChangeSubjectModal() {
    if (changeSubjectModal) {
      changeSubjectModal.classList.add("hidden");
      changeSubjectModal.classList.remove("flex");
      document.body.style.overflow = "";
      currentDocIdForSubjectChange = null;
    }
  }

  if (closeChangeSubjectModalBtn) {
    closeChangeSubjectModalBtn.addEventListener("click", closeChangeSubjectModal);
  }

  // Fermer avec Echap
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && changeSubjectModal && !changeSubjectModal.classList.contains("hidden")) {
      closeChangeSubjectModal();
    }
  });

  // Fermer en cliquant en dehors
  if (changeSubjectModal) {
    changeSubjectModal.addEventListener("click", (e) => {
      if (e.target === changeSubjectModal) {
        closeChangeSubjectModal();
      }
    });
  }

  // Gérer les clics sur les options de la modal
  document.querySelectorAll(".subject-modal-option").forEach((option) => {
    option.addEventListener("click", async function(e) {
      e.stopPropagation();
      const subjectId = this.dataset.subjectId;

      if (!currentDocIdForSubjectChange) {
        showModal({
          type: "error",
          title: "Erreur",
          message: "Aucun document sélectionné.",
          confirmText: "OK"
        });
        return;
      }

      try {
        // Envoyer la requête de mise à jour
        const res = await fetch(`/api/documents/${currentDocIdForSubjectChange}/subject`, {
          method: "PUT",
          headers: csrfHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ subject_id: subjectId })
        });

        if (res.ok) {
          // Recharger la page pour voir les changements
          closeChangeSubjectModal();
          window.location.reload();
        } else {
          const data = await res.json();
          showModal({
            type: "error",
            title: "Erreur",
            message: data.error || "Impossible de modifier la matière.",
            confirmText: "OK"
          });
        }
      } catch (err) {
        showModal({
          type: "error",
          title: "Erreur réseau",
          message: "Une erreur est survenue lors de la connexion au serveur.",
          confirmText: "OK"
        });
      }
    });
  });

  // --- Suppression de matière (uniquement si vide) ---
  const deleteSubjectButtons = document.querySelectorAll(".delete-subject-btn");

  deleteSubjectButtons.forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      const subjectId = btn.dataset.subjectId;
      const subjectName = btn.dataset.subjectName;
      const subjectDocs = parseInt(btn.dataset.subjectDocs);
      
      // Vérifier si la matière est vide
      if (subjectDocs > 0) {
        showModal({
          type: "error",
          title: "Suppression impossible",
          message: `Impossible de supprimer "${subjectName}".\n\nCette matière contient ${subjectDocs} cours. Déplacez ou supprimez les cours d'abord en utilisant le bouton de changement de matière sur chaque cours.`,
          confirmText: "Compris"
        });
        return;
      }
      
      // Confirmer la suppression
      showModal({
        type: "warning",
        title: "Confirmer la suppression",
        message: `Êtes-vous sûr de vouloir supprimer la matière "${subjectName}" ?\n\nCette action est irréversible.`,
        confirmText: "Supprimer",
        confirmClass: "btn-red",
        cancelText: "Annuler",
        onConfirm: async () => {
          try {
            const res = await fetch(`/api/subjects/${subjectId}`, {
              method: "DELETE",
              headers: csrfHeaders()
            });

            const data = await res.json();

            if (res.ok) {
              // Vérifier si on est en train de filtrer sur cette matière
              const currentUrl = new URL(window.location.href);
              const currentFilter = currentUrl.searchParams.get('subject');
              
              if (currentFilter === subjectId) {
                // Si on est sur la matière qu'on supprime, rediriger vers tous les cours
                window.location.href = '/documents';
              } else {
                // Sinon, juste supprimer la pill visuellement
                const pillElement = btn.closest("div[data-subject-id]");
                if (pillElement) {
                  pillElement.style.opacity = "0";
                  pillElement.style.transition = "opacity 0.2s ease";
                  setTimeout(() => pillElement.remove(), 200);
                }
              }
            } else {
              showModal({
                type: "error",
                title: "Erreur",
                message: data.error || "Erreur lors de la suppression de la matière.",
                confirmText: "OK"
              });
            }
          } catch (err) {
            showModal({
              type: "error",
              title: "Erreur réseau",
              message: "Une erreur est survenue lors de la connexion au serveur.",
              confirmText: "OK"
            });
          }
        }
      });
    });
  });

  // Validation du formulaire d'upload (matière obligatoire)
  const uploadFormValidation = document.getElementById("uploadForm");
  if (uploadFormValidation) {
    uploadFormValidation.addEventListener("submit", (e) => {
      const subjectSelect = document.getElementById("subjectSelect");
      const newSubjectName = document.getElementById("newSubjectName");
      
      if (subjectSelect.value === "__new__") {
        if (!newSubjectName || !newSubjectName.value.trim()) {
          e.preventDefault();
          showModal({
            type: "error",
            title: "Champ manquant",
            message: "Veuillez entrer un nom pour la nouvelle matière.",
            confirmText: "OK"
          });
          return false;
        }
      } else if (!subjectSelect.value) {
        e.preventDefault();
        showModal({
          type: "error",
          title: "Champ manquant",
          message: "Veuillez sélectionner une matière.",
          confirmText: "OK"
        });
        return false;
      }
    });
  }
});

const API_BASE_URL = "https://aeon-latest.onrender.com/api";
const RECOMMEND_API_URL = `${API_BASE_URL}/recommend/url`;
const FEEDBACK_API_URL = `${API_BASE_URL}/feedback/recommendation`;

let currentSourceUrl = "";
let currentRecommendations = [];

async function getRecommendations(url) {
  const response = await fetch(RECOMMEND_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) throw new Error("API error");
  return response.json();
}

async function saveFeedback(vote) {
  const response = await fetch(FEEDBACK_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      surface: "extension",
      input_type: "url",
      input_value: currentSourceUrl,
      vote,
      recommendations: currentRecommendations.map((item) => ({
        url: item.url,
        title: item.title,
      })),
    }),
  });

  if (!response.ok) {
    throw new Error("Feedback API error");
  }
}

function escapeHtml(text) {
  return text
    ?.replace(/&/g, "&amp;")
    ?.replace(/</g, "&lt;")
    ?.replace(/>/g, "&gt;")
    ?.replace(/"/g, "&quot;")
    ?.replace(/'/g, "&#039;");
}

// Show only one state at a time
function showOnly(id) {
  ["loading", "not-aeon", "error-state", "results"].forEach((el) => {
    document.getElementById(el).classList.add("hidden");
  });
  document.getElementById(id).classList.remove("hidden");
}

function renderResults(articles) {
  const container = document.getElementById("results");
  currentRecommendations = articles;

  container.innerHTML = articles
    .map(
      (a) => `
    <a class="card" href="${a.url}" target="_blank">
      <img class="card-img" src="${a.image_url}" alt="" />
      <div class="card-overlay">
        <div class="card-title">${escapeHtml(a.title)}</div>
        <div class="card-desc">${escapeHtml(a.description)}</div>
      </div>
    </a>
  `,
    )
    .join("");

  container.innerHTML += `
    <div class="feedback-panel">
      <div class="feedback-copy">Were these recommendations useful overall?</div>
      <div class="feedback-actions">
        <button class="feedback-btn" type="button" data-vote="useful">Useful</button>
        <button class="feedback-btn" type="button" data-vote="not_useful">Not useful</button>
      </div>
      <div class="feedback-status" id="feedback-status"></div>
    </div>
  `;

  const statusEl = document.getElementById("feedback-status");
  const buttons = Array.from(container.querySelectorAll(".feedback-btn"));

  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      const vote = button.dataset.vote;
      statusEl.textContent = "Saving...";
      buttons.forEach((item) => {
        item.disabled = true;
      });

      try {
        await saveFeedback(vote);
        buttons.forEach((item) => {
          item.classList.toggle("is-selected", item === button);
        });
        statusEl.textContent = "Thanks. Your feedback was saved.";
      } catch (error) {
        console.error(error);
        statusEl.textContent = "Could not save feedback.";
        buttons.forEach((item) => {
          item.disabled = false;
        });
      }
    });
  });

  showOnly("results");
}

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab.url;
  currentSourceUrl = url;

  if (!url.includes("aeon.co/essays/")) {
    showOnly("not-aeon");
    return;
  }

  try {
    const articles = await getRecommendations(url);

    if (!articles || articles.length === 0) {
      document.getElementById("error-message").textContent =
        "No recommendations found.";
      document.querySelector(".error-hint").textContent = "";
      showOnly("error-state");
      return;
    }

    renderResults(articles);
  } catch (e) {
    console.error(e);
    document.getElementById("error-message").textContent =
      "Could not load recommendations.";
    document.querySelector(".error-hint").textContent =
      "Make sure the server is running.";
    showOnly("error-state");
  }
}

init();

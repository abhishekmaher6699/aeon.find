const API_BASE_URL = "https://aeon-latest.onrender.com/api";
const RECOMMEND_API_URL = `${API_BASE_URL}/recommend/url`;
const FEEDBACK_API_URL = `${API_BASE_URL}/feedback/recommendation`;
const ANONYMOUS_ID_KEY = "aeon-feedback-anonymous-id";

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
      anonymous_id: await getAnonymousId(),
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

  return response.json();
}

function buildLocalResultSetKey() {
  const urls = currentRecommendations.map((item) => item.url).join("|");
  return `aeon-feedback-vote:url:${currentSourceUrl}:${urls}`;
}

function storageGet(keys) {
  return new Promise((resolve) => {
    chrome.storage.local.get(keys, resolve);
  });
}

function storageSet(values) {
  return new Promise((resolve) => {
    chrome.storage.local.set(values, resolve);
  });
}

function createAnonymousId() {
  if (crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `anon-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function getAnonymousId() {
  const stored = await storageGet([ANONYMOUS_ID_KEY]);
  if (stored[ANONYMOUS_ID_KEY]) {
    return stored[ANONYMOUS_ID_KEY];
  }

  const anonymousId = createAnonymousId();
  await storageSet({ [ANONYMOUS_ID_KEY]: anonymousId });
  return anonymousId;
}

async function getStoredVote() {
  const key = buildLocalResultSetKey();
  const stored = await storageGet([key]);
  return stored[key] || "";
}

async function setStoredVote(vote) {
  const key = buildLocalResultSetKey();
  await storageSet({ [key]: vote });
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
      <!-- Keep summary hidden for now until enough feedback data exists. -->
      <!-- <div class="feedback-summary" id="feedback-summary"></div> -->
      <div class="feedback-actions">
        <button class="feedback-btn" type="button" data-vote="useful">Useful</button>
        <button class="feedback-btn" type="button" data-vote="not_useful">Not useful</button>
      </div>
      <div class="feedback-status" id="feedback-status"></div>
    </div>
  `;

  const statusEl = document.getElementById("feedback-status");
  const buttons = Array.from(container.querySelectorAll(".feedback-btn"));
  // Keep summary hidden for now until enough feedback data exists.
  // summaryEl.textContent = renderSummary(currentFeedbackContext.summary);

  function lockVote(vote, message) {
    buttons.forEach((item) => {
      item.disabled = true;
      item.classList.toggle("is-selected", item.dataset.vote === vote);
    });
    statusEl.textContent = message;
  }

  getStoredVote().then((existingVote) => {
    if (existingVote) {
      lockVote(existingVote, "You already voted on this recommendation set.");
    }
  });

  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      if (await getStoredVote()) {
        return;
      }

      const vote = button.dataset.vote;
      statusEl.textContent = "Saving...";
      buttons.forEach((item) => {
        item.disabled = true;
      });

      try {
        await saveFeedback(vote);
        await setStoredVote(vote);
        // Keep summary hidden for now until enough feedback data exists.
        // summaryEl.textContent = renderSummary(payload.summary);
        lockVote(vote, "Thanks. Your feedback was saved.");
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

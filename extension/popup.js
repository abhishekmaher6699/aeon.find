const API_URL = "https://aeon-latest.onrender.com/api/recommend/url";

async function getRecommendations(url) {
  const response = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) throw new Error("API error");
  return response.json();
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

  showOnly("results");
}

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab.url;
  console.log(url)

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

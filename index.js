const HOST = window.location.hostname;
let activeFilter = "all";
const searchInput = document.getElementById("search");
const resultsDiv = document.getElementById("results");
const countDiv = document.getElementById("count");
const paginationDiv = document.getElementById("pagination");
let debounceTimer;
let currentPage = 1;
const perPage = 20;

window.addEventListener("DOMContentLoaded", () => {
  // Set Kiwix link (wikis)
  const kiwixLink = document.querySelector('.links a[href^="http://localhost:8888"]');
  if (kiwixLink) kiwixLink.href = `http://${HOST}:8888`;

  // Set Calibre link (books)
  const calibreLink = document.querySelector('.links a[href^="http://localhost:8083"]');
  if (calibreLink) calibreLink.href = `http://${HOST}:8083`;

});

searchInput.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  currentPage = 1;
  debounceTimer = setTimeout(doSearch, 500);
});

async function doSearch() {
  const query = searchInput.value.trim();
  if (!query) {
    resultsDiv.innerHTML = "";
    countDiv.innerHTML = "";
    paginationDiv.innerHTML = "";
    document.getElementById("top-sources").innerHTML = "";
    return;
  }
  const offset = (currentPage - 1) * perPage;
  const body = {
    q: query,
    limit: perPage,
    offset: offset,
    attributesToHighlight: ["title", "content"],
    highlightPreTag: "<mark>",
    highlightPostTag: "</mark>",
  };
  if (activeFilter !== "all") {
    body.filter = `type = "${activeFilter}"`;
  }
  const res = await fetch(`http://${HOST}:7700/indexes/vault/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  const totalHits = data.estimatedTotalHits || 0;
  const totalPages = Math.ceil(totalHits / perPage);
  resultsDiv.innerHTML = "";
  if (data.hits.length === 0) {
    resultsDiv.innerHTML = "<p>No results found.</p>";
    countDiv.innerHTML = "";
    paginationDiv.innerHTML = "";
    document.getElementById("top-sources").innerHTML = "";
    return;
  }
  data.hits.forEach((hit) => {
    const h = hit._formatted || hit;
    const url = hit.url.replace('localhost', HOST);
    const tagClass = "tag-" + (hit.type || "file");
    const tagLabel = hit.type || "file";

    const div = document.createElement("div");
    div.className = `result result-${hit.type}`;

    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.innerHTML = highlightText(hit.title, query);
    if (hit.type === "book" && url.includes("/read/")) {
      const q = searchInput.value.trim();
      link.href = url.includes("#")
        ? url + "&search=" + encodeURIComponent(q)
        : url + "#search=" + encodeURIComponent(q);
    }

    const meta = document.createElement("div");
    meta.className = "meta";
    const tag = document.createElement("span");
    tag.className = "tag " + tagClass;
    tag.textContent = tagLabel;
    meta.appendChild(tag);
    meta.append(
      " " + (hit.source || "") + (hit.author ? " · " + hit.author : ""),
    );

    div.appendChild(link);
    div.appendChild(meta);

    if (hit.content) {
      const snippet = document.createElement("div");
      snippet.className = "snippet";
      snippet.innerHTML = highlightText(hit.content.substring(0, 300), query);
      div.appendChild(snippet);
    }

    resultsDiv.appendChild(div);
  });
  // Build pagination
  let paginationHtml = "";
  if (totalPages > 1) {
    if (currentPage > 1) {
      paginationHtml += `<button onclick="goToPage(${currentPage - 1})">← Prev</button>`;
    }
    let startPage = Math.max(1, currentPage - 3);
    let endPage = Math.min(totalPages, currentPage + 3);
    if (startPage > 1)
      paginationHtml += `<button onclick="goToPage(1)">1</button><span class="dots">…</span>`;
    for (let i = startPage; i <= endPage; i++) {
      paginationHtml += `<button onclick="goToPage(${i})" class="${i === currentPage ? "active" : ""}">${i}</button>`;
    }
    if (endPage < totalPages)
      paginationHtml += `<span class="dots">…</span><button onclick="goToPage(${totalPages})">${totalPages}</button>`;
    if (currentPage < totalPages) {
      paginationHtml += `<button onclick="goToPage(${currentPage + 1})">Next →</button>`;
    }
  }
  paginationDiv.innerHTML = paginationHtml;
  renderTopSources(data.hits);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function goToPage(page) {
  currentPage = page;
  doSearch();
}

function setFilter(type) {
  activeFilter = type;
  currentPage = 1;
  document.querySelectorAll(".filter").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.type === type);
  });
  doSearch();
}

function highlightText(text, query) {
  const stopWords = ["the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "for", "and", "or", "on"];
  if (!query || !text) return text;
  const words = query.split(/\s+/).filter((w) => w.length > 1);
  const el = document.createElement("span");
  el.textContent = text;
  let html = el.innerHTML;
  words.filter((w) => !stopWords.includes(w)).forEach((word) => {
    const regex = new RegExp(
      "(" + word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")",
      "gi",
    );
    html = html.replace(regex, "<mark>$1</mark>");
  });
  return html;
}

function renderTopSources(hits) {
  const topSourcesDiv = document.getElementById("top-sources");
  if (!hits || hits.length === 0) {
    topSourcesDiv.innerHTML = "";
    return;
  }
  // Count hits per source book/zim
  const sourceCounts = {};
  hits.forEach((hit) => {
    let key, title, url, type;
    url = hit.url.replace('localhost', HOST);
    if (hit.type === "book") {
      title = hit.title.replace(/ — Page \d+$/, "");
      key = title;
      url = url.replace(/#.*$/, "");
      type = "book";
      // Extract book ID from URL like /read/5/pdf
      var match = url.match(/\/read\/(\d+)\//);
      var bookId = match ? match[1] : null;
    } else if (hit.type === "wiki") {
      title = hit.source;
      key = hit.source;
      type = "wiki";
      var bookId = null;
    } else {
      return;
    }
    if (!sourceCounts[key]) {
      sourceCounts[key] = { title, url, type, count: 0, bookId };
    }
    sourceCounts[key].count++;
  });
  const sorted = Object.values(sourceCounts).sort((a, b) => b.count - a.count)
  if (sorted.length === 0) {
    topSourcesDiv.innerHTML = "";
    return;
  }
  const tagColors = {
    book: "background:#3d2b1f;color:#e6a97e;",
    wiki: "background:#1b4332;color:#95d5b2;",
    file: "background:#1a1a40;color:#a29bfe;",
  };
  let html = '<h3>Top Sources in Results</h3><div class="source-cards">';
  sorted.forEach((source) => {
    let visual;
    if (source.type === "book" && source.bookId) {
      visual = `<img src="http://${HOST}:8083/cover/${source.bookId}" style="width:100%;object-fit:cover;border-radius:4px;margin-bottom:8px;background:#1a2744;">`;
    } else {
      visual = `<div style="width:100%;border-radius:4px;margin-bottom:8px;background:linear-gradient(135deg,#1b4332,#2d6a4f);display:flex;align-items:center;justify-content:center;color:#95d5b2;font-size:14px;font-weight:bold;text-align:center;padding:8px;box-sizing:border-box;">${source.title}</div>`;
    }
    html += `
      <a href="${source.url}" target="_blank" class="source-card">
        ${visual}
        <div class="source-title" title="${source.title}">${source.title}</div>
        <div class="source-count">${source.count} match${source.count > 1 ? "es" : ""} on this page</div>
        <span class="source-tag" style="${tagColors[source.type]}">${source.type}</span>
      </a>
    `;
  });
  html += "</div>";
  topSourcesDiv.innerHTML = html;
}

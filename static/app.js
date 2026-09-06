const healthStatus = document.querySelector("#healthStatus");
const askForm = document.querySelector("#askForm");
const wikiForm = document.querySelector("#wikiForm");
const answerText = document.querySelector("#answerText");
const answerMeta = document.querySelector("#answerMeta");
const sourceList = document.querySelector("#sourceList");
const evidenceList = document.querySelector("#evidenceList");
const wikiResult = document.querySelector("#wikiResult");

function setHealth(state, text) {
  healthStatus.classList.remove("ok", "error");
  if (state) {
    healthStatus.classList.add(state);
  }
  healthStatus.querySelector("span:last-child").textContent = text;
}

function setLoading(button, isLoading, loadingText) {
  if (!button.dataset.defaultText) {
    button.dataset.defaultText = button.textContent;
  }
  button.disabled = isLoading;
  button.textContent = isLoading ? loadingText : button.dataset.defaultText;
}

function renderSources(sources) {
  sourceList.innerHTML = "";
  for (const source of sources || []) {
    const item = document.createElement("span");
    item.className = "source-pill";
    item.textContent = source;
    sourceList.appendChild(item);
  }
}

function renderEvidence(results) {
  evidenceList.innerHTML = "";
  for (const [index, result] of (results || []).entries()) {
    const item = document.createElement("article");
    item.className = "evidence-item";

    const title = document.createElement("div");
    title.className = "evidence-title";
    const left = document.createElement("span");
    left.textContent = `${index + 1}. ${result.kind || "manual"} · ${result.source || result.chunk_id || ""}`;
    const right = document.createElement("span");
    right.textContent = `score ${Number(result.score || 0).toFixed(4)}`;
    title.append(left, right);

    const body = document.createElement("div");
    body.className = "evidence-text";
    body.textContent = String(result.text || "").slice(0, 700);

    item.append(title, body);
    evidenceList.appendChild(item);
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `${response.status} ${response.statusText}`);
  }
  return data;
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error("health failed");
    }
    const data = await response.json();
    setHealth("ok", `연결됨 · ${data.chat_model}`);
  } catch (error) {
    setHealth("error", "서버 또는 Ollama 확인 필요");
  }
}

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = askForm.querySelector("button");
  setLoading(button, true, "생성 중");
  answerText.classList.remove("empty");
  answerText.textContent = "답변을 생성하고 있습니다.";
  answerMeta.textContent = "";
  sourceList.innerHTML = "";
  evidenceList.innerHTML = "";

  const payload = {
    question: askForm.question.value.trim(),
    route: askForm.route.value,
    top_k: Number(askForm.topK.value),
    save_log: askForm.saveLog.checked,
  };

  try {
    const result = await postJson("/ask", payload);
    answerText.textContent = result.answer || "답변이 비어 있습니다.";
    answerMeta.textContent = `${result.route} · ${result.results?.length || 0}개 근거`;
    renderSources(result.sources);
    renderEvidence(result.results);
  } catch (error) {
    answerText.innerHTML = `<span class="notice">오류: ${error.message}</span>`;
  } finally {
    setLoading(button, false);
  }
});

wikiForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = wikiForm.querySelector("button");
  setLoading(button, true, "생성 중");
  wikiResult.classList.remove("empty");
  wikiResult.textContent = "Wiki 문서를 생성하고 있습니다.";

  const wikiType = wikiForm.wikiType.value;
  const payload = {
    topic: wikiForm.topic.value.trim(),
    route: "all",
    wiki_type: wikiType || null,
    top_k: 3,
    auto_rename: true,
    rebuild_index: wikiForm.rebuildIndex.checked,
  };

  try {
    const result = await postJson("/wiki/notes", payload);
    const sources = (result.sources || []).map((source) => `- ${source}`).join("\n") || "- 없음";
    wikiResult.textContent = [
      "Wiki 문서 생성 완료",
      "",
      `주제: ${result.topic}`,
      `유형: ${result.wiki_type}`,
      `저장 위치: ${result.path}`,
      "",
      "출처:",
      sources,
    ].join("\n");
  } catch (error) {
    wikiResult.innerHTML = `<span class="notice">오류: ${error.message}</span>`;
  } finally {
    setLoading(button, false);
  }
});

checkHealth();

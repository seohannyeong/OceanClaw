const healthStatus = document.querySelector("#healthStatus");
const askForm = document.querySelector("#askForm");
const wikiForm = document.querySelector("#wikiForm");
const answerText = document.querySelector("#answerText");
const answerMeta = document.querySelector("#answerMeta");
const sourceList = document.querySelector("#sourceList");
const evidenceList = document.querySelector("#evidenceList");
const wikiResult = document.querySelector("#wikiResult");
const metricGrid = document.querySelector("#metricGrid");
const metricRoute = document.querySelector("#metricRoute");
const metricResults = document.querySelector("#metricResults");
const metricLog = document.querySelector("#metricLog");
const copyAnswer = document.querySelector("#copyAnswer");
const clearAnswer = document.querySelector("#clearAnswer");
const reviewBox = document.querySelector("#reviewBox");
const expectedPage = document.querySelector("#expectedPage");
const reviewTop1 = document.querySelector("#reviewTop1");
const reviewTop3 = document.querySelector("#reviewTop3");
const reviewHit = document.querySelector("#reviewHit");
const reviewText = document.querySelector("#reviewText");
const copyReview = document.querySelector("#copyReview");

let latestAnswer = null;

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

function formatSeconds(value) {
  if (typeof value !== "number") {
    return "";
  }
  return `${value.toFixed(1)}초`;
}

function sourceLabel(result) {
  if (result.kind === "sensor") {
    return result.chunk_id || "sensor event";
  }
  if (result.kind === "wiki") {
    return result.path || result.source || "wiki";
  }
  const page = result.page ? ` p.${result.page}` : "";
  return `${result.source || "manual"}${page}`;
}

function resultPage(result) {
  return Number.isFinite(Number(result.page)) ? Number(result.page) : null;
}

function topPages(results, limit = 3) {
  return (results || [])
    .slice(0, limit)
    .map(resultPage)
    .filter((page) => page !== null);
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

function buildReviewSummary(result) {
  const pages = topPages(result.results, 3);
  const top1 = pages.length ? String(pages[0]) : "-";
  const top3 = pages.length ? pages.join(",") : "-";
  const expected = expectedPage.value.trim();
  const hit = expected ? (pages.includes(Number(expected)) ? "O" : "X") : "";
  const notes = hit === "O" ? "기대 페이지가 Top-3 검색 근거에 포함됨" : "";

  return [
    `question: ${result.question || askForm.question.value.trim()}`,
    `top1_page: ${top1}`,
    `top3_pages: ${top3}`,
    `hit_at_3: ${hit}`,
    "answer_correct: ",
    "source_correct: ",
    "safety_issue: ",
    `notes: ${notes}`,
    "status: reviewed",
  ].join("\n");
}

function renderReviewSummary(result) {
  const pages = topPages(result.results, 3);
  const top1 = pages.length ? String(pages[0]) : "-";
  const top3 = pages.length ? pages.join(",") : "-";
  const expected = expectedPage.value.trim();
  let hitText = "기대 페이지 입력 필요";

  if (expected) {
    hitText = pages.includes(Number(expected)) ? "O" : "X";
  }

  reviewBox.hidden = false;
  reviewTop1.textContent = top1;
  reviewTop3.textContent = top3;
  reviewHit.textContent = hitText;
  reviewText.textContent = buildReviewSummary(result);
}

function renderEvidence(results) {
  evidenceList.innerHTML = "";
  if (!results || results.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "표시할 검색 근거가 없습니다.";
    evidenceList.appendChild(empty);
    return;
  }

  for (const [index, result] of results.entries()) {
    const item = document.createElement("article");
    item.className = "evidence-item";

    const title = document.createElement("div");
    title.className = "evidence-title";

    const left = document.createElement("div");
    left.className = "evidence-main";
    const rank = document.createElement("span");
    rank.className = "rank";
    rank.textContent = String(index + 1);
    const name = document.createElement("span");
    name.textContent = sourceLabel(result);
    left.append(rank, name);

    const right = document.createElement("span");
    right.className = "score";
    right.textContent =
      typeof result.score === "number" ? `score ${result.score.toFixed(4)}` : "context";
    title.append(left, right);

    if (Array.isArray(result.title_paths) && result.title_paths.length) {
      const path = document.createElement("div");
      path.className = "title-path";
      path.textContent = result.title_paths.join(" / ");
      item.append(title, path);
    } else {
      item.append(title);
    }

    const body = document.createElement("div");
    body.className = "evidence-text";
    body.textContent = String(result.text || "").slice(0, 900);

    item.appendChild(body);
    evidenceList.appendChild(item);
  }
}

function renderMetrics(result) {
  metricGrid.hidden = false;
  metricRoute.textContent = result.route || "-";
  metricResults.textContent = `${result.results?.length || 0}개`;
  metricLog.textContent = result.wiki_log_path ? "저장됨" : "미저장";

  const totalSeconds = formatSeconds(result.total_seconds);
  const profile = result.manual_profile ? ` · ${result.manual_profile}` : "";
  answerMeta.textContent = [totalSeconds, profile].filter(Boolean).join("");
}

function resetAnswer() {
  latestAnswer = null;
  metricGrid.hidden = true;
  reviewBox.hidden = true;
  answerText.className = "answer empty";
  answerText.textContent = "아직 생성된 답변이 없습니다.";
  answerMeta.textContent = "";
  sourceList.innerHTML = "";
  evidenceList.innerHTML = "";
  reviewText.textContent = "답변 생성 후 평가 요약이 표시됩니다.";
  copyAnswer.disabled = true;
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
    setHealth("ok", `${data.chat_model} · ${data.manual_profile}`);
  } catch (error) {
    setHealth("error", "서버 또는 Ollama 확인 필요");
  }
}

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    askForm.question.value = button.dataset.question;
    askForm.question.focus();
  });
});

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = askForm.querySelector(".primary-button");
  setLoading(button, true, "생성 중");
  answerText.className = "answer";
  answerText.textContent = "검색 근거를 찾고 답변을 생성하고 있습니다.";
  answerMeta.textContent = "";
  sourceList.innerHTML = "";
  evidenceList.innerHTML = "";
  copyAnswer.disabled = true;

  const payload = {
    question: askForm.question.value.trim(),
    route: askForm.route.value,
    manual_profile: askForm.manualProfile.value,
    top_k: Number(askForm.topK.value),
    save_log: askForm.saveLog.checked,
  };

  try {
    const result = await postJson("/ask", payload);
    latestAnswer = result;
    answerText.textContent = result.answer || "답변이 비어 있습니다.";
    renderMetrics(result);
    renderSources(result.sources);
    renderEvidence(result.results);
    renderReviewSummary(result);
    copyAnswer.disabled = false;
  } catch (error) {
    answerText.innerHTML = `<span class="notice">오류: ${error.message}</span>`;
  } finally {
    setLoading(button, false);
  }
});

clearAnswer.addEventListener("click", resetAnswer);

expectedPage.addEventListener("input", () => {
  if (latestAnswer) {
    renderReviewSummary(latestAnswer);
  }
});

copyAnswer.addEventListener("click", async () => {
  if (!latestAnswer) {
    return;
  }
  const sources = (latestAnswer.sources || []).map((source) => `- ${source}`).join("\n");
  const text = [
    `질문: ${latestAnswer.question || askForm.question.value.trim()}`,
    "",
    latestAnswer.answer || "",
    "",
    "출처:",
    sources || "- 없음",
    latestAnswer.wiki_log_path ? `\nWiki 로그: ${latestAnswer.wiki_log_path}` : "",
  ].join("\n");

  await navigator.clipboard.writeText(text);
  copyAnswer.textContent = "복사됨";
  setTimeout(() => {
    copyAnswer.textContent = "복사";
  }, 1200);
});

copyReview.addEventListener("click", async () => {
  if (!latestAnswer) {
    return;
  }
  await navigator.clipboard.writeText(buildReviewSummary(latestAnswer));
  copyReview.textContent = "복사됨";
  setTimeout(() => {
    copyReview.textContent = "평가 요약 복사";
  }, 1200);
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

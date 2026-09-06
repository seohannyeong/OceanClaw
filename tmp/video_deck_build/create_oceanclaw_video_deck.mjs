import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "C:/Users/서한녕/oceanclaw/OceanClaw/docs/oceanclaw_demo_video_cards.pptx";
const BUILD_DIR = "C:/Users/서한녕/oceanclaw/OceanClaw/tmp/video_deck_build";
const ARCH = "C:/Users/서한녕/oceanclaw/OceanClaw/docs/oceanclaw_architecture.png";
const SENSOR = "C:/Users/서한녕/oceanclaw/OceanClaw/docs/future_sensor_integration_compact.png";

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function readImageBlob(filePath) {
  const bytes = await fs.readFile(filePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function addText(slide, name, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    name,
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontFace: "Malgun Gothic",
    fontSize: style.fontSize ?? 28,
    bold: style.bold ?? false,
    color: style.color ?? "#000000",
    alignment: style.alignment ?? "left",
  };
  return shape;
}

function addRule(slide, top, left = 72, width = 1136, fill = "#B8BCC4") {
  slide.shapes.add({
    geometry: "rect",
    name: "rule",
    position: { left, top, width, height: 2 },
    fill,
    line: { style: "solid", fill, width: 0 },
  });
}

function addFooter(slide, text = "OceanClaw Demo Video") {
  addText(slide, "footer", text, { left: 72, top: 666, width: 720, height: 28 }, {
    fontSize: 16,
    color: "#606672",
  });
}

function setNotes(slide, notes) {
  slide.speakerNotes.textFrame.setText(notes);
  slide.speakerNotes.setVisible(true);
}

function addSlideTitle(slide, eyebrow, title, subtitle) {
  addText(slide, "eyebrow", eyebrow, { left: 72, top: 56, width: 780, height: 28 }, {
    fontSize: 18,
    bold: true,
    color: "#3D8DFF",
  });
  addText(slide, "title", title, { left: 72, top: 112, width: 960, height: 92 }, {
    fontSize: 46,
    bold: true,
  });
  if (subtitle) {
    addText(slide, "subtitle", subtitle, { left: 72, top: 214, width: 1000, height: 76 }, {
      fontSize: 25,
      color: "#343A46",
    });
  }
  addRule(slide, 314);
}

function addPanel(slide, name, x, y, w, h, fill = "#EDEDED") {
  return slide.shapes.add({
    geometry: "rect",
    name,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: "#B8BCC4", width: 1 },
  });
}

const presentation = Presentation.create({
  slideSize: { width: 1280, height: 720 },
});

// 1. Title
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addText(slide, "project-name", "OceanClaw", { left: 72, top: 150, width: 920, height: 110 }, {
    fontSize: 82,
    bold: true,
  });
  addText(slide, "tagline", "RAG 기반 선박 정비 AI Agent", { left: 78, top: 278, width: 980, height: 46 }, {
    fontSize: 34,
    bold: true,
    color: "#3D8DFF",
  });
  addText(slide, "scope", "PDF Manual · Sensor Event · Wiki · Local LLM · FastAPI", { left: 80, top: 368, width: 980, height: 42 }, {
    fontSize: 26,
    color: "#343A46",
  });
  addRule(slide, 456, 80, 780, "#3D8DFF");
  addText(slide, "caption", "선박 정비 자료를 검색하고, 근거가 있는 답변을 제공합니다.", { left: 80, top: 496, width: 900, height: 46 }, {
    fontSize: 28,
  });
  addFooter(slide, "2분 시연 영상");
  setNotes(slide, "[Sources]\n- Project content: OceanClaw local workspace.\n\n[Video]\n0:00~0:05 제목 화면으로 사용.");
}

// 2. Architecture
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addSlideTitle(slide, "SYSTEM FLOW", "검색 근거 기반으로 답변을 생성합니다", "PDF, 센서 CSV, Wiki 문서를 먼저 검색하고 그 결과를 LLM context로 사용합니다.");
  const archBytes = await readImageBlob(ARCH);
  slide.images.add({
    blob: archBytes,
    contentType: "image/png",
    alt: "OceanClaw system architecture",
    fit: "contain",
    position: { left: 125, top: 342, width: 1030, height: 280 },
  });
  addFooter(slide);
  setNotes(slide, "[Sources]\n- Architecture image: docs/oceanclaw_architecture.png in OceanClaw workspace.\n\n[Video]\n0:05~0:15 구조 설명 카드.");
}

// 3. Search step
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addSlideTitle(slide, "DEMO 1", "매뉴얼에서 관련 페이지를 검색합니다", "질문을 embedding하고 FAISS index에서 유사한 manual chunk를 찾습니다.");
  addPanel(slide, "command-box", 90, 360, 1100, 92, "#111827");
  addText(slide, "command", 'python scripts\\search.py "engine oil level check dipstick MIN MAX" --top-k 3', { left: 122, top: 388, width: 1040, height: 40 }, {
    fontSize: 24,
    color: "#FFFFFF",
  });
  addText(slide, "result-key", "확인 포인트: page=69 · Check Oil Level in Engine · dipstick · MIN/MAX", { left: 96, top: 492, width: 1080, height: 44 }, {
    fontSize: 27,
    bold: true,
    color: "#000000",
  });
  addFooter(slide);
  setNotes(slide, "[Sources]\n- Command based on OceanClaw scripts/search.py.\n\n[Video]\n0:15~0:45 이 카드 뒤에 실제 터미널 검색 화면을 붙이기.");
}

// 4. Answer step
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addSlideTitle(slide, "DEMO 2", "검색된 근거로 한국어 답변을 생성합니다", "Ollama LLM은 검색 결과 context를 바탕으로 정비 절차와 출처를 함께 제공합니다.");
  addPanel(slide, "answer-box", 90, 344, 1100, 154, "#EDEDED");
  addText(slide, "answer-sample", "질문: 엔진 오일 점검 방법 알려줘\n답변: 엔진 정지 및 저온 상태에서 dipstick으로 MIN/MAX 범위를 확인합니다.\n출처: yanmar_6lf_operation_manual.pdf p.69", { left: 122, top: 370, width: 1036, height: 102 }, {
    fontSize: 25,
    color: "#000000",
  });
  addText(slide, "caption", "핵심 장면은 답변과 출처 페이지가 함께 보이는 화면입니다.", { left: 96, top: 528, width: 1080, height: 42 }, {
    fontSize: 26,
    bold: true,
    color: "#3D8DFF",
  });
  addFooter(slide);
  setNotes(slide, "[Sources]\n- Example answer/source derived from OceanClaw RAG test result.\n\n[Video]\n0:45~1:15 ask.py 실행 화면 또는 API 응답 화면을 붙이기.");
}

// 5. Wiki logs
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addSlideTitle(slide, "DEMO 3", "답변 결과를 Wiki logs에 저장합니다", "질문, 답변, 출처를 Markdown 파일로 남겨 정비 지식을 축적합니다.");
  addPanel(slide, "wiki-panel", 90, 350, 520, 176, "#EDEDED");
  addText(slide, "wiki-tree", "wiki/\n  logs/\n    2026-xx-xx_엔진_오일_점검.md", { left: 122, top: 382, width: 460, height: 96 }, {
    fontSize: 28,
    bold: true,
  });
  addPanel(slide, "md-panel", 650, 350, 540, 176, "#FFFFFF");
  addText(slide, "md-body", "# 질문\n엔진 오일 점검 방법 알려줘\n\n# 답변\n...\n\n# 출처\nmanual.pdf p.69", { left: 682, top: 374, width: 476, height: 124 }, {
    fontSize: 23,
  });
  addFooter(slide);
  setNotes(slide, "[Sources]\n- Wiki behavior based on OceanClaw wiki_log.py and wiki/logs structure.\n\n[Video]\n1:15~1:30 wiki/logs 폴더와 생성된 Markdown 파일을 보여주기.");
}

// 6. FastAPI
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addSlideTitle(slide, "SERVICE", "FastAPI 서버로 기능을 제공합니다", "CLI뿐 아니라 API endpoint로 검색과 답변 기능을 사용할 수 있습니다.");
  const endpoints = ["/health", "/ask", "/search/manual", "/search/sensor", "/search/wiki", "/mattermost/slash"];
  endpoints.forEach((ep, idx) => {
    const x = idx % 2 === 0 ? 130 : 680;
    const y = 350 + Math.floor(idx / 2) * 74;
    addPanel(slide, `ep-${idx}`, x, y, 470, 52, idx === 1 ? "#D0EDFA" : "#EDEDED");
    addText(slide, `ep-text-${idx}`, ep, { left: x + 24, top: y + 12, width: 420, height: 26 }, {
      fontSize: 24,
      bold: true,
      color: "#000000",
    });
  });
  addFooter(slide);
  setNotes(slide, "[Sources]\n- Endpoint list based on OceanClaw FastAPI implementation.\n\n[Video]\n1:30~1:45 브라우저에서 http://127.0.0.1:8000/docs 화면을 보여주기.");
}

// 7. Jetson and sensors
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addSlideTitle(slide, "EDGE AI", "Jetson 기반 로컬 정비 AI로 확장합니다", "인터넷 의존도를 낮추고 선박 내부망 또는 실습 환경에서 운용할 수 있는 구조입니다.");
  const sensorBytes = await readImageBlob(SENSOR);
  slide.images.add({
    blob: sensorBytes,
    contentType: "image/png",
    alt: "Future sensor integration",
    fit: "contain",
    position: { left: 118, top: 348, width: 1044, height: 182 },
  });
  addText(slide, "bottom", "향후 실제 온도·압력·진동 센서와 공공데이터 API 연계를 통해 예방정비 기능으로 확장할 수 있습니다.", { left: 92, top: 566, width: 1100, height: 42 }, {
    fontSize: 24,
  });
  addFooter(slide);
  setNotes(slide, "[Sources]\n- Sensor integration image: docs/future_sensor_integration_compact.png in OceanClaw workspace.\n\n[Video]\n1:45~1:55 Jetson 또는 향후 센서 연동 설명 카드.");
}

// 8. Closing
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addText(slide, "closing-title", "OceanClaw", { left: 72, top: 174, width: 900, height: 96 }, {
    fontSize: 72,
    bold: true,
  });
  addText(slide, "closing-message", "검색 가능한 정비 자료와 로컬 LLM을 연결해\n근거가 남는 선박 정비 AI Agent를 구현했습니다.", { left: 76, top: 300, width: 1040, height: 104 }, {
    fontSize: 34,
    color: "#000000",
  });
  addRule(slide, 456, 80, 760, "#3D8DFF");
  addText(slide, "closing-small", "Manual RAG · Sensor Search · Wiki Logs · FastAPI · Jetson Ready", { left: 80, top: 498, width: 1000, height: 38 }, {
    fontSize: 24,
    color: "#343A46",
  });
  addFooter(slide, "Demo complete");
  setNotes(slide, "[Sources]\n- Project feature summary: OceanClaw local workspace.\n\n[Video]\n1:55~2:00 마무리 화면.");
}

// 9. Editing checklist
{
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  addSlideTitle(slide, "CAPCUT GUIDE", "이 순서대로 붙이면 2분 시연 영상이 됩니다", "마지막 슬라이드는 제출 영상에 넣지 않아도 되는 편집용 체크리스트입니다.");
  const items = [
    "1. 제목 화면 5초",
    "2. 구조도 10초",
    "3. search.py 실제 실행 화면 25초",
    "4. ask.py 답변 + sources 화면 35초",
    "5. wiki/logs Markdown 저장 화면 15초",
    "6. FastAPI /docs 화면 15초",
    "7. Jetson 또는 확장 카드 10초",
  ];
  items.forEach((item, idx) => {
    addText(slide, `check-${idx}`, item, { left: 112, top: 342 + idx * 42, width: 900, height: 32 }, {
      fontSize: 24,
      color: idx === 3 ? "#3D8DFF" : "#000000",
      bold: idx === 3,
    });
  });
  addFooter(slide, "편집용 슬라이드");
  setNotes(slide, "[Sources]\n- Video sequence based on requested 2-minute demo format.\n\n[Video]\n이 슬라이드는 편집 참고용이며 제출 영상에서는 제외 가능.");
}

await fs.mkdir(path.dirname(OUT), { recursive: true });
await fs.mkdir(`${BUILD_DIR}/rendered`, { recursive: true });

for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await writeBlob(`${BUILD_DIR}/rendered/slide-${String(index + 1).padStart(2, "0")}.png`, png);
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${BUILD_DIR}/rendered/slide-${String(index + 1).padStart(2, "0")}.layout.json`, await layout.text(), "utf-8");
}

const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
await writeBlob(`${BUILD_DIR}/rendered/montage.webp`, montage);

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(OUT);
console.log(OUT);

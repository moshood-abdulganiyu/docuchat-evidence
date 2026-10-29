"use strict";

const API_BASE = ""; // change to "/api" if the deployed API sits under /api
const MAX_TURNS = 6;
const MAX_CONTENT = 2000;

const state = {
  mode: "demo",
  sessionId: sessionStorage.getItem("sid"),
  files: JSON.parse(sessionStorage.getItem("files") || "[]"),
  history: [],
  busy: false,
};

const $ = (id) => document.getElementById(id);
const thread = $("thread");
const questionEl = $("question");
const sendBtn = $("send");
const errorEl = $("error");

function showError(text) {
  errorEl.textContent = text || "";
  errorEl.hidden = !text;
}

async function readDetail(status, text) {
  try {
    const body = JSON.parse(text);
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch (_) { /* not JSON, for example a platform error page */ }
  if (status === 413) return "The file is too large for the server.";
  return `Request failed (HTTP ${status}).`;
}

/* ---------- mode toggle ---------- */
function setMode(mode) {
  state.mode = mode;
  $("mode-demo").classList.toggle("active", mode === "demo");
  $("mode-upload").classList.toggle("active", mode === "upload");
  $("upload-box").hidden = mode !== "upload";
  $("hint").textContent =
    mode === "demo"
      ? "Ask a question about the 30 demo arXiv papers. Every answer cites the file and page it used. If the papers do not contain the answer, the app says so."
      : "Upload up to 5 PDFs, then ask questions about them. Answers cite the file and page.";
  state.history = []; // history belongs to one source
  showError("");
}
$("mode-demo").addEventListener("click", () => setMode("demo"));
$("mode-upload").addEventListener("click", () => setMode("upload"));

/* ---------- upload ---------- */
function renderFiles() {
  const list = $("file-list");
  list.textContent = "";
  for (const name of state.files) {
    const li = document.createElement("li");
    li.textContent = name;
    list.appendChild(li);
  }
}

function uploadOne(file) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    if (state.sessionId) form.append("session_id", state.sessionId);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/upload`);
    const bar = $("progress");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) bar.value = Math.round((e.loaded / e.total) * 100);
    };
    xhr.onload = async () => {
      if (xhr.status === 200) return resolve(JSON.parse(xhr.responseText));
      reject(new Error(await readDetail(xhr.status, xhr.responseText)));
    };
    xhr.onerror = () => reject(new Error("Network error. Is the server running?"));
    xhr.send(form);
  });
}

$("file-input").addEventListener("change", async (e) => {
  const files = Array.from(e.target.files);
  e.target.value = "";
  const status = $("upload-status");
  const bar = $("progress");
  showError("");
  for (const file of files) {
    if (file.size > 4 * 1024 * 1024) {
      status.textContent = `${file.name}: larger than 4 MB, skipped.`;
      continue;
    }
    bar.hidden = false;
    bar.value = 0;
    status.textContent = `Uploading and indexing ${file.name}... (this can take a while)`;
    try {
      const res = await uploadOne(file);
      state.sessionId = res.session_id;
      sessionStorage.setItem("sid", state.sessionId);
      if (!state.files.includes(res.file)) state.files.push(res.file);
      sessionStorage.setItem("files", JSON.stringify(state.files));
      renderFiles();
      status.textContent = `${res.file}: ${res.pages} pages, ${res.chunks} chunks indexed.`;
    } catch (err) {
      status.textContent = "";
      showError(`${file.name}: ${err.message}`);
      break;
    }
  }
  bar.hidden = true;
});

/* ---------- chat ---------- */
function showSources(citations) {
  const list = $("sources-list");
  list.textContent = "";
  $("sources-empty").hidden = citations.length > 0;
  if (!citations.length) $("sources-empty").textContent = "This answer has no citations.";
  for (const c of citations) {
    const li = document.createElement("li");
    li.value = c.n;
    li.textContent = `${c.file}, page ${c.page}`;
    list.appendChild(li);
  }
}

function addMessage(role, text, extra) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  const body = document.createElement("div");
  body.textContent = text;
  div.appendChild(body);
  if (extra && extra.rewritten) {
    const s = document.createElement("div");
    s.className = "searched";
    s.textContent = `Searched as: ${extra.rewritten}`;
    div.appendChild(s);
  }
  if (role === "bot" && extra) {
    const meta = document.createElement("div");
    meta.className = "meta";
    const src = document.createElement("button");
    src.type = "button";
    src.textContent = "Sources";
    src.addEventListener("click", () => showSources(extra.citations || []));
    meta.appendChild(src);
    if ("speechSynthesis" in window) {
      const speak = document.createElement("button");
      speak.type = "button";
      speak.textContent = "Read aloud";
      speak.addEventListener("click", () => toggleSpeech(text, speak));
      meta.appendChild(speak);
    }
    div.appendChild(meta);
  }
  thread.appendChild(div);
  thread.scrollTop = thread.scrollHeight;
  return div;
}

async function send() {
  const question = questionEl.value.trim();
  if (!question || state.busy) return;
  if (state.mode === "upload" && !state.sessionId) {
    showError("Upload at least one PDF first.");
    return;
  }
  showError("");
  state.busy = true;
  sendBtn.disabled = true;
  $("hint").hidden = true;
  addMessage("user", question);
  questionEl.value = "";
  const pending = addMessage("bot", "Searching...");

  const body = {
    question,
    history: state.history.slice(-MAX_TURNS),
  };
  if (state.mode === "upload") body.session_id = state.sessionId;

  try {
    const res = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    if (!res.ok) throw new Error(await readDetail(res.status, text));
    const data = JSON.parse(text);
    pending.remove();
    addMessage("bot", data.answer, {
      citations: data.citations,
      rewritten: data.rewritten_question,
    });
    showSources(data.citations);
    state.history.push({ role: "user", content: question.slice(0, MAX_CONTENT) });
    state.history.push({ role: "assistant", content: data.answer.slice(0, MAX_CONTENT) });
    state.history = state.history.slice(-MAX_TURNS);
  } catch (err) {
    pending.remove();
    showError(err.message);
  } finally {
    state.busy = false;
    sendBtn.disabled = false;
    questionEl.focus();
  }
}

sendBtn.addEventListener("click", send);
questionEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});

/* ---------- voice ---------- */
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (Recognition) {
  const mic = $("mic");
  mic.hidden = false;
  let rec = null;
  mic.addEventListener("click", () => {
    if (rec) { rec.stop(); return; }
    rec = new Recognition();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.onresult = (e) => { questionEl.value = e.results[0][0].transcript.slice(0, 500); };
    rec.onerror = (e) => showError(`Microphone: ${e.error}`);
    rec.onend = () => { rec = null; mic.textContent = "Mic"; };
    mic.textContent = "Stop";
    rec.start();
  });
}

let speakingBtn = null;
function toggleSpeech(text, btn) {
  const synth = window.speechSynthesis;
  const wasThis = speakingBtn === btn;
  synth.cancel();
  if (speakingBtn) speakingBtn.textContent = "Read aloud";
  speakingBtn = null;
  if (wasThis) return;
  const u = new SpeechSynthesisUtterance(text);
  u.onend = u.onerror = () => { btn.textContent = "Read aloud"; speakingBtn = null; };
  btn.textContent = "Stop";
  speakingBtn = btn;
  synth.speak(u);
}

renderFiles();
setMode("demo");
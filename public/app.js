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

/* ---------- icons ---------- */
const ICON = {
  send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/></svg>',
  mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/><path d="M12 18v4"/></svg>',
  stop: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
  sources: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>',
  speak: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/></svg>',
};
const label = (icon, text) => `${icon}<span>${text}</span>`;

/* ---------- theme (light / dark) ---------- */
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try { localStorage.setItem("theme", theme); } catch (_) { /* storage blocked */ }
  const btn = $("theme-toggle");
  btn.innerHTML = theme === "dark" ? ICON.sun : ICON.moon;
  const next = theme === "dark" ? "light" : "dark";
  btn.setAttribute("aria-label", `Switch to ${next} mode`);
  btn.title = `Switch to ${next} mode`;
}
$("theme-toggle").addEventListener("click", () => {
  applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
});
applyTheme(document.documentElement.getAttribute("data-theme") || "light");
sendBtn.innerHTML = ICON.send;
$("mic").innerHTML = ICON.mic;

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
    li.dataset.n = c.n;
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
    src.innerHTML = label(ICON.sources, "Sources");
    src.addEventListener("click", () => showSources(extra.citations || []));
    meta.appendChild(src);
    if ("speechSynthesis" in window) {
      const speak = document.createElement("button");
      speak.type = "button";
      speak.innerHTML = label(ICON.speak, "Read aloud");
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
    rec.onend = () => { rec = null; mic.innerHTML = ICON.mic; mic.classList.remove("listening"); };
    mic.innerHTML = ICON.stop;
    mic.classList.add("listening");
    rec.start();
  });
}

let speakingBtn = null;
function toggleSpeech(text, btn) {
  const synth = window.speechSynthesis;
  const wasThis = speakingBtn === btn;
  synth.cancel();
  if (speakingBtn) speakingBtn.innerHTML = label(ICON.speak, "Read aloud");
  speakingBtn = null;
  if (wasThis) return;
  const u = new SpeechSynthesisUtterance(text);
  u.onend = u.onerror = () => { btn.innerHTML = label(ICON.speak, "Read aloud"); speakingBtn = null; };
  btn.innerHTML = label(ICON.stop, "Stop");
  speakingBtn = btn;
  synth.speak(u);
}

renderFiles();
setMode("demo");
const chatForm = document.getElementById("chatForm");
const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const sendIcon = document.getElementById("sendIcon");
const chatArea = document.getElementById("chatArea");

let isLoading = false;

// Auto-resize textarea
messageInput.addEventListener("input", function () {
  this.style.height = "auto";
  this.style.height = Math.min(this.scrollHeight, 200) + "px";
});

// Handle form submission
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = messageInput.value.trim();
  if (!question || isLoading) return;

  chatArea.style.display = "block"; // show chat area on first question
  addUserMessage(question);

  // Reset input
  setTimeout(() => {
    messageInput.value = "";
    messageInput.style.height = "auto";
  }, 100);

  // Show loading
  showLoading();

  try {
    const formData = new FormData();
    formData.append("question", question);

    const response = await fetch("/ask", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    hideLoading();

    if (data.ok) {
      addAssistantMessage(data.answer);
    } else {
      addErrorMessage(data.error || "An unexpected error occurred.");
    }
  } catch (error) {
    hideLoading();
    addErrorMessage("Failed to connect to the server.");
  }
});

function addUserMessage(message) {
  const div = document.createElement("div");
  div.className = "message user-message";
  div.textContent = message;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function addAssistantMessage(answer) {
  const div = document.createElement("div");
  div.className = "message assistant-message";

  const formattedAnswer = formatAnswer(answer);

  // Only add the answer (no sources)
  div.innerHTML = `<div>${formattedAnswer}</div>`;
  chatMessages.appendChild(div);
  scrollToBottom();

  // Re-render MathJax and Prism.js after adding answer
  if (window.MathJax) MathJax.typesetPromise();
  if (window.Prism) Prism.highlightAll();
}

function addErrorMessage(error) {
  const div = document.createElement("div");
  div.className = "message assistant-message";
  div.innerHTML = `<div style="color:#e53e3e;font-weight:600;"><strong>⚠️ Error:</strong> ${escapeHtml(
    error
  )}</div>`;
  chatMessages.appendChild(div);
  scrollToBottom();
}

function showLoading() {
  isLoading = true;
  sendButton.disabled = true;
  sendIcon.textContent = "⏳";

  const div = document.createElement("div");
  div.className = "message assistant-message";
  div.id = "loadingMessage";
  div.innerHTML =
    '<div class="loading">🔍 Researching and analyzing your question...</div>';
  chatMessages.appendChild(div);
  scrollToBottom();
}

function hideLoading() {
  isLoading = false;
  sendButton.disabled = false;
  sendIcon.textContent = "→";

  const loadingDiv = document.getElementById("loadingMessage");
  if (loadingDiv) loadingDiv.remove();
}

function formatAnswer(answer) {
  // Clean stray markdown citations like ([text](url))
  answer = answer.replace(/\([^\)]*\[.*?\]\(.*?\)\)/g, "");

  // Math formatting
  answer = answer.replace(/\$\$(.+?)\$\$/gs, "\\[$1\\]");
  answer = answer.replace(/\$(.+?)\$/g, "\\($1\\)");

  let formatted = answer
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/^---$/gm, "<hr>")
    // Code blocks
    .replace(/```(\w+)?\n([\s\S]*?)```/g, (m, lang, code) => {
      return `<pre><code class="language-${lang || "plaintext"}">${escapeHtml(
        code
      )}</code></pre>`;
    });

  // ✅ Fixed Markdown Table Formatting
  formatted = formatted.replace(
    /\|(.+)\|\r?\n\|([-\s|:]+)\|\r?\n((?:\|.+\|\r?\n?)*)/g,
    (match, header, divider, body) => {
      const headers = header
        .split("|")
        .map((h) => `<th>${h.trim()}</th>`)
        .join("");

      const rows = body
        .trim()
        .split(/\r?\n/)
        .filter((row) => row.trim())
        .map((row) => {
          const cells = row
            .split("|")
            .map((c) => `<td>${c.trim()}</td>`)
            .join("");
          return `<tr>${cells}</tr>`;
        })
        .join("");

      return `<table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table>`;
    }
  );

  // ✅ Mixed Nested List Handling
  formatted = formatted.replace(
    /((?:^|\n)(?:\s*(?:[-*]|\d+\.)\s.+\n?)+)/g,
    (match) => {
      const lines = match.trim().split(/\n/);

      let result = "";
      let stack = [];

      lines.forEach((line) => {
        const indent = line.match(/^\s*/)[0].length;
        const isOrdered = /^\s*\d+\./.test(line);
        const tag = isOrdered ? "ol" : "ul";
        const content = line.replace(/^(\s*(?:[-*]|\d+\.)\s+)/, "").trim();

        // Close deeper or mismatched lists
        while (
          stack.length &&
          (stack[stack.length - 1].indent > indent ||
            stack[stack.length - 1].tag !== tag)
        ) {
          result += `</${stack[stack.length - 1].tag}>`;
          stack.pop();
        }

        // Open new list if indent increases or type changes
        if (
          !stack.length ||
          indent > stack[stack.length - 1].indent ||
          stack[stack.length - 1].tag !== tag
        ) {
          result += `<${tag}>`;
          stack.push({ indent, tag });
        }

        result += `<li>${content}</li>`;
      });

      // Close remaining open lists
      while (stack.length) {
        result += `</${stack[stack.length - 1].tag}>`;
        stack.pop();
      }

      return result;
    }
  );

  // Convert plain text to paragraphs
  return formatted
    .split(/\r?\n\r?\n/)
    .map((p) => {
      p = p.trim();
      if (!p) return "";
      if (
        p.startsWith("<") ||
        p.includes("<table>") ||
        p.includes("<h") ||
        p.includes("<hr") ||
        p.includes("<pre>") ||
        p.includes("<ul>") ||
        p.includes("<ol>")
      )
        return p;
      return `<p>${p}</p>`;
    })
    .filter((p) => p)
    .join("");
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

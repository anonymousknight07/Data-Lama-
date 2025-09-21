// const chatForm = document.getElementById("chatForm");
// const chatMessages = document.getElementById("chatMessages");
// const messageInput = document.getElementById("messageInput");
// const sendButton = document.getElementById("sendButton");
// const sendIcon = document.getElementById("sendIcon");

// let isLoading = false;

// // Auto-resize textarea
// messageInput.addEventListener("input", function () {
//   this.style.height = "auto";
//   this.style.height = Math.min(this.scrollHeight, 200) + "px";
// });

// // Handle form submission
// chatForm.addEventListener("submit", async (e) => {
//   e.preventDefault();
//   const question = messageInput.value.trim();
//   if (!question || isLoading) return;

//   addUserMessage(question);

//   // Reset input
//   messageInput.value = "";
//   messageInput.style.height = "auto";

//   // Show loading
//   showLoading();

//   try {
//     const formData = new FormData();
//     formData.append("question", question);

//     const response = await fetch("/ask", {
//       method: "POST",
//       body: formData,
//     });

//     const data = await response.json();
//     hideLoading();

//     if (data.ok) {
//       addAssistantMessage(data.answer, data.citations);
//     } else {
//       addErrorMessage(data.error || "An unexpected error occurred.");
//     }
//   } catch (error) {
//     hideLoading();
//     addErrorMessage("Failed to connect to the server.");
//   }
// });

// function addUserMessage(message) {
//   const div = document.createElement("div");
//   div.className = "message message-user";
//   div.textContent = message;
//   chatMessages.appendChild(div);
//   scrollToBottom();
// }

// function addAssistantMessage(answer, citations) {
//   const div = document.createElement("div");
//   div.className = "message message-assistant";

//   const formattedAnswer = formatAnswer(answer);
//   const sourcesHtml = formatSources(citations);

//   div.innerHTML = `<div>${formattedAnswer}</div>${sourcesHtml}`;
//   chatMessages.appendChild(div);
//   scrollToBottom();
// }

// function addErrorMessage(error) {
//   const div = document.createElement("div");
//   div.className = "message message-assistant";
//   div.innerHTML = `<div style="color:red"><strong>Error:</strong> ${escapeHtml(error)}</div>`;
//   chatMessages.appendChild(div);
//   scrollToBottom();
// }

// function showLoading() {
//   isLoading = true;
//   sendButton.disabled = true;
//   sendIcon.textContent = "⏳";

//   const div = document.createElement("div");
//   div.className = "message message-assistant";
//   div.id = "loadingMessage";
//   div.textContent = "Researching and analyzing...";
//   chatMessages.appendChild(div);
//   scrollToBottom();
// }

// function hideLoading() {
//   isLoading = false;
//   sendButton.disabled = false;
//   sendIcon.textContent = "↑";

//   const loadingDiv = document.getElementById("loadingMessage");
//   if (loadingDiv) loadingDiv.remove();
// }

// function formatAnswer(answer) {
//   return answer
//     .split("\n\n")
//     .map((p) => `<p>${escapeHtml(p)}</p>`)
//     .join("");
// }

// function formatSources(citations) {
//   if (!citations || citations.length === 0) return "";
//   const items = citations
//     .map((c) => {
//       const match = c.match(/^\[(\d+)\]\s*(.+?)\s*—\s*(.+)$/);
//       if (match) {
//         const [, number, title, url] = match;
//         return `<div class="source-item"><strong>[${number}]</strong> ${escapeHtml(
//           title.trim()
//         )} — <a href="${escapeHtml(
//           url.trim()
//         )}" target="_blank" rel="noopener">${escapeHtml(url.trim())}</a></div>`;
//       }
//       return `<div class="source-item">${escapeHtml(c)}</div>`;
//     })
//     .join("");
//   return `<div class="sources-section"><div class="sources-title">Sources</div>${items}</div>`;
// }

// function scrollToBottom() {
//   chatMessages.scrollTop = chatMessages.scrollHeight;
// }

// function escapeHtml(text) {
//   const div = document.createElement("div");
//   div.textContent = text;
//   return div.innerHTML;
// }

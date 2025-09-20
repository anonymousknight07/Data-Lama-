const form = document.getElementById("qform");
const result = document.getElementById("result");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = document.getElementById("question").value;

  result.innerText = "Thinking...";

  const fd = new FormData();
  fd.append("question", q);

  try {
    const resp = await fetch("/ask", {
      method: "POST",
      body: fd,
    });

    const j = await resp.json();

    if (!j.ok) {
      result.innerText = "Error: " + (j.error || "Unknown");
      return;
    }

    
    result.innerHTML = `
            <h3>Answer:</h3>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; white-space: pre-wrap; font-family: Arial, sans-serif; line-height: 1.5;">${
              j.answer
            }</div>
            <h3>Sources:</h3>
            <ul style="margin: 10px 0; padding-left: 20px;">
                ${j.citations
                  .map((c) => `<li style="margin: 5px 0;">${c}</li>`)
                  .join("")}
            </ul>
        `;
  } catch (error) {
    result.innerText =
      "Error: Failed to get response. Check console for details.";
    console.error("Request failed:", error);
  }
});

const API_BASE_URL = "REPLACE_WITH_API_ENDPOINT";

const button = document.getElementById("analyzeButton");
const textarea = document.getElementById("resumeText");
const result = document.getElementById("result");

button.addEventListener("click", async () => {
  result.textContent = "Analyzing...";

  try {
    const response = await fetch(`${API_BASE_URL}/analyze-resume`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        resumeText: textarea.value
      })
    });

    const data = await response.json();
    result.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    result.textContent = `Error: ${error.message}`;
  }
});

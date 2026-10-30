const API_BASE = "http://localhost:8000";
const form = document.getElementById("start-form");
const activePanel = document.getElementById("active-panel");
const message = document.getElementById("message");
const startButton = document.getElementById("start");

function send(messageData) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(messageData, (response) => {
      if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
      else resolve(response);
    });
  });
}

async function getActiveStatus() {
  const status = await send({ type: "getMonitoringStatus" });
  if (status?.active) {
    form.hidden = true;
    document.getElementById("disclosure").hidden = true;
    activePanel.hidden = false;
    document.getElementById("session-label").textContent = `Session ${status.interviewId}`;
  } else {
    form.hidden = false;
    document.getElementById("disclosure").hidden = false;
    activePanel.hidden = true;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "";
  startButton.disabled = true;
  const interviewId = Number(document.getElementById("interview-id").value);
  const token = document.getElementById("token").value.trim();

  try {
    const response = await fetch(`${API_BASE}/interviews/${interviewId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error("Could not authorize this interview. Check the ID and signed-in token.");
    const interview = await response.json();
    if (!["scheduled", "active", "in_progress"].includes(interview.status)) {
      throw new Error("This interview is no longer available for monitoring.");
    }

    const consentResponse = await fetch(`${API_BASE}/interviews/${interviewId}/consent`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ candidate_consent: true }),
    });
    if (!consentResponse.ok) throw new Error("Consent could not be recorded for this account.");

    const started = await send({
      type: "startInterviewMonitoring",
      interviewId,
      token,
      allowlist: interview.allowlist || [],
    });
    if (!started?.ok) throw new Error("The extension could not start monitoring.");
    await getActiveStatus();
    message.textContent = "Monitoring started for this interview session.";
  } catch (error) {
    message.textContent = error.message || "Unable to start monitoring.";
  } finally {
    startButton.disabled = false;
  }
});

document.getElementById("stop").addEventListener("click", async () => {
  message.textContent = "";
  try {
    const { extension_session: session } = await new Promise((resolve) => chrome.storage.local.get("extension_session", resolve));
    if (session?.interviewId && session?.token) {
      const response = await fetch(`${API_BASE}/interviews/${session.interviewId}/consent`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({ candidate_consent: false }),
      });
      if (!response.ok) throw new Error("Consent withdrawal could not be recorded. Monitoring remains active until you retry.");
    }
    await send({ type: "stopInterviewMonitoring" });
    await getActiveStatus();
    message.textContent = "Monitoring stopped and consent withdrawn.";
  } catch (error) {
    message.textContent = error.message || "Unable to stop monitoring.";
  }
});

getActiveStatus().catch((error) => {
  message.textContent = error.message || "Unable to read monitoring status.";
});

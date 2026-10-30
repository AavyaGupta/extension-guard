const API_BASE = "http://localhost:8000";
const DEFAULT_AI_DOMAINS = [
  "chatgpt.com",
  "openai.com",
  "deepseek.com",
  "claude.ai",
  "gemini.google.com",
  "copilot.microsoft.com",
];

const SESSION_KEY = "extension_session";

function readStorage(keys) {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
}

function sendRuntimeMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, () => resolve());
  });
}

async function getSessionState() {
  const { [SESSION_KEY]: session } = await readStorage([SESSION_KEY]);
  return session?.active && session.interviewId && session.token ? session : null;
}

function normalizedHostname(url) {
  try {
    return new URL(url).hostname.toLowerCase().replace(/^\[|\]$/g, "");
  } catch {
    return "";
  }
}

function isPrivateIPv4(hostname) {
  const octets = hostname.split(".").map(Number);
  if (octets.length !== 4 || octets.some((value) => !Number.isInteger(value) || value < 0 || value > 255)) {
    return false;
  }
  return octets[0] === 127
    || octets[0] === 10
    || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31)
    || (octets[0] === 192 && octets[1] === 168);
}

function isLocalDevelopmentUrl(url) {
  const hostname = normalizedHostname(url);
  return hostname === "localhost"
    || hostname.endsWith(".localhost")
    || hostname === "0.0.0.0"
    || hostname === "::1"
    || hostname.startsWith("fc")
    || hostname.startsWith("fd")
    || hostname.startsWith("fe80:")
    || isPrivateIPv4(hostname);
}

function matchesDomain(url, domains = []) {
  const hostname = normalizedHostname(url);
  return domains.some((entry) => {
    const domain = String(entry).trim().toLowerCase().replace(/^\*\./, "");
    return domain && (hostname === domain || hostname.endsWith(`.${domain}`));
  });
}

async function sendEvent(session, eventType, details, payload = {}) {
  try {
    const response = await fetch(`${API_BASE}/interviews/${session.interviewId}/browser-events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.token}`,
      },
      body: JSON.stringify({ event_type: eventType, details, ...payload }),
    });
    if (response.status === 400 || response.status === 403 || response.status === 404) {
      await stopMonitoring(false);
    }
  } catch (error) {
    console.error("ExtensionGuard event error:", error);
  }
}

async function processNavigation(details) {
  if (details.frameId !== 0) return;
  const session = await getSessionState();
  if (!session) return;

  const url = details.url;
  if (matchesDomain(url, session.allowlist)) return;

  if (isLocalDevelopmentUrl(url)) {
    const hostname = normalizedHostname(url);
    const eventType = hostname === "localhost" || hostname.endsWith(".localhost") || hostname === "0.0.0.0"
      ? "LOCALHOST_ACCESS"
      : "LOCAL_IP_ACCESS";
    await sendEvent(session, eventType, "Candidate navigated to a local development address.", {
      url,
      tab_id: details.tabId,
    });
  }

  if (matchesDomain(url, session.aiDomains || DEFAULT_AI_DOMAINS)) {
    await sendEvent(session, "AI_WEBSITE_ACCESS", "Candidate navigated to a configured AI assistance domain.", {
      url,
      tab_id: details.tabId,
    });
  }
}

async function setDeviceConnection(session, connected) {
  try {
    await fetch(`${API_BASE}/interviews/${session.interviewId}/device-status`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.token}`,
      },
      body: JSON.stringify({ device_type: "browser_extension", connected }),
    });
  } catch (error) {
    console.error("ExtensionGuard connection update failed:", error);
  }
}

async function stopMonitoring(reportDisconnect = true) {
  const session = await getSessionState();
  await chrome.alarms.clear("interview-session-check");
  if (session && reportDisconnect) await setDeviceConnection(session, false);
  await chrome.storage.local.remove(SESSION_KEY);
}

chrome.tabs.onCreated.addListener(async (tab) => {
  const session = await getSessionState();
  if (session) {
    await sendEvent(session, "TAB_SWITCH", "A new browser tab was opened during the interview.", {
      tab_id: tab.id,
    });
  }
});

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const session = await getSessionState();
  if (session) {
    await sendEvent(session, "TAB_SWITCH", "Candidate switched to another browser tab.", { tab_id: tabId });
  }
});

chrome.windows.onFocusChanged.addListener(async (windowId) => {
  const session = await getSessionState();
  if (!session) return;
  const eventType = windowId === chrome.windows.WINDOW_ID_NONE ? "BROWSER_FOCUS_LOST" : "WINDOW_BLUR";
  await sendEvent(session, eventType, "Browser window focus changed.", { tab_id: windowId });
});

chrome.webNavigation.onCommitted.addListener(processNavigation);

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "interview-session-check") return;
  const session = await getSessionState();
  if (!session) return;

  try {
    const response = await fetch(`${API_BASE}/interviews/${session.interviewId}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    });
    if (!response.ok) {
      await stopMonitoring(false);
      return;
    }
    const interview = await response.json();
    if (!["active", "in_progress"].includes(interview.status) || !interview.candidate_consent) {
      await stopMonitoring(false);
    }
  } catch (error) {
    console.error("ExtensionGuard session check failed:", error);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "startInterviewMonitoring") {
    const session = {
      interviewId: Number(message.interviewId),
      token: message.token,
      allowlist: Array.isArray(message.allowlist) ? message.allowlist : [],
      aiDomains: Array.isArray(message.aiDomains) ? message.aiDomains : DEFAULT_AI_DOMAINS,
      active: true,
    };
    chrome.storage.local.set({ [SESSION_KEY]: session }, async () => {
      await setDeviceConnection(session, true);
      chrome.alarms.create("interview-session-check", { periodInMinutes: 1 });
      sendResponse({ ok: true });
    });
    return true;
  }

  if (message?.type === "stopInterviewMonitoring") {
    stopMonitoring().then(() => sendResponse({ ok: true }));
    return true;
  }

  if (message?.type === "getMonitoringStatus") {
    getSessionState().then((session) => sendResponse({ active: Boolean(session), interviewId: session?.interviewId }));
    return true;
  }

  sendResponse({ ok: false });
  return false;
});
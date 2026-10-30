import { useEffect, useState } from "react";
import { apiCall } from "../utils/api";

function InterviewDashboard() {
  const [interviews, setInterviews] = useState([]);
  const [reports, setReports] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [candidateEmail, setCandidateEmail] = useState("");
  const [interviewType, setInterviewType] = useState("technical");

  async function loadInterviews() {
    try {
      const data = await apiCall("/interviews", "GET");
      setInterviews(data);
      const reportPairs = await Promise.all(data.map(async (session) => {
        try {
          return [session.id, await apiCall(`/interviews/${session.id}/report`, "GET")];
        } catch {
          return [session.id, null];
        }
      }));
      setReports(Object.fromEntries(reportPairs));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadInterviews();
    const timer = window.setInterval(loadInterviews, 15000);
    return () => window.clearInterval(timer);
  }, []);

  async function endInterview(sessionId) {
    try {
      await apiCall(`/interviews/${sessionId}/status`, "POST", { status: "completed" });
      await loadInterviews();
    } catch (err) {
      setError(err.message);
    }
  }

  async function createInterview(e) {
    e.preventDefault();
    try {
      await apiCall("/interviews", "POST", {
        candidate_name: candidateName,
        candidate_email: candidateEmail,
        interview_type: interviewType,
        allowlist: ["https://docs.example.com"],
        status: "scheduled",
        started_at: new Date().toISOString(),
        ends_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
      });
      setCandidateName("");
      setCandidateEmail("");
      await loadInterviews();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <header style={styles.header}>
          <div>
            <div style={styles.eyebrow}>RECRUITER OPERATIONS</div>
            <h1 style={styles.title}>Interview Integrity Dashboard</h1>
          </div>
          <div style={styles.statusPill}>Monitoring ready</div>
        </header>

        <form onSubmit={createInterview} style={styles.formCard}>
          <h3 style={styles.formTitle}>Create interview</h3>
          <div style={styles.fieldRow}>
            <input
              value={candidateName}
              onChange={(e) => setCandidateName(e.target.value)}
              placeholder="Candidate name"
              style={styles.input}
            />
            <input
              value={candidateEmail}
              onChange={(e) => setCandidateEmail(e.target.value)}
              placeholder="Candidate email"
              style={styles.input}
            />
          </div>
          <div style={styles.fieldRow}>
            <select value={interviewType} onChange={(e) => setInterviewType(e.target.value)} style={styles.select}>
              <option value="technical">Technical</option>
              <option value="hr">HR</option>
              <option value="mixed">Mixed</option>
            </select>
            <button type="submit" style={styles.primaryBtn}>Start session</button>
          </div>
        </form>

        {error && <div style={styles.errorBox}>{error}</div>}
        {loading ? <div style={styles.loading}>Loading interviews...</div> : null}

        <div style={styles.grid}>
          {interviews.map((session) => (
            <div key={session.id} style={styles.card}>
              {(() => {
                const report = reports[session.id];
                const risk = report?.risk;
                const events = report?.events || [];
                const elapsedMs = session.started_at
                  ? new Date(session.ends_at || Date.now()).getTime() - new Date(session.started_at).getTime()
                  : 0;
                return (
                  <>
              <div style={styles.cardHeader}>
                <div>
                  <div style={styles.sessionType}>{session.interview_type}</div>
                  <h3 style={styles.sessionName}>{session.candidate_name}</h3>
                </div>
                <span style={styles.badge}>{session.status}</span>
              </div>

              <p style={styles.meta}>{session.candidate_email}</p>
              <p style={styles.meta}>Consent: {session.candidate_consent ? "Granted" : "Pending"}</p>
              <p style={styles.meta}>Allowlisted: {Array.isArray(session.allowlist) ? session.allowlist.join(", ") || "None" : "None"}</p>
              <p style={styles.meta}>Duration: {Math.max(0, Math.floor(elapsedMs / 60000))} min · Events: {events.length}</p>
              <p style={styles.meta}>Concern: <strong style={styles[`risk_${risk?.level || "low"}`]}>{risk?.level || "low"}</strong> · Score: {risk?.score ?? 0}</p>

              <div style={styles.footer}>
                <span>Browser: {report?.connection_status?.browser_extension ? "connected" : "disconnected"}</span>
                <span>Desktop: {report?.connection_status?.desktop_companion ? "connected" : "disconnected"}</span>
              </div>
              {risk?.reasons?.length > 0 && (
                <div style={styles.reasons}>
                  <strong>Correlated indicators for recruiter review</strong>
                  {risk.reasons.map((reason, index) => <p key={`${session.id}-reason-${index}`}>{reason}</p>)}
                </div>
              )}
              <div style={styles.timeline}>
                <strong>Event timeline</strong>
                {events.slice(-6).reverse().map((event) => (
                  <div key={event.id} style={styles.eventRow}>
                    <span>{new Date(event.created_at).toLocaleTimeString()}</span>
                    <span>{event.event_type}</span>
                    <span>{event.app_name || event.url || event.details || event.source}</span>
                  </div>
                ))}
                {events.length === 0 && <p style={styles.meta}>No monitoring events recorded.</p>}
              </div>
              {!["completed", "cancelled"].includes(session.status) && (
                <button onClick={() => endInterview(session.id)} style={styles.endBtn}>End interview</button>
              )}
                  </>
                );
              })()}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#0f172a", color: "#e2e8f0", padding: "32px 18px" },
  container: { maxWidth: "1100px", margin: "0 auto" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" },
  eyebrow: { fontSize: "12px", letterSpacing: "2px", color: "#67e8f9", marginBottom: "8px" },
  title: { margin: 0, fontSize: "32px" },
  statusPill: { border: "1px solid #1d4ed8", background: "rgba(59,130,246,0.15)", color: "#bfdbfe", padding: "8px 12px", borderRadius: "999px" },
  formCard: { background: "#111827", border: "1px solid #1f2937", borderRadius: "16px", padding: "16px", marginBottom: "20px" },
  formTitle: { marginTop: 0 },
  fieldRow: { display: "flex", gap: "12px", marginTop: "12px", flexWrap: "wrap" },
  input: { flex: 1, minWidth: "220px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", padding: "12px 14px", borderRadius: "10px" },
  select: { flex: 1, minWidth: "180px", background: "#0f172a", border: "1px solid #334155", color: "#f8fafc", padding: "12px 14px", borderRadius: "10px" },
  primaryBtn: { background: "#22c55e", color: "#06211a", border: "none", borderRadius: "10px", padding: "12px 18px", fontWeight: 700, cursor: "pointer" },
  errorBox: { background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.35)", color: "#fecaca", padding: "10px 12px", borderRadius: "10px", marginBottom: "12px" },
  loading: { padding: "14px", color: "#cbd5e1" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" },
  card: { background: "#111827", border: "1px solid #1f2937", borderRadius: "16px", padding: "18px" },
  cardHeader: { display: "flex", justifyContent: "space-between", alignItems: "center", gap: "10px" },
  sessionType: { color: "#67e8f9", textTransform: "uppercase", fontSize: "11px", letterSpacing: "1px" },
  sessionName: { margin: "6px 0 0 0", fontSize: "24px" },
  badge: { background: "#1e293b", border: "1px solid #334155", color: "#cbd5e1", borderRadius: "999px", padding: "6px 10px", fontSize: "12px" },
  meta: { color: "#cbd5e1", margin: "8px 0" },
  footer: { display: "flex", justifyContent: "space-between", marginTop: "14px", color: "#93c5fd", fontSize: "13px" },
  risk_low: { color: "#86efac", textTransform: "capitalize" },
  risk_medium: { color: "#facc15", textTransform: "capitalize" },
  risk_high: { color: "#f87171", textTransform: "capitalize" },
  reasons: { marginTop: "14px", borderTop: "1px solid #334155", paddingTop: "12px", color: "#fbbf24", fontSize: "13px" },
  timeline: { marginTop: "14px", borderTop: "1px solid #334155", paddingTop: "12px", fontSize: "13px" },
  eventRow: { display: "grid", gridTemplateColumns: "66px 1fr 1.5fr", gap: "8px", padding: "6px 0", borderBottom: "1px solid #1f2937", color: "#cbd5e1", overflowWrap: "anywhere" },
  endBtn: { marginTop: "14px", padding: "8px 12px", border: "1px solid #b4533c", borderRadius: "6px", background: "#3a1c1b", color: "#fecaca", cursor: "pointer" },
};

export default InterviewDashboard;

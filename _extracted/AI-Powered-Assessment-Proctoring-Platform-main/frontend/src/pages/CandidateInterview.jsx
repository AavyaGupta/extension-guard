import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiCall } from "../utils/api";

function CandidateInterview() {
  const { interviewId } = useParams();
  const [interview, setInterview] = useState(null);
  const [consentChecked, setConsentChecked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function loadInterview() {
    try {
      setInterview(await apiCall(`/interviews/${interviewId}`, "GET"));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadInterview();
  }, [interviewId]);

  async function recordConsent(consented) {
    setSaving(true);
    setError("");
    try {
      setInterview(await apiCall(`/interviews/${interviewId}/consent`, "POST", {
        candidate_consent: consented,
        required_components: ["browser_extension", "desktop_companion"],
      }));
      setConsentChecked(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const active = interview && ["active", "in_progress"].includes(interview.status);
  const ended = interview && ["completed", "cancelled"].includes(interview.status);

  return (
    <main style={styles.page}>
      <section style={styles.panel}>
        <p style={styles.eyebrow}>EXTENSIONGUARD · CANDIDATE SESSION</p>
        <h1 style={styles.title}>Interview monitoring</h1>
        {loading && <p>Loading interview details...</p>}
        {error && <p role="alert" style={styles.error}>{error}</p>}
        {interview && (
          <>
            <dl style={styles.details}>
              <div style={styles.detailItem}><dt style={styles.detailLabel}>Candidate</dt><dd style={styles.detailValue}>{interview.candidate_name}</dd></div>
              <div style={styles.detailItem}><dt style={styles.detailLabel}>Interview type</dt><dd style={styles.detailValue}>{interview.interview_type}</dd></div>
              <div style={styles.detailItem}><dt style={styles.detailLabel}>Session</dt><dd style={styles.detailValue}>#{interview.id}</dd></div>
              <div style={styles.detailItem}><dt style={styles.detailLabel}>Status</dt><dd style={styles.detailValue}>{interview.status}</dd></div>
            </dl>

            <section style={styles.disclosure}>
              <h2>What monitoring collects</h2>
              <p>The browser extension can record tab and focus changes, configured AI-site visits, and local or private network addresses. The desktop companion records foreground application and process names and application switches.</p>
              <p>Neither tool records keystrokes, screen contents, personal files, or browsing activity outside this interview. Monitoring is visible and can be stopped by withdrawing consent.</p>
            </section>

            {ended ? (
              <p style={styles.notice}>This interview has ended. Monitoring should be stopped in the extension and desktop companion.</p>
            ) : active ? (
              <>
                <p style={styles.notice}>Consent is recorded. Start the browser extension and desktop companion for session #{interview.id}; each will verify this interview before monitoring.</p>
                <button disabled={saving} onClick={() => recordConsent(false)} style={styles.stopButton}>
                  Withdraw consent and stop monitoring
                </button>
              </>
            ) : (
              <>
                <label style={styles.consent}>
                  <input
                    type="checkbox"
                    checked={consentChecked}
                    onChange={(event) => setConsentChecked(event.target.checked)}
                  />
                  I have reviewed the disclosure and consent to monitoring for this interview.
                </label>
                <button
                  disabled={!consentChecked || saving}
                  onClick={() => recordConsent(true)}
                  style={styles.startButton}
                >
                  {saving ? "Recording consent..." : "Consent and continue"}
                </button>
              </>
            )}
          </>
        )}
      </section>
    </main>
  );
}

const styles = {
  page: { minHeight: "100vh", background: "#edf2f0", color: "#172b2a", padding: "40px 18px", fontFamily: "'Segoe UI', sans-serif" },
  panel: { maxWidth: "720px", margin: "0 auto", background: "#fff", border: "1px solid #cbd8d4", borderRadius: "8px", padding: "28px" },
  eyebrow: { color: "#087e73", fontSize: "12px", fontWeight: 700 },
  title: { margin: "8px 0 24px", fontSize: "28px" },
  details: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px", margin: "0 0 24px" },
  detailItem: { padding: "12px", background: "#f4f7f6", borderRadius: "6px" },
  detailLabel: { color: "#526562", fontSize: "12px" },
  detailValue: { margin: "4px 0 0", fontWeight: 600, overflowWrap: "anywhere" },
  disclosure: { borderTop: "1px solid #dce5e2", borderBottom: "1px solid #dce5e2", padding: "14px 0", lineHeight: 1.55 },
  consent: { display: "flex", gap: "10px", alignItems: "flex-start", margin: "20px 0", lineHeight: 1.45 },
  startButton: { background: "#087e73", color: "white", border: 0, borderRadius: "6px", padding: "12px 16px", fontWeight: 700, cursor: "pointer" },
  stopButton: { background: "#fff", color: "#9b3028", border: "1px solid #9b3028", borderRadius: "6px", padding: "10px 14px", cursor: "pointer" },
  notice: { background: "#eef6f4", borderLeft: "3px solid #087e73", padding: "12px", lineHeight: 1.5 },
  error: { color: "#9b3028" },
};

export default CandidateInterview;
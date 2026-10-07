import { useEffect, useState } from "react";
import { listJobs, startRun, type Job } from "./api";

export function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listJobs().then(setJobs, (e: Error) => setError(e.message));
  }, []);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      await startRun();
      setJobs(await listJobs());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <main>
      <header>
        <h1>Job Tracker</h1>
        <button onClick={run} disabled={running}>
          {running ? "Running…" : "Run"}
        </button>
      </header>
      {error && <p className="error">{error}</p>}
      {jobs.length === 0 ? (
        <p className="empty">No jobs yet. Click Run to fetch postings.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Company</th>
              <th>Location</th>
              <th>Posting</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>{job.title}</td>
                <td>{job.company}</td>
                <td>{job.locations.join(", ") || "—"}</td>
                <td>
                  <a href={job.posting_url} target="_blank" rel="noreferrer">
                    Open
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}

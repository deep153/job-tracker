import { useEffect, useState, type ReactNode } from "react";
import { getStatus, type SystemStatus } from "./api";
import { AlertIcon } from "./icons";

export type Page = "jobs" | "resume" | "settings";

const PAGES: { id: Page; label: string; href: string }[] = [
  { id: "jobs", label: "Jobs", href: "#/" },
  { id: "resume", label: "Resume", href: "#/resume" },
  { id: "settings", label: "Settings", href: "#/settings" },
];

// Checked once per page load: LibreOffice is detected when the backend starts.
let status: Promise<SystemStatus> | null = null;

export function Topbar({ page, children }: { page: Page; children?: ReactNode }) {
  const [missing, setMissing] = useState<string | null>(null);

  useEffect(() => {
    status ??= getStatus();
    status.then(
      ({ libreoffice }) => setMissing(libreoffice.available ? null : libreoffice.message),
      () => {
        status = null;
      },
    );
  }, []);

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="topbar-start">
            <div className="brand">
              <span className="brand-mark" aria-hidden="true">
                JT
              </span>
              <span className="brand-name">Job Tracker</span>
            </div>
            <nav className="nav" aria-label="Pages">
              {PAGES.map((p) => (
                <a key={p.id} href={p.href} className="nav-link" aria-current={p.id === page ? "page" : undefined}>
                  {p.label}
                </a>
              ))}
            </nav>
          </div>
          {children}
        </div>
      </header>
      {missing && (
        <div className="system-notice" role="alert">
          <div className="system-notice-inner">
            <AlertIcon />
            <span>{missing}</span>
          </div>
        </div>
      )}
    </>
  );
}

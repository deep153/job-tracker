import { useEffect, useState } from "react";
import type { Page } from "./components/Topbar";
import { Dashboard } from "./pages/Dashboard";
import { ResumePage } from "./pages/ResumePage";
import { SettingsPage } from "./pages/SettingsPage";

function pageFromHash(): Page {
  if (window.location.hash === "#/resume") return "resume";
  if (window.location.hash === "#/settings") return "settings";
  return "jobs";
}

export function App() {
  const [page, setPage] = useState(pageFromHash);

  useEffect(() => {
    const onChange = () => {
      setPage(pageFromHash());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  if (page === "resume") return <ResumePage />;
  if (page === "settings") return <SettingsPage />;
  return <Dashboard />;
}

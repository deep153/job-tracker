import { useEffect, useState } from "react";
import { Dashboard } from "./Dashboard";
import { ResumePage } from "./ResumePage";
import type { Page } from "./Topbar";

function pageFromHash(): Page {
  return window.location.hash === "#/resume" ? "resume" : "jobs";
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

  return page === "resume" ? <ResumePage /> : <Dashboard />;
}

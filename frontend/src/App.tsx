import { useEffect, useState } from "react";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { Dashboard } from "./pages/Dashboard";
import { ResumePage } from "./pages/ResumePage";
import { ReviewPage } from "./pages/ReviewPage";
import { SettingsPage } from "./pages/SettingsPage";

type Route = { page: "jobs" | "applications" | "resume" | "settings" } | { page: "review"; applicationId: number };

function routeFromHash(): Route {
  const hash = window.location.hash;
  if (hash === "#/applications") return { page: "applications" };
  if (hash === "#/resume") return { page: "resume" };
  if (hash === "#/settings") return { page: "settings" };
  const review = /^#\/applications\/(\d+)$/.exec(hash);
  if (review) return { page: "review", applicationId: Number(review[1]) };
  return { page: "jobs" };
}

export function App() {
  const [route, setRoute] = useState(routeFromHash);

  useEffect(() => {
    const onChange = () => {
      setRoute(routeFromHash());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  if (route.page === "review") return <ReviewPage key={route.applicationId} id={route.applicationId} />;
  if (route.page === "applications") return <ApplicationsPage />;
  if (route.page === "resume") return <ResumePage />;
  if (route.page === "settings") return <SettingsPage />;
  return <Dashboard />;
}

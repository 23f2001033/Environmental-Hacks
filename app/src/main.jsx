import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import "maplibre-gl/dist/maplibre-gl.css";
import "./styles.css";
import { LangProvider, useLang } from "./i18n.jsx";
import Home from "./pages/Home.jsx";
import Village from "./pages/Village.jsx";
import Engineer from "./pages/Engineer.jsx";
import Relay from "./pages/Relay.jsx";
import Officials from "./pages/Officials.jsx";
import Impact from "./pages/Impact.jsx";

function Header() {
  const { t, lang, setLang } = useLang();
  return (
    <header className="top">
      <div className="wrap">
        <a className="brand" href="/"><img src="/app/icon.svg" alt="" /><span>JalSaathi</span></a>
        <nav className="nav">
          <a href="/">{t("nav_about")}</a>
          <NavLink to="/officials">{t("nav_officials")}</NavLink>
          <NavLink to="/impact">{t("nav_impact")}</NavLink>
          <a className="nav-primary" href="/?find">{t("nav_find")}</a>
        </nav>
        <button className="lang" onClick={() => setLang(lang === "hi" ? "en" : "hi")}>{t("lang_switch")}</button>
      </div>
    </header>
  );
}

// Telegram alerts and printed posters link to /?v=<village key>; keep them working.
function LegacyVillage({ children }) {
  const { search } = useLocation();
  const v = new URLSearchParams(search).get("v");
  return v ? <Navigate to={`/village/${encodeURIComponent(v)}`} replace /> : children;
}

function App() {
  const { t } = useLang();
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<LegacyVillage><Home /></LegacyVillage>} />
        <Route path="/village/:key" element={<Village />} />
        <Route path="/engineer/:block" element={<Engineer />} />
        <Route path="/relay/:village" element={<Relay />} />
        <Route path="/officials" element={<Officials />} />
        <Route path="/impact" element={<Impact />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <footer className="no-print"><div className="wrap">{t("footer")}</div></footer>
    </>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <LangProvider>
      <BrowserRouter basename="/app"><App /></BrowserRouter>
    </LangProvider>
  </StrictMode>,
);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/app/sw.js", { scope: "/app/" }).catch(() => {}));
}

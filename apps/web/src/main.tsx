import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import AuthGate from "./auth";
import { LocaleProvider } from "./locale";
import "./styles.css";
import "./auth.css";
import "./chat-polish.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LocaleProvider>
      <AuthGate><App /></AuthGate>
    </LocaleProvider>
  </StrictMode>,
);

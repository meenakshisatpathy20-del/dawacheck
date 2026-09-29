import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router-dom";
import "./styles.css";
import App from "./App.jsx";
import { StoreProvider } from "./store.jsx";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "");
const Router = ({ children }) => (__HASH_ROUTER__
  ? <HashRouter>{children}</HashRouter>
  : <BrowserRouter basename={basename}>{children}</BrowserRouter>);

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Router>
      <StoreProvider>
        <App />
      </StoreProvider>
    </Router>
  </StrictMode>
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL }).catch(() => {});
}

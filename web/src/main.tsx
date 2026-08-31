import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles/app.css";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<App />);
}

// Pinch and double-tap zoom would fight the trackpad for the same gestures.
document.addEventListener("gesturestart", (event) => event.preventDefault());
document.addEventListener("dblclick", (event) => event.preventDefault());

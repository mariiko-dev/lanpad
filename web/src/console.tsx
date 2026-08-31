import { createRoot } from "react-dom/client";

import { ConsoleApp } from "./console/ConsoleApp";
import "./styles/console.css";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<ConsoleApp />);
}

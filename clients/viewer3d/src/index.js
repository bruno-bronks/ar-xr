// Ponto de entrada do bundle: expoe window.SpatialViewer (usado por clients/web-fallback/app.js).
import { Viewer, webglAvailable } from "./viewer.js";
import { WardViewer } from "./ward.js";

function mount(container, options, Kind = Viewer) {
  if (!webglAvailable()) {
    container.replaceChildren();
    const note = document.createElement("p");
    note.className = "v3d-note muted";
    note.setAttribute("data-testid", (options && options.testPrefix ? options.testPrefix : "viewer3d") + "-note");
    note.textContent = "Este navegador/dispositivo não oferece WebGL 2: a vista 3D está indisponível. A planta 2D e os cartões continuam funcionando.";
    container.appendChild(note);
    container.setAttribute("data-ready", "false");
    container.setAttribute("data-unavailable", "true");
    return null;
  }
  try {
    return new Kind(container, options);
  } catch (error) {
    container.replaceChildren();
    const note = document.createElement("p");
    note.className = "v3d-note muted";
    note.setAttribute("data-testid", (options && options.testPrefix ? options.testPrefix : "viewer3d") + "-note");
    note.textContent = "Não foi possível iniciar a vista 3D neste dispositivo. A planta 2D e os cartões continuam funcionando.";
    container.appendChild(note);
    container.setAttribute("data-ready", "false");
    container.setAttribute("data-unavailable", "true");
    console.error("viewer3d:", error && error.message);
    return null;
  }
}

const mountWard = (container, options) => mount(container, { testPrefix: "ward3d", labelPrefix: "label-ward3d", ...options }, WardViewer);

window.SpatialViewer = Object.freeze({ mount, mountWard, webglAvailable });

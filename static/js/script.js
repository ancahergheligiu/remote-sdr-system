const socket = io();

// verificare conexiune 
socket.on("connect", () => {
  console.log("[Js] Conectat la Socket.IO");
});
socket.on("disconnect", () => {
  console.warn("[Js] Deconectat de la Socket.IO");
});

// variabile globale
const waterfallHistory = [];
const maxLines = 100;
let latestFreqs = [];
let expectedLength = null;
let pendingWaterfall = [];
let centerFrequency = null;
let zoomWidth = 5000000; 

// layout FFT 
const fftLayout = {
  title: "Spectru/FFT",
  paper_bgcolor: "#fff",
  plot_bgcolor: "#fff",
  font: { color: "#212529" },
  yaxis: {
    title: "Amplitudine [dB]",
    range: [-100, 0],
    color: "#333",
    gridcolor: "#ccc"
  },
  xaxis: {
    title: "Frecvență [Hz]",
    tickformat: ".3f",
    color: "#333",
    gridcolor: "#ccc"
  },
  margin: { t: 40 }
};

// layout spectrograma
const waterfallLayout = {
  title: "Spectrogramă / Waterfall",
  font: { color: "#212529" },
  paper_bgcolor: "#fff",
  plot_bgcolor: "#fff",
  margin: { t: 40 }
};

// initializare grafice
Plotly.newPlot("spectrum", [{
  x: [],
  y: [],
  type: "scatter",
  line: { color: "#33cc66", width: 2 }
}], fftLayout, { responsive: true });

Plotly.newPlot("waterfall", [{
  z: [[]],
  type: "heatmap",
  colorscale: "Jet",
  zmin: -100,
  zmax: 0
}], {
  ...waterfallLayout,
  xaxis: { title: "Frecvență [Hz]" },
  yaxis: { title: "Timp (linii)", autorange: "reversed" }
}, { responsive: true });

// toast
function showToast(msg) {
  let el = document.getElementById("toast-msg");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast-msg";
    el.style.cssText = `
      position: fixed; bottom: 20px; right: 20px;
      background: #d1e7dd; color: #0f5132; padding: 12px 20px;
      border-radius: 8px; font-weight: bold; display: none;
      box-shadow: 0 0 10px rgba(0,0,0,0.1); z-index: 9999;
    `;
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.style.display = "block";
  setTimeout(() => el.style.display = "none", 2000);
}

// FFT
function updateFFT(freqs, data) {
  if (!Array.isArray(freqs) || !Array.isArray(data)) return;

  if (!expectedLength) {
    expectedLength = data.length;
    console.log(`[Js] Dimensiune spectru setată: ${expectedLength}`);
  }

  if (data.length !== expectedLength || freqs.length !== expectedLength) {
    console.warn(`[Js] Spectru ignorat – dimensiune invalidă`);
    return;
  }

  latestFreqs = freqs;

  let xRange = null;
  if (centerFrequency !== null) {
    xRange = [centerFrequency - zoomWidth / 2, centerFrequency + zoomWidth / 2];
  }

  const layoutZoom = JSON.parse(JSON.stringify(fftLayout));
  if (xRange) layoutZoom.xaxis.range = xRange;

  Plotly.react("spectrum", [{
    x: freqs,
    y: data,
    type: "scatter",
    line: { color: "#33cc66", width: 2 }
  }], layoutZoom, { responsive: true });

  const maxDb = Math.max(...data);
  const minDb = Math.min(...data);

  const analysisEl = document.getElementById("analysis");
  if (analysisEl && centerFrequency !== null) {
    analysisEl.innerHTML = `
      <strong>Centru:</strong> ${centerFrequency.toFixed(0)} Hz<br>
      <strong>Max dB:</strong> ${maxDb.toFixed(1)}<br>
      <strong>Min dB:</strong> ${minDb.toFixed(1)}
    `;
  }

  if (pendingWaterfall.length > 0) {
    const toProcess = [...pendingWaterfall];
    pendingWaterfall.length = 0;
    for (const line of toProcess) updateWaterfall(line);
  }
}

// spectrograma
function updateWaterfall(newLine) {
  if (
    !Array.isArray(newLine) ||
    !Array.isArray(latestFreqs) ||
    latestFreqs.length === 0 ||
    newLine.length !== expectedLength
  ) {
    console.warn("[Js] Linie waterfall invalidă – adăugată temporar în buffer");
    if (Array.isArray(newLine)) pendingWaterfall.push(newLine);
    return;
  }

  if (!newLine.every(Number.isFinite)) {
    console.warn("[Js] Linie waterfall conține valori non-numerice – ignorată");
    return;
  }

  waterfallHistory.push(newLine);
  if (waterfallHistory.length > maxLines) waterfallHistory.shift();

  const y_vals = Array.from({ length: waterfallHistory.length }, (_, i) => i);
  const x_vals = latestFreqs;

  let xRange = null;
  if (centerFrequency !== null) {
    xRange = [centerFrequency - zoomWidth / 2, centerFrequency + zoomWidth / 2];
  }

  const layoutZoom = JSON.parse(JSON.stringify(waterfallLayout));
  if (xRange) layoutZoom.xaxis = {
    ...layoutZoom.xaxis,
    range: xRange,
    tickformat: ".3f",
    color: "#333",
    gridcolor: "#ccc",
    title: "Frecvență [Hz]"
  };
  layoutZoom.yaxis = {
    title: "Timp (linii)",
    autorange: "reversed",
    color: "#333",
    gridcolor: "#ccc"
  };

  Plotly.react("waterfall", [{
    z: waterfallHistory,
    x: x_vals,
    y: y_vals,
    type: "heatmap",
    colorscale: "Jet",
    zmin: -100,
    zmax: 0
  }], layoutZoom, { responsive: true });
}

// socket spectru FFT 
socket.on("spectrum", payload => {
  if (!payload || !payload.spectrum || !payload.freqs) return;

  document.getElementById("status-msg").style.display = "none";
  updateFFT(payload.freqs, payload.spectrum);
});

// socket spectrograma
socket.on("waterfall", payload => {
  if (payload?.line) {
    updateWaterfall(payload.line);
  } else if (Array.isArray(payload?.waterfall)) {
    waterfallHistory.length = 0;
    waterfallHistory.push(...payload.waterfall);
    updateWaterfall(payload.waterfall.at(-1));
  }
});

// formular
document.getElementById("control").addEventListener("submit", e => {
  e.preventDefault();

  const freqBase = parseFloat(document.getElementById("frequency").value) || 0;
  const freqMult = parseFloat(document.getElementById("freq_unit").value) || 1;
  const sampleBase = parseFloat(document.getElementById("sample_rate").value) || 0;
  const sampleMult = parseFloat(document.getElementById("samp_unit").value) || 1;
  const gain = parseFloat(document.getElementById("gain").value) || 0;

  const frequency = freqBase * freqMult;
  const sample_rate = sampleBase * sampleMult;

  if (frequency < 1e5 || frequency > 6e9 || sample_rate < 1e4 || sample_rate > 50e6) {
    showToast("Valori invalide pentru frecvență sau rată de eșantionare.");
    return;
  }

  centerFrequency = frequency;
  document.getElementById("status-msg").style.display = "block";
  document.getElementById("status-msg").textContent = "Se aplică modificările...";

  socket.emit("update_parameters", {
    frequency,
    sample_rate,
    gain
  });

  showToast("Modificările au fost trimise");
});

// redimensionare grafice
window.addEventListener("resize", () => {
  Plotly.Plots.resize(document.getElementById("spectrum"));
  Plotly.Plots.resize(document.getElementById("waterfall"));
});


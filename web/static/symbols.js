// Schematic symbols as SVG markup in component-local grid units (1 unit = one 20 px board cell, as GRID_SIZE in
// config.py), drawn for rotation 0 with leads ending on the rounded connection points of components/*.py.
// The caller wraps the markup in <g transform="translate(x,y) rotate(r) scale(G)">.

const lead = (x1, y1, x2, y2) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;

function resistor() {
  const pts = [[-2, 0], [-1, 0]];
  for (let k = 0; k < 6; k++) pts.push([-1 + (k + 0.5) / 3, k % 2 ? 0.35 : -0.35]);
  pts.push([1, 0], [2, 0]);
  return `<polyline points="${pts.map(p => p.join(',')).join(' ')}"/>`;
}
function capacitor() {
  return lead(-1, 0, -0.2, 0) + lead(0.2, 0, 1, 0) + lead(-0.2, -0.6, -0.2, 0.6) + lead(0.2, -0.6, 0.2, 0.6);
}
function inductor() {
  let d = 'M-2 0 L-1.2 0';
  for (let k = 0; k < 4; k++) d += ` A0.3 0.3 0 0 1 ${-1.2 + 0.6 * (k + 1)} 0`;
  return `<path d="${d} L2 0"/>`;
}
function ground() {
  return lead(0, 0, 0, 0.6) + lead(-0.7, 0.6, 0.7, 0.6) + lead(-0.45, 0.85, 0.45, 0.85) + lead(-0.2, 1.1, 0.2, 1.1);
}
function sourceCircle(inner) {
  return lead(0, -2, 0, -1.1) + lead(0, 1.1, 0, 2) + `<circle cx="0" cy="0" r="1.1" class="body"/>` + inner;
}
const dcSource = () => sourceCircle(lead(-0.25, 0.55, 0.25, 0.55) + lead(0, 0.3, 0, 0.8) + lead(-0.25, -0.55, 0.25, -0.55));
const acSource = () => sourceCircle('<path d="M-0.6 0 C-0.3 -0.7 -0.1 -0.7 0 0 S0.3 0.7 0.6 0"/>'
  + lead(-0.18, 0.75, 0.18, 0.75) + lead(0, 0.57, 0, 0.93));
// arrow towards the pos terminal (+y): current leaves the source at pos
const currentSource = () => sourceCircle(lead(0, -0.6, 0, 0.6) + '<path d="M-0.3 0.25 L0 0.65 L0.3 0.25" class="fillst"/>');
function diode(led, brightness = 0, color = 'red') {
  let s = lead(-1, 0, -0.4, 0) + lead(0.4, 0, 1, 0) + '<path d="M-0.4 -0.45 L-0.4 0.45 L0.4 0 Z" class="body"/>'
    + lead(0.4, -0.45, 0.4, 0.45);
  if (led) {
    const glow = Math.max(0, Math.min(1, brightness));
    s = `<circle cx="0" cy="0" r="0.9" class="glow" style="fill:${ledColor(color)};opacity:${(glow * 0.75).toFixed(3)}"/>` + s
      + '<path d="M0 -0.6 L0.45 -1.05 M0.25 -1.05 L0.45 -1.05 L0.45 -0.85 M0.35 -0.45 L0.8 -0.9 M0.6 -0.9 L0.8 -0.9 L0.8 -0.7"/>';
  }
  return s;
}
export const ledColor = c => ({ red: '#ff3b3b', green: '#3dff6a', blue: '#4f8dff', yellow: '#ffe14a', white: '#ffffff' }[c] || '#ff3b3b');
function bjt(pnp) {
  const arrow = pnp ? '<path d="M-0.25 -0.62 L-0.5 -0.35 L-0.15 -0.3 Z" class="fillst"/>'
    : '<path d="M-0.18 -0.9 L0 -1 L-0.1 -0.72 Z" class="fillst"/>';
  return '<circle cx="-0.1" cy="0" r="1.25" class="body"/>' + lead(-2, 0, -0.5, 0) + lead(-0.5, -0.7, -0.5, 0.7)
    + lead(-0.5, 0.35, 0, 1) + lead(0, 1, 0, 2) + lead(-0.5, -0.35, 0, -1) + lead(0, -1, 0, -2) + arrow;
}
function switchSym(closed) {
  return lead(-1, 0, -0.55, 0) + lead(0.55, 0, 1, 0) + '<circle cx="-0.55" cy="0" r="0.09" class="fillst"/>'
    + '<circle cx="0.55" cy="0" r="0.09" class="fillst"/>'
    + (closed ? lead(-0.55, 0, 0.55, 0) : lead(-0.55, 0, 0.45, -0.5));
}

// SVG markup for one component; `live` carries readouts used for visual state (LED glow, switch position).
export function symbol(c, live = {}) {
  const p = c.properties || {};
  switch (c.type) {
    case 'Resistor': return resistor();
    case 'Capacitor': return capacitor();
    case 'Inductor': return inductor();
    case 'Ground': return ground();
    case 'DCVoltageSource': return dcSource();
    case 'ACVoltageSource': return acSource();
    case 'DCCurrentSource': return currentSource();
    case 'Diode': return diode(false);
    case 'LED': return diode(true, live.brightness || 0, p.color);
    case 'BJT': return bjt(String(p.type || 'npn').toLowerCase() === 'pnp');
    case 'Switch': return switchSym(!!p.state);
    default: return '<rect x="-1" y="-1" width="2" height="2"/>';
  }
}

// Clickable/selectable area in local units: [x, y, w, h].
export function hitBox(c) {
  switch (c.type) {
    case 'Resistor': case 'Inductor': return [-2, -0.7, 4, 1.4];
    case 'Ground': return [-0.8, -0.1, 1.6, 1.4];
    case 'DCVoltageSource': case 'ACVoltageSource': case 'DCCurrentSource': return [-1.3, -2, 2.6, 4];
    case 'BJT': return [-2, -2, 3.5, 4];
    default: return [-1, -0.7, 2, 1.4];
  }
}

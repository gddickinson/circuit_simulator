// Simulator page (#/sim?ex=<example>): schematic editor + in-browser MNA engine + oscilloscope.
import { $, api, app, esc, route, animate, download, isStatic, go, onLeave } from './core.js';
import { CircuitDoc } from './circuit_doc.js';
import { Schematic } from './schematic.js';
import { Scope } from './scope.js';
import { Transient } from './transient_engine.js';
import { CircuitError } from './circuit_engine.js';
import { paletteHtml, renderProps, renderLive, makeProbe } from './sim_panel.js';
import { formatValue } from './units.js';

const SPEEDS = [[1e-5, '10 µs'], [2e-5, '20 µs'], [5e-5, '50 µs'], [1e-4, '100 µs'], [1e-3, '1 ms (desktop speed)'], [1e-2, '10 ms'], [1e-1, '100 ms']];
const WINDOWS = [[1e-3, '1 ms'], [2e-3, '2 ms'], [5e-3, '5 ms'], [1e-2, '10 ms'], [5e-2, '50 ms'], [0.2, '200 ms'], [1, '1 s'], [10, '10 s']];
// Scope probes preset for the examples: [component, 'v'|'i'].
const PRESET = { voltage_divider: [['resistor_2', 'v'], ['resistor_1', 'i']], rc_circuit: [['capacitor_1', 'v'], ['resistor_1', 'i']],
  diode_circuit: [['diode_1', 'v'], ['diode_1', 'i']], led_circuit: [['led_1', 'v'], ['led_1', 'i']],
  bjt_circuit: [['bjt_1', 'v'], ['bjt_1', 'i']], oscillator_circuit: [['ac_source_1', 'v'], ['capacitor_1', 'v'], ['resistor_1', 'i']],
  switch_circuit: [['led_1', 'v'], ['led_1', 'i']] };
// Simulated time per frame and scope sweep per example, so the transient is visible (default 1 ms frames, 200 ms).
const PACE = { rc_circuit: [5e-5, 1e-2], oscillator_circuit: [2e-5, 5e-3] };

route('sim', async (args, query) => {
  const [catalog, examples] = await Promise.all([api('/components'), api('/examples')]);
  const exName = query.ex || (query.new ? '' : 'rc_circuit');
  app().innerHTML = `
  <div class="simhead"><div><p class="kicker">Simulator</p><h1 class="glow">Circuit board</h1></div>
    <div class="bar top-bar">
      <label class="sr" for="ex-sel">Example circuit</label>
      <select id="ex-sel"><option value="">Examples…</option>${examples.map(e => `<option value="${e.name}"${e.name === exName ? ' selected' : ''}>${esc(e.title)}</option>`).join('')}</select>
      <button class="alt" id="b-new">New</button><button class="alt" id="b-load">Open .circuit</button><button class="alt" id="b-save">Save .circuit</button>
      <input type="file" id="f-load" accept=".circuit,.json,application/json" hidden>
    </div></div>
  <p class="mute small" id="ex-note"></p>
  <div class="sim">
    <aside class="panel side-pal"><h2 class="h-pal">Components</h2>${paletteHtml(catalog)}
      <p class="small mute">Click a part, then the board. Click one terminal then another to wire them. Drag to move,
      <kbd>R</kbd> rotates, <kbd>Del</kbd> deletes, double-click or <kbd>Space</kbd> toggles a switch.</p></aside>
    <section class="boardwrap">
      <div class="bar runbar">
        <button id="b-run">Run</button><button class="alt" id="b-step">Step</button><button class="alt" id="b-reset">Reset</button>
        <label for="spd" class="inl">Simulated time per frame</label>
        <select id="spd">${SPEEDS.map(([v, l]) => `<option value="${v}"${v === 1e-3 ? ' selected' : ''}>${l}</option>`).join('')}</select>
        <span class="mono small" id="clock">t = 0 s</span>
        ${isStatic() ? '' : '<button class="alt" id="b-check" title="Run the same circuit through the Python engine">Check vs Python</button>'}
      </div>
      <div class="stage board-stage" id="board"></div>
      <p class="small" id="status" role="status" aria-live="polite"></p>
      <div class="scopewrap"><canvas id="scope" aria-label="Oscilloscope traces" role="img"></canvas>
        <div class="bar scopebar"><label for="win" class="inl">Sweep</label>
          <select id="win">${WINDOWS.map(([v, l]) => `<option value="${v}"${v === 1e-2 ? ' selected' : ''}>${l}</option>`).join('')}</select>
          <span id="legend"></span></div></div>
    </section>
    <aside class="panel side-sel" id="sel"><p class="mute small">Select a component to edit its values and read its voltages and currents.</p></aside>
  </div>`;

  const doc = new CircuitDoc(catalog), scope = new Scope($('#scope'));
  const S = { running: false, tr: null, readouts: null, dirty: true, error: '' };
  const status = msg => { $('#status').textContent = msg; };
  const ed = new Schematic($('#board'), doc, {
    onSelect: () => showSel(), onStatus: status,
    onChange: kind => { S.dirty = true; if (kind !== 'move') rebuild(); showSel(); },
  });

  // Rebuild the engine after an edit, keeping time and the dynamic state (capacitor v, inductor i, diode/BJT region)
  // of components that still exist, as the desktop solver keeps them in the components' own state.
  function rebuild() {
    const old = S.tr;
    try {
      S.tr = new Transient(doc.engineCircuit());
      if (old) {
        S.tr.t = old.t;
        for (const id of Object.keys(S.tr.state)) if (old.state[id]) S.tr.state[id] = { ...S.tr.state[id], ...old.state[id] };
      }
      S.error = '';
    } catch (e) { S.error = e.message; }
  }
  function reset() {
    S.tr = null; rebuild(); S.readouts = null; scope.clearData(); ed.render(null); showSel(); tick(0);
  }
  function stepOnce() {
    if (!S.tr) rebuild();
    if (!S.tr || !Object.keys(doc.components).length) return;
    try {
      S.readouts = S.tr.advance(+$('#spd').value);
      S.error = '';
    } catch (e) {
      S.running = false;
      S.error = e instanceof CircuitError ? `Cannot solve: ${e.message}` : e.message;
      status(S.error);
      return;
    }
    scope.sample(S.tr.t, S.readouts);
  }
  function liveInfo() {
    if (!S.readouts) return null;
    let vmax = 0;
    for (const r of Object.values(S.readouts)) for (const v of Object.values(r.voltages)) vmax = Math.max(vmax, Math.abs(v));
    return { readouts: S.readouts, vmax };
  }
  function tick(frame) {
    if (S.running) stepOnce();
    if (S.running || frame === 0) {
      ed.render(liveInfo());
      const sel = ed.selected;
      if (sel?.kind === 'comp' && doc.components[sel.id]) renderLive($('#pp-live'), doc.components[sel.id], S.readouts?.[sel.id], addProbe);
    }
    $('#clock').textContent = `t = ${formatValue(S.tr?.t || 0, 's')}${S.tr && !S.tr.converged ? ' (regions not settled)' : ''}`;
    scope.window = +$('#win').value;
    scope.draw(S.tr?.t || 0);
  }
  function setRunning(on) {
    S.running = on;
    $('#b-run').textContent = on ? 'Pause' : 'Run';
    if (on && S.error) status('');
  }
  function addProbe(c, kind) {
    scope.add(makeProbe(c, kind));
    legend();
  }
  function legend() {
    $('#legend').innerHTML = scope.traces.map(t => `<span class="trace" style="--c:${t.color}">${esc(t.label)}
      <button class="x" data-key="${esc(t.key)}" aria-label="Remove trace ${esc(t.label)}">×</button></span>`).join('');
    for (const b of $('#legend').querySelectorAll('button')) b.onclick = () => { scope.remove(b.dataset.key); legend(); scope.draw(S.tr?.t || 0); };
  }
  function showSel() {
    const sel = ed.selected, host = $('#sel');
    if (sel?.kind === 'wire') {
      const [a, ta, b, tb] = sel.w;
      host.innerHTML = `<div class="selhead"><b>Wire</b></div><p class="mono small">${esc(a)}.${esc(ta)} — ${esc(b)}.${esc(tb)}</p>
        <button class="alt" id="w-del">Delete wire</button>`;
      $('#w-del').onclick = () => ed.deleteSelected();
      return;
    }
    const c = sel?.kind === 'comp' && doc.components[sel.id];
    if (!c) { host.innerHTML = '<p class="mute small">Select a component to edit its values and read its voltages and currents.</p>'; return; }
    renderProps(host, c, doc.catalog[c.type], {
      onEdit: (name, val) => { c.properties[name] = val; S.dirty = true; rebuild(); ed.render(liveInfo()); },
      onRotate: () => ed.rotateSelected(), onDelete: () => ed.deleteSelected(), onToggle: () => ed.toggleSwitch(c.id),
    });
    renderLive($('#pp-live'), c, S.readouts?.[c.id], addProbe);
  }
  async function loadExample(name) {
    const data = await api('/examples/' + name);
    doc.load(data);
    $('#ex-note').textContent = data.metadata?.description || '';
    scope.traces = [];
    for (const [id, kind] of PRESET[name] || []) if (doc.components[id]) scope.add(makeProbe(doc.components[id], kind));
    const [spd, win] = PACE[name] || [1e-3, 0.2];
    $('#spd').value = String(spd); $('#win').value = String(win);
    legend(); ed.select(null); reset(); setRunning(true);
  }

  $('#ex-sel').onchange = e => { if (e.target.value) go(`#/sim?ex=${e.target.value}`); };
  $('#b-new').onclick = () => { doc.clear(); scope.traces = []; legend(); $('#ex-note').textContent = ''; setRunning(false); ed.select(null); reset(); };
  $('#b-save').onclick = () => download('circuit.circuit', JSON.stringify(doc.toFile(S.tr?.t || 0), null, 2), 'application/json');
  $('#b-load').onclick = () => $('#f-load').click();
  $('#f-load').onchange = async e => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const skipped = doc.load(JSON.parse(await f.text()));
      scope.traces = []; legend(); ed.select(null); reset();
      $('#ex-note').textContent = `Opened ${f.name}${skipped ? ` (${skipped} unknown component(s) skipped)` : ''}.`;
    } catch (err) { status(`Could not open ${f.name}: ${err.message}`); }
    e.target.value = '';
  };
  $('#b-run').onclick = () => setRunning(!S.running);
  $('#b-step').onclick = () => { setRunning(false); stepOnce(); tick(0); };
  $('#b-reset').onclick = () => reset();
  $('#win').onchange = () => tick(0);
  for (const b of app().querySelectorAll('.pal')) b.onclick = () => ed.setPlace(b.dataset.type);
  const chk = $('#b-check');
  if (chk) chk.onclick = () => checkPython(doc, +$('#spd').value, status);

  if (exName) await loadExample(exName); else reset();
  let f = 0;
  const stop = animate(() => tick(++f));
  onLeave(() => { stop(); ed.destroy(); });
});

// Local app only: run 20 frames in the Python engine (POST /api/simulate) and in JS, report the largest difference.
async function checkPython(doc, frame, status) {
  status('Running the circuit in Python…');
  try {
    const frames = 20, py = await api('/simulate', { body: { circuit: doc.engineCircuit(), frame, frames } });
    const tr = new Transient(doc.engineCircuit());
    let worst = 0, n = 0;
    for (let k = 0; k < frames; k++) {
      const js = tr.advance(frame);
      for (const [id, r] of Object.entries(py.results[k])) {
        for (const kind of ['voltages', 'currents']) {
          for (const [term, v] of Object.entries(r[kind])) { worst = Math.max(worst, Math.abs(js[id][kind][term] - v)); n++; }
        }
      }
    }
    status(`Python and JS engines agree on ${n} values over ${frames} frames: largest difference ${worst.toExponential(2)}.`);
  } catch (e) { status(`Python check failed: ${e.message}`); }
}

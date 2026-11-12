// Examples gallery: the circuits of examples/basic_circuits.py with schematic previews.
import { api, app, esc, route } from './core.js';
import { CircuitDoc } from './circuit_doc.js';
import { Schematic } from './schematic.js';

route('examples', async () => {
  const [catalog, examples] = await Promise.all([api('/components'), api('/examples')]);
  app().innerHTML = `<p class="kicker">From examples/basic_circuits.py</p><h1 class="glow">Example circuits</h1>
    <p class="lead">The desktop app's built-in example circuits, with the same parts, values and connections
    (laid out on the board for readability). Open one to run it.</p>
    <div class="grid wide">${examples.map(e => `<a class="card excard" href="#/sim?ex=${e.name}">
      <div class="thumb" id="th-${e.name}" aria-hidden="true"></div><b>${esc(e.title)}</b><span>${esc(e.note)}</span></a>`).join('')}</div>`;
  for (const e of examples) {
    const doc = new CircuitDoc(catalog);
    doc.load(await api('/examples/' + e.name));
    const host = document.getElementById('th-' + e.name);
    const ed = new Schematic(host, doc);
    ed.svg.setAttribute('viewBox', '60 60 520 360');
    ed.svg.removeAttribute('tabindex');
    ed.svg.setAttribute('aria-hidden', 'true');
    ed.destroy();
  }
});

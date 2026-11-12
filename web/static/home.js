// Home page: hero, counts, entry cards.
import { api, app, esc, route } from './core.js';

route('home', async () => {
  const [info, examples] = await Promise.all([api('/info'), api('/examples')]);
  app().innerHTML = `
  <section class="hero"><p class="kicker">Modified Nodal Analysis · in your browser</p>
    <h1 class="glow">Circuit Simulator</h1>
    <p class="lead">${esc(info.description)} This site is the simulator itself: draw a schematic, press Run, and the
      same MNA engine as the desktop app (ported to JavaScript and tested against it) solves every node and branch while
      an oscilloscope traces voltages and currents.</p>
    <a class="btn" href="#/sim">Open the simulator</a><a class="btn alt" href="#/examples">Example circuits</a></section>
  <div class="tiles">
    <div class="tile"><b>${info.components}</b><span>component types</span></div>
    <div class="tile"><b>${info.examples}</b><span>example circuits</span></div>
    <div class="tile"><b>${info.max_step * 1e6} µs</b><span>max integration step</span></div>
    <div class="tile"><b>.circuit</b><span>files open in the desktop app</span></div>
  </div>
  <h2>Start with an example</h2>
  <div class="grid">${examples.map(e => `<a class="card" href="#/sim?ex=${e.name}"><b>${esc(e.title)}</b>
    <small>${e.components} components</small><span>${esc(e.note)}</span></a>`).join('')}</div>
  <h2>What you can do</h2>
  <div class="grid wide">
    <div class="card"><b>Build</b><span>Place resistors, capacitors, inductors, sources, diodes, LEDs, BJTs and switches on
      the same 20 px grid as the desktop board; wire terminal to terminal; rotate, drag and delete.</span></div>
    <div class="card"><b>Edit values with units</b><span>Type 4.7k, 10u or 2.2 MΩ; changes apply while the circuit runs.</span></div>
    <div class="card"><b>Measure</b><span>Wires glow with their node voltage; every part shows V across and current; the
      scope plots up to four probes against simulated time.</span></div>
    <div class="card"><b>Save and share</b><span>Save to the desktop app's .circuit format and open it in either app.</span></div>
  </div>`;
});

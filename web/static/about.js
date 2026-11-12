// About page: what the simulator is, the models and conventions, how to run both apps, credits.
import { app, route } from './core.js';

route('about', () => {
  app().innerHTML = `<p class="kicker">About</p><h1 class="glow">How it works</h1>
  <p class="lead">Circuit Simulator is an interactive electronic circuit simulator built with Python and PyQt5. This web
  version runs the same solver in the browser, so the GitHub Pages site is a working simulator with no server.</p>
  <h2>The solver</h2>
  <p>Every frame advances the circuit by a fixed amount of simulated time (1 ms in the desktop app). Inside a frame
  the engine takes steps of at most 10 µs (and at most 1/50 of the period of any AC source). Each step
  builds the Modified Nodal Analysis system <span class="eq">A x = b</span> &mdash; node voltages plus one current
  per voltage source &mdash; and solves it by LU decomposition.</p>
  <ul>
    <li><b>Capacitors and inductors</b> use trapezoidal companion models (a conductance 2C/h or h/2L with a history
      current source; error about 10<sup>−5</sup> at one RC time constant), starting from rest. After any sudden change
      &mdash; the start, a switch flip or edited value, a diode or transistor changing state &mdash; three
      backward-Euler steps are taken instead, which stops the trapezoidal rule's ringing.</li>
    <li><b>Diodes and LEDs</b> are piecewise linear: off (1 nS leakage) or on (forward voltage in series with 0.1 Ω).
      <b>BJTs</b> use the desktop model: base current (V<sub>BE</sub> − 0.7 V) / 1 kΩ, collector current β·I<sub>B</sub>
      in the active region, V<sub>CE</sub> held near 0.2 V in saturation. The engine iterates until every device is in
      a self-consistent region (at most 100 passes, with 1 µV of hysteresis: the desktop app's
      <code>MAX_ITERATIONS</code> and <code>CONVERGENCE_THRESHOLD</code>).</li>
    <li><b>Ratings</b> (max power, voltage or current of each part, as in the desktop property dialog) never change
      the solution: a part driven past its rating is outlined in red and its readout says by how much.</li>
    <li><b>Switches</b> are 0.01 Ω closed and 1 TΩ open. Every node has 10<sup>−12</sup> S to ground so a floating
      part cannot make the matrix singular; two different voltage sources in parallel are reported as unsolvable.</li>
    <li><b>Ground</b>: every node touching a ground symbol is 0 V. With no ground symbol, the − terminal of the first
      voltage source is the reference.</li>
  </ul>
  <h3>Sign conventions</h3>
  <p>Terminal currents are the current flowing <i>into</i> the component at that terminal, so a source that delivers
  power shows a negative current at its + terminal. Power is the power absorbed; a negative value is delivered.
  A DC current source pushes its current out of its + terminal.</p>
  <h3>Verification</h3>
  <p>The JavaScript engine (<code>circuit_engine.js</code>, <code>transient_engine.js</code>) is a line-by-line port of
  <code>simulation/mna.py</code> and <code>simulation/transient.py</code>. A node test replays fourteen circuits (the seven
  examples plus RL, current-source, pnp, RLC-with-diode, closed-switch, over-rated LED and a mid-run switch flip) and requires every terminal voltage and
  current to match the Python results to 1 part in 10<sup>9</sup>. Python tests check hand calculations: the divider
  midpoint, the RC and RL time constants, diode and LED currents, the RC low-pass amplitude and phase, BJT saturation.
  On the local app, the simulator's <b>Check vs Python</b> button runs your circuit through both engines.</p>
  <h2>Run it yourself</h2>
  <h3>Desktop app (PyQt5)</h3>
  <pre>pip install -r requirements.txt
python main.py                 # --example, --load file.circuit, --debug</pre>
  <h3>Web app</h3>
  <pre>pip install -r requirements-web.txt
python run_web.py              # http://127.0.0.1:8234</pre>
  <p>Files saved here (<b>Save .circuit</b>) open in the desktop app with File &gt; Open, and the desktop app's saved
  circuits open here.</p>
  <h2>Credits</h2>
  <p>By George Dickinson. Open source under the MIT License. Built with AI assistance from
  <a href="https://claude.com/" target="_blank" rel="noopener">Claude (Anthropic)</a>.</p>`;
});

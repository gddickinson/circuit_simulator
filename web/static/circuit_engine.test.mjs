// node web/static/circuit_engine.test.mjs — the JS engine reproduces the Python MNA engine
// (fixture: tests/fixtures/engine_fixture.json from scripts/make_engine_fixture.py) and hand-calculable circuits.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DEFAULTS, TERMINALS, RATINGS, MAX_PWL_ITER, REGION_TOL, CircuitError } from './circuit_engine.js';
import { Transient, BE_STEPS } from './transient_engine.js';
import { parseValue, formatValue } from './units.js';

const fx = JSON.parse(readFileSync(new URL('../../tests/fixtures/engine_fixture.json', import.meta.url)));
assert.deepEqual(TERMINALS, fx.terminals, 'terminal names match simulation/mna.py');
assert.deepEqual(DEFAULTS, fx.defaults, 'defaults match simulation/mna.py');
assert.deepEqual(RATINGS, fx.ratings, 'ratings match simulation/mna.py');
assert.deepEqual({ MAX_PWL_ITER, REGION_TOL, BE_STEPS }, fx.constants, 'iteration constants match');

const close = (a, b, what) => {
  const tol = 1e-9 * Math.max(Math.abs(a), Math.abs(b)) + 1e-11;
  assert.ok(Math.abs(a - b) <= tol, `${what}: js ${a} vs py ${b}`);
};
let worst = 0, checked = 0;
for (const [name, c] of Object.entries(fx.cases)) {
  const circ = structuredClone(c.circuit);
  let tr = new Transient(circ);
  c.results.forEach((row, f) => {
    if (c.toggle && f === c.toggle.frame) {  // flip the switch mid-run, keeping state and time
      const p = circ.components[c.toggle.id].properties;
      p.state = !p.state;
      const nt = new Transient(circ, undefined, tr.state);
      nt.t = tr.t; tr = nt; tr.discontinuity();
    }
    const r = tr.advance(c.frame);
    for (const [cid, want] of Object.entries(row)) {
      for (const kind of ['v', 'i']) {
        for (const [term, val] of Object.entries(want[kind])) {
          const got = r[cid][kind === 'v' ? 'voltages' : 'currents'][term];
          close(got, val, `${name} frame ${f} ${cid}.${kind}.${term}`);
          worst = Math.max(worst, Math.abs(got - val)); checked++;
        }
      }
      close(r[cid].power, want.p, `${name} ${cid} power`);
      for (const k of ['region', 'conducting', 'overload']) assert.equal(r[cid][k], want[k], `${name} ${cid} ${k}`);
    }
  });
}
console.log(`python fixture: ${checked} values in ${Object.keys(fx.cases).length} circuits, max |js - py| = ${worst.toExponential(2)}`);

// hand-calculable checks
const ex = n => structuredClone(fx.cases[n].circuit);
{ const r = new Transient(ex('voltage_divider')).advance(1e-3);
  assert.ok(Math.abs(r.resistor_1.voltages.p2 - 5) < 1e-6, 'divider midpoint 5 V');
  assert.ok(Math.abs(r.dc_source_1.currents.pos + 0.005) < 1e-9, 'source delivers 5 mA'); }
{ const tr = new Transient(ex('rc_circuit'));
  const r = tr.advance(1e-3), vc = r.capacitor_1.voltages.p1;
  assert.ok(Math.abs(vc / (5 * (1 - Math.exp(-1))) - 1) < 0.01, `RC at tau: ${vc}`); }
{ const r = new Transient(ex('led_circuit')).advance(1e-3);
  assert.ok(Math.abs(r.led_1.currents.anode - 3 / 220.1) < 1e-9, 'LED current'); }
{ const c = ex('voltage_divider');  // two sources in parallel with different voltages: singular
  c.components.dc_source_2 = { ...structuredClone(c.components.dc_source_1), id: 'dc_source_2', properties: { voltage: 3 } };
  assert.throws(() => new Transient(c).advance(1e-3), CircuitError); }

// units
assert.equal(parseValue('4.7k'), 4700);
assert.equal(parseValue('10u'), 1e-5);
assert.equal(parseValue('1 µF', 'F'), 1e-6);
assert.equal(parseValue('2.2 MΩ', 'Ω'), 2.2e6);
assert.equal(parseValue('100m'), 0.1);
assert.equal(parseValue('-3.3'), -3.3);
assert.ok(Number.isNaN(parseValue('abc')));
assert.equal(formatValue(0.0047, 'A'), '4.7 mA');
assert.equal(formatValue(1000, 'Ω'), '1 kΩ');
assert.equal(formatValue(0, 'V'), '0 V');
console.log('circuit engine tests: ok');

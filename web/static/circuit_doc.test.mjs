// node web/static/circuit_doc.test.mjs — the editor's circuit document: terminals, wiring, delete, .circuit save/load.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { CircuitDoc, pyRound, rotateOffset } from './circuit_doc.js';
import { formatValue, parseValue } from './units.js';

const fx = JSON.parse(readFileSync(new URL('../../tests/fixtures/engine_fixture.json', import.meta.url)));
const catalog = Object.entries(fx.terminals).map(([type, terms]) => ({
  type, size: [1, 1], defaults: { ...fx.defaults[type], ...(fx.ratings[type] || {}) },
  connections: Object.fromEntries(terms.map((t, k) => [t, type === 'BJT' ? [[0, 1.5], [-1.5, 0], [0, -1.5]][k]
    : type === 'Ground' ? [0, -0.5] : (type.endsWith('Source') ? [[0, 1.5], [0, -1.5]][k] : [[-1.5, 0], [1.5, 0]][k])])),
}));

// Python round() and BaseComponent._rotate_point
assert.deepEqual([pyRound(1.5), pyRound(-1.5), pyRound(0.5), pyRound(-0.5), pyRound(2.5)].map(x => x + 0), [2, -2, 0, 0, 2]);
assert.deepEqual(rotateOffset([-1.5, 0], 90), [0, -2]);
assert.deepEqual(rotateOffset([0, 1.5], 180), [0, -2]);

const doc = new CircuitDoc(catalog);
const v = doc.add('DCVoltageSource', 5, 12, 180), r = doc.add('Resistor', 12, 8), g = doc.add('Ground', 12, 17);
assert.deepEqual(doc.terminals(v), { pos: [5, 10], neg: [5, 14] });
assert.ok(doc.connect(v, 'pos', r, 'p1'));
assert.ok(!doc.connect(r, 'p1', v, 'pos'), 'duplicate wire refused');
assert.ok(!doc.connect(r, 'p1', r, 'p2'), 'self wire refused');
doc.connect(r, 'p2', g, 'gnd'); doc.connect(v, 'neg', g, 'gnd');
assert.equal(doc.wires().length, 3);
doc.rotate(r); assert.equal(doc.components[r].rotation, 90);
doc.rotate(r, -180); assert.equal(doc.components[r].rotation, 270);

// save -> load keeps parts, values and both sides of every wire; no "state" is written
doc.components[r].properties.resistance = parseValue('4.7 kΩ', 'Ω');
const file = JSON.parse(JSON.stringify(doc.toFile()));
assert.ok(Object.values(file.components).every(c => c.type && !('state' in c)));
const back = new CircuitDoc(catalog);
assert.equal(back.load(file), 0);
assert.equal(back.components[r].properties.resistance, 4700);
assert.equal(back.wires().length, 3);

// a one-sided link in a file is made two-sided; a link to a missing part is dropped
const oneSided = structuredClone(file);
oneSided.components[g].connected_to = {};
oneSided.components[r].connected_to.p1.push(['nope_1', 'p1']);
back.load(oneSided);
assert.ok(back.connected(g, 'gnd', r, 'p2'));
assert.ok(!back.components[r].connected_to.p1.some(([o]) => o === 'nope_1'));

// deleting a part removes its wires from the other parts
doc.remove(r);
assert.equal(doc.wires().length, 1);
assert.ok(!(doc.components[v].connected_to.pos || []).length);

// values shown in the property editor parse back to the same number
for (const [val, unit] of [[0.5, 'A'], [1e-6, 'F'], [4700, 'Ω'], [0.02, 'A'], [1000, 'Hz'], [2.2e6, 'Ω']]) {
  assert.equal(parseValue(formatValue(val, unit, 6), unit), val, `${val} ${unit}`);
}
console.log('circuit doc tests: ok');

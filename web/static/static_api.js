// Static-site data layer: answers api() GETs from the JSON files exported by scripts/build_static.py
// (api/info.json, api/components.json, api/examples.json, api/examples/<name>.json). POST /simulate is answered in the
// browser by the JS port of the Python engine (transient_engine.js), which the node tests hold to the Python results.
import { Transient } from './transient_engine.js';

const files = new Map();
function file(rel) {
  if (!files.has(rel)) {
    files.set(rel, fetch('api/' + rel + '.json').then(r => { if (!r.ok) throw new Error(`${r.status} ${rel}`); return r.json(); }));
  }
  return files.get(rel);
}

export async function staticApi(path, body) {
  const clean = path.split('?')[0].replace(/^\/+/, '');
  if (clean === 'simulate' && body) {
    const tr = new Transient(body.circuit), rows = [], t = [];
    for (let k = 0; k < body.frames; k++) { rows.push(tr.advance(body.frame)); t.push(tr.t); }
    return { t, results: rows, converged: tr.converged };
  }
  if (body) throw new Error('This needs the local app (python run_web.py).');
  return file(clean);
}

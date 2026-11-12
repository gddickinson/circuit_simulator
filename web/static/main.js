// Entry point: lazy page modules, footer mode, router.
import { start, lazy, route, app, isStatic, $ } from './core.js';

const PAGES = { 'home.js': ['home'], 'sim.js': ['sim'], 'examples.js': ['examples'], 'about.js': ['about'] };
lazy(Object.fromEntries(Object.entries(PAGES).flatMap(([file, names]) => names.map(n => [n, () => import('./' + file)]))));

route('notfound', () => { app().innerHTML = '<h1>Not found</h1><p><a href="#/">Back to the start</a></p>'; });

$('#mode').textContent = isStatic()
  ? 'static site: the simulator runs entirely in your browser'
  : 'local app: browser engine + Python engine at /api';
start();

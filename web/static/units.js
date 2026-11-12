// SI-prefix parsing and formatting for component values ("4.7k", "10 uF", "2.2 MΩ") and live readouts.
const PREFIX = { p: -12, n: -9, u: -6, µ: -6, μ: -6, m: -3, '': 0, k: 3, K: 3, M: 6, G: 9 };  // powers of ten

// Number from text with an optional SI prefix and optional unit (ignored if it matches `unit`). NaN if unreadable.
export function parseValue(text, unit = '') {
  let s = String(text ?? '').trim().replace(/\s+/g, '').replace(/ohms?$/i, '');
  if (unit && s.endsWith(unit)) s = s.slice(0, -unit.length);
  s = s.replace(/[ΩFHVAW°]$|Hz$/, '');
  const m = s.match(/^([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)(meg|MEG|Meg|[pnuµμmkKMG]?)$/);
  if (!m) return NaN;
  const p = m[2].toLowerCase() === 'meg' ? 6 : PREFIX[m[2]];
  if (p === undefined) return NaN;
  return /e/i.test(m[1]) ? Number(m[1]) * 10 ** p : Number(`${m[1]}e${p}`);  // '10u' -> 10e-6 exactly
}

const STEPS = [[1e9, 'G'], [1e6, 'M'], [1e3, 'k'], [1, ''], [1e-3, 'm'], [1e-6, 'µ'], [1e-9, 'n'], [1e-12, 'p']];

// "4.7 mA": three significant figures, trailing zeros trimmed; values below 1 pico-unit print as 0.
export function formatValue(v, unit = '', digits = 3) {
  if (!Number.isFinite(v)) return '—';
  const a = Math.abs(v);
  if (a < 1e-12) return `0 ${unit}`.trim();
  const [scale, pre] = STEPS.find(([s]) => a >= s * 0.9995) || STEPS[STEPS.length - 1];
  const txt = String(Number((v / scale).toPrecision(digits)));
  return `${txt} ${pre}${unit}`.trim();
}

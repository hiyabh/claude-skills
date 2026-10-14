// DOM: toolbar (views | layers), mode switch, side sheet (rooms, finishes, notes, variants, export), captions.
import { el, fmtArea, shoelace } from './util.js';
import { FINISHES } from './materials.js';

const $ = (id) => document.getElementById(id);

const TOGGLES = [
  { id: 'items', label: 'תוויות', modes: ['present', 'work'] },
  { id: 'dims', label: 'מידות', modes: ['present', 'work'] },
  { id: 'ceiling', label: 'תקרה', modes: ['present', 'work'] },
  { id: 'furniture', label: 'ריהוט', modes: ['work'] },
  { id: 'underlay', label: 'שרטוט', modes: ['work'], needs: 'underlay' },
  { id: 'walls', label: 'מזהי קירות', modes: ['work'] },
  { id: 'measure', label: 'מדידה', modes: ['work'] },
  { id: 'notes', label: 'הערות', modes: ['present', 'work'] },
];

function pressed(btn, on) { btn.setAttribute('aria-pressed', String(on)); }

export class UI {
  constructor(app) {
    this.app = app;
    this.mode = 'present';
    this.state = { items: false, dims: false, ceiling: false, furniture: true, underlay: false, walls: false, measure: false, notes: true };
    this.tab = 'rooms';
    this.ref = { joy: $('joy'), hud: $('walkhud'), crosshair: $('crosshair'), room: $('walk-room'), measureHint: $('measure-hint'), pop: $('pop'), labels: $('labels') };
    this.bindChrome();
  }

  bindChrome() {
    document.querySelectorAll('[data-mode]').forEach((b) => b.addEventListener('click', () => this.setMode(b.dataset.mode)));
    $('menu-btn').addEventListener('click', () => this.toggleSheet());
    $('walk-exit').addEventListener('click', () => this.app.exitWalk());
    const info = $('info');
    $('info-toggle').addEventListener('click', (e) => {
      const collapsed = info.classList.toggle('collapsed');
      e.currentTarget.setAttribute('aria-expanded', String(!collapsed));
      e.currentTarget.textContent = collapsed ? '⌄' : '⌃';
    });
    if (innerWidth < 640) $('info-toggle').click();
    addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (this.app.walking) this.app.exitWalk(); this.closeSheet(); } });
  }

  /** Called whenever the plan (variant) changes. */
  render(data) {
    this.data = data;
    const { meta, plan } = data;
    $('eyebrow').textContent = (meta.sheets || []).map((s) => [s.kind, s.date].filter(Boolean).join(' · ')).join('  |  ');
    $('title').textContent = meta.title || 'מודל תלת-מימד';
    $('subtitle').textContent = meta.subtitle || '';
    const net = plan.rooms.filter((r) => !['balcony', 'garden'].includes(r.type)).reduce((s, r) => s + shoelace(r.polygon), 0);
    $('area-total').textContent = `${fmtArea(net)} נטו`;
    document.title = meta.title || document.title;
    this.renderToolbar();
    this.renderSheet();
  }

  renderToolbar() {
    const views = $('views');
    views.replaceChildren();
    for (const v of this.app.views) {
      const b = el('button', 'tb press', v.label);
      b.dataset.view = v.id;
      b.addEventListener('click', () => this.app.goView(v.id));
      views.append(b);
    }
    const walk = el('button', 'tb press', 'סיור בדירה');
    walk.addEventListener('click', () => this.app.enterWalk());
    views.append(walk);
    if (this.mode === 'present') {
      const tour = el('button', 'tb press', 'סיור מודרך');
      tour.addEventListener('click', () => this.app.startTour());
      views.append(tour);
    }
    this.markView(this.app.currentView);
    this.renderToggles();
  }

  renderToggles() {
    const box = $('toggles');
    box.replaceChildren();
    for (const t of TOGGLES) {
      if (!t.modes.includes(this.mode) || (t.needs && !this.data[t.needs])) continue;
      const b = el('button', 'tb toggle press', t.label);
      if (t.id === 'notes' && this.data.notes.length) b.append(el('span', 'badge', String(this.data.notes.length)));
      pressed(b, !!this.state[t.id]);
      b.addEventListener('click', () => {
        this.state[t.id] = !this.state[t.id];
        pressed(b, this.state[t.id]);
        this.app.setLayer(t.id, this.state[t.id]);
      });
      box.append(b);
    }
  }

  markView(id) {
    document.querySelectorAll('[data-view]').forEach((b) => pressed(b, b.dataset.view === id));
  }

  setMode(mode) {
    this.mode = mode;
    document.querySelectorAll('[data-mode]').forEach((b) => pressed(b, b.dataset.mode === mode));
    const work = mode === 'work';
    for (const id of ['dims', 'items']) { this.state[id] = work; this.app.setLayer(id, work); }
    if (!work) for (const id of ['walls', 'measure', 'underlay']) { this.state[id] = false; this.app.setLayer(id, false); }
    if (!work && !this.state.furniture) { this.state.furniture = true; this.app.setLayer('furniture', true); }
    this.renderToolbar();
    this.renderSheet();
  }

  toggleSheet() { return $('sheet').classList.contains('closed') ? this.openSheet() : this.closeSheet(); }

  openSheet(tab) {
    if (tab) this.tab = tab;
    this.renderSheet();
    $('sheet').classList.remove('closed');
    $('sheet').setAttribute('aria-hidden', 'false');
    $('menu-btn').setAttribute('aria-expanded', 'true');
  }

  closeSheet() {
    $('sheet').classList.add('closed');
    $('sheet').setAttribute('aria-hidden', 'true');
    $('menu-btn').setAttribute('aria-expanded', 'false');
  }

  renderSheet() {
    const tabs = [['rooms', 'חדרים'], ['finish', 'גימור'], ['notes', 'הערות']];
    if (this.data.variants.length > 1) tabs.push(['variants', 'חלופות']);
    tabs.push(['export', 'ייצוא']);
    if (!tabs.some(([id]) => id === this.tab)) this.tab = 'rooms';
    const bar = $('tabs');
    bar.replaceChildren(...tabs.map(([id, label]) => {
      const b = el('button', 'press', label);
      b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', String(id === this.tab));
      b.addEventListener('click', () => { this.tab = id; this.renderSheet(); });
      return b;
    }));
    $('pane').replaceChildren(...this[`pane_${this.tab}`]());
  }

  pane_rooms() {
    const { plan } = this.data;
    const list = el('ul', 'list');
    const rooms = [...plan.rooms].sort((p, q) => shoelace(q.polygon) - shoelace(p.polygon));
    for (const r of rooms) {
      const row = el('button', 'row press');
      row.append(el('span', null, r.label || r.type), el('span', 'meta num', fmtArea(shoelace(r.polygon))));
      row.addEventListener('click', () => { this.app.flyToRoom(r.id); if (innerWidth < 640) this.closeSheet(); });
      const li = el('li');
      li.append(row);
      list.append(li);
    }
    const net = rooms.filter((r) => !['balcony', 'garden'].includes(r.type)).reduce((s, r) => s + shoelace(r.polygon), 0);
    const total = el('div', 'total');
    total.append(el('span', null, 'סה״כ נטו (ללא מרפסות)'), el('span', 'num', fmtArea(net)));
    const stated = plan.checks?.stated_total_m2;
    const out = [el('h2', null, 'חדרים ושטחים'), list, total];
    if (stated) out.push(el('p', 'empty', `שטח הדירה לפי הגיליון: ${stated} מ״ר (כולל קירות)`));
    return out;
  }

  pane_finish() {
    const out = [];
    const names = { floor: 'ריצוף', cabinet: 'חזיתות נגרות', counter: 'משטח עבודה' };
    for (const kind of Object.keys(FINISHES)) {
      out.push(el('h2', null, names[kind]));
      const row = el('div', 'swatches');
      for (const f of FINISHES[kind]) {
        const b = el('button', 'swatch press');
        const chipEl = el('i'); chipEl.style.background = f.swatch;
        b.append(chipEl, el('span', null, f.label));
        pressed(b, this.app.finishes[kind] === f.id);
        b.addEventListener('click', () => { this.app.setFinish(kind, f.id); this.renderSheet(); });
        row.append(b);
      }
      out.push(row);
    }
    return out;
  }

  pane_notes() {
    const notes = this.data.notes;
    if (!notes.length) return [el('p', 'empty', 'אין הערות פתוחות לתוכנית הזו.')];
    const list = el('ul', 'list');
    notes.forEach((n, i) => {
      const row = el('button', 'note press');
      const pin = el('span', `pin ${n.kind === 'question' ? '' : 'assumption'}`, String(i + 1));
      const body = el('div');
      body.append(el('small', null, n.kind === 'question' ? 'שאלה פתוחה' : 'הנחה'), el('p', null, n.text));
      row.append(pin, body);
      row.addEventListener('click', () => this.app.flyToNote(n));
      const li = el('li');
      li.append(row);
      list.append(li);
    });
    return [el('h2', null, 'הנחות ושאלות לאדריכל'), list];
  }

  pane_variants() {
    const list = el('div', 'actions');
    this.data.variants.forEach((v, i) => {
      const b = el('button', 'action press');
      b.append(el('span', null, v.name), el('span', 'meta', i === this.app.variant ? 'מוצגת' : ''));
      b.addEventListener('click', () => this.app.setVariant(i));
      list.append(b);
    });
    return [el('h2', null, 'חלופות תכנון'), list];
  }

  pane_export() {
    const status = el('p', 'empty', 'הקבצים נוצרים בדפדפן שלך.');
    const act = (label, sub, fn) => {
      const b = el('button', 'action press');
      b.append(el('span', null, label), el('span', 'meta', sub));
      b.addEventListener('click', async () => { status.textContent = 'מכין קובץ...'; status.textContent = await fn(); });
      return b;
    };
    const box = el('div', 'actions');
    box.append(
      act('מודל תלת-מימד', 'GLB · ל-SketchUp / Blender', () => this.app.exportModel()),
      act('צילום של המבט הנוכחי', 'PNG', () => this.app.exportImage()),
      act('נתוני התוכנית', 'plan.json', () => this.app.exportPlan()),
    );
    return [el('h2', null, 'ייצוא'), box, status];
  }

  caption(text, sub) {
    const c = $('caption');
    if (!text) { c.classList.add('closed'); return; }
    c.replaceChildren(document.createTextNode(text), ...(sub ? [el('small', null, sub)] : []));
    c.classList.remove('closed');
  }

  fail(message) {
    $('state-loading').hidden = true;
    $('error-text').textContent = message;
    $('state-error').hidden = false;
  }

  ready() { $('state-loading').classList.add('done'); }
}

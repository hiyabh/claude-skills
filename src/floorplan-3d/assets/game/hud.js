// Game HUD: start screen, room name + area, minimap with a view cone, time-of-day slider, quality chip,
// the look-to-interact prompt, toasts, and an action button for touch screens.
import { bounds, shoelace, IS_TOUCH } from '../viewer/util.js';
import { QUALITY } from './render.js';

const $ = (id) => document.getElementById(id);
const MAP_PX = 168;
const MAP_PAD = 10;
const ROOM_FILL = { living: '#e9c9a7', kitchen: '#e6d3b3', bedroom: '#d9c2d6', safe_room: '#c9d3e0', bathroom: '#c6dde0',
  toilet: '#c6dde0', hallway: '#e2ddd3', balcony: '#cfdcc0' };
const TOAST_MS = 1800;

const clock = (h) => `${String(Math.floor(h)).padStart(2, '0')}:${String(Math.round((h % 1) * 60) % 60).padStart(2, '0')}`;

export class Hud {
  constructor({ plan, onTime, onQuality, onStart, onAction, onPhoto, onPhotoTraced, onPhotoSave, onPhotoClose }) {
    Object.assign(this, { plan, onTime, onQuality, onStart, onAction });
    this.ref = { joy: $('joy'), hud: $('walkhud'), crosshair: $('reticle'), room: $('room-name'), onLock: (l) => this.setLocked(l) };
    this.initMap();
    $('time').addEventListener('input', (e) => { const h = Number(e.target.value); $('time-label').textContent = clock(h); onTime(h); });
    $('quality').addEventListener('click', () => {
      const names = Object.keys(QUALITY); const next = names[(names.indexOf(this.quality) + 1) % names.length];
      onQuality(next);
    });
    $('start').addEventListener('click', () => this.start());
    $('resume').addEventListener('click', () => this.start());
    $('act').addEventListener('click', () => onAction());
    $('photo').addEventListener('click', () => onPhoto());
    $('photo-pt').addEventListener('click', () => onPhotoTraced());
    $('photo-save').addEventListener('click', () => onPhotoSave());
    $('photo-close').addEventListener('click', () => onPhotoClose());
    if (IS_TOUCH) {
      $('help').textContent = 'ג׳ויסטיק להליכה · גרירה להסתכלות · כפתור לפעולה';
      const touch = ['ג׳ויסטיק בפינה: הליכה', 'גרירה באצבע על המסך: הסתכלות', 'כפתור הפעולה: פתיחת דלת, הדלקת אור, החלפת חומר', 'פס השעה למטה: מבוקר ועד לילה'];
      $('controls').replaceChildren(...touch.map((text) => Object.assign(document.createElement('li'), { textContent: text })));
    }
  }

  start() {
    $('intro').classList.add('closed');
    $('resume').hidden = true;
    this.onStart();
  }

  setLocked(locked) {
    if (!IS_TOUCH && !locked && $('intro').classList.contains('closed')) $('resume').hidden = false;
  }

  photo(state, ratio = 0, label = '', url = null) {
    $('photo-panel').hidden = state === 'closed';
    $('photo-bar').style.transform = `scaleX(${ratio.toFixed(3)})`;
    $('photo-label').textContent = label;
    $('photo-img').hidden = !url;
    if (url) $('photo-img').src = url;
    $('photo-save').hidden = state !== 'done';
  }

  setTime(h) { $('time').value = String(h); $('time-label').textContent = clock(h); }

  setQuality(name) { this.quality = name; $('quality').textContent = `איכות: ${QUALITY[name].label}`; }

  room(room) {
    if (room?.id === this.roomId) return;
    this.roomId = room?.id;
    $('room-name').textContent = room ? room.label : '';
    $('room-area').textContent = room ? `${shoelace(room.polygon).toFixed(1)} מ״ר` : '';
  }

  prompt(label) {
    $('prompt').hidden = !label;
    $('act').hidden = !label || !IS_TOUCH;
    if (label) { $('prompt-text').textContent = label; $('act').textContent = label; }
  }

  toast(text, sub) {
    const t = $('toast');
    t.replaceChildren(document.createTextNode(text), Object.assign(document.createElement('small'), { textContent: sub || '' }));
    t.classList.remove('closed');
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => t.classList.add('closed'), TOAST_MS);
  }

  initMap() {
    const canvas = $('minimap');
    const dpr = Math.min(devicePixelRatio, 2);
    canvas.width = canvas.height = MAP_PX * dpr;
    this.ctx = canvas.getContext('2d');
    this.ctx.scale(dpr, dpr);
    const b = bounds(this.plan.walls.flatMap((w) => [w.a, w.b]));
    const span = Math.max(b.maxX - b.minX, b.maxY - b.minY);
    this.k = (MAP_PX - MAP_PAD * 2) / span;
    this.ox = MAP_PAD + ((MAP_PX - MAP_PAD * 2) - (b.maxX - b.minX) * this.k) / 2 - b.minX * this.k;
    this.oy = MAP_PAD + ((MAP_PX - MAP_PAD * 2) - (b.maxY - b.minY) * this.k) / 2 + b.maxY * this.k;
  }

  mapXY([x, y]) { return [this.ox + x * this.k, this.oy - y * this.k]; }

  minimap(pos, yaw) {
    const g = this.ctx;
    g.clearRect(0, 0, MAP_PX, MAP_PX);
    for (const r of this.plan.rooms) {
      g.beginPath();
      r.polygon.forEach((p, i) => { const [x, y] = this.mapXY(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
      g.closePath();
      g.fillStyle = r.id === this.roomId ? '#f0b46a' : (ROOM_FILL[r.type] || '#ddd');
      g.globalAlpha = r.id === this.roomId ? 0.85 : 0.6;
      g.fill();
    }
    g.globalAlpha = 1; g.strokeStyle = '#2a2622'; g.lineWidth = 2;
    for (const w of this.plan.walls) {
      const [ax, ay] = this.mapXY(w.a); const [bx, by] = this.mapXY(w.b);
      g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke();
    }
    const [px, py] = this.mapXY(pos);
    const a = -yaw - Math.PI / 2;                      // yaw 0 looks north (up on the map)
    g.fillStyle = 'rgba(240, 180, 106, 0.35)';
    g.beginPath(); g.moveTo(px, py); g.arc(px, py, 26, a - 0.5, a + 0.5); g.closePath(); g.fill();
    g.fillStyle = '#c4572f'; g.beginPath(); g.arc(px, py, 4.5, 0, Math.PI * 2); g.fill();
  }
}

// Suggested furniture for rooms the drawing leaves empty. Everything here is marked src:"estimated" and auto:true,
// and anything that would block a door swing, leave its room or collide with existing items is dropped.
import { bounds, insidePoly } from './util.js';

const WALL_GAP = 0.03;
const DOOR_CLEAR = 0.2;   // extra clearance around a door swing
const MIN_PASS = 0.6;     // walking clearance in front of furniture

function sides(room) {
  const b = bounds(room.polygon);
  const mk = (name, x0, y0, x1, y1, nx, ny) => ({ name, x0, y0, x1, y1, nx, ny, len: Math.hypot(x1 - x0, y1 - y0),
    ux: (x1 - x0) / (Math.hypot(x1 - x0, y1 - y0) || 1), uy: (y1 - y0) / (Math.hypot(x1 - x0, y1 - y0) || 1), doors: [] });
  return {
    b,
    list: [mk('S', b.minX, b.minY, b.maxX, b.minY, 0, 1), mk('N', b.minX, b.maxY, b.maxX, b.maxY, 0, -1),
      mk('W', b.minX, b.minY, b.minX, b.maxY, 1, 0), mk('E', b.maxX, b.minY, b.maxX, b.maxY, -1, 0)],
  };
}

function markDoors(sideList, room, openings) {
  for (const o of openings) {
    if (o.kind === 'window' || !(o.rooms || []).includes(room.id)) continue;
    for (const s of sideList) {
      const t = (o.center[0] - s.x0) * s.ux + (o.center[1] - s.y0) * s.uy;
      const off = Math.abs((o.center[0] - s.x0) * s.nx + (o.center[1] - s.y0) * s.ny);
      if (off < 0.35 && t > -0.2 && t < s.len + 0.2) s.doors.push({ t, w: o.width });
    }
  }
}

function depthAcross(side, b) {
  return side.name === 'S' || side.name === 'N' ? b.maxY - b.minY : b.maxX - b.minX;
}

function place(side, t, w, d, h, kind, extra = {}) {
  const out = d / 2 + WALL_GAP + (extra.out || 0);
  return {
    kind, size: [w, d, h], z: 0, rot: Math.atan2(side.ny, side.nx),
    center: [side.x0 + side.ux * t + side.nx * out, side.y0 + side.uy * t + side.ny * out],
    src: 'estimated', auto: true, tier: 'furniture', label: extra.label || '',
  };
}

function freeSpan(side, width) {
  // Centre an item of this width on the side, nudged away from doors on it.
  let t = side.len / 2;
  for (const d of side.doors) if (Math.abs(d.t - t) < (d.w + width) / 2 + 0.1) t = d.t < side.len / 2 ? d.t + (d.w + width) / 2 + 0.1 : d.t - (d.w + width) / 2 - 0.1;
  return t > width / 2 && t < side.len - width / 2 ? t : null;
}

function candidateSides(list, b, need, exclude = []) {
  const ok = list.filter((s) => !exclude.includes(s) && depthAcross(s, b) >= need);
  return ok.sort((p, q) => (p.doors.length - q.doors.length) || (q.len - p.len));
}

/**
 * The first side + candidate whose anchor piece fits, so an occupied wall (the kitchen, a door swing) is skipped.
 * build(side) returns candidate groups, best first; each group's first item is its anchor.
 */
function firstFitting(sidesList, build, fits) {
  for (const side of sidesList) {
    for (const items of build(side)) {
      if (items.length && fits(items[0])) return { side, items };
    }
  }
  return null;
}

/** Positions along a side to try: clear of doors first, then a third and two thirds along. */
function spans(side, width) {
  const ts = [freeSpan(side, width), side.len * 0.35, side.len * 0.65];
  return ts.filter((t) => t != null && t > width / 2 && t < side.len - width / 2);
}

function bedFor(S, area) {
  return (head) => {
    const bw = area >= 9 && head.len >= 2.6 ? 1.6 : 0.9;
    return spans(head, bw + 0.9).map((t) => {
      const items = [place(head, t, bw, 2.0, 0.55, 'bed', { label: bw > 1 ? 'מיטה זוגית' : 'מיטה' })];
      for (const k of [-1, 1]) items.push(place(head, t + k * (bw / 2 + 0.28), 0.45, 0.4, 0.5, 'nightstand'));
      return items;
    });
  };
}

function bedroom(room, S, fits) {
  const area = (S.b.maxX - S.b.minX) * (S.b.maxY - S.b.minY);
  const found = firstFitting(candidateSides(S.list, S.b, 2.0 + MIN_PASS), bedFor(S, area), fits);
  if (!found) return [];
  const { side: head, items } = found;
  const store = candidateSides(S.list.filter((s) => s.nx !== -head.nx || s.ny !== -head.ny), S.b, 0.6 + MIN_PASS + 0.4, [head])[0];
  if (store && room.type !== 'safe_room') {
    const ww = Math.min(2.2, store.len - 0.9);
    const tw = ww > 0.9 ? freeSpan(store, ww) : null;
    if (tw != null) items.push(place(store, tw, ww, 0.6, 2.4, 'wardrobe', { label: 'ארון בגדים' }));
  } else if (store) {
    const td = freeSpan(store, 1.2);
    if (td != null) items.push(place(store, td, 1.2, 0.6, 0.75, 'desk', { label: 'שולחן עבודה' }), place(store, td, 0.44, 0.44, 0.9, 'chair', { out: 0.55 }));
  }
  return items;
}

const SOFA_WIDTHS = [2.4, 2.0, 1.6];

function sofaGroup(side) {
  const groups = [];
  for (const sw of SOFA_WIDTHS.filter((w) => w <= side.len - 0.6)) {
    for (const t of spans(side, sw)) {
      groups.push([
        place(side, t, sw, 0.92, 0.8, 'sofa', { label: 'ספה' }),
        place(side, t, 1.1, 0.6, 0.4, 'coffee_table', { out: 0.92 + 0.42 }),
        place(side, t, Math.min(2.6, sw + 0.4), 1.9, 0.01, 'rug', { out: 0.55 }),
      ]);
    }
  }
  return groups;
}

function living(room, S, fits) {
  const found = firstFitting(candidateSides(S.list, S.b, 3.0), sofaGroup, fits);
  if (!found) return [];
  const { side: sofaSide, items } = found;
  const across = depthAcross(sofaSide, S.b);
  const opposite = S.list.find((s) => s.nx === -sofaSide.nx && s.ny === -sofaSide.ny);
  if (opposite && across >= 3.4) {
    const tt = freeSpan(opposite, 1.8);
    if (tt != null) items.push(place(opposite, tt, 1.8, 0.42, 0.5, 'tv_unit', { label: 'מזנון וטלוויזיה' }));
  }
  items.push(place(sofaSide, 0.35, 0.5, 0.5, 1.1, 'plant'));
  return items;
}

function balcony(room, S, fits) {
  const base = { src: 'estimated', auto: true, tier: 'furniture', z: 0, label: '' };
  const wide = S.b.maxX - S.b.minX >= S.b.maxY - S.b.minY;   // chairs go along the long axis
  const [dx, dy] = wide ? [0.62, 0] : [0, 0.62];
  const cy = (S.b.minY + S.b.maxY) / 2; const cx = (S.b.minX + S.b.maxX) / 2;
  // Try the middle, then the ends and the far edges: a sliding door often claims the middle.
  const along = wide ? [cx, S.b.minX + 1.1, S.b.maxX - 1.1] : [cy, S.b.minY + 1.1, S.b.maxY - 1.1];
  const across = wide ? [cy, S.b.maxY - 0.5, S.b.minY + 0.5] : [cx, S.b.maxX - 0.5, S.b.minX + 0.5];
  const spots = across.flatMap((c) => along.map((a) => (wide ? [a, c] : [c, a])));
  const set = ([x, y]) => [
    { ...base, kind: 'outdoor_table', center: [x, y], size: [0.7, 0.7, 0.72], rot: 0 },
    { ...base, kind: 'outdoor_chair', center: [x + dx, y + dy], size: [0.44, 0.44, 0.9], rot: Math.atan2(-dy, -dx) },
    { ...base, kind: 'outdoor_chair', center: [x - dx, y - dy], size: [0.44, 0.44, 0.9], rot: Math.atan2(dy, dx) },
  ];
  const chosen = spots.map(set).find((g) => g.every(fits)) || [];
  return [...chosen, { ...base, kind: 'plant', center: [S.b.minX + 0.35, S.b.maxY - 0.35], size: [0.5, 0.5, 1.1], rot: 0 }];
}

const LAYOUTS = { bedroom, safe_room: bedroom, living, balcony };
// A room that already has its anchor piece drawn on the sheet is left alone.
const ANCHOR = { bedroom: 'bed', safe_room: 'bed', living: 'sofa', balcony: 'outdoor_table' };

function footprint(item) {
  const [w, d] = item.size; const r = item.rot;
  const fx = Math.cos(r); const fy = Math.sin(r);
  return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, o]) => [
    item.center[0] - fy * a * w / 2 + fx * o * d / 2, item.center[1] + fx * a * w / 2 + fy * o * d / 2]);
}

function overlaps(item, others) {
  const fp = footprint(item);
  return others.some((o) => o.kind !== 'rug' && item.kind !== 'rug' && (fp.some((p) => insidePoly(p, footprint(o))) || footprint(o).some((p) => insidePoly(p, fp))));
}

/** The floor a door needs: its opening, as deep as the leaf (both sides), plus a little elbow room. */
function doorZones(plan) {
  const walls = Object.fromEntries(plan.walls.map((w) => [w.id, w]));
  return plan.openings.filter((o) => o.kind !== 'window' && walls[o.wall]).map((o) => {
    const w = walls[o.wall];
    const len = Math.hypot(w.b[0] - w.a[0], w.b[1] - w.a[1]) || 1;
    const ux = (w.b[0] - w.a[0]) / len; const uy = (w.b[1] - w.a[1]) / len;
    const depth = o.style === 'sliding' ? MIN_PASS + 0.2 : o.width + DOOR_CLEAR;
    const half = o.width / 2 + 0.1;
    const zone = [[-half, -depth], [half, -depth], [half, depth], [-half, depth]].map(([a, n]) => [
      o.center[0] + ux * a - uy * n, o.center[1] + uy * a + ux * n]);
    return zone;
  });
}

function blocksDoor(item, zones) {
  const fp = footprint(item);
  return zones.some((z) => fp.some((p) => insidePoly(p, z)) || z.some((p) => insidePoly(p, fp)));
}

/** Suggested furniture for each room that has no drawn furniture of its own. */
export function autoFurnish(plan, existing) {
  const out = [];
  const zones = doorZones(plan);
  for (const room of plan.rooms) {
    const layout = LAYOUTS[room.type];
    if (!layout || existing.some((e) => e.room === room.id && e.kind === ANCHOR[room.type])) continue;
    const S = sides(room);
    markDoors(S.list, room, plan.openings);
    const fits = (item) => (item.kind === 'rug' || footprint(item).every((p) => insidePoly(p, room.polygon)))
      && (item.kind === 'rug' || !blocksDoor(item, zones)) && !overlaps(item, [...existing, ...out]);
    for (const item of layout(room, S, fits)) {
      item.room = room.id;
      item.id = `auto.${room.id}.${out.length + 1}`;
      if (fits(item)) out.push(item);
    }
  }
  return out;
}

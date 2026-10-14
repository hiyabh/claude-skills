// Shared by the viewer's walk mode and game mode.
import { centroid, shoelace, insidePoly } from './util.js';

/** Where walk mode starts: just inside the entrance, facing in; otherwise the biggest room. */
export function walkStart(plan) {
  const door = plan.openings.find((o) => o.entrance) || plan.openings.find((o) => o.kind === 'door');
  const wall = door && plan.walls.find((w) => w.id === door.wall);
  if (wall) {
    const len = Math.hypot(wall.b[0] - wall.a[0], wall.b[1] - wall.a[1]);
    const ux = (wall.b[0] - wall.a[0]) / len; const uy = (wall.b[1] - wall.a[1]) / len;
    for (const s of [1, -1]) {
      const x = door.center[0] - uy * 0.75 * s; const y = door.center[1] + ux * 0.75 * s;
      if (plan.rooms.some((r) => insidePoly([x, y], r.polygon))) return { x, y, yaw: Math.atan2(uy * s, ux * s) };
    }
  }
  const room = [...plan.rooms].sort((p, q) => shoelace(q.polygon) - shoelace(p.polygon))[0];
  const [x, y] = centroid(room.polygon);
  return { x, y, yaw: 0 };
}

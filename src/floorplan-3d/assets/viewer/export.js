// Exports: the 3D model (GLB, zipped inside an Artifact), a PNG of the current view, and plan.json.
// Inside a claude.ai Artifact files go through the `downloads` capability (the viewer confirms each save);
// a local file falls back to an ordinary <a download>.
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';

let downloads;

async function capability() {
  if (downloads !== undefined) return downloads;
  downloads = window.claude?.use ? await window.claude.use('downloads').catch(() => null) : null;
  return downloads;
}

function anchorSave(filename, blob) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

/** Returns a short Hebrew status line for the UI. */
export async function save(filename, blob) {
  const dl = await capability();
  if (!dl) { anchorSave(filename, blob); return 'הקובץ ירד'; }
  try {
    await dl.save({ filename, data: blob });
    return 'הקובץ נשמר';
  } catch (err) {
    if (err?.code === 'declined') return 'השמירה בוטלה';
    if (err?.code === 'rate_limited') return 'חלון שמירה כבר פתוח';
    return 'לא ניתן לשמור קבצים בתצוגה הזו';
  }
}

export async function exportModel(root, name) {
  const glb = await new GLTFExporter().parseAsync(root, { binary: true, onlyVisible: true });
  const dl = await capability();
  if (!dl) return save(`${name}.glb`, new Blob([glb], { type: 'model/gltf-binary' }));
  // .glb is not on the downloads allowlist; a zip is.
  const { zipSync } = await import('fflate');
  const zipped = zipSync({ [`${name}.glb`]: new Uint8Array(glb) });
  return save(`${name}.zip`, new Blob([zipped], { type: 'application/zip' }));
}

export async function exportImage(renderer, render, name) {
  render();
  const blob = await new Promise((resolve) => renderer.domElement.toBlob(resolve, 'image/png'));
  return blob ? save(`${name}.png`, blob) : 'צילום המסך נכשל - נסה שוב';
}

export function exportPlan(plan, name) {
  return save(`${name}.plan.json`, new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' }));
}

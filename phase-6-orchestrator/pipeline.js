/**
 * Phase 6 pipeline runner: orchestrates P1–P5 by spawning their run scripts sequentially.
 */

import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function runCommand(command, args, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      stdio: 'inherit',
      shell: false,
    });
    child.on('error', reject);
    child.on('exit', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} ${args.join(' ')} exited with code ${code}`));
    });
  });
}

/**
 * Run the full weekly pipeline: P1→P2→P3→P4→P5.
 * Assumes each phase has a `run.js` at its root (as implemented).
 */
export async function runWeeklyPipeline() {
  const root = path.join(__dirname, '..');
  const phases = [
    { name: 'Phase 1 (Ingest)', cwd: path.join(root, 'phase-1-ingest'), args: ['run.js'] },
    { name: 'Phase 2 (Clean)', cwd: path.join(root, 'phase-2-clean'), args: ['run.js'] },
    { name: 'Phase 3 (Analyze)', cwd: path.join(root, 'phase-3-analyze'), args: ['run.js'] },
    { name: 'Phase 4 (Report)', cwd: path.join(root, 'phase-4-report'), args: ['run.js'] },
    { name: 'Phase 5 (Email)', cwd: path.join(root, 'phase-5-email'), args: ['run.js'] },
  ];

  for (const p of phases) {
    console.log(`\n[Phase 6] Starting ${p.name}...`);
    await runCommand('node', p.args, p.cwd);
    console.log(`[Phase 6] Completed ${p.name}.`);
  }
}


import { FormEvent, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';

/**
 * Calls the Rust `run_kurt_cli` command (src-tauri/src/lib.rs), which shells
 * out to the locally installed `kurt` CLI in one-off-prompt mode. This is
 * deliberately not a re-implementation of desktop automation — kurt's own
 * computer_use/app_launcher/agent tool-calling (already tested elsewhere in
 * this project) is reused as-is for anything that needs to happen on this
 * machine, per the approved plan's Phase 3 design.
 */
export default function LocalBridge() {
  const [prompt, setPrompt] = useState('');
  const [output, setOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = prompt.trim();
    if (!text || running) return;
    setRunning(true);
    setError(null);
    setOutput(null);
    try {
      const result = await invoke<string>('run_kurt_cli', { prompt: text });
      setOutput(result);
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Hindi na-run ang kurt CLI.');
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="kurt-card" style={{ marginTop: 16 }}>
      <h2>Local bridge</h2>
      <p>
        Direktang tumatawag ito sa naka-install na <code>kurt</code> CLI sa makinang ito — kaya kong buksan ng app,
        i-type, o kontrolin ang desktop mo, gamit ang existing at tested na capabilities ni Kurt (hindi bagong
        automation code).
      </p>
      <form onSubmit={handleSubmit}>
        <input
          className="kurt-field"
          placeholder='hal. "buksan ang Notes"'
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          disabled={running}
        />
        <button className="kurt-button" type="submit" disabled={running || !prompt.trim()}>
          {running ? 'Tumatakbo…' : 'Run via local kurt CLI'}
        </button>
      </form>
      {error && <div className="kurt-error">{error}</div>}
      {output && (
        <pre style={{ whiteSpace: 'pre-wrap', overflowX: 'auto', fontSize: '0.85em' }}>{output}</pre>
      )}
    </div>
  );
}

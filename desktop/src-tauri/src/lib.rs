use std::process::Command;

/// The "local bridge": instead of re-implementing desktop automation in
/// Rust/JS, this shells out to the already-installed, already-tested `kurt`
/// CLI (kurt.main:run, see pyproject.toml's [project.scripts]) in its normal
/// one-off-prompt mode. Everything kurt can already do on this machine
/// (open apps, files, computer_use, agent tool-calling, its own safety
/// checks) is reused as-is — this command adds no new automation surface of
/// its own.
///
/// stdin is left closed (the default for Command::output()), which is exact-
/// ly what makes `kurt "<prompt>"` exit cleanly after one reply instead of
/// waiting for further interactive input — kurt's own chat loop catches EOF
/// on stdin and exits ("👋 Bye!"). Verified manually with
/// `kurt "..." < /dev/null` before wiring this up.
#[tauri::command]
fn run_kurt_cli(prompt: String) -> Result<String, String> {
    let trimmed = prompt.trim();
    if trimmed.is_empty() {
        return Err("empty_prompt".into());
    }
    let output = Command::new("kurt")
        .arg(trimmed)
        .output()
        .map_err(|err| format!("kurt_not_found: {err}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
    if output.status.success() {
        Ok(stdout)
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
        Err(if stderr.trim().is_empty() { stdout } else { stderr })
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![run_kurt_cli])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

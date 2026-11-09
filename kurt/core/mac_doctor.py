"""
KURT Cross-Platform Host Machine Doctor & System Control
Auto-adapts to the host operating system (macOS, Windows, or Linux):
  - Hardware, OS, CPU load, RAM, disk, and power/battery overview
  - Top CPU & RAM processes (ps on macOS/Linux, PowerShell Get-Process / tasklist on Windows)
  - Disk usage & SMART status (diskutil on macOS, Get-PhysicalDisk/wmic on Windows, lsblk/df on Linux)
  - Network ports, interfaces & DNS (lsof/ifconfig/scutil on macOS, netstat/ipconfig on Windows, ss/ip/resolv on Linux)
  - Crash logs & system error events (DiagnosticReports on macOS, CrashDumps/EventLog on Windows, /var/crash & journalctl on Linux)
  - Startup items (LaunchAgents on macOS, Registry/Startup on Windows, autostart/systemd on Linux)
  - Native file manager folder open/reveal (Finder on macOS, Explorer on Windows, xdg-open/gio on Linux)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from kurt.utils.security import child_env, redact, sensitive_path

OS = platform.system()  # "Darwin" | "Windows" | "Linux"


def get_os_profile() -> dict:
    """
    Auto-detect the host operating system, shell, package manager, file manager,
    shortcut modifier key, and automation backend.
    """
    system = platform.system()
    if system == "Darwin":
        os_label = "macOS"
        file_manager = "Finder"
        mod_key = "cmd"
        shell_name = os.environ.get("SHELL", "/bin/zsh")
        pkg_mgr = "brew" if shutil.which("brew") else "macports" if shutil.which("port") else "none"
        automation = "AppleScript (osascript) / Peekaboo / PyAutoGUI"
    elif system == "Windows":
        os_label = "Windows"
        file_manager = "File Explorer"
        mod_key = "ctrl"
        shell_name = "PowerShell / cmd.exe"
        pkg_mgr = (
            "winget" if shutil.which("winget")
            else "choco" if shutil.which("choco")
            else "scoop" if shutil.which("scoop")
            else "none"
        )
        automation = "PowerShell / PyAutoGUI"
    else:
        os_label = "Linux"
        file_manager = "xdg-open"
        mod_key = "ctrl"
        shell_name = os.environ.get("SHELL", "/bin/bash")
        for candidate in ("apt", "dnf", "pacman", "zypper", "apk", "snap"):
            if shutil.which(candidate):
                pkg_mgr = candidate
                break
        else:
            pkg_mgr = "none"
        automation = "bash / xdotool / wmctrl / PyAutoGUI"

    return {
        "system": system,
        "os_label": os_label,
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "shell": shell_name,
        "package_manager": pkg_mgr,
        "file_manager": file_manager,
        "primary_modifier": mod_key,
        "automation_engine": automation,
    }


def _run_cmd(argv: list[str], timeout: int = 15) -> tuple[int, str, str]:
    """Run a system inspection command safely without shell interpolation."""
    try:
        res = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=child_env(),
        )
        return res.returncode, redact(res.stdout.strip()), redact(res.stderr.strip())
    except subprocess.TimeoutExpired:
        return 124, "", f"Timed out after {timeout}s"
    except Exception as exc:
        return 1, "", redact(str(exc))


def _run_powershell(script: str, timeout: int = 15) -> tuple[int, str, str]:
    """Run a PowerShell command on Windows (or pwsh if installed)."""
    exe = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
    return _run_cmd([exe, "-NoProfile", "-NonInteractive", "-Command", script], timeout=timeout)


def mac_system_summary(os_override: Optional[str] = None) -> dict:
    """Return a comprehensive overview of the host machine (auto-adapts to macOS/Windows/Linux)."""
    current_os = os_override or OS
    profile = get_os_profile()
    info = {
        "os": current_os,
        "os_label": "macOS" if current_os == "Darwin" else "Windows" if current_os == "Windows" else "Linux",
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count() or 1,
        "profile": profile,
    }

    if hasattr(os, "getloadavg"):
        try:
            load1, load5, load15 = os.getloadavg()
            info["load_avg"] = {"1m": round(load1, 2), "5m": round(load5, 2), "15m": round(load15, 2)}
        except OSError:
            pass

    # Disk space for home drive
    try:
        usage = shutil.disk_usage(Path.home())
        info["disk"] = {
            "total_gb": round(usage.total / (1024 ** 3), 1),
            "used_gb": round(usage.used / (1024 ** 3), 1),
            "free_gb": round(usage.free / (1024 ** 3), 1),
            "percent_used": round((usage.used / usage.total) * 100, 1) if usage.total else 0.0,
        }
    except OSError:
        pass

    if current_os == "Darwin":
        _, sw_vers, _ = _run_cmd(["sw_vers"])
        if sw_vers:
            info["os_details"] = sw_vers

        _, uptime_out, _ = _run_cmd(["uptime"])
        if uptime_out:
            info["uptime"] = uptime_out

        _, vm_out, _ = _run_cmd(["vm_stat"])
        if vm_out:
            info["memory_details"] = vm_out

        _, batt_out, _ = _run_cmd(["pmset", "-g", "batt"])
        if batt_out:
            info["power"] = batt_out

    elif current_os == "Linux":
        os_rel = Path("/etc/os-release")
        if os_rel.exists():
            try:
                info["os_details"] = redact(os_rel.read_text(encoding="utf-8", errors="replace").strip())
            except Exception:
                pass
        _, uptime_out, _ = _run_cmd(["uptime"])
        if uptime_out:
            info["uptime"] = uptime_out
        if shutil.which("free"):
            _, free_out, _ = _run_cmd(["free", "-h"])
            if free_out:
                info["memory_details"] = free_out
        # Check Linux power supply
        power_dir = Path("/sys/class/power_supply")
        if power_dir.exists():
            batts = []
            for b in power_dir.glob("BAT*"):
                cap = (b / "capacity").read_text().strip() if (b / "capacity").exists() else "?"
                stat = (b / "status").read_text().strip() if (b / "status").exists() else "?"
                batts.append(f"{b.name}: {cap}% ({stat})")
            if batts:
                info["power"] = "\n".join(batts)

    elif current_os == "Windows":
        ps_script = (
            "$os = Get-CimInstance Win32_OperatingSystem; "
            "$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1; "
            "Write-Output \"OS: $($os.Caption) ($($os.Version))\"; "
            "Write-Output \"FreeRAM_MB: $([math]::Round($os.FreePhysicalMemory/1024, 1)) / TotalRAM_MB: $([math]::Round($os.TotalVisibleMemorySize/1024, 1))\"; "
            "Write-Output \"CPU: $($cpu.Name) (Load: $($cpu.LoadPercentage)%)\""
        )
        rc, out, _ = _run_powershell(ps_script, timeout=10)
        if rc == 0 and out:
            info["os_details"] = out

        rc_b, batt_out, _ = _run_powershell(
            "Get-CimInstance Win32_Battery | ForEach-Object { \"$($_.Name): $($_.EstimatedChargeRemaining)%\" }",
            timeout=8,
        )
        if rc_b == 0 and batt_out:
            info["power"] = batt_out

    return info


def mac_top_processes(sort_by: str = "cpu", limit: int = 10, os_override: Optional[str] = None) -> dict:
    """
    List top resource-consuming processes sorted by 'cpu' or 'mem'.
    Auto-adapts across macOS, Linux, and Windows.
    """
    current_os = os_override or OS
    limit = max(1, min(int(limit), 50))
    sort_key = "mem" if str(sort_by).lower().startswith("m") else "cpu"

    if current_os == "Windows":
        prop = "WorkingSet64" if sort_key == "mem" else "CPU"
        ps_cmd = (
            f"Get-Process | Sort-Object {prop} -Descending | Select-Object -First {limit} "
            "Id, ProcessName, @{Name='CPU_s';Expression={[math]::Round($_.CPU,1)}}, "
            "@{Name='Mem_MB';Expression={[math]::Round($_.WorkingSet64/1MB,1)}} | ConvertTo-Json"
        )
        rc, out, err = _run_powershell(ps_cmd, timeout=10)
        if rc == 0 and out:
            import json
            try:
                raw = json.loads(out)
                if isinstance(raw, dict):
                    raw = [raw]
                processes = [
                    {
                        "user": "local",
                        "pid": str(p.get("Id", "")),
                        "cpu_percent": str(p.get("CPU_s", 0)),
                        "mem_percent": f"{p.get('Mem_MB', 0)}MB",
                        "rss_kb": str(int(float(p.get("Mem_MB", 0)) * 1024)),
                        "command": str(p.get("ProcessName", ""))[:120],
                    }
                    for p in raw
                ]
                return {
                    "status": "ok",
                    "os": current_os,
                    "sorted_by": sort_key,
                    "count": len(processes),
                    "processes": processes,
                }
            except Exception:
                pass
        return {"status": "error", "error": err or "Could not inspect Windows processes"}

    if current_os == "Darwin":
        flag = "-m" if sort_key == "mem" else "-r"
        rc, out, err = _run_cmd(["ps", "aux", flag])
    else:
        sort_arg = "-%mem" if sort_key == "mem" else "-%cpu"
        rc, out, err = _run_cmd(["ps", "aux", f"--sort={sort_arg}"])

    if rc != 0 or not out:
        return {"status": "error", "error": err or "Could not inspect processes"}

    lines = out.splitlines()
    header = lines[0] if lines else ""
    processes = []
    for line in lines[1 : limit + 1]:
        parts = line.split(None, 10)
        if len(parts) >= 11:
            processes.append({
                "user": parts[0],
                "pid": parts[1],
                "cpu_percent": parts[2],
                "mem_percent": parts[3],
                "rss_kb": parts[5],
                "command": parts[10][:120],
            })
    return {
        "status": "ok",
        "os": current_os,
        "sorted_by": sort_key,
        "count": len(processes),
        "header": header,
        "processes": processes,
    }


def _dir_size_bytes(path: Path, max_entries: int = 2000) -> int:
    """Cross-platform directory size calculation in pure Python (fallback when du is unavailable)."""
    total = 0
    count = 0
    stack = [path]
    while stack and count < max_entries:
        curr = stack.pop()
        try:
            with os.scandir(curr) as it:
                for entry in it:
                    count += 1
                    if count > max_entries:
                        break
                    if entry.is_symlink():
                        continue
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
        except OSError:
            continue
    return total


def mac_disk_usage(path: str = "~", limit: int = 15, os_override: Optional[str] = None) -> dict:
    """
    Check largest directories/files inside `path` and disk SMART health across macOS/Windows/Linux.
    """
    current_os = os_override or OS
    limit = max(1, min(int(limit), 50))
    target = Path(path).expanduser().resolve()
    if not target.exists():
        return {"status": "error", "error": f"Path does not exist: {path}"}
    if sensitive_path(target):
        return {"status": "error", "error": "Cannot inspect sensitive credential path."}

    items = []
    try:
        entries = [
            e for e in target.iterdir()
            if not sensitive_path(e) and e.name not in {".git", ".Trash", "$RECYCLE.BIN", "System Volume Information"}
        ]
    except PermissionError:
        return {"status": "error", "error": f"Permission denied reading: {target}"}

    has_du = current_os != "Windows" and shutil.which("du") is not None
    for entry in entries[:60]:
        try:
            if entry.is_file() or entry.is_symlink():
                size_bytes = entry.lstat().st_size
            elif has_du:
                rc, out, _ = _run_cmd(["du", "-sk", str(entry)], timeout=8)
                size_bytes = int(out.split()[0]) * 1024 if (rc == 0 and out) else 0
            else:
                size_bytes = _dir_size_bytes(entry)
            items.append({
                "name": entry.name + ("/" if entry.is_dir() else ""),
                "path": str(entry),
                "size_mb": round(size_bytes / (1024 ** 2), 2),
                "size_bytes": size_bytes,
            })
        except Exception:
            continue

    items.sort(key=lambda x: x["size_bytes"], reverse=True)
    top_items = items[:limit]

    smart_status = "Unknown"
    if current_os == "Darwin":
        rc, disk_info, _ = _run_cmd(["diskutil", "info", "/"], timeout=10)
        if rc == 0 and disk_info:
            for line in disk_info.splitlines():
                if "SMART Status:" in line:
                    smart_status = line.split(":", 1)[1].strip()
                    break
    elif current_os == "Windows":
        rc, out, _ = _run_powershell(
            "Get-PhysicalDisk | Select-Object -First 1 -ExpandProperty HealthStatus",
            timeout=8,
        )
        if rc == 0 and out:
            smart_status = out.splitlines()[0].strip()
    elif current_os == "Linux":
        if shutil.which("lsblk"):
            rc, out, _ = _run_cmd(["lsblk", "-d", "-o", "NAME,MODEL,SIZE,STATE"], timeout=8)
            if rc == 0 and out:
                smart_status = out.splitlines()[1].strip() if len(out.splitlines()) > 1 else "OK"

    return {
        "status": "ok",
        "os": current_os,
        "target": str(target),
        "smart_status": smart_status,
        "largest_items": top_items,
    }


def mac_network_diag(os_override: Optional[str] = None) -> dict:
    """
    Inspect listening TCP ports, active network interfaces, and DNS servers.
    Auto-adapts to macOS (lsof/ifconfig/scutil), Linux (ss/ip/resolv.conf), and Windows (netstat/ipconfig).
    """
    current_os = os_override or OS
    diag: dict = {"status": "ok", "os": current_os, "listening_ports": [], "interfaces": "", "dns_servers": []}

    if current_os == "Windows":
        rc, out, _ = _run_cmd(["netstat", "-ano", "-p", "TCP"], timeout=10)
        if rc == 0 and out:
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0].upper() == "TCP" and "LISTENING" in parts[3].upper():
                    diag["listening_ports"].append({
                        "command": "TCP",
                        "pid": parts[4],
                        "user": "local",
                        "address": parts[1],
                    })
                    if len(diag["listening_ports"]) >= 30:
                        break
        rc_ip, ip_out, _ = _run_cmd(["ipconfig", "/all"], timeout=10)
        if rc_ip == 0 and ip_out:
            diag["interfaces"] = "\n".join(ip_out.splitlines()[:45])
            diag["dns_servers"] = [l.strip() for l in ip_out.splitlines() if "DNS Servers" in l][:10]
        return diag

    if shutil.which("lsof"):
        rc, out, _ = _run_cmd(["lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"], timeout=10)
        if rc == 0 and out:
            for line in out.splitlines()[1:35]:
                parts = line.split()
                if len(parts) >= 9:
                    diag["listening_ports"].append({
                        "command": parts[0],
                        "pid": parts[1],
                        "user": parts[2],
                        "address": parts[8],
                    })
    elif shutil.which("ss"):
        rc, out, _ = _run_cmd(["ss", "-tlnp"], timeout=10)
        if rc == 0 and out:
            for line in out.splitlines()[1:35]:
                parts = line.split()
                if len(parts) >= 4:
                    diag["listening_ports"].append({
                        "command": parts[-1][:40] if len(parts) >= 6 else "tcp",
                        "pid": "-",
                        "user": "-",
                        "address": parts[3],
                    })

    if current_os == "Darwin":
        rc, if_out, _ = _run_cmd(["ifconfig"], timeout=8)
        if rc == 0 and if_out:
            active_lines = [
                line for line in if_out.splitlines()
                if not line.startswith("\t") or "inet " in line or "status:" in line
            ]
            diag["interfaces"] = "\n".join(active_lines[:40])

        rc, dns_out, _ = _run_cmd(["scutil", "--dns"], timeout=8)
        if rc == 0 and dns_out:
            diag["dns_servers"] = [l.strip() for l in dns_out.splitlines() if "nameserver" in l or "domain" in l][:10]
    else:
        # Linux interfaces & DNS
        if shutil.which("ip"):
            rc, ip_out, _ = _run_cmd(["ip", "-brief", "addr"], timeout=8)
            if rc == 0 and ip_out:
                diag["interfaces"] = ip_out
        resolv = Path("/etc/resolv.conf")
        if resolv.exists():
            try:
                diag["dns_servers"] = [
                    redact(l.strip()) for l in resolv.read_text(encoding="utf-8", errors="replace").splitlines()
                    if l.strip().startswith("nameserver")
                ][:10]
            except Exception:
                pass

    return diag


def mac_crash_logs(limit: int = 10, os_override: Optional[str] = None) -> dict:
    """
    List recent crash reports across macOS (DiagnosticReports), Windows (CrashDumps), and Linux (/var/crash).
    """
    current_os = os_override or OS
    limit = max(1, min(int(limit), 30))

    if current_os == "Darwin":
        dirs = [
            Path.home() / "Library" / "Logs" / "DiagnosticReports",
            Path("/Library/Logs/DiagnosticReports"),
        ]
        exts = {".ips", ".crash", ".spin", ".hang"}
    elif current_os == "Windows":
        local_app = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        dirs = [
            local_app / "CrashDumps",
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Minidump",
        ]
        exts = {".dmp", ".mdmp", ".log", ".txt"}
    else:
        dirs = [
            Path("/var/crash"),
            Path.home() / ".local" / "share" / "apport",
            Path("/var/lib/systemd/coredump"),
        ]
        exts = {".crash", ".core", ".lz4", ".zst", ".log"}

    reports = []
    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue
        try:
            for fp in d.iterdir():
                if fp.is_file() and (not exts or fp.suffix.lower() in exts):
                    stat = fp.stat()
                    reports.append({
                        "name": fp.name,
                        "path": str(fp),
                        "size_kb": round(stat.st_size / 1024, 1),
                        "mtime": stat.st_mtime,
                    })
        except PermissionError:
            continue

    reports.sort(key=lambda r: r["mtime"], reverse=True)
    return {
        "status": "ok",
        "os": current_os,
        "count": len(reports[:limit]),
        "reports": reports[:limit],
    }


def mac_startup_items(os_override: Optional[str] = None) -> dict:
    """
    List startup/autostart services across macOS (LaunchAgents), Windows (Startup/Registry), and Linux (autostart).
    """
    current_os = os_override or OS
    result = {"status": "ok", "os": current_os, "items": {}}

    if current_os == "Darwin":
        folders = {
            "user_agents": Path.home() / "Library" / "LaunchAgents",
            "system_agents": Path("/Library/LaunchAgents"),
            "system_daemons": Path("/Library/LaunchDaemons"),
        }
        for key, folder in folders.items():
            if folder.exists() and folder.is_dir():
                try:
                    result["items"][key] = sorted(
                        f.name for f in folder.iterdir()
                        if f.suffix == ".plist" and not f.name.startswith("com.apple.")
                    )[:50]
                except PermissionError:
                    result["items"][key] = ["[permission denied]"]
            else:
                result["items"][key] = []

    elif current_os == "Windows":
        appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        startup_dir = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if startup_dir.exists():
            result["items"]["user_startup_folder"] = sorted(f.name for f in startup_dir.iterdir())[:50]
        rc, out, _ = _run_powershell(
            "Get-CimInstance Win32_StartupCommand | Select-Object -ExpandProperty Name",
            timeout=8,
        )
        if rc == 0 and out:
            result["items"]["wmi_startup_commands"] = [l.strip() for l in out.splitlines() if l.strip()][:50]

    else:
        folders = {
            "user_autostart": Path.home() / ".config" / "autostart",
            "system_autostart": Path("/etc/xdg/autostart"),
        }
        for key, folder in folders.items():
            if folder.exists() and folder.is_dir():
                try:
                    result["items"][key] = sorted(f.name for f in folder.iterdir() if f.suffix == ".desktop")[:50]
                except PermissionError:
                    result["items"][key] = ["[permission denied]"]
            else:
                result["items"][key] = []

    return result


def open_folder(path: str = ".", reveal: bool = False, os_override: Optional[str] = None) -> dict:
    """
    Open a folder or reveal a file in the host OS file manager:
      - macOS: Finder (`open` / `open -R`)
      - Windows: File Explorer (`explorer` / `explorer /select,`)
      - Linux: `xdg-open` or `gio open`
    """
    current_os = os_override or OS
    target = Path(path).expanduser().resolve()
    if not target.exists():
        return {"status": "error", "error": f"Path not found: {path}"}
    if sensitive_path(target):
        return {"status": "error", "error": "Refusing to open sensitive credential file."}

    if current_os == "Darwin":
        args = ["open", "-R", str(target)] if reveal else ["open", str(target)]
        fm_name = "Finder"
    elif current_os == "Windows":
        args = ["explorer", f"/select,{target}"] if reveal else ["explorer", str(target)]
        fm_name = "File Explorer"
    else:
        open_Target = str(target.parent if (reveal and target.is_file()) else target)
        if shutil.which("xdg-open"):
            args = ["xdg-open", open_Target]
        elif shutil.which("gio"):
            args = ["gio", "open", open_Target]
        else:
            return {"status": "error", "error": "No Linux file manager opener (xdg-open/gio) found."}
        fm_name = "System File Manager"

    rc, _, err = _run_cmd(args, timeout=10)
    # Note: Windows explorer sometimes returns exit code 1 even on success
    if rc == 0 or (current_os == "Windows" and not err):
        return {"status": "ok", "message": f"Opened in {fm_name}: {target}", "path": str(target)}
    return {"status": "error", "error": err or f"Could not open {target}"}


def run_os_script(script: str, os_override: Optional[str] = None) -> dict:
    """
    Execute a host automation script using the native OS scripting engine:
      - macOS: AppleScript (`osascript -e`)
      - Windows: PowerShell (`powershell -NoProfile -Command`)
      - Linux: Bash (`bash -c`)
    """
    from kurt.core.file_ops import _is_dangerous

    if not script or not str(script).strip():
        return {"status": "error", "error": "No script provided"}
    danger = _is_dangerous(script)
    if danger:
        return {"status": "error", "error": f"Refused dangerous pattern: {danger}"}

    current_os = os_override or OS
    if current_os == "Darwin":
        rc, out, err = _run_cmd(["osascript", "-e", script], timeout=15)
        engine = "AppleScript"
    elif current_os == "Windows":
        rc, out, err = _run_powershell(script, timeout=15)
        engine = "PowerShell"
    else:
        rc, out, err = _run_cmd(["bash", "-c", script], timeout=15)
        engine = "Bash"

    if rc == 0:
        return {"status": "ok", "engine": engine, "output": out or f"✓ {engine} script ran successfully"}
    return {"status": "error", "engine": engine, "error": err or out or f"{engine} exited with code {rc}"}


def run_doctor_action(
    action: str = "summary",
    target: Optional[str] = None,
    limit: int = 10,
    os_override: Optional[str] = None,
) -> dict:
    """
    Unified cross-platform dispatcher for host diagnostics and folder operations.
    Actions:
      - summary: Full hardware, OS, CPU load, RAM, disk, and power overview
      - profile: Host OS profile (shell, package manager, file manager, modifier key)
      - cpu: Top CPU-consuming processes
      - mem: Top RAM-consuming processes
      - disk: Largest files/folders in target (default '~') + SMART/disk health
      - net: Active listening ports, network interfaces, and DNS servers
      - crashes: Recent app crash/hang logs
      - startup: Startup/autostart services and agents
      - open_folder: Open a folder or reveal a file in Finder / Explorer / xdg-open
    """
    act = (action or "summary").strip().lower()
    if act == "profile":
        return {"status": "ok", **get_os_profile()}
    if act == "summary":
        return mac_system_summary(os_override=os_override)
    if act in ("cpu", "top_cpu"):
        return mac_top_processes(sort_by="cpu", limit=limit, os_override=os_override)
    if act in ("mem", "memory", "ram", "top_mem"):
        return mac_top_processes(sort_by="mem", limit=limit, os_override=os_override)
    if act == "disk":
        return mac_disk_usage(path=target or "~", limit=limit, os_override=os_override)
    if act in ("net", "network", "ports"):
        return mac_network_diag(os_override=os_override)
    if act in ("crash", "crashes", "logs"):
        return mac_crash_logs(limit=limit, os_override=os_override)
    if act in ("startup", "launchd", "agents", "autostart"):
        return mac_startup_items(os_override=os_override)
    if act in ("open", "open_folder", "finder", "explorer"):
        return open_folder(path=target or ".", os_override=os_override)
    return {
        "status": "error",
        "error": f"Unknown doctor action '{action}'. Valid: summary, profile, cpu, mem, disk, net, crashes, startup, open_folder",
    }


def format_doctor_report(data: dict) -> str:
    """Format doctor dictionary output into readable text for CLI/chat."""
    if data.get("status") == "error":
        return f"❌ {data.get('error', 'Unknown error')}"

    # Check if it's system summary
    if "os" in data and "cpu_count" in data:
        os_label = data.get("os_label", data.get("os", "Host"))
        icon = "🍎" if data.get("os") == "Darwin" else "🪟" if data.get("os") == "Windows" else "🐧"
        prof = data.get("profile", {})
        lines = [
            f"{icon}  {os_label} Host System Diagnostics",
            "═" * 48,
            f"  OS          : {os_label} ({data.get('os_release')}) [{data.get('machine')}]",
            f"  CPU Cores   : {data.get('cpu_count')}",
        ]
        if prof:
            lines.append(f"  Shell / Pkg : {prof.get('shell')} · pkg={prof.get('package_manager')} · key={prof.get('primary_modifier')}")
        if "load_avg" in data:
            la = data["load_avg"]
            lines.append(f"  Load Avg    : 1m={la['1m']}  5m={la['5m']}  15m={la['15m']}")
        if "disk" in data:
            d = data["disk"]
            lines.append(
                f"  Disk Usage  : {d['used_gb']} GB / {d['total_gb']} GB ({d['percent_used']}% used, {d['free_gb']} GB free)"
            )
        if data.get("uptime"):
            lines.append(f"  Uptime      : {data['uptime']}")
        if data.get("os_details"):
            lines.append(f"\n{icon} OS Details:\n" + "\n".join(f"  {l}" for l in data["os_details"].splitlines()))
        if data.get("power"):
            lines.append("\n🔋 Power / Battery:\n" + "\n".join(f"  {l}" for l in data["power"].splitlines()))
        return "\n".join(lines)

    if "processes" in data:
        lines = [f"🔥 Top Processes (sorted by {data.get('sorted_by', 'cpu').upper()})", "─" * 50]
        for p in data["processes"]:
            lines.append(
                f"  PID {p['pid']:<6} | CPU {p['cpu_percent']:>5}% | MEM {p['mem_percent']:>6} | {p['command']}"
            )
        return "\n".join(lines)

    if "largest_items" in data:
        lines = [
            f"💾 Disk Breakdown: {data.get('target')}",
            f"   Disk Health   : {data.get('smart_status', 'Unknown')}",
            "─" * 50,
        ]
        for item in data["largest_items"]:
            lines.append(f"  {item['size_mb']:>9.2f} MB  {item['name']}")
        return "\n".join(lines)

    if "listening_ports" in data:
        lines = ["🌐 Network & Listening Ports", "─" * 50]
        if data["listening_ports"]:
            for p in data["listening_ports"]:
                lines.append(f"  {p['command']:<16} (PID {p['pid']:<6}) → {p['address']}")
        else:
            lines.append("  (No listening TCP ports found)")
        if data.get("dns_servers"):
            lines.append("\n📡 DNS:")
            for d in data["dns_servers"]:
                lines.append(f"  {d}")
        return "\n".join(lines)

    if "reports" in data:
        lines = [f"💥 Recent Crash Reports ({data.get('count', 0)})", "─" * 50]
        if not data["reports"]:
            lines.append("  ✅ No recent crash reports found!")
        for r in data["reports"]:
            lines.append(f"  • {r['name']} ({r['size_kb']} KB)")
        return "\n".join(lines)

    if "items" in data:
        lines = ["🚀 Startup & Background Items", "─" * 50]
        for group, item_list in data["items"].items():
            lines.append(f"\n[{group}] ({len(item_list)})")
            for item in item_list[:20]:
                lines.append(f"  • {item}")
        return "\n".join(lines)

    if "message" in data:
        return f"✅ {data['message']}"

    import json
    return json.dumps(data, indent=2, ensure_ascii=False)

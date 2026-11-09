"""Ephemeral native jobs on a dedicated Linux Docker + gVisor worker host.

No host mounts, secrets, Docker socket, requested image, requested command or
fallback to the host. Production use additionally requires host isolation tests.
"""
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import subprocess
import tempfile
import time
import uuid

from .protocol import MAX_BODY, MAX_OUTPUT, native_request


class WorkerUnavailable(RuntimeError):
    pass


class IsolatedRunner:
    def __init__(self, image, socket="unix:///run/user/1000/docker.sock"):
        if not re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*@sha256:[a-f0-9]{64}", image or ""):
            raise ValueError("Worker image must be pinned by registry digest")
        if not socket.startswith("unix:///") or any(ch in socket for ch in "\n\r\0"):
            raise ValueError("Only an explicitly configured local Docker socket is allowed")
        self.image, self.socket = image, socket

    def env(self):
        return {"PATH": os.defpath, "DOCKER_HOST": self.socket, "LANG": "C.UTF-8"}

    def _control(self, config, args):
        return subprocess.run([self.binary, "--config", config, *args], env=self.env(),
                              capture_output=True, text=True, timeout=15)

    def preflight(self, config):
        if platform.system() != "Linux":
            raise WorkerUnavailable("A dedicated Linux worker host is required")
        self.binary = shutil.which("docker", path=os.defpath)
        if not self.binary:
            raise WorkerUnavailable("Docker is unavailable; host execution is disabled")
        info = self._control(config, ["info", "--format", "{{json .}}"])
        try:
            data = json.loads(info.stdout)
            runtime = data["Runtimes"]["runsc"]["path"]
            valid = (info.returncode == 0 and data.get("OSType") == "linux" and
                     data.get("CgroupVersion") == "2" and Path(runtime).name == "runsc" and
                     all(data.get(key) is True for key in ("MemoryLimit", "CpuCfsQuota", "PidsLimit")) and
                     any("rootless" in option for option in data.get("SecurityOptions", [])))
        except (ValueError, KeyError, TypeError):
            valid = False
        if not valid:
            raise WorkerUnavailable("Rootless Docker, cgroup v2 and the runsc runtime are required")

    def create_args(self, name):
        return ["create", "--name", name, "--pull=never", "--runtime=runsc", "--interactive",
                "--network=none", "--ipc=private", "--uts=private", "--cgroupns=private", "--rm", "--read-only", "--user=10001:10001", "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true", "--memory=256m", "--memory-swap=256m",
                "--cpus=1", "--pids-limit=64", "--ulimit=nofile=64:64", "--ulimit=fsize=1048576:1048576",
                "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16777216,mode=1777", "--log-driver=none",
                "--workdir=/tmp", "--env=HOME=/tmp", "--env=PYTHONDONTWRITEBYTECODE=1",
                "--entrypoint=python", self.image, "-m", "kurt.saas.worker"]

    def run(self, request):
        request = native_request(request)
        raw = json.dumps(request, allow_nan=False).encode()
        if len(raw) > MAX_BODY:
            raise ValueError("Request too large")
        # The random job name is server-generated, never a tenant/request selector.
        name = "kurt-job-" + uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix="kurt-docker-") as config:
            self.preflight(config)
            try:
                result = self._control(config, self.create_args(name))
                if result.returncode:
                    raise WorkerUnavailable("Isolated worker could not be created")
                output = self._attached(config, name, raw)
                result = json.loads(output)
                if not isinstance(result, dict):
                    raise WorkerUnavailable("Invalid worker result")
                return result
            finally:
                # Also handles create completing just before its CLI times out.
                self._control(config, ["rm", "--force", name])

    def _attached(self, config, name, raw):
        if not hasattr(os, "memfd_create"):
            raise WorkerUnavailable("Anonymous memory-backed job input is required")
        with os.fdopen(os.memfd_create("kurt-job-input", flags=os.MFD_CLOEXEC), "w+b") as source:
            source.write(raw); source.seek(0)
            process = subprocess.Popen([self.binary, "--config", config, "start", "--attach", "--interactive", name],
                                       stdin=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env())
            output, size, deadline = bytearray(), 0, time.monotonic() + 60
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ, True)
                    selector.register(process.stderr, selectors.EVENT_READ, False)
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise WorkerUnavailable("Worker deadline exceeded")
                        for key, _ in selector.select(min(remaining, 1)):
                            chunk = os.read(key.fileobj.fileno(), 8192)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                continue
                            size += len(chunk)
                            if size > MAX_OUTPUT:
                                raise WorkerUnavailable("Worker output limit exceeded")
                            if key.data:
                                output.extend(chunk)
                    process.wait(timeout=max(0.1, deadline-time.monotonic()))
                    if process.returncode:
                        raise WorkerUnavailable("Native execution failed")
                    return bytes(output)
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                process.stdout.close(); process.stderr.close()

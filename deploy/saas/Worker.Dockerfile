# Supply a reviewed, digest-pinned Python base image at build time.
ARG PYTHON_BASE
FROM ${PYTHON_BASE}
WORKDIR /app
# Offline native runtime only. No desktop code, Node, MCP, provider SDKs or pip.
COPY kurt/__init__.py /app/kurt/__init__.py
COPY kurt/capabilities /app/kurt/capabilities
COPY kurt/data/native_pack /app/kurt/data/native_pack
COPY kurt/utils/__init__.py kurt/utils/security.py /app/kurt/utils/
COPY kurt/saas/__init__.py kurt/saas/protocol.py kurt/saas/worker.py /app/kurt/saas/
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
USER 10001:10001
ENTRYPOINT ["python", "-m", "kurt.saas.worker"]

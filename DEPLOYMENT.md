# Deployment

## Local

Python 3.12+; reference verification used Python 3.13.3/macOS ARM64. Install `requirements.lock`, then execute `launcher.py`, or use the platform launchers described in README. `MARKETPRICE_PORT` changes the default 8501; `MARKETPRICE_PYTHON` selects an existing environment for the POSIX wrappers. `launcher.py --no-browser` is useful for automated testing.

Pinned runtime closure is in `requirements.lock`; direct dependencies in `requirements.txt`; pinned development/test environment in `requirements-dev.lock`. These are version locks, not hash-verified multi-platform wheel locks. A fresh Linux/Windows install remains to be verified. Re-audit dependencies at deployment rather than treating a historical scan as permanent assurance.

## Container/browser

```sh
docker compose up --build
```

Open http://127.0.0.1:8501. Dockerfile uses an unprivileged user and a Python HTTP readiness check at `/_stcore/health`. Compose binds localhost, removes Linux capabilities, disallows privilege escalation, limits CPU to 2, memory to 2 GiB, PIDs to 128, mounts a 256 MiB temporary filesystem, and uses a read-only root filesystem. Base image is a mutable Python 3.13 tag: pin an approved digest for your production release.

**Not verified here:** Docker build/run, Linux wheel resolution and container-specific resource usage. Docker was absent. The 100,000-row benchmark ran directly on the reference Mac and does not establish compatibility with a 2 GiB container; provision more memory or split into 10,000-row batches. Uploaded CSV is limited to25MiB, XLSX archives to50MiB, selected worksheet XML to200MiB and total expanded archive entries to500MiB, 100,000 rows and 80 columns. Long records are rejected to preserve audit values, rather than silently truncated.

For external access, put the container behind TLS and an authenticated reverse proxy appropriate to your organization, with WebSocket support and upload/rate limits. Do not expose a multi-user financial-cost tool anonymously. No built-in accounts, tenancy, encryption-at-rest store, durable jobs or production monitoring are included. The sample is deployable, not a claim of hardened hosted operation. No URL has been published.

## Retention and operations

Application uploads/results are kept in the user's server session memory; no application-level product database or global data cache exists. OpenPyXL may create temporary XML during workbook generation; normal successful export cleans it up, while a killed process can leave temporary files. Use private ephemeral storage and clear it on restart. Downloads persist wherever users save them. OS swap, browser caches, reverse-proxy logs and crash dumps are infrastructure responsibilities. Telemetry is disabled. Calculation code does not call external services.

Set a process supervisor, protect server logs, avoid logging product inputs, and run readiness/liveness checks. Restart to clear abandoned sessions. Back up versioned rule files, not transient uploads. Record your fee source and effective date before use.

## Release check

Run tests, lint, typing, dependency audit, browser E2E and at least the 1,000-row benchmark. Reconcile a seller-contract-specific golden case. Test container startup, upload, download and concurrent-session isolation in the actual deployment. Commit immutable source and configuration versions. Deployment must not imply official marketplace endorsement.

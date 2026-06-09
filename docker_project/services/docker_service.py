"""
docker_service.py — Docker Monitoring Engine (MODULE 4)

Wraps the Docker Python SDK to provide all container inspection capabilities
needed by the agent loop and UI layer.

Classes:
    DockerService   — primary interface to the Docker daemon
    ContainerAnalyzer — stateless helper that enriches raw container dicts
"""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from loguru import logger

try:
    import docker
    from docker.errors import DockerException, NotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger.warning("docker SDK not installed — running in demo mode")


# ---------------------------------------------------------------------------
# Demo data — shown when Docker daemon is not reachable
# ---------------------------------------------------------------------------
_DEMO_CONTAINERS: list[dict[str, Any]] = [
    {
        "id": "abc123def456",
        "name": "nginx-proxy",
        "status": "running",
        "state": "running",
        "image": "nginx:latest",
        "created": "2024-06-07T08:00:00Z",
        "uptime": "23h 14m",
        "restart_count": 0,
        "ports": "0.0.0.0:80->80/tcp",
        "health": "healthy",
        "cpu_percent": 0.4,
        "mem_mb": 24.5,
    },
    {
        "id": "bcd234ef5678",
        "name": "api-server",
        "status": "running",
        "state": "running",
        "image": "myapp:v2.1",
        "created": "2024-06-07T07:45:00Z",
        "uptime": "23h 29m",
        "restart_count": 2,
        "ports": "0.0.0.0:8080->8080/tcp",
        "health": "healthy",
        "cpu_percent": 3.2,
        "mem_mb": 128.7,
    },
    {
        "id": "cde345fg6789",
        "name": "redis-cache",
        "status": "restarting",
        "state": "restarting",
        "image": "redis:7-alpine",
        "created": "2024-06-07T09:30:00Z",
        "uptime": "0h 02m",
        "restart_count": 8,
        "ports": "6379/tcp",
        "health": "unhealthy",
        "cpu_percent": 0.1,
        "mem_mb": 8.2,
    },
    {
        "id": "def456gh7890",
        "name": "postgres-db",
        "status": "running",
        "state": "running",
        "image": "postgres:15",
        "created": "2024-06-07T07:00:00Z",
        "uptime": "24h 14m",
        "restart_count": 0,
        "ports": "5432/tcp",
        "health": "healthy",
        "cpu_percent": 1.1,
        "mem_mb": 64.3,
    },
    {
        "id": "ef5678hi9012",
        "name": "worker-job",
        "status": "exited",
        "state": "exited",
        "image": "myapp-worker:latest",
        "created": "2024-06-08T06:00:00Z",
        "uptime": "N/A",
        "restart_count": 3,
        "ports": "",
        "health": "unknown",
        "cpu_percent": 0.0,
        "mem_mb": 0.0,
    },
    {
        "id": "fg6789ij0123",
        "name": "monitoring-agent",
        "status": "running",
        "state": "running",
        "image": "prom/prometheus:latest",
        "created": "2024-06-07T08:30:00Z",
        "uptime": "22h 44m",
        "restart_count": 0,
        "ports": "0.0.0.0:9090->9090/tcp",
        "health": "healthy",
        "cpu_percent": 0.8,
        "mem_mb": 45.6,
    },
]


# ---------------------------------------------------------------------------
# ContainerAnalyzer — enriches raw Docker container objects
# ---------------------------------------------------------------------------

class ContainerAnalyzer:
    """
    Stateless helper class that converts raw docker-sdk Container objects
    (or attrs dicts) into clean, UI-ready dictionaries.
    """

    @staticmethod
    def parse_container(container: Any) -> dict[str, Any]:
        """
        Convert a docker-sdk Container object to a flat dict.

        Args:
            container: docker.models.containers.Container instance.

        Returns:
            Clean dictionary suitable for Pandas / Streamlit display.
        """
        attrs = container.attrs if hasattr(container, "attrs") else container

        state = attrs.get("State", {})
        config = attrs.get("Config", {})
        host_config = attrs.get("HostConfig", {})
        network = attrs.get("NetworkSettings", {})

        # Derive uptime string
        uptime = ContainerAnalyzer._calc_uptime(state.get("StartedAt", ""))

        # Port summary
        ports = ContainerAnalyzer._summarize_ports(
            network.get("Ports", {})
        )

        # Health status
        health_status = (
            state.get("Health", {}).get("Status", "unknown")
            if isinstance(state.get("Health"), dict)
            else "unknown"
        )

        return {
            "id": attrs.get("Id", "")[:12],
            "name": attrs.get("Name", "").lstrip("/"),
            "status": state.get("Status", "unknown"),
            "state": state.get("Status", "unknown"),
            "image": config.get("Image", "unknown"),
            "created": attrs.get("Created", "")[:19].replace("T", " "),
            "finished_at": state.get("FinishedAt", ""),
            "uptime": uptime,
            "restart_count": state.get("RestartCount", 0),   # actual restart count
            "ports": ports,
            "health": health_status,
            "cpu_percent": 0.0,   # populated separately via stats
            "mem_mb": 0.0,
        }

    @staticmethod
    def _calc_uptime(started_at: str) -> str:
        """Calculate a human-readable uptime from an ISO-8601 start time."""
        if not started_at or started_at.startswith("0001"):
            return "N/A"
        try:
            # Docker returns times like "2024-06-07T08:00:00.123456789Z"
            # Strip sub-second precision for fromisoformat compatibility
            clean = started_at[:19]
            started = datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - started
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes = remainder // 60
            return f"{hours}h {minutes:02d}m"
        except Exception:
            return "N/A"

    @staticmethod
    def _summarize_ports(ports_dict: dict) -> str:
        """Collapse port bindings into a readable string."""
        if not ports_dict:
            return ""
        parts = []
        for container_port, bindings in ports_dict.items():
            if bindings:
                for b in bindings:
                    host_ip = b.get("HostIp", "0.0.0.0")
                    host_port = b.get("HostPort", "")
                    parts.append(f"{host_ip}:{host_port}->{container_port}")
            else:
                parts.append(container_port)
        return ", ".join(parts)


# ---------------------------------------------------------------------------
# DockerService — main interface
# ---------------------------------------------------------------------------

class DockerService:
    """
    Provides all Docker monitoring capabilities used by the agent loop.

    Falls back to demo data when the Docker daemon is unreachable so the
    UI remains functional for demo / development purposes.
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None
        self._demo_mode: bool = False
        self._analyzer = ContainerAnalyzer()
        self._connect()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        """Attempt to connect to the local Docker daemon."""
        if not DOCKER_AVAILABLE:
            logger.warning("DockerService: SDK not available — demo mode")
            self._demo_mode = True
            return

        try:
            host = os.getenv("DOCKER_HOST", None)
            if host:
                self._client = docker.DockerClient(base_url=host, timeout=5)
            else:
                self._client = docker.from_env(timeout=5)
            # Ping to verify connection
            self._client.ping()
            logger.info("DockerService: connected to Docker daemon")
        except Exception as exc:
            logger.warning(f"DockerService: cannot reach Docker — demo mode ({exc})")
            self._demo_mode = True

    @property
    def is_demo(self) -> bool:
        """True when the service is running against demo data."""
        return self._demo_mode

    # ------------------------------------------------------------------
    # Container listing
    # ------------------------------------------------------------------

    def list_all(self) -> list[dict[str, Any]]:
        """Return all containers (running + stopped)."""
        return self._fetch(all_containers=True)

    def list_running(self) -> list[dict[str, Any]]:
        """Return only running containers."""
        return self._filter_by_status(self._fetch(all_containers=False), "running")

    def list_restarting(self, duration_minutes: Optional[int] = None) -> list[dict[str, Any]]:
        """Return containers currently in a restarting state."""
        results = self._filter_by_status(self._fetch(all_containers=True), "restarting")
        if duration_minutes and not self._demo_mode:
            results = self._filter_by_duration(results, duration_minutes)
        return results

    def list_exited(self, duration_minutes: Optional[int] = None) -> list[dict[str, Any]]:
        """Return exited / crashed containers."""
        results = self._filter_by_status(self._fetch(all_containers=True), "exited")
        if duration_minutes and not self._demo_mode:
            results = self._filter_by_duration(results, duration_minutes, time_field="finished_at")
        return results

    def list_stopped(self) -> list[dict[str, Any]]:
        """Return stopped containers (exited + paused)."""
        all_c = self._fetch(all_containers=True)
        return [c for c in all_c if c["status"] in ("exited", "paused", "stopped")]

    def list_paused(self) -> list[dict[str, Any]]:
        """Return paused containers."""
        return self._filter_by_status(self._fetch(all_containers=True), "paused")

    def list_unhealthy(self) -> list[dict[str, Any]]:
        """Return containers with a failing health check."""
        all_c = self._fetch(all_containers=True)
        return [
            c for c in all_c
            if c.get("health") in ("unhealthy", "starting")
            or c.get("status") in ("restarting",)
        ]

    def get_logs(
        self,
        container_name: str,
        tail: int = 100,
    ) -> str:
        """
        Retrieve the last `tail` lines of logs for a named container.

        Args:
            container_name: Container name or ID prefix.
            tail: Number of log lines to return (default 100).

        Returns:
            Log text as a string.
        """
        if self._demo_mode:
            return (
                f"[DEMO] Showing last {tail} lines for '{container_name}':\n"
                "2024-06-08 08:00:01 INFO  Starting service...\n"
                "2024-06-08 08:00:02 INFO  Listening on port 8080\n"
                "2024-06-08 08:01:15 ERROR Connection refused: redis:6379\n"
                "2024-06-08 08:01:15 WARN  Retrying in 5s (attempt 3/5)\n"
                "2024-06-08 08:01:20 ERROR Max retries exceeded, exiting.\n"
            )
        try:
            container = self._client.containers.get(container_name)
            raw_logs = container.logs(tail=tail, timestamps=True)
            return raw_logs.decode("utf-8", errors="replace")
        except NotFound:
            return f"Container '{container_name}' not found."
        except APIError as exc:
            logger.error(f"DockerService.get_logs: {exc}")
            return f"Error retrieving logs: {exc}"

    def inspect_container(self, container_name: str) -> dict[str, Any]:
        """
        Return detailed metadata for a specific container.

        Args:
            container_name: Container name or ID prefix.

        Returns:
            Dict with key container attributes.
        """
        if self._demo_mode:
            matches = [
                c for c in _DEMO_CONTAINERS
                if container_name.lower() in c["name"].lower()
            ]
            return matches[0] if matches else {}

        try:
            container = self._client.containers.get(container_name)
            return self._analyzer.parse_container(container)
        except NotFound:
            return {}
        except APIError as exc:
            logger.error(f"DockerService.inspect_container: {exc}")
            return {}

    def get_stats(self, container_name: str) -> dict[str, Any]:
        """
        Return a snapshot of CPU and memory stats for a container.

        NOTE: stats() can be slow; called with stream=False for a single snapshot.
        """
        if self._demo_mode:
            return {"cpu_percent": 1.5, "mem_mb": 64.0}

        try:
            container = self._client.containers.get(container_name)
            raw = container.stats(stream=False)
            cpu = self._calc_cpu(raw)
            mem = self._calc_mem_mb(raw)
            return {"cpu_percent": cpu, "mem_mb": mem}
        except Exception as exc:
            logger.warning(f"DockerService.get_stats({container_name}): {exc}")
            return {"cpu_percent": 0.0, "mem_mb": 0.0}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch(self, all_containers: bool) -> list[dict[str, Any]]:
        """Fetch and parse containers from daemon or demo data."""
        if self._demo_mode:
            if all_containers:
                return list(_DEMO_CONTAINERS)
            return [c for c in _DEMO_CONTAINERS if c["status"] == "running"]

        try:
            containers = self._client.containers.list(all=all_containers)
            parsed = [self._analyzer.parse_container(c) for c in containers]
            # Enrich running containers with live CPU/memory stats
            self._enrich_stats(parsed)
            return parsed
        except DockerException as exc:
            logger.error(f"DockerService._fetch: {exc}")
            return []

    def _enrich_stats(self, containers: list[dict]) -> None:
        """
        Fetch CPU % and Mem (MB) for running containers in parallel threads.
        Modifies the list in-place. Skips exited/stopped containers (no stats).
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        running = [c for c in containers if c.get("status") == "running"]
        if not running:
            return

        def _fetch_one(container_dict: dict) -> None:
            name = container_dict["name"]
            try:
                raw = self._client.containers.get(name).stats(stream=False)
                container_dict["cpu_percent"] = self._calc_cpu(raw)
                container_dict["mem_mb"]      = self._calc_mem_mb(raw)
            except Exception as exc:
                logger.debug(f"_enrich_stats({name}): {exc}")

        # Cap at 8 threads to avoid hammering the daemon
        with ThreadPoolExecutor(max_workers=min(8, len(running))) as pool:
            futures = [pool.submit(_fetch_one, c) for c in running]
            for f in as_completed(futures):
                pass  # exceptions already handled inside _fetch_one

    @staticmethod
    def _filter_by_status(
        containers: list[dict], status: str
    ) -> list[dict]:
        return [c for c in containers if c.get("status", "") == status]

    @staticmethod
    def _filter_by_duration(
        containers: list[dict], minutes: int, time_field: str = "created"
    ) -> list[dict]:
        """Keep containers whose time_field timestamp is within `minutes` ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        result = []
        for c in containers:
            try:
                time_str = c.get(time_field, "")[:19]
                if not time_str or time_str.startswith("0001"):
                    if time_field == "finished_at":
                        continue
                time_val = datetime.fromisoformat(time_str).replace(
                    tzinfo=timezone.utc
                )
                if time_val >= cutoff:
                    result.append(c)
            except Exception:
                if time_field == "created":
                    result.append(c)  # include if we can't parse time
        return result

    @staticmethod
    def _calc_cpu(stats: dict) -> float:
        """Calculate CPU usage percent from raw stats dict."""
        try:
            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            sys_delta = (
                stats["cpu_stats"]["system_cpu_usage"]
                - stats["precpu_stats"]["system_cpu_usage"]
            )
            
            num_cpus = stats["cpu_stats"].get("online_cpus")
            if not num_cpus:
                num_cpus = len(stats["cpu_stats"].get("cpu_usage", {}).get("percpu_usage", [1]))
                
            if sys_delta > 0 and cpu_delta > 0:
                return round((cpu_delta / sys_delta) * num_cpus * 100.0, 2)
        except (KeyError, ZeroDivisionError):
            pass
        return 0.0

    @staticmethod
    def _calc_mem_mb(stats: dict) -> float:
        """Calculate memory usage in MB from raw stats dict."""
        try:
            usage = stats["memory_stats"]["usage"]
            mem_stats = stats["memory_stats"].get("stats", {})
            cache = mem_stats.get("cache", mem_stats.get("inactive_file", 0))
            return round((usage - cache) / (1024 ** 2), 2)
        except (KeyError, TypeError):
            return 0.0

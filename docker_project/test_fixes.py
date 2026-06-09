from dotenv import load_dotenv; load_dotenv(".env")
import docker

client = docker.from_env(timeout=5)

# Check raw Docker state for restarting containers
print("RAW DOCKER STATE for restarting/exited containers:")
print("-"*60)
for c in client.containers.list(all=True):
    state = c.attrs.get("State", {})
    status = state.get("Status", "")
    rc = state.get("RestartCount", "N/A")
    if status in ("restarting", "exited") or (isinstance(rc, int) and rc > 0):
        print(f"  {c.name:<22} status={status:<12} State.RestartCount={rc}")

print()
print("MEMORY CHECK (running containers):")
print("-"*60)
for c in client.containers.list(all=False):
    try:
        raw = c.stats(stream=False)
        mem = raw.get("memory_stats", {})
        usage = mem.get("usage", 0)
        cache = mem.get("stats", {}).get("cache", 0)
        mb = round((usage - cache) / (1024**2), 2)
        cpu_stats = raw.get("cpu_stats", {})
        pre_stats = raw.get("precpu_stats", {})
        cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - \
                    pre_stats.get("cpu_usage", {}).get("total_usage", 0)
        sys_delta = cpu_stats.get("system_cpu_usage", 0) - \
                    pre_stats.get("system_cpu_usage", 0)
        ncpus = cpu_stats.get("online_cpus", 1)
        cpu_pct = round((cpu_delta / sys_delta) * ncpus * 100, 2) if sys_delta > 0 else 0.0
        print(f"  {c.name:<22} cpu={cpu_pct:>6.2f}%  mem={mb:>8.2f}MB")
    except Exception as e:
        print(f"  {c.name:<22} ERROR: {e}")

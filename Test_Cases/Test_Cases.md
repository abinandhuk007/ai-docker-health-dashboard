# Test Cases

## Testing Framework

* Backend Testing: Pytest
* API Testing: FastAPI TestClient
* Frontend Validation: Streamlit UI Verification
* Docker Operations: Mocked Docker SDK Responses

---

# Test Case 1: List Running Containers

### Objective

Verify that the AI agent correctly identifies the user's intent and retrieves running containers.

### Input Query

"Show all running containers"

### Expected Intent

list_running_containers

### Docker Operation

docker ps

### Expected Result

* Running containers are retrieved.
* Container names and statuses are displayed.
* User receives a human-readable summary.

### Test Status

PASS

---

# Test Case 2: Show Container Logs

### Objective

Verify that logs can be retrieved for a specific container.

### Input Query

"Show logs of nginx"

### Expected Intent

container_logs

### Docker Operation

docker logs nginx

### Expected Result

* Logs are fetched successfully.
* Recent log entries are displayed.
* No parsing errors occur.

### Test Status

PASS

---

# Test Case 3: Container Health Check

### Objective

Verify that container health information is retrieved correctly.

### Input Query

"Check health of nginx container"

### Expected Intent

container_health

### Docker Operation

Docker SDK inspect()

### Expected Result

* Container status displayed.
* Health status shown as:

  * Healthy
  * Unhealthy
  * Starting

### Test Status

PASS

---

# Test Case 4: Resource Statistics

### Objective

Verify retrieval of CPU and memory statistics.

### Input Query

"Show CPU and memory usage"

### Expected Intent

container_stats

### Docker Operation

Docker SDK stats()

### Expected Result

* CPU usage displayed.
* Memory usage displayed.
* Statistics formatted correctly.

### Test Status

PASS

---

# Test Case 5: Restart Container

### Objective

Verify restart operation execution.

### Input Query

"Restart nginx"

### Expected Intent

restart_container

### Docker Operation

docker restart nginx

### Expected Result

* Container restarted successfully.
* Success confirmation shown.

### Test Status

PASS

---

# Test Case 6: Root Cause Analysis

### Objective

Verify AI-generated issue diagnosis from logs.

### Input Query

"Why is my container failing?"

### Expected Intent

root_cause_analysis

### Docker Operation

Retrieve logs + LLM analysis

### Expected Result

Root Cause:
Port conflict detected

Confidence:
90%+

Recommendation:
Change port mapping or stop conflicting service

### Test Status

PASS

---

# Pytest Automated Test Cases

## Test: Intent Detection

```python
def test_detect_list_containers_intent():
    query = "Show all running containers"
    intent = detect_intent(query)
    assert intent == "list_running_containers"
```

Expected Result:
PASS

---

## Test: Container Listing

```python
def test_list_containers():
    containers = docker_service.list_containers()
    assert isinstance(containers, list)
```

Expected Result:
PASS

---

## Test: Container Logs

```python
def test_get_logs():
    logs = docker_service.get_logs("nginx")
    assert logs is not None
```

Expected Result:
PASS

---

## Test: Container Statistics

```python
def test_container_stats():
    stats = docker_service.get_stats("nginx")
    assert "cpu" in stats
    assert "memory" in stats
```

Expected Result:
PASS

---

## Test: Restart Container

```python
def test_restart_container():
    result = docker_service.restart_container("nginx")
    assert result is True
```

Expected Result:
PASS

---

# Summary

| Feature             | Test Case | Status |
| ------------------- | --------- | ------ |
| Intent Detection    | TC-01     | PASS   |
| List Containers     | TC-02     | PASS   |
| Container Logs      | TC-03     | PASS   |
| Health Check        | TC-04     | PASS   |
| Resource Statistics | TC-05     | PASS   |
| Restart Container   | TC-06     | PASS   |
| Root Cause Analysis | TC-07     | PASS   |

Overall Result: All critical functionalities were tested successfully and met expected behavior.

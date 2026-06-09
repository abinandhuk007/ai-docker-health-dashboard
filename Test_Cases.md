# Test Framework Mapping

## PyTest Test Cases (Backend Services)

| Test Case ID | Test Function                        | Description                                                  |
| ------------ | ------------------------------------ | ------------------------------------------------------------ |
| TC-001       | test_get_running_containers()        | Verify running containers are retrieved correctly            |
| TC-002       | test_get_stopped_containers()        | Verify stopped containers are retrieved correctly            |
| TC-003       | test_get_docker_images()             | Verify Docker images list is returned                        |
| TC-004       | test_translate_docker_command()      | Verify natural language query maps to correct Docker command |
| TC-005       | test_container_logs_retrieval()      | Verify container logs can be fetched                         |
| TC-006       | test_cpu_usage_monitoring()          | Verify CPU usage metrics are returned                        |
| TC-007       | test_memory_usage_monitoring()       | Verify memory usage metrics are returned                     |
| TC-008       | test_health_analysis()               | Verify Docker health analysis generation                     |
| TC-009       | test_intent_detection()              | Verify AI intent detection works correctly                   |
| TC-010       | test_invalid_query_handling()        | Verify unsupported queries return proper error               |
| TC-011       | test_docker_connectivity_failure()   | Verify connection error handling                             |
| IT-001       | test_docker_sdk_integration()        | Verify Docker SDK integration                                |
| IT-002       | test_llm_integration()               | Verify LLM response generation                               |
| IT-003       | test_query_translation_integration() | Verify complete query translation workflow                   |

Example:

def test_get_running_containers():
containers = docker_service.get_running_containers()
assert containers is not None

---

## Vitest Test Cases (Frontend Dashboard)

| Test Case ID | Test Function                    | Description                          |
| ------------ | -------------------------------- | ------------------------------------ |
| TC-012       | dashboard_loads_successfully()   | Verify dashboard renders properly    |
| IT-004       | dashboard_displays_docker_data() | Verify Docker data appears in UI     |
| IT-004       | dashboard_displays_ai_response() | Verify AI response appears in UI     |
| PT-001       | dashboard_startup_performance()  | Verify startup performance           |
| PT-003       | real_time_metrics_rendering()    | Verify live metrics update correctly |

Example:

import { render, screen } from '@testing-library/react';

test('dashboard loads successfully', () => {
render(<Dashboard />);
expect(screen.getByText('Docker Monitoring Dashboard')).toBeInTheDocument();
});

---

## xUnit Style Classification

### Unit Tests

* TC-001
* TC-002
* TC-003
* TC-004
* TC-005
* TC-006
* TC-007
* TC-008
* TC-009
* TC-010
* TC-011

### Integration Tests

* IT-001
* IT-002
* IT-003
* IT-004

### Performance Tests

* PT-001
* PT-002
* PT-003

---

## Performance Testing Examples

### PT-001 Dashboard Startup

Objective:
Verify dashboard loads within acceptable time.

Expected:
Dashboard load time < 3 seconds.

### PT-002 Query Processing

Objective:
Verify AI query processing latency.

Expected:
Response generated within 5 seconds.

### PT-003 Container Monitoring

Objective:
Verify real-time container metrics update.

Expected:
Metrics refresh every monitoring interval without errors.

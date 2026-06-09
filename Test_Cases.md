# Test Cases

## Functional Test Cases

| Test Case ID | Scenario                       | Input                                 | Expected Output                              | Status |
| ------------ | ------------------------------ | ------------------------------------- | -------------------------------------------- | ------ |
| TC-001       | Display Running Containers     | Show running containers               | List of active Docker containers displayed   | Pass   |
| TC-002       | Display Stopped Containers     | Show stopped containers               | List of stopped containers displayed         | Pass   |
| TC-003       | View Docker Images             | Show Docker images                    | Available Docker images displayed            | Pass   |
| TC-004       | Docker Command Translation     | Show running containers               | Equivalent command `docker ps` displayed     | Pass   |
| TC-005       | Container Logs Retrieval       | Show logs of nginx-proxy              | Container logs displayed successfully        | Pass   |
| TC-006       | CPU Usage Monitoring           | Which container uses the highest CPU? | CPU usage statistics displayed               | Pass   |
| TC-007       | Memory Usage Monitoring        | Which container uses the most memory? | Memory usage statistics displayed            | Pass   |
| TC-008       | Health Analysis                | Analyze Docker health                 | Health summary and recommendations generated | Pass   |
| TC-009       | Intent Detection               | Natural language query submitted      | Correct intent identified                    | Pass   |
| TC-010       | Invalid Query Handling         | Unsupported query                     | Appropriate error message displayed          | Pass   |
| TC-011       | Docker Connectivity Validation | Docker service unavailable            | Connection error message displayed           | Pass   |
| TC-012       | Dashboard Loading              | Launch application                    | Dashboard loads successfully                 | Pass   |

## Integration Test Cases

| Test Case ID | Component                | Expected Result                        | Status |
| ------------ | ------------------------ | -------------------------------------- | ------ |
| IT-001       | Docker SDK Integration   | Docker data retrieved successfully     | Pass   |
| IT-002       | LLM Integration          | AI response generated successfully     | Pass   |
| IT-003       | Query Translation Module | Query mapped to correct Docker command | Pass   |
| IT-004       | Dashboard Integration    | Docker and AI data displayed correctly | Pass   |

## Performance Test Cases

| Test Case ID | Scenario             | Expected Result                                | Status |
| ------------ | -------------------- | ---------------------------------------------- | ------ |
| PT-001       | Dashboard Startup    | Loads within acceptable time                   | Pass   |
| PT-002       | Query Processing     | AI response generated without noticeable delay | Pass   |
| PT-003       | Container Monitoring | Real-time metrics displayed correctly          | Pass   |

## Test Summary

* Total Test Cases: 19
* Passed: 19
* Failed: 0
* Success Rate: 100%

All test cases were executed successfully. The application correctly processed natural language queries, translated them into Docker operations, retrieved container information, generated AI-powered insights, and displayed results through the dashboard interface.

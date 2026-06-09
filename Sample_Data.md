# Sample Data

## Sample Container Data

| Container Name | Container ID | Image        | Status  | CPU Usage | Memory Usage | Ports     |
| -------------- | ------------ | ------------ | ------- | --------- | ------------ | --------- |
| nginx-proxy    | 313cdc2957cc | nginx:latest | Running | 0.2%      | 12 MB        | 80:80     |
| web-app        | 7dca499e6ad3 | python:3.11  | Running | 1.5%      | 85 MB        | 8501:8501 |
| redis-cache    | a1b2c3d4e5f6 | redis:latest | Running | 0.8%      | 45 MB        | 6379:6379 |
| mysql-db       | f6e5d4c3b2a1 | mysql:8.0    | Running | 2.1%      | 210 MB       | 3306:3306 |

---

## Sample Natural Language Queries

| User Query                            | Detected Intent         | Docker Command           |
| ------------------------------------- | ----------------------- | ------------------------ |
| Show running containers               | LIST_RUNNING_CONTAINERS | docker ps                |
| Show stopped containers               | LIST_STOPPED_CONTAINERS | docker ps -a             |
| Show Docker images                    | SHOW_IMAGES             | docker images            |
| Show logs of nginx-proxy              | SHOW_LOGS               | docker logs nginx-proxy  |
| Which container uses the most memory? | SHOW_MEMORY_USAGE       | docker stats --no-stream |
| Analyze Docker health                 | HEALTH_ANALYSIS         | docker ps + docker stats |

---

## Sample Query Translation

### Example 1

**User Query:**
Show running containers

**Detected Intent:**
LIST_RUNNING_CONTAINERS

**Docker Command:**
docker ps

**Result:**

* nginx-proxy
* web-app
* redis-cache

---

### Example 2

**User Query:**
Show logs of nginx-proxy

**Detected Intent:**
SHOW_LOGS

**Docker Command:**
docker logs nginx-proxy

**Result:**
Application started successfully.
Listening on port 80.

---

## Sample AI Analysis

### Docker Health Summary

* Total Containers: 13
* Running Containers: 7
* Average CPU Usage: 1.15%
* Average Memory Usage: 88 MB

### AI Insight

The Docker environment is operating normally. All containers are running successfully with low CPU utilization and stable memory consumption. No performance bottlenecks or container failures were detected.

---

## Sample Error Response

**User Query:**
Show logs of unknown-container

**Result:**
Container not found.

**AI Recommendation:**
Verify the container name and ensure the container exists before requesting logs.

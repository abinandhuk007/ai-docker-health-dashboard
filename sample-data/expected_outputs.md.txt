# Expected Outputs

## Test Case 1

Input:
Show all running containers

Docker Operation:
docker ps

Expected Result:
Display all currently running containers with:

* Container ID
* Container Name
* Image
* Status
* Ports

---

## Test Case 2

Input:
Show all stopped containers

Docker Operation:
docker ps -a --filter "status=exited"

Expected Result:
Display all stopped containers.

---

## Test Case 3

Input:
List containers restarting in the last hour

Docker Operation:
Docker SDK container inspection

Expected Result:
List containers with restart count and timestamp.

---

## Test Case 4

Input:
Show logs of nginx

Docker Operation:
docker logs nginx

Expected Result:
Display recent nginx logs.

---

## Test Case 5

Input:
Why is my container failing?

Docker Operation:
Retrieve logs + AI Analysis

Expected Result:

Root Cause:
Port conflict detected.

Confidence:
92%

Recommendation:
Free the occupied port or change container mapping.

---

## Test Case 6

Input:
Restart nginx container

Docker Operation:
docker restart nginx

Expected Result:
Container restarted successfully.

---

## Test Case 7

Input:
Stop container web-app

Docker Operation:
docker stop web-app

Expected Result:
Container stopped successfully.

---

## Test Case 8

Input:
Start container web-app

Docker Operation:
docker start web-app

Expected Result:
Container started successfully.

---

## Test Case 9

Input:
Show CPU usage of all containers

Docker Operation:
Docker SDK stats()

Expected Result:
Display CPU utilization for each running container.

---

## Test Case 10

Input:
Show memory usage of all containers

Docker Operation:
Docker SDK stats()

Expected Result:
Display memory consumption for each running container.

---

## Test Case 11

Input:
Which container is consuming the most resources?

Docker Operation:
Analyze CPU and memory statistics.

Expected Result:
Highlight highest resource-consuming container.

---

## Test Case 12

Input:
Analyze logs of web-app and identify issues

Docker Operation:
Retrieve logs + AI Analysis

Expected Result:

Root Cause:
Database connection timeout.

Confidence:
88%

Recommendation:
Verify database availability and connection configuration.

---

## Test Case 13

Input:
Give root cause analysis for nginx container failure

Docker Operation:
Retrieve nginx logs + LLM analysis

Expected Result:

Root Cause:
Port 80 already in use.

Confidence:
95%

Recommendation:
Stop conflicting service or modify port mapping.

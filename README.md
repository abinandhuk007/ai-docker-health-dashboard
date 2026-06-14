# AI Docker Health Dashboard

An AI-powered Docker monitoring dashboard that enables users to interact with Docker environments using natural language queries. The application combines Docker monitoring, health analysis, and Docker command translation to simplify container management and improve operational visibility.

## Features

* Docker Container Monitoring
* Real-Time CPU and Memory Tracking
* Natural Language Query Processing
* Query-to-Docker Command Translation
* Docker Health Analysis
* Container Status Monitoring
* AI-Powered Operational Insights
* Interactive Dashboard Interface

## Technology Stack

* Python
* Streamlit
* Docker SDK for Python
* Groq
* Docker Engine

## Architecture

User Query → Intent Detection → Docker SDK → Data Processing → AI Analysis → Dashboard Visualization

## Installation

### Prerequisites

* Python 3.10+
* Docker Desktop
* Groq API Key

### Clone Repository

```bash
git clone <repository-url>
cd ai-docker-health-dashboard
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
streamlit run app.py
```

## Usage

### Example Queries

* Show running containers
* Show stopped containers
* Show Docker images
* Show logs of nginx-proxy
* Which container uses the most memory?
* Which container uses the highest CPU?
* Analyze Docker health

## Docker Command Translation

The system displays the equivalent Docker command for each natural language query.

Example:

User Query:
Show running containers

Detected Intent:
LIST_RUNNING_CONTAINERS

Docker Command:
docker ps

## AI Usage Note

This project was developed with assistance from AI-powered tools, including Claude and Kiro, for requirement analysis, solution design, code generation, debugging, UI enhancement, testing, and documentation support.

All project architecture, Docker integration, business logic implementation, testing, validation, and deployment activities were performed and verified by the developer. AI-generated outputs were reviewed, refined, and validated before incorporation into the final solution.

## Future Enhancements

* Kubernetes Integration
* Multi-Host Docker Monitoring
* Predictive Health Analysis
* Container Resource Forecasting
* Alert and Notification System

## License

This project is intended for educational, research, and demonstration purposes.

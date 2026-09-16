# LeakHunter V3 ??????

LeakHunter V3 is an autonomous, enterprise-grade Cyber Threat Intelligence (CTI) platform designed to hunt, extract, and categorize stolen data across the deep/dark web in real-time.

## Features
- **Stealth Scraper Fleet:** Headless Playwright workers routed through Tor to monitor .onion forums, Telegram channels, and Pastebins.
- **AI-Driven Categorization:** In-memory Machine Learning (Random Forest) to instantly categorize data dumps (e.g., Ransomware, Botnet Logs).
- **Zero-Loss Event Bus:** RabbitMQ-backed asynchronous message queues ensuring data resilience during traffic spikes.
- **Confidence Scoring Engine:** Heuristic algorithm scoring leaks from 0-100% based on HIBP correlation, source credibility, and PII density.
- **Real-Time Dashboards & Alerts:** React SPA frontend coupled with a FastAPI backend pushing immediate Discord/Slack webhooks for high-confidence threats.

## Architecture Stack
- **Frontend:** React, Vite, Tailwind CSS v4
- **Backend:** Python 3.10+, FastAPI, Uvicorn, SQLAlchemy
- **Data Layer:** PostgreSQL (Relational), Elasticsearch (Full-text), Redis (Caching)
- **Infrastructure:** Docker, Docker Compose, Nginx (SSL Reverse Proxy), RabbitMQ (AMQP)

## Quick Start (Docker)
1. Clone the repository.
2. Configure your .env file (see .env.example).
3. Run docker-compose up --build -d to spin up the cluster.
4. Access the API at https://localhost/api/ and the frontend locally.

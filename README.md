# nz-quake-watch
# NZ Quake Watch

A real-time earthquake monitoring dashboard for New Zealand. It polls the
public [GeoNet](https://www.geonet.org.nz/) API, stores earthquake events in
PostgreSQL, and displays them on an interactive map.

This is a personal portfolio project built to practice containerized service
architecture, database migrations, and (in later stages) cloud deployment on
AWS.

## Data source & attribution

Earthquake data is provided by [GeoNet](https://www.geonet.org.nz/), a
partnership between the Earthquake Commission (EQC), GNS Science, and Land
Information New Zealand (LINZ).

Data is sourced from the
[GeoNet API](https://api.geonet.org.nz/) and is licensed under
[CC BY 3.0 NZ](https://creativecommons.org/licenses/by/3.0/nz/).

Map tiles are provided by [CARTO](https://carto.com/attributions), based on
[OpenStreetMap](https://www.openstreetmap.org/copyright) data, and rendered
with [MapLibre GL JS](https://maplibre.org/).

## Architecture

The application runs as four containerized services, orchestrated with
Docker Compose:

| Service   | Role                                                                 |
|-----------|-----------------------------------------------------------------------|
| `db`      | PostgreSQL — stores earthquake records                               |
| `flyway`  | Runs versioned SQL migrations against `db` on startup                |
| `fetcher` | Polls the GeoNet API on a schedule and upserts events into `db`       |
| `web`     | Flask app serving a JSON API and an interactive MapLibre GL dashboard |

```
GeoNet API
    │  (poll every N seconds)
    ▼
fetcher ──► PostgreSQL ◄── flyway (migrations)
                │
                ▼
              web (Flask + MapLibre GL) ──► browser
```

Each earthquake is upserted by its GeoNet `publicID`, since GeoNet revises
event details (magnitude, depth, quality) in the hours after an event, and
occasionally retracts events entirely (`quality: deleted`).

## Tech stack

- **Python 3.11**, **Flask**, **Gunicorn**
- **PostgreSQL 16**
- **Flyway** for schema migrations
- **MapLibre GL JS** + **CARTO** basemap tiles
- **Docker Compose**

## Running locally

Requirements: Docker and Docker Compose.

```bash
git clone https://github.com/<your-username>/nz-quake-watch.git
cd nz-quake-watch
docker compose up --build -d
```

This will:
1. Start PostgreSQL and wait for it to become healthy
2. Run Flyway migrations to create the schema
3. Start the fetcher, which begins polling GeoNet
4. Start the web dashboard

Open **http://localhost:5000** in your browser.

Check that data is arriving:

```bash
docker compose logs -f fetcher
```

## Roadmap

- [ ] Telegram notifications for strong quakes (high MMI) near major NZ cities
- [ ] Deploy to AWS (Lambda/Fargate + RDS or DynamoDB, provisioned via
      Terraform)
- [ ] Data retention policy for older events

## License

The application code in this repository is licensed under the MIT License.
Earthquake data displayed by the application remains subject to the GeoNet
CC BY 3.0 NZ license noted above.

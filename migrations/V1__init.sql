CREATE TABLE quakes (
    public_id   TEXT PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    depth       DOUBLE PRECISION NOT NULL,
    magnitude   DOUBLE PRECISION NOT NULL,
    mmi         INTEGER NOT NULL,
    locality    TEXT NOT NULL,
    quality     TEXT NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_quakes_time ON quakes (time DESC);
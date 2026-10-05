CREATE TABLE IF NOT EXISTS models (
    id          uuid PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now(),
    mae         double precision NOT NULL,
    rmse        double precision NOT NULL,
    is_active   boolean NOT NULL DEFAULT false
);

CREATE UNIQUE INDEX IF NOT EXISTS models_single_active
    ON models (is_active)
    WHERE is_active;

CREATE TABLE IF NOT EXISTS users (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username       text NOT NULL UNIQUE,
    password_hash  text NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);

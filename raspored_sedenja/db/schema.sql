-- SeatApp MVP schema (PostgreSQL) with local auth
CREATE TABLE IF NOT EXISTS building (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS floor (
  id SERIAL PRIMARY KEY,
  building_id INT NOT NULL REFERENCES building(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  map_svg TEXT
);

CREATE TABLE IF NOT EXISTS zone (
  id SERIAL PRIMARY KEY,
  floor_id INT NOT NULL REFERENCES floor(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type TEXT DEFAULT 'open',
  capacity INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS seat (
  id SERIAL PRIMARY KEY,
  zone_id INT NOT NULL REFERENCES zone(id) ON DELETE CASCADE,
  code TEXT NOT NULL UNIQUE,
  features JSONB DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS app_user (
  id SERIAL PRIMARY KEY,
  upn TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  dept TEXT,
  roles TEXT[] DEFAULT ARRAY['employee'],
  password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS booking (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  seat_id INT NOT NULL REFERENCES seat(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  timeslot TEXT NOT NULL DEFAULT 'full_day',
  status TEXT NOT NULL CHECK (status IN ('held','confirmed','checked_in','no_show','cancelled','remote')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (seat_id, date, timeslot)
);

CREATE TABLE IF NOT EXISTS rule (
  id SERIAL PRIMARY KEY,
  scope TEXT NOT NULL DEFAULT 'global',
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS audit (
  id SERIAL PRIMARY KEY,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  entity TEXT NOT NULL,
  before JSONB,
  after JSONB,
  ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_booking_user_date ON booking(user_id, date);
CREATE INDEX IF NOT EXISTS idx_booking_seat_date ON booking(seat_id, date);
CREATE INDEX IF NOT EXISTS idx_rule_scope ON rule(scope);

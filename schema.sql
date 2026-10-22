-- Re-runnable: rebuilds all SoilSense tables
DROP VIEW IF EXISTS v_field_advisory;
DROP TABLE IF EXISTS irrigation_log, fields, farmers, users, weather_soil_daily, districts CASCADE;
CREATE TABLE districts (
  district_id SERIAL PRIMARY KEY,
  name        VARCHAR(60) UNIQUE NOT NULL,
  latitude    NUMERIC(8,4) NOT NULL,
  longitude   NUMERIC(8,4) NOT NULL
);
CREATE TABLE users (
  user_id       SERIAL PRIMARY KEY,
  full_name     VARCHAR(100) NOT NULL,
  email         VARCHAR(120) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  phone         VARCHAR(15),
  role          VARCHAR(20) NOT NULL DEFAULT 'farmer' CHECK (role IN ('farmer','supervisor','admin')),
  created_at    TIMESTAMP DEFAULT NOW()
);
CREATE TABLE farmers (
  farmer_id   INT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  village     VARCHAR(80),
  taluka      VARCHAR(80),
  district_id INT REFERENCES districts(district_id)
);
CREATE TABLE fields (
  field_id      SERIAL PRIMARY KEY,
  farmer_id     INT NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
  field_name    VARCHAR(80) NOT NULL,
  area_acres    NUMERIC(6,2) CHECK (area_acres > 0),
  soil_type     VARCHAR(30),
  cane_variety  VARCHAR(30) DEFAULT 'Co 86032',
  planting_date DATE,
  district_id   INT NOT NULL REFERENCES districts(district_id)
);
CREATE TABLE weather_soil_daily (
  district_id INT REFERENCES districts(district_id),
  obs_date DATE,
  max_temp NUMERIC, min_temp NUMERIC, max_app_temp NUMERIC, min_app_temp NUMERIC,
  avg_rh NUMERIC, precip_mm NUMERIC, rain_mm NUMERIC, precip_hours NUMERIC,
  max_wind NUMERIC, max_gust NUMERIC, wind_dir NUMERIC,
  solar_rad NUMERIC, sunshine_sec NUMERIC, et0_mm NUMERIC,
  soil_temp_0_7 NUMERIC, soil_temp_7_28 NUMERIC,
  soil_moist_0_7 NUMERIC, soil_moist_7_28 NUMERIC,
  irrigation_reco VARCHAR(30), water_balance_mm NUMERIC, crop_water_status VARCHAR(30),
  PRIMARY KEY (district_id, obs_date)
);
CREATE TABLE irrigation_log (
  log_id       SERIAL PRIMARY KEY,
  field_id     INT NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
  irrigated_on DATE NOT NULL,
  duration_hrs NUMERIC(4,1) NOT NULL CHECK (duration_hrs > 0),
  water_kl     NUMERIC(8,1),
  fertilizer   VARCHAR(60),
  notes        TEXT
);
CREATE INDEX idx_weather_date   ON weather_soil_daily(obs_date);
CREATE INDEX idx_fields_farmer  ON fields(farmer_id);
CREATE INDEX idx_log_field_date ON irrigation_log(field_id, irrigated_on DESC);

CREATE VIEW v_field_advisory AS
SELECT f.field_id, f.farmer_id, f.field_name, f.area_acres, f.soil_type, d.name AS district,
       w.obs_date, w.soil_moist_0_7, w.soil_moist_7_28, w.max_temp, w.avg_rh,
       w.rain_mm, w.et0_mm, w.water_balance_mm, w.irrigation_reco, w.crop_water_status,
       (SELECT MAX(irrigated_on) FROM irrigation_log l WHERE l.field_id = f.field_id) AS last_irrigated
FROM fields f
JOIN districts d ON d.district_id = f.district_id
JOIN LATERAL (SELECT * FROM weather_soil_daily x WHERE x.district_id = f.district_id
              ORDER BY obs_date DESC LIMIT 1) w ON TRUE;

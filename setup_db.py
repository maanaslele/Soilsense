"""Run once:  python setup_db.py   -> creates tables + loads the Excel dataset into PostgreSQL."""
import io
import pandas as pd
from db import conn

COLS = ['district','latitude','longitude','obs_date','max_temp','min_temp','max_app_temp','min_app_temp',
        'avg_rh','precip_mm','rain_mm','precip_hours','max_wind','max_gust','wind_dir','solar_rad',
        'sunshine_sec','et0_mm','soil_temp_0_7','soil_temp_7_28','soil_moist_0_7','soil_moist_7_28',
        'irrigation_reco','water_balance_mm','crop_water_status']

df = pd.read_excel("data/Irrigation_Advisory_Workbook.xlsx")
df.columns = COLS
df["obs_date"] = pd.to_datetime(df["obs_date"]).dt.date

c = conn(); cur = c.cursor()
cur.execute(open("db/schema.sql").read())
print("Tables created.")

d = df.groupby("district", as_index=False).agg(latitude=("latitude", "first"), longitude=("longitude", "first"))
buf = io.StringIO(); d.to_csv(buf, index=False, header=False); buf.seek(0)
cur.copy_expert("COPY districts(name,latitude,longitude) FROM STDIN WITH CSV", buf)
cur.execute("SELECT district_id, name FROM districts")
df["district_id"] = df["district"].map({n: i for i, n in cur.fetchall()})

wcols = ["district_id"] + [x for x in COLS if x not in ("district", "latitude", "longitude")]
buf = io.StringIO(); df[wcols].to_csv(buf, index=False, header=False); buf.seek(0)
cur.copy_expert(f"COPY weather_soil_daily({','.join(wcols)}) FROM STDIN WITH CSV", buf)
c.commit()
cur.execute("SELECT COUNT(*) FROM weather_soil_daily")
print("Weather rows loaded:", cur.fetchone()[0], "(expected 43830)")
c.close()

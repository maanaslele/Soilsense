import html, datetime as dt
import bcrypt, pandas as pd, psycopg2.errors, streamlit as st
from db import run

st.set_page_config(page_title="SoilSense", page_icon="🌱", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@500&display=swap');
h1,h2,h3{font-family:'Bebas Neue',Impact,sans-serif!important;letter-spacing:.02em;font-weight:400!important}
.hero{padding:34px 30px;border-radius:14px;margin-bottom:22px;background:linear-gradient(120deg,#12301f 0%,#0f1110 70%);border:1px solid #2b302d}
.hero h1{font-size:76px;line-height:.95;margin:0 0 10px}.hero .hl{background:#52b788;color:#0b0d0c;padding:0 10px}
.hero p{color:#9a9f98;font-size:18px;max-width:640px;margin:0}
.card{background:#171a18;border:1px solid #2b302d;border-radius:12px;padding:18px 20px;margin-bottom:14px;position:relative}
.card small{font-family:'IBM Plex Mono',monospace;color:#9a9f98}.card h3{font-size:36px;margin:6px 0 8px}.card p{margin:0;color:#cfcabd}
.badge{position:absolute;top:14px;right:16px;color:#111;font:700 12px 'IBM Plex Mono',monospace;padding:3px 10px;border-radius:20px}
.stat{background:#171a18;border:1px solid #2b302d;border-radius:12px;padding:14px 18px;text-align:center}
.stat b{display:block;font:44px 'Bebas Neue',sans-serif;color:#52b788;line-height:1}.stat span{color:#9a9f98;font-size:13px}
[data-testid=stSidebar]{border-right:1px solid #2b302d}
.stButton>button,.stFormSubmitButton>button{border-radius:8px;font-weight:600}
</style>""", unsafe_allow_html=True)

ADV = {"Irrigate Immediately": ("Irrigate today", "#d9b44a", "HIGH"),
       "Irrigate Soon": ("Irrigate soon", "#7fb069", "MEDIUM"),
       "Adequate - Monitor": ("Moisture is adequate", "#52b788", "OK"),
       "No Irrigation Needed": ("No irrigation needed", "#3a9d78", "OK")}
SOILS = ["Black cotton", "Red", "Alluvial", "Sandy loam", "Clay loam"]
H = html.escape

def districts():
    return {r["name"]: r["district_id"] for r in run("SELECT district_id, name FROM districts ORDER BY name")}

def advice_card(f):
    t, c, b = ADV.get(f["irrigation_reco"], (f["irrigation_reco"], "#52b788", "INFO"))
    st.markdown(f"""<div class="card" style="border-left:6px solid {c}"><span class="badge" style="background:{c}">{b}</span>
    <small>{H(f['field_name'])} · {H(f['district'])} · {f['area_acres']} acres</small><h3 style="color:{c}">{t}</h3>
    <p>Soil moisture <b>{float(f['soil_moist_0_7'])*100:.0f}%</b> · Rain <b>{f['rain_mm']} mm</b> ·
    Water balance <b>{f['water_balance_mm']} mm</b> · {f['crop_water_status']} · weather of {f['obs_date']} ·
    last irrigated: {f['last_irrigated'] or 'never'}</p></div>""", unsafe_allow_html=True)

# ---------------- session / navigation ----------------
ss = st.session_state
ss.setdefault("user", None)
if "go" in ss:
    ss["nav"] = ss.pop("go")
OUT = ["Home", "Log in", "Sign up"]
IN = ["Dashboard", "My fields", "Irrigation log", "Reports", "Log out"]

with st.sidebar:
    st.markdown("## 🌱 SOILSENSE")
    st.caption("SUGARCANE ADVISORY")
    page = st.radio("Menu", IN if ss.user else OUT, key="nav", label_visibility="collapsed")
    if ss.user:
        st.success(f"Logged in: {ss.user['full_name']}")

try:
    run("SELECT 1")
except Exception as e:
    st.error("Cannot connect to PostgreSQL. Check your .env file and that setup_db.py was run.")
    st.code(str(e))
    st.stop()

# ---------------- HOME ----------------
if page == "Home":
    st.markdown("""<div class="hero"><h1>WATER THE CANE <span class="hl">AT THE RIGHT</span> HOUR.</h1>
    <p>Register your field and SoilSense reads soil moisture, rain and water loss for your district, tells you
    whether to irrigate, and keeps a record of every watering.</p></div>""", unsafe_allow_html=True)
    s = run("""SELECT (SELECT COUNT(*) FROM farmers) AS farmers, (SELECT COUNT(*) FROM fields) AS fields,
               (SELECT COUNT(*) FROM districts) AS districts, (SELECT COUNT(*) FROM weather_soil_daily) AS records""", one=True)
    for col, (v, l) in zip(st.columns(4), [(s["farmers"], "farmers"), (s["fields"], "fields"),
                                           (s["districts"], "districts"), (f"{s['records']:,}", "day records")]):
        col.markdown(f'<div class="stat"><b>{v}</b><span>{l}</span></div>', unsafe_allow_html=True)
    x = run("""SELECT d.name, w.obs_date, w.soil_moist_0_7, w.max_temp, w.avg_rh, w.irrigation_reco
               FROM weather_soil_daily w JOIN districts d USING (district_id)
               WHERE w.obs_date = (SELECT MAX(obs_date) FROM weather_soil_daily) AND w.irrigation_reco='Irrigate Immediately'
               ORDER BY w.water_balance_mm LIMIT 1""", one=True)
    st.write("")
    if x:
        st.markdown(f"""<div class="card" style="border-left:6px solid #d9b44a"><span class="badge" style="background:#d9b44a">HIGH</span>
        <small>LATEST READING IN THE DATA · {x['name']} · {x['obs_date']}</small><h3 style="color:#d9b44a">{x['irrigation_reco']}</h3>
        <p>Soil moisture <b>{float(x['soil_moist_0_7'])*100:.0f}%</b> · Max temp <b>{x['max_temp']}°C</b> · Humidity <b>{x['avg_rh']}%</b></p></div>""", unsafe_allow_html=True)
    st.info("New here? Open **Sign up** in the left menu. Want a quick look? Use **Log in → Try the demo account**.")

# ---------------- SIGN UP ----------------
elif page == "Sign up":
    st.markdown("# CREATE YOUR ACCOUNT")
    dmap = districts()
    with st.form("signup"):
        name = st.text_input("Full name")
        c1, c2 = st.columns(2)
        email = c1.text_input("Email"); phone = c2.text_input("Phone (optional)")
        v, t = c1.text_input("Village"), c2.text_input("Taluka")
        dist = st.selectbox("District", list(dmap))
        pw = st.text_input("Password (6+ characters)", type="password")
        ok = st.form_submit_button("Create account", type="primary")
    if ok:
        if not name.strip() or "@" not in email or len(pw) < 6:
            st.error("Enter your name, a valid email and a password of 6+ characters.")
        else:
            h = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            try:   # one statement = one atomic transaction (user + farmer rows together)
                run("""WITH u AS (INSERT INTO users(full_name,email,password_hash,phone) VALUES(%s,%s,%s,%s) RETURNING user_id)
                       INSERT INTO farmers(farmer_id,village,taluka,district_id) SELECT user_id,%s,%s,%s FROM u""",
                    (name.strip(), email.lower().strip(), h, phone or None, v or None, t or None, dmap[dist]))
                st.success("Account created. Open **Log in** in the left menu.")
            except psycopg2.errors.UniqueViolation:
                st.error("This email is already registered. Log in instead.")

# ---------------- LOG IN ----------------
elif page == "Log in":
    st.markdown("# WELCOME BACK")
    with st.form("login"):
        email = st.text_input("Email"); pw = st.text_input("Password", type="password")
        ok = st.form_submit_button("Log in", type="primary")
    if ok:
        u = run("SELECT * FROM users WHERE email=%s", (email.lower().strip(),), one=True)
        if u and bcrypt.checkpw(pw.encode(), u["password_hash"].encode()):
            ss.user = u; ss["go"] = "Dashboard"; st.rerun()
        else:
            st.error("Email or password is wrong.")
    if st.button("Try the demo account"):
        email = "demo@soilsense.in"
        if not run("SELECT 1 FROM users WHERE email=%s", (email,), one=True):
            did = districts()
            d = next((n for n in did if n in ("Kolhapur", "Sangli", "Satara")), list(did)[0])
            h = bcrypt.hashpw(b"Demo@1234", bcrypt.gensalt()).decode()
            uid = run("INSERT INTO users(full_name,email,password_hash) VALUES('Ramesh Patil',%s,%s) RETURNING user_id", (email, h), one=True)["user_id"]
            run("INSERT INTO farmers(farmer_id,village,district_id) VALUES(%s,'Yalakeet',%s)", (uid, did[d]))
            fid = run("INSERT INTO fields(farmer_id,field_name,area_acres,soil_type,district_id) VALUES(%s,'North plot',5.6,'Black cotton',%s) RETURNING field_id", (uid, did[d]), one=True)["field_id"]
            run("INSERT INTO irrigation_log(field_id,irrigated_on,duration_hrs,water_kl,fertilizer) VALUES(%s,'2024-12-20',2.5,120,'Urea 20 kg')", (fid,))
        ss.user = run("SELECT * FROM users WHERE email=%s", (email,), one=True); ss["go"] = "Dashboard"; st.rerun()

elif page == "Log out":
    ss.user = None; ss["go"] = "Home"; st.rerun()

# ---------------- LOGGED-IN PAGES ----------------
else:
    uid = ss.user["user_id"]
    fields = run("SELECT * FROM v_field_advisory WHERE farmer_id=%s ORDER BY field_id", (uid,))

    if page == "Dashboard":
        st.markdown("# TODAY'S ADVICE")
        if not fields:
            st.warning("You have no fields yet. Open **My fields** in the left menu to add one.")
        for f in fields:
            advice_card(f)
            with st.expander(f"Last 30 days for {f['field_name']}"):
                h = pd.DataFrame(run("""SELECT w.obs_date, w.soil_moist_0_7*100 AS moisture_pct, w.rain_mm, w.et0_mm
                    FROM weather_soil_daily w JOIN fields f ON f.district_id=w.district_id
                    WHERE f.field_id=%s AND f.farmer_id=%s ORDER BY w.obs_date DESC LIMIT 30""", (f["field_id"], uid)))
                h = h.set_index("obs_date").apply(pd.to_numeric).sort_index()
                a, b = st.columns(2)
                a.caption("Soil moisture (%)"); a.line_chart(h["moisture_pct"], color="#52b788")
                b.caption("Rain vs water loss (mm)"); b.bar_chart(h[["rain_mm", "et0_mm"]], color=["#4aa3df", "#d9b44a"])
        st.caption("Advice = the dataset's daily recommendation for your district. Data ends 31 Dec 2024.")

    elif page == "My fields":
        st.markdown("# MY FIELDS")
        dmap = districts()
        with st.form("addfield"):
            n = st.text_input("Field name", placeholder="North plot")
            a, b, c = st.columns(3)
            area = a.number_input("Area (acres)", 0.1, 500.0, 1.0, 0.1)
            soil = b.selectbox("Soil type", SOILS)
            dist = c.selectbox("District", list(dmap))
            ok = st.form_submit_button("Save field", type="primary")
        if ok and n.strip():
            run("INSERT INTO fields(farmer_id,field_name,area_acres,soil_type,district_id) VALUES(%s,%s,%s,%s,%s)",
                (uid, n.strip(), area, soil, dmap[dist])); st.success("Field saved."); st.rerun()
        if fields:
            st.dataframe(pd.DataFrame(fields)[["field_name", "area_acres", "soil_type", "district"]], use_container_width=True, hide_index=True)
            d = st.selectbox("Delete a field", [f["field_name"] for f in fields])
            if st.button("Delete selected field"):
                run("DELETE FROM fields WHERE farmer_id=%s AND field_name=%s", (uid, d)); st.rerun()

    elif page == "Irrigation log":
        st.markdown("# IRRIGATION LOG")
        if not fields:
            st.warning("Add a field first.")
        else:
            with st.form("log"):
                fm = {f["field_name"]: f["field_id"] for f in fields}
                fn = st.selectbox("Field", list(fm))
                a, b = st.columns(2)
                day = a.date_input("Date", dt.date.today()); hrs = b.number_input("Hours pumped", 0.5, 48.0, 2.0, 0.5)
                kl = a.number_input("Water used (kL)", 0.0, 100000.0, 0.0); fert = b.text_input("Fertilizer given")
                notes = st.text_area("Notes")
                ok = st.form_submit_button("Save irrigation", type="primary")
            if ok:
                run("INSERT INTO irrigation_log(field_id,irrigated_on,duration_hrs,water_kl,fertilizer,notes) VALUES(%s,%s,%s,%s,%s,%s)",
                    (fm[fn], day, hrs, kl or None, fert or None, notes or None)); st.success("Irrigation saved."); st.rerun()
        rows = run("""SELECT l.irrigated_on AS date, f.field_name AS field, l.duration_hrs AS hours, l.water_kl, l.fertilizer, l.notes
                      FROM irrigation_log l JOIN fields f USING(field_id) WHERE f.farmer_id=%s ORDER BY l.irrigated_on DESC, l.log_id DESC""", (uid,))
        st.subheader("HISTORY")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True) if rows else st.info("No irrigations logged yet.")

    elif page == "Reports":
        st.markdown("# REPORTS (SQL QUERIES)")
        q1 = """SELECT f.field_name, TO_CHAR(l.irrigated_on,'YYYY-MM') AS month, COUNT(*) AS times,
       SUM(l.duration_hrs) AS hours, SUM(l.water_kl) AS water_kl
FROM irrigation_log l JOIN fields f USING(field_id) WHERE f.farmer_id=%s
GROUP BY f.field_name, month ORDER BY month DESC"""
        st.subheader("Your water use by month")
        r = run(q1, (uid,)); st.dataframe(pd.DataFrame(r), use_container_width=True, hide_index=True) if r else st.info("Log an irrigation to see this report.")
        with st.expander("Show SQL"): st.code(q1, language="sql")
        q2 = """SELECT d.name AS district,
       COUNT(*) FILTER (WHERE w.irrigation_reco='Irrigate Immediately') AS irrigate_days,
       COUNT(*) FILTER (WHERE w.crop_water_status='Water Stress Risk') AS stress_days,
       ROUND(AVG(w.soil_moist_0_7)::numeric*100,1) AS avg_moisture_pct
FROM weather_soil_daily w JOIN districts d USING(district_id)
WHERE w.obs_date >= DATE '2024-01-01' GROUP BY d.name ORDER BY irrigate_days DESC LIMIT 10"""
        st.subheader("Top 10 districts needing irrigation in 2024")
        df = pd.DataFrame(run(q2)); st.dataframe(df, use_container_width=True, hide_index=True)
        st.bar_chart(df.set_index("district")[["irrigate_days", "stress_days"]].apply(pd.to_numeric), color=["#d9b44a", "#e0674f"])
        with st.expander("Show SQL"): st.code(q2, language="sql")

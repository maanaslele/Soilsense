# SoilSense (Python + Streamlit + PostgreSQL)

1. Install PostgreSQL (includes pgAdmin) and Python 3.10+.
2. pgAdmin: right-click Databases > Create > Database > name it `soilsense`.
3. Copy `.env.example` to `.env`, put your postgres password in it.
4. Terminal in this folder:
   pip install -r requirements.txt
   python setup_db.py        (creates tables, loads 43,830 rows; expect "Weather rows loaded: 43830")
   streamlit run app.py      (opens http://localhost:8501)
5. Use: Sign up > Log in > My fields > Dashboard > Irrigation log > Reports.
   Or Log in > "Try the demo account".
6. Check data in pgAdmin: SELECT * FROM users; SELECT * FROM v_field_advisory;

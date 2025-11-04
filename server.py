
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
from pydoc import text
from sqlalchemy import *
from flask import Flask, request, render_template, g, redirect, Response, abort, url_for, abort, flash
from datetime import date, timedelta
from math import ceil

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@34.139.8.30/proj1part2
#
# For example, if you had username ab1234 and password 123123, then the following line would be:
#
#     DATABASEURI = "postgresql://ab1234:123123@34.139.8.30/proj1part2"
#
# Modify these with your own credentials you received from TA!
DATABASE_USERNAME = "yl5961"
DATABASE_PASSWRD = "115674"
DATABASE_HOST = "34.139.8.30"
DATABASEURI = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWRD}@{DATABASE_HOST}/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
'''
with engine.connect() as conn:
	create_table_command = """
	CREATE TABLE IF NOT EXISTS test (
		id serial,
		name text
	)
	"""
	res = conn.execute(text(create_table_command))
	insert_table_command = """INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace')"""
	res = conn.execute(text(insert_table_command))
	# you need to commit for create, insert, update queries to reflect
	conn.commit()
'''
@app.route('/admin')
def admin_index():
    page = max(int(request.args.get("page", 1)), 1)
    incidents_per_page = 20

    # regular filters
    lawcategory     = request.args.get("lawcategory")
    status          = request.args.get("status")
    borough         = request.args.getlist("borough")
    severity        = request.args.get("severity")
    crime_type      = request.args.get("crime_type")
    postal_code     = request.args.get("postal_code")
    date_start      = request.args.get("date_start")
    date_end        = request.args.get("date_end")

    # NEW: victim filters
    victim_gender    = request.args.get("victim_gender")
    victim_age_grp   = request.args.get("victim_age_grp")
    victim_ethnicity = request.args.get("victim_ethnicity")

    filters = []
    params  = {}

    if lawcategory:
        filters.append("lc.category = :lawcategory")
        params["lawcategory"] = lawcategory

    if status:
        filters.append("i.status = :status")
        params["status"] = status

    if borough:
        filters.append("a.borough = ANY(:borough)")
        params["borough"] = borough

    if severity:
        filters.append("ct.severity = :severity")
        params["severity"] = severity

    clean_crime_type = (crime_type or "").strip().lower()
    if clean_crime_type:
        # escape % and _ on our side; use ESCAPE '\\'
        filters.append("ct.crime_type ILIKE :crime_type ESCAPE '\\\\'")
        params["crime_type"] = f"%{handle_wildcards_characters(clean_crime_type)}%"

    if postal_code:
        filters.append("a.postal_code = :postal_code")
        params["postal_code"] = postal_code

    if date_start:
        filters.append("i.occurred_date >= :date_start")
        params["date_start"] = date_start

    if date_end:
        filters.append("i.occurred_date <= :date_end")
        params["date_end"] = date_end

    # ----- Victim EXISTS subfilter (prevents duplicate incidents) -----
    victim_clauses = []
    if victim_gender:
        victim_clauses.append("v.gender = :v_gender")
        params["v_gender"] = victim_gender
    if victim_age_grp:
        victim_clauses.append("v.age_grp = :v_age_grp")
        params["v_age_grp"] = victim_age_grp
    if victim_ethnicity:
        victim_clauses.append("v.race = :v_ethnicity")
        params["v_ethnicity"] = victim_ethnicity

    if victim_clauses:
        victim_sql = "EXISTS (SELECT 1 FROM victim v WHERE v.incident_id = i.incident_id AND " + " AND ".join(victim_clauses) + ")"
        filters.append(victim_sql)

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    # ---------- COUNT ----------
    count_query = f"""
        SELECT COUNT(*) AS total
        FROM incident i
        JOIN address a        ON i.address_id = a.address_id
        JOIN jurisdiction j   ON i.jur_id = j.jur_id
        JOIN classified_as ca ON i.incident_id = ca.incident_id
        JOIN crimetype ct     ON ca.crime_type_id = ct.crime_type_id
        JOIN lawcategory lc   ON lc.law_cat_id = ct.law_cat_id
        {where_clause}
    """
    total_incidents = g.conn.execute(text(count_query), params).scalar_one()
    total_pages = max(ceil(total_incidents / incidents_per_page), 1)
    offset = (page - 1) * incidents_per_page

    # ---------- DATA ----------
    data_query = f"""
        SELECT
            i.incident_id,
            i.occurred_date,
            ct.crime_type,
            lc.category,
            ct.severity,
            i.status,
            j.description AS jurisdiction,
            a.borough,
            a.postal_code
        FROM incident i
        JOIN address a        ON i.address_id = a.address_id
        JOIN jurisdiction j   ON i.jur_id = j.jur_id
        JOIN classified_as ca ON i.incident_id = ca.incident_id
        JOIN crimetype ct     ON ca.crime_type_id = ct.crime_type_id
        JOIN lawcategory lc   ON lc.law_cat_id = ct.law_cat_id
        {where_clause}
        ORDER BY i.occurred_date DESC
        LIMIT :limit OFFSET :offset;
    """
    cursor = g.conn.execute(
        text(data_query),
        {**params, "limit": incidents_per_page, "offset": offset},
    )
    rows = cursor.fetchall()
    columns = [
        "occurred_date",
        "crime_type",
        "category",
        "severity",
        "status",
        "jurisdiction",
        "borough",
        "postal_code",
    ]
    cursor.close()

    # pagination url builder for /admin
    def make_url_admin(page_num: int):
        base_args = request.args.to_dict(flat=False)
        base_args["page"] = [str(page_num)]
        args_flat = {}
        for k, v in base_args.items():
            if len(v) > 1:
                args_flat[k] = v
            else:
                args_flat[k] = v[0] if v else ""
        return url_for("admin_index", **args_flat)

    window = 3
    start = max(page - window, 1)
    end = min(page + window, total_pages)
    page_numbers = list(range(start, end + 1))

    return render_template(
        "admin.html",
        rows=rows,
        columns=columns,
        page=page,
        per_page=incidents_per_page,
        total=total_incidents,
        total_pages=total_pages,
        page_numbers=page_numbers,
        make_url=make_url_admin,
    )
@app.route('/admin/<int:incident_id>', methods=['GET', 'POST'])
def admin_incident_detail(incident_id):
    # Incident core
    incident = g.conn.execute(text("""
        SELECT
            i.incident_id,
            i.occurred_date,
            i.status,
            i.incident_details AS description,
            ct.crime_type,
            lc.category,
            ct.severity,
            j.description AS jurisdiction,
            a.borough,
            a.postal_code
        FROM incident i
        JOIN address a        ON i.address_id = a.address_id
        JOIN jurisdiction j   ON i.jur_id = j.jur_id
        JOIN classified_as ca ON i.incident_id = ca.incident_id
        JOIN crimetype ct     ON ca.crime_type_id = ct.crime_type_id
        JOIN lawcategory lc   ON lc.law_cat_id = ct.law_cat_id
        WHERE i.incident_id = :incident_id
    """), {"incident_id": incident_id}).mappings().first()
    if not incident:
        abort(404)

    # Related rows
    suspects = g.conn.execute(text("""
        SELECT suspect_id, gender, race, age_grp, arrest_status
        FROM suspect
        WHERE incident_id = :incident_id
        ORDER BY suspect_id
    """), {"incident_id": incident_id}).mappings().all()

    victims = g.conn.execute(text("""
        SELECT victim_id, gender, race, injury_severity, age_grp
        FROM victim
        WHERE incident_id = :incident_id
        ORDER BY victim_id
    """), {"incident_id": incident_id}).mappings().all()

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()

        # 1) Update status
        if action == "update_status":
            new_status = (request.form.get("new_status") or "").strip()
            if new_status in ("Open", "Closed"):
                g.conn.execute(text("""
                    UPDATE incident SET status = :s WHERE incident_id = :id
                """), {"s": new_status, "id": incident_id})
                g.conn.commit()
            return redirect(url_for("admin_incident_detail", incident_id=incident_id))

        # 2) Delete incident
        if action == "delete_incident":
            g.conn.execute(text("DELETE FROM incident WHERE incident_id = :id"), {"id": incident_id})
            g.conn.commit()
            flash(f"Incident #{incident_id} was deleted as a false report.", "success")
            return redirect(url_for("admin_index"))

        # 3) Toggle suspect arrest
        if action == "update_suspect_arrest":
            sid = request.form.get("suspect_id")
            val = request.form.get("arrest_status")  # "Yes" / "No"
            if sid and val in ("Yes", "No"):
                g.conn.execute(text("""
                    UPDATE suspect
                    SET arrest_status = :ar
                    WHERE incident_id = :iid AND suspect_id = :sid
                """), {"ar": (val == "Yes"), "iid": incident_id, "sid": int(sid)})
                g.conn.commit()
            return redirect(url_for("admin_incident_detail", incident_id=incident_id))

        # 4) Update description  (uses incident_details column)
        if action == "update_description":
            new_desc = (request.form.get("incident_details") or request.form.get("new_description") or "").strip()
            g.conn.execute(
                text("UPDATE incident SET incident_details = :d WHERE incident_id = :iid"),
                {"d": new_desc or None, "iid": incident_id},
            )
            g.conn.commit()
            flash("Incident description updated.", "success")
            return redirect(url_for("admin_incident_detail", incident_id=incident_id))

        # 5) Add Suspect  (matches your form names: s_gender, s_race, s_age_grp, s_arrest)
        if action == "add_suspect":
            s_gender = (request.form.get("s_gender") or "").strip()
            s_race = (request.form.get("s_race") or "").strip()
            s_age = (request.form.get("s_age_grp") or "").strip()
            s_arrest = (request.form.get("s_arrest") or "No").strip()

            # minimal validation to avoid empty rows
            if s_gender in ("Female", "Male") and s_age in ("<18", "18-24", "25-44", "45-64", "65+"):
                g.conn.execute(text("""
                    INSERT INTO suspect (incident_id, gender, race, age_grp, arrest_status)
                    VALUES (:iid, :g, :r, :age, :ar)
                """), {
                    "iid": incident_id,
                    "g": s_gender,
                    "r": (s_race or None),
                    "age": s_age,
                    "ar": (s_arrest == "Yes"),
                })
                g.conn.commit()
                flash("Suspect added.", "success")
            else:
                flash("Please select a valid Gender and Age Group for the suspect.", "error")

            return redirect(url_for("admin_incident_detail", incident_id=incident_id))

        # 6) Add Victim  (matches your form names: v_gender, v_race, v_age_grp, v_injury)
        if action == "add_victim":
            v_gender = (request.form.get("v_gender") or "").strip()
            v_race = (request.form.get("v_race") or "").strip()
            v_age = (request.form.get("v_age_grp") or "").strip()
            v_injury = (request.form.get("v_injury") or "").strip()

            # Must satisfy Victim CHECK constraints:
            # gender in ('Female','Male'), injury_severity in ('None','Minor','Severe','Fatal'), age_grp in ('<18','18-24','25-44','45-64','65+')
            if v_gender in ("Female", "Male") and v_age in ("<18", "18-24", "25-44", "45-64", "65+") and v_injury in (
                    "None", "Minor", "Severe", "Fatal"):
                g.conn.execute(text("""
                    INSERT INTO victim (incident_id, gender, race, injury_severity, age_grp)
                    VALUES (:iid, :g, :r, :inj, :age)
                """), {
                    "iid": incident_id,
                    "g": v_gender,
                    "r": (v_race or None),
                    "inj": v_injury,
                    "age": v_age,
                })
                g.conn.commit()
                flash("Victim added.", "success")
            else:
                flash("Please select valid Gender, Age Group, and Injury Severity for the victim.", "error")

            return redirect(url_for("admin_incident_detail", incident_id=incident_id))

        # If we get here, unknown action; just bounce back.
        flash("Unknown action.", "error")
        return redirect(url_for("admin_incident_detail", incident_id=incident_id))

    # Render
    return render_template(
        "admin_detail.html",
        incident=incident,
        suspects=suspects,
        victims=victims,
    )


@app.route('/admin/new', methods=['GET', 'POST'])
def admin_new_incident():
    # Dropdowns
    jurs_raw = g.conn.execute(text("""
        SELECT jur_id, description
        FROM jurisdiction
        ORDER BY description
    """)).mappings().all()
    jurs = []
    for j in jurs_raw:
        try:
            display_id = int(float(j["jur_id"]))
        except Exception:
            display_id = j["jur_id"]
        jurs.append({"jur_id": j["jur_id"], "description": j["description"], "display_id": display_id})

    crimes = g.conn.execute(text("""
        SELECT ct.crime_type_id, ct.crime_type, ct.severity, lc.category
        FROM crimetype ct
        JOIN lawcategory lc ON lc.law_cat_id = ct.law_cat_id
        ORDER BY lc.category, ct.crime_type
    """)).mappings().all()

    if request.method == 'GET':
        return render_template('admin_new.html', jurs=jurs, crimes=crimes)

    # --- POST: read form (single occurred_date) ---
    occurred_date = (request.form.get('occurred_date') or '').strip()
    status        = (request.form.get('status') or 'Open').strip() or 'Open'
    details       = (request.form.get('incident_details') or '').strip()

    jur_id_raw     = (request.form.get('jur_id') or '').strip()
    crime_type_id  = (request.form.get('crime_type_id') or '').strip()

    borough     = (request.form.get('borough') or '').strip()
    postal_code = (request.form.get('postal_code') or '').strip()
    latitude    = (request.form.get('latitude') or '').strip()
    longitude   = (request.form.get('longitude') or '').strip()

    errors = []

    if not occurred_date:
        errors.append("Occurred Date is required.")
    if status not in ('Open', 'Closed'):
        errors.append("Status must be Open or Closed.")
    if not jur_id_raw:
        errors.append("Jurisdiction is required.")
    if not crime_type_id:
        errors.append("Crime type is required.")
    if not borough or not postal_code or not latitude or not longitude:
        errors.append("Address requires borough, postal code, latitude, and longitude.")

    # validate date format YYYY-MM-DD
    from datetime import date
    def _parse_date(s):
        try:
            y, m, d = map(int, s.split('-'))
            return date(y, m, d)
        except Exception:
            return None
    d_when = _parse_date(occurred_date)
    if not d_when:
        errors.append("Occurred Date is invalid (use YYYY-MM-DD).")

    # numerics
    try:
        float(latitude); float(longitude)
    except Exception:
        errors.append("Latitude/Longitude must be numeric.")

    # jurisdiction exists
    jur_id = None
    if jur_id_raw:
        try:
            jur_id = float(jur_id_raw)
        except Exception:
            errors.append("Jurisdiction value is invalid.")
    if jur_id is not None:
        exists = g.conn.execute(
            text("SELECT 1 FROM jurisdiction WHERE jur_id = :id"),
            {"id": jur_id}
        ).first()
        if not exists:
            errors.append("Selected jurisdiction does not exist.")

    if errors:
        return render_template('admin_new.html', jurs=jurs, crimes=crimes, errors=errors, form=request.form)

    # --- DB writes ---
    # 1) Address reuse/insert
    addr_row = g.conn.execute(
        text("""
            SELECT address_id
            FROM address
            WHERE borough = :b AND postal_code = :p AND latitude = :lat AND longitude = :lon
            LIMIT 1
        """),
        {"b": borough, "p": postal_code, "lat": latitude, "lon": longitude},
    ).first()
    address_id = addr_row[0] if addr_row else g.conn.execute(
        text("""
            INSERT INTO address (borough, postal_code, latitude, longitude)
            VALUES (:b, :p, :lat, :lon)
            RETURNING address_id
        """),
        {"b": borough, "p": postal_code, "lat": latitude, "lon": longitude},
    ).scalar_one()

    # 2) Incident (store the single occurred_date; no end-date tag)
    incident_id = g.conn.execute(
        text("""
            INSERT INTO incident (jur_id, address_id, occurred_date, status, incident_details)
            VALUES (:jur, :addr, :odate, :status, :details)
            RETURNING incident_id
        """),
        {
            "jur": jur_id,
            "addr": address_id,
            "odate": d_when.isoformat(),
            "status": status,
            "details": details or None
        },
    ).scalar_one()

    # 3) Classified_As
    g.conn.execute(
        text("INSERT INTO classified_as (incident_id, crime_type_id) VALUES (:iid, :ctid)"),
        {"iid": incident_id, "ctid": int(crime_type_id)},
    )

    # 4) Suspects (up to 3)
    for i in range(1, 4):
        s_gender = (request.form.get(f'suspect{i}_gender') or '').strip()
        s_race   = (request.form.get(f'suspect{i}_race') or '').strip()
        s_age    = (request.form.get(f'suspect{i}_age_grp') or '').strip()
        s_arrest = request.form.get(f'suspect{i}_arrest_status')
        arrest_status = True if s_arrest == 'on' else False
        if any([s_gender, s_race, s_age, s_arrest]):
            if s_gender and s_age:
                g.conn.execute(
                    text("""
                        INSERT INTO suspect (incident_id, gender, race, age_grp, arrest_status)
                        VALUES (:iid, :g, :r, :age, :ar)
                    """),
                    {"iid": incident_id, "g": s_gender or None, "r": s_race or None,
                     "age": s_age or None, "ar": arrest_status},
                )

    # 5) Victims (up to 3)
    for i in range(1, 4):
        v_gender = (request.form.get(f'victim{i}_gender') or '').strip()
        v_race   = (request.form.get(f'victim{i}_race') or '').strip()
        v_age    = (request.form.get(f'victim{i}_age_grp') or '').strip()
        v_injury = (request.form.get(f'victim{i}_injury') or '').strip()
        if any([v_gender, v_race, v_age, v_injury]):
            if v_gender and v_age:
                g.conn.execute(
                    text("""
                        INSERT INTO victim (incident_id, gender, race, injury_severity, age_grp)
                        VALUES (:iid, :g, :r, :inj, :age)
                    """),
                    {"iid": incident_id, "g": v_gender or None, "r": v_race or None,
                     "inj": v_injury or None, "age": v_age or None},
                )

    g.conn.commit()
    return redirect(url_for('admin_incident_detail', incident_id=incident_id))

@app.route('/admin/system', methods=['GET', 'POST'])
def admin_system():
    # Still load existing categories so Crime Type can reference them
    lawcats = g.conn.execute(text("""
        SELECT law_cat_id, category FROM lawcategory ORDER BY law_cat_id
    """)).mappings().all()

    msg = None
    errors = []

    if request.method == 'POST':
        kind = request.form.get('kind')

        # --- Create Crime Type (uses existing law categories only) ---
        if kind == 'crimetype':
            law_cat_id = (request.form.get('ct_law_cat_id') or '').strip().upper()
            crime_type = (request.form.get('crime_type') or '').strip()
            severity   = (request.form.get('severity') or '').strip().lower()

            if law_cat_id not in ('F','M','V'):
                errors.append("Law category must be F/M/V (choose an existing one).")
            if not crime_type:
                errors.append("Crime type name is required.")
            if severity not in ('low','medium','high'):
                errors.append("Severity must be low/medium/high.")

            if not errors:
                lc_ok = g.conn.execute(
                    text("SELECT 1 FROM lawcategory WHERE law_cat_id = :id"),
                    {"id": law_cat_id}
                ).first()
                if not lc_ok:
                    errors.append(f"Law category '{law_cat_id}' does not exist.")
                else:
                    dup = g.conn.execute(text("""
                        SELECT 1 FROM crimetype
                        WHERE law_cat_id=:lc AND lower(crime_type)=:ct
                    """), {"lc": law_cat_id, "ct": crime_type.lower()}).first()
                    if dup:
                        errors.append("Crime type already exists under that law category.")
                    else:
                        g.conn.execute(text("""
                            INSERT INTO crimetype (law_cat_id, crime_type, severity)
                            VALUES (:lc, :ct, :sev)
                        """), {"lc": law_cat_id, "ct": crime_type, "sev": severity})
                        g.conn.commit()
                        msg = f"Created crime type “{crime_type}” ({severity}) under {law_cat_id}"

        # --- Create Jurisdiction (INT input -> FLOAT PK) ---
        elif kind == 'jurisdiction':
            jur_int_raw = (request.form.get('jur_id_int') or '').strip()
            description = (request.form.get('jur_description') or '').strip()

            if not jur_int_raw:
                errors.append("Jurisdiction ID (integer) is required.")
            if not description:
                errors.append("Jurisdiction description is required.")

            jur_float = None
            if jur_int_raw:
                try:
                    jur_int = int(jur_int_raw)
                    if jur_int < 0:
                        errors.append("Jurisdiction ID must be non-negative.")
                    jur_float = float(jur_int)
                except Exception:
                    errors.append("Jurisdiction ID must be an integer (e.g., 72).")

            if not errors:
                exists = g.conn.execute(
                    text("SELECT 1 FROM jurisdiction WHERE jur_id = :id"),
                    {"id": jur_float}
                ).first()
                if exists:
                    errors.append(f"Jurisdiction {int(jur_float)} already exists.")
                else:
                    g.conn.execute(
                        text("INSERT INTO jurisdiction (jur_id, description) VALUES (:id, :d)"),
                        {"id": jur_float, "d": description}
                    )
                    g.conn.commit()
                    msg = f"Created jurisdiction {int(jur_float)} — {description}"

    return render_template(
        "admin_system.html",
        lawcats=lawcats,  # still needed for the crime-type dropdown
        msg=msg,
        errors=errors,
    )

######################################### above is admin functions ######################################################
@app.route("/recommendations", methods=["GET"])
def recommendations():
    """
    Personalized recommendations using demographic match rate:
      demo_pct = demo_incidents / total_incidents (per postal_code+borough)
    A victim "matches" if at least one victim in the incident has
    (gender == :gender) AND/OR (age_grp == :age_grp) AND/OR (race == :race),
    for any fields the user actually provided.
    """
    # --- incoming filters used for BOTH sections ---
    postal = (request.args.get("postal_code") or "").strip()
    gender = (request.args.get("gender") or "").strip()
    age_grp = (request.args.get("age_grp") or "").strip()
    race   = (request.args.get("race") or "").strip()

    params = {"gender": gender, "age_grp": age_grp, "race": race}

    # ------------------------------------------------------------
    # Section A: Top 10 "safest" (lowest demographic match %)
    # ------------------------------------------------------------
    # Notes:
    # - We only include rows with BOTH postal_code and borough present.
    # - If no demographic filters were supplied (all empty), demo_incidents == total_incidents,
    #   so demo_pct == 100% for all rows. That’s expected: “people like me” == everyone.
    top10_sql = """
    WITH base AS (
      SELECT
        i.incident_id,
        a.postal_code::text AS postal_code,
        a.borough
      FROM incident i
      JOIN address a        ON a.address_id = i.address_id
      WHERE a.postal_code IS NOT NULL
        AND a.postal_code <> ''
        AND a.borough IS NOT NULL
        AND a.borough <> ''
    ),
    tot AS (
      SELECT
        b.postal_code,
        b.borough,
        COUNT(DISTINCT b.incident_id) AS total_incidents
      FROM base b
      GROUP BY b.postal_code, b.borough
    ),
    demo AS (
      SELECT
        b.postal_code,
        b.borough,
        COUNT(DISTINCT b.incident_id) AS demo_incidents
      FROM base b
      WHERE
        -- If all demographic filters are empty, count EVERY incident as matching.
        (:gender = '' AND :age_grp = '' AND :race = '')
        OR EXISTS (
            SELECT 1
            FROM victim v
            WHERE v.incident_id = b.incident_id
              AND (:gender  = '' OR v.gender = :gender)
              AND (:age_grp = '' OR v.age_grp = :age_grp)
              AND (:race    = '' OR v.race   = :race)
        )
      GROUP BY b.postal_code, b.borough
    )
    SELECT
      t.postal_code,
      t.borough,
      t.total_incidents,
      COALESCE(d.demo_incidents, 0) AS demo_incidents,
      CASE WHEN t.total_incidents = 0
           THEN 0.0
           ELSE ROUND(100.0 * COALESCE(d.demo_incidents,0) / t.total_incidents, 2)
      END AS demo_pct
    FROM tot t
    LEFT JOIN demo d
      ON d.postal_code = t.postal_code AND d.borough = t.borough
    -- SAFEST first = lowest demographic match percentage.
    ORDER BY demo_pct ASC, t.total_incidents DESC, t.postal_code ASC
    LIMIT 10;
    """
    top_rows = g.conn.execute(text(top10_sql), params).mappings().all()

    # Build a simple column header list for the table
    top_cols = ["Postal Code", "Borough", "Total Incidents", "Matching Incidents", "Match %"]

    # ------------------------------------------------------------
    # Section B: Risk for a specific postal code (optional)
    # ------------------------------------------------------------
    user_result = None
    risk_bucket = None

    if postal:
        row = g.conn.execute(
            text("""
            WITH tot AS (
              SELECT
                a.postal_code::text AS postal_code,
                a.borough           AS borough,
                COUNT(DISTINCT i.incident_id) AS total_incidents
              FROM incident i
              JOIN address a ON a.address_id = i.address_id
              WHERE a.postal_code::text = :zip
              GROUP BY a.postal_code, a.borough
            ),
            demo AS (
              SELECT
                COUNT(DISTINCT i.incident_id) AS demo_incidents
              FROM incident i
              JOIN address a ON a.address_id = i.address_id
              WHERE a.postal_code::text = :zip
                AND (
                  (:gender = '' AND :age_grp = '' AND :race = '')
                  OR EXISTS (
                      SELECT 1
                      FROM victim v
                      WHERE v.incident_id = i.incident_id
                        AND (:gender  = '' OR v.gender = :gender)
                        AND (:age_grp = '' OR v.age_grp = :age_grp)
                        AND (:race    = '' OR v.race   = :race)
                  )
                )
            )
            SELECT
              t.postal_code,
              t.borough,
              t.total_incidents,
              COALESCE(d.demo_incidents,0) AS demo_incidents,
              CASE WHEN t.total_incidents = 0
                   THEN 0.0
                   ELSE ROUND(100.0 * COALESCE(d.demo_incidents,0) / t.total_incidents, 2)
              END AS demo_pct
            FROM tot t
            CROSS JOIN demo d
            """),
            {"zip": postal, **params},
        ).mappings().first()

        if row:
            pct = float(row["demo_pct"])
            # Buckets — tweak thresholds if you prefer
            if pct <= 10:
                risk_bucket = "Low"
            elif pct <= 25:
                risk_bucket = "Moderate"
            else:
                risk_bucket = "High"

            user_result = {
                "postal_code": row["postal_code"],
                "borough": row["borough"],
                "total_incidents": row["total_incidents"],
                "demo_incidents": row["demo_incidents"],
                "demo_pct": pct,
            }

    return render_template(
        "recommendations.html",
        # top-10 table
        top_rows=top_rows,
        top_cols=top_cols,
        # echo the filters back to the page
        postal_code=postal,
        gender=gender,
        age_grp=age_grp,
        race=race,
        # right-side card
        user_result=user_result,
        risk_bucket=risk_bucket,
    )


######################################### above is personalized recommendation functions ######################################################
@app.route('/incident/<int:incident_id>', methods=['GET'])
def user_incident_detail(incident_id):
    incident = g.conn.execute(text("""
        SELECT
            i.incident_id,
            i.occurred_date,
            i.status,
            i.incident_details AS description,
            ct.crime_type,
            lc.category,
            ct.severity,
            j.description AS jurisdiction,
            a.borough,
            a.postal_code
        FROM incident i
        JOIN address a        ON i.address_id = a.address_id
        JOIN jurisdiction j   ON i.jur_id = j.jur_id
        JOIN classified_as ca ON i.incident_id = ca.incident_id
        JOIN crimetype ct     ON ca.crime_type_id = ct.crime_type_id
        JOIN lawcategory lc   ON lc.law_cat_id = ct.law_cat_id
        WHERE i.incident_id = :incident_id
    """), {"incident_id": incident_id}).mappings().first()
    if not incident:
        abort(404)

    suspects = g.conn.execute(text("""
        SELECT suspect_id, gender, race, age_grp, arrest_status
        FROM suspect
        WHERE incident_id = :incident_id
        ORDER BY suspect_id
    """), {"incident_id": incident_id}).mappings().all()

    victims = g.conn.execute(text("""
        SELECT victim_id, gender, race, injury_severity, age_grp
        FROM victim
        WHERE incident_id = :incident_id
        ORDER BY victim_id
    """), {"incident_id": incident_id}).mappings().all()

    return render_template("user_detail.html",
                           incident=incident, suspects=suspects, victims=victims)

# helper functions
def build_base_args():
	base_args = request.args.to_dict(flat=False)
	base_args.pop("page", None)
	return base_args

def make_url_page(page):
	base_args = build_base_args()
	base_args["page"] = [str(page)]
	
	args_flat = {}
	for k, v in base_args.items():
		if len(v) > 1:
			args_flat[k] = v
		else:
			if v:
				args_flat[k] = v[0]
			else:
				args_flat[k] = ""
	return url_for("index", **args_flat)

def handle_wildcards_characters(s):
	s = s.replace("\\", "\\\\")
	s = s.replace("%", "\\%")
	s = s.replace("_", "\\_")
	return s

@app.before_request
def before_request():
	"""
	This function is run at the beginning of every web request 
	(every time you enter an address in the web browser).
	We use it to setup a database connection that can be used throughout the request.

	The variable g is globally accessible.
	"""
	try:
		g.conn = engine.connect()
	except:
		print("uh oh, problem connecting to database")
		import traceback; traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	try:
		g.conn.close()
	except Exception as e:
		pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: https://flask.palletsprojects.com/en/1.1.x/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
@app.route('/incidents', methods=['GET'])
def index():
    """
    General-user incidents list with filters + 'View details' action.
    """
    # --- query parameters ---
    page = max(int(request.args.get("page", 1)), 1)
    incidents_per_page = 20

    lawcategory      = request.args.get("lawcategory")
    status           = request.args.get("status")
    borough          = request.args.getlist("borough")
    severity         = request.args.get("severity")
    crime_type       = request.args.get("crime_type")
    postal_code      = request.args.get("postal_code")
    date_start       = request.args.get("date_start")
    date_end         = request.args.get("date_end")
    victim_gender    = request.args.get("victim_gender")
    victim_age_grp   = request.args.get("victim_age_grp")
    victim_ethnicity = request.args.get("victim_ethnicity")

    filters     = []
    parameters  = {}

    if lawcategory:
        filters.append("lc.category = :lawcategory")
        parameters["lawcategory"] = lawcategory

    if status:
        filters.append("i.status = :status")
        parameters["status"] = status

    if borough:
        filters.append("a.borough = ANY(:borough)")
        parameters["borough"] = borough

    if severity:
        filters.append("ct.severity = :severity")
        parameters["severity"] = severity

    clean_crime_type = (crime_type or "").strip().lower()
    if clean_crime_type:
        filters.append("ct.crime_type ILIKE :crime_type ESCAPE '\\'")
        parameters["crime_type"] = f"%{handle_wildcards_characters(clean_crime_type)}%"

    if postal_code:
        filters.append("a.postal_code = :postal_code")
        parameters["postal_code"] = postal_code

    if date_start:
        filters.append("i.occurred_date >= :date_start")
        parameters["date_start"] = date_start

    if date_end:
        filters.append("i.occurred_date <= :date_end")
        parameters["date_end"] = date_end

    # victim filters
    if victim_gender:
        filters.append("v.gender = :victim_gender")
        parameters["victim_gender"] = victim_gender

    if victim_age_grp:
        filters.append("v.age_grp = :victim_age_grp")
        parameters["victim_age_grp"] = victim_age_grp

    if victim_ethnicity:
        filters.append("v.race = :victim_ethnicity")
        parameters["victim_ethnicity"] = victim_ethnicity

    # build WHERE
    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    # --- counts for pagination ---
    count_query = f"""
        SELECT COUNT(*) AS total
        FROM incident i
        JOIN address a        ON i.address_id = a.address_id
        JOIN jurisdiction j   ON i.jur_id = j.jur_id
        JOIN classified_as ca ON i.incident_id = ca.incident_id
        JOIN crimetype ct     ON ca.crime_type_id = ct.crime_type_id
        JOIN lawcategory lc   ON lc.law_cat_id = ct.law_cat_id
        LEFT JOIN victim v    ON v.incident_id = i.incident_id
        {where_clause}
    """
    total_incidents = g.conn.execute(text(count_query), parameters).scalar_one()
    total_pages = max(ceil(total_incidents / incidents_per_page), 1)
    offset = (page - 1) * incidents_per_page

    # --- data query (incident_id LAST) ---
    data_query = f"""
        SELECT
            i.occurred_date,
            ct.crime_type,
            lc.category,
            ct.severity,
            i.status,
            j.description AS jurisdiction,
            a.borough,
            a.postal_code,
            i.incident_id
        FROM incident i
        JOIN address a        ON i.address_id = a.address_id
        JOIN jurisdiction j   ON i.jur_id = j.jur_id
        JOIN classified_as ca ON i.incident_id = ca.incident_id
        JOIN crimetype ct     ON ca.crime_type_id = ct.crime_type_id
        JOIN lawcategory lc   ON lc.law_cat_id = ct.law_cat_id
        LEFT JOIN victim v    ON v.incident_id = i.incident_id
        {where_clause}
        ORDER BY i.occurred_date DESC
        LIMIT :limit OFFSET :offset
    """
    cursor = g.conn.execute(
        text(data_query),
        {**parameters, "limit": incidents_per_page, "offset": offset},
    )
    rows = cursor.fetchall()

    # mutate header so the last column shows as "Action"
    columns = list(cursor.keys())
    if columns and str(columns[-1]).lower() == "incident_id":
        columns[-1] = "Action"

    cursor.close()

    # pagination window
    window = 3
    start = max(page - window, 1)
    end = min(page + window, total_pages)
    page_numbers = list(range(start, end + 1))

    return render_template(
        "index.html",
        rows=rows,
        columns=columns,
        page=page,
        per_page=incidents_per_page,
        total=total_incidents,
        total_pages=total_pages,
        page_numbers=page_numbers,
        make_url=make_url_page,
    )

#
# This is an example of a different path.  You can see it at:
# 
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#

@app.route('/incidents/analysis', methods=['GET'])
def incidents_analysis():

	# section 1: top 10 crime types in nyc

	# user inputs
	window = request.args.get("window", "all")  # 90d, 180d, 1y, 3y, all
	borough = request.args.get("borough")
	postal_code = request.args.get("postal_code")
	PRESETS_DAYS = {"90d": 90, "1y": 365, "5y": 365*5, "10y": 365*10}

	filters = []
	parameters = {}

	if window != "all":
		cutoff_date = date.today() - timedelta(days=PRESETS_DAYS.get(window, 90))
		filters.append("i.occurred_date >= :cutoff_date")
		parameters["cutoff_date"] = cutoff_date

	if borough:
		filters.append("a.borough = :borough")
		parameters["borough"] = borough

	if postal_code:
		filters.append("a.postal_code = :postal_code")
		parameters["postal_code"] = postal_code

	if filters:
		where_clause = "WHERE " + " AND ".join(filters)
	else:
		where_clause = ""

	# query 1: top 10 crime types
	top10_sql = f"""
	WITH counts AS (
	SELECT
		ct.crime_type_id,
        lc.category,
		ct.crime_type,
		COUNT(*) AS incident_count
	FROM classified_as ca
	JOIN crimetype ct ON ct.crime_type_id = ca.crime_type_id
	JOIN incident i ON i.incident_id = ca.incident_id
	JOIN address a ON a.address_id = i.address_id
    JOIN lawcategory lc ON lc.law_cat_id = ct.law_cat_id
	{where_clause}
	GROUP BY ct.crime_type_id, ct.crime_type, lc.category
	),
	ranked AS (
	SELECT
		c.*,
		DENSE_RANK() OVER (ORDER BY c.incident_count DESC) AS rnk
	FROM counts c
	)
	SELECT category as law_category, crime_type, incident_count
	FROM ranked
	WHERE rnk <= 10
	ORDER BY incident_count DESC, crime_type;
	"""

	# execute query & store results
	cursor = g.conn.execute(text(top10_sql), parameters)
	rows = cursor.fetchall()
	columns = cursor.keys()
	cursor.close()
    
	# query 2: customized filter
    
	# user inputs
	custom_postal_code = request.args.get("custom_postal_code")
	custom_gender = request.args.get("custom_gender")
	custom_age_group = request.args.get("custom_age_group")
	custom_ethnicity = request.args.get("custom_ethnicity")

	custom_filters = []
	custom_parameters = {}

	if custom_postal_code:
		custom_filters.append("a.postal_code = :custom_postal_code")
		custom_parameters["custom_postal_code"] = custom_postal_code

	if custom_gender:
		custom_filters.append("v.gender = :custom_gender")
		custom_parameters["custom_gender"] = custom_gender

	if custom_age_group:
		custom_filters.append("v.age_grp = :custom_age_group")
		custom_parameters["custom_age_group"] = custom_age_group

	if custom_ethnicity:
		custom_filters.append("v.race = :custom_ethnicity")
		custom_parameters["custom_ethnicity"] = custom_ethnicity

	if custom_filters:
		custom_where_clause = "WHERE " + " AND ".join(custom_filters)
	else:
		custom_where_clause = ""
            
    # query 2: customized filters
	custom_sql = f"""
    SELECT 
        lc.category as law_category,
        ct.crime_type,
        COUNT(*) AS num_incidents
    FROM incident i
        JOIN victim v ON v.incident_id = i.incident_id
        JOIN address a ON i.address_id = a.address_id
        JOIN classified_as ca ON ca.incident_id = i.incident_id
        JOIN crimetype ct ON ct.crime_type_id = ca.crime_type_id
        JOIN lawcategory lc ON lc.law_cat_id = ct.law_cat_id
    {custom_where_clause}
    GROUP BY ct.crime_type_id, lc.category, ct.crime_type
    ORDER BY num_incidents DESC;
    """

    # execute query & store results
	custom_cursor = g.conn.execute(text(custom_sql), custom_parameters)
	custom_rows = custom_cursor.fetchall()
	custom_columns = custom_cursor.keys()
	custom_cursor.close()


    # query 3: crime trend over time

    # set up
	crime_types = g.conn.execute(text("""
        SELECT ct.crime_type_id, ct.crime_type, ct.severity, lc.category
        FROM crimetype ct
        JOIN lawcategory lc ON lc.law_cat_id = ct.law_cat_id
        ORDER BY lc.category, ct.crime_type
    """)).mappings().all()

    # user inputs
	year_from = request.args.get("year_from")
	year_to = request.args.get("year_to")
	crime_type_id = request.args.get("crime_type_id")
	trend_borough = request.args.get("trend_borough")

	trend_filters = []
	trend_parameters = {}

	if year_from:
		trend_filters.append("i.occurred_date >= :year_from")
		trend_parameters["year_from"] = f"{int(year_from)}-01-01"

	if year_to:
		trend_filters.append("i.occurred_date <= :year_to")
		trend_parameters["year_to"] = f"{int(year_to)}-12-31"

	if crime_type_id:
		trend_filters.append("ct.crime_type_id = :crime_type_id")
		trend_parameters["crime_type_id"] = crime_type_id

	if trend_borough:
		trend_filters.append("a.borough = :trend_borough")
		trend_parameters["trend_borough"] = trend_borough

	if trend_filters:
		where_clause_trend = "WHERE " + " AND ".join(trend_filters)
	else:
		where_clause_trend = ""


    # query 3: crime trend over time
	crime_trend_sql = f"""
    SELECT 
        EXTRACT(YEAR FROM i.occurred_date)::INT AS year,
        COUNT(*) AS num_incidents
    FROM incident i
        JOIN classified_as ca ON i.incident_id = ca.incident_id
        JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
        JOIN address a ON i.address_id = a.address_id
    {where_clause_trend}
    GROUP BY year
    ORDER BY year;
    """

    # execute query & store results
	trend_cursor = g.conn.execute(text(crime_trend_sql), trend_parameters)
	trend_rows = trend_cursor.fetchall()
	trend_columns = trend_cursor.keys()
	trend_cursor.close()


	return render_template(
        "incidents-analysis.html", 
        rows=rows, columns=columns, window=window, borough=borough, postal_code=postal_code,
        custom_rows=custom_rows, custom_columns=custom_columns, custom_postal_code=custom_postal_code, custom_gender=custom_gender, custom_age_group=custom_age_group, custom_ethnicity=custom_ethnicity,
        trend_rows=trend_rows, trend_columns=trend_columns, crime_types=crime_types, crime_type_id=crime_type_id, year_from=year_from, year_to=year_to, trend_borough=trend_borough
    )

# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
	# accessing form inputs from user
	name = request.form['name']
	
	# passing params in for each variable into query
	params = {}
	params["new_name"] = name
	g.conn.execute(text('INSERT INTO test(name) VALUES (:new_name)'), params)
	g.conn.commit()
	return redirect('/')


@app.route('/login')
def login():
	abort(401)
	# Your IDE may highlight this as a problem - because no such function exists (intentionally).
	# This code is never executed because of abort().
	this_is_never_executed()


if __name__ == "__main__":
	import click

	@click.command()
	@click.option('--debug', is_flag=True)
	@click.option('--threaded', is_flag=True)
	@click.argument('HOST', default='0.0.0.0')
	@click.argument('PORT', default=8111, type=int)
	def run(debug, threaded, host, port):
		"""
		This function handles command line parameters.
		Run the server using:

			python server.py

		Show the help text using:

			python server.py --help

		"""

		HOST, PORT = host, port
		print("running on %s:%d" % (HOST, PORT))
		app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

run()

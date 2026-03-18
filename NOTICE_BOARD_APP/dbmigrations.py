import psycopg2
import json
from psycopg2.extras import execute_batch

# ==============================
# 🔹 CONFIGURATION
# ==============================

MODE = "overwrite"
# OPTIONS:
# "overwrite" → delete & reload table (recommended 🔥)
# "skip"      → skip if table already has data
# "append"    → add data without deleting

LOCAL_DB = {
    "host":"localhost",
    "database":"digital_notice_board",
    "user":"postgres",
    "password":"JANANI",
    "port":"5432",
}

RENDER_DB = {
    "host":"dpg-d6so6kk50q8c73fnf1c0-a.oregon-postgres.render.com",
    "database":"digital_notice_board_hxk9",
    "user":"digital_notice_board_hxk9_user",
    "password":"i5gAIxhZ0ZO3i3OnIVjNYTa8cPva0tza",
    "port":"5432",
    "sslmode":"require",   # IMPORTANT for Render
}

SKIP_TABLES = []  # optional manual skip

# ==============================
# 🔹 CONNECT
# ==============================

local_conn = psycopg2.connect(**LOCAL_DB)
render_conn = psycopg2.connect(**RENDER_DB)

local_cur = local_conn.cursor()
render_cur = render_conn.cursor()

# ==============================
# 🔹 GET TABLES
# ==============================

local_cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema='public'
""")

tables = local_cur.fetchall()

# ==============================
# 🔹 PROCESS
# ==============================

for table in tables:
    table_name = table[0]

    if table_name in SKIP_TABLES:
        print(f"⏭️ Skipping (manual): {table_name}")
        continue

    print(f"\n📦 Processing table: {table_name}")

    try:
        # Check existing data in Render
        render_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = render_cur.fetchone()[0]

        if MODE == "skip" and count > 0:
            print(f"⏭️ Skipped (already has data): {table_name}")
            continue

        if MODE == "overwrite":
            print(f"🧹 Clearing table: {table_name}")
            render_cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")

        # Fetch local data
        local_cur.execute(f"SELECT * FROM {table_name}")
        rows = local_cur.fetchall()

        if not rows:
            print(f"⚠️ No data in {table_name}")
            continue

        # Columns
        colnames = [desc[0] for desc in local_cur.description]
        columns = ",".join(colnames)
        placeholders = ",".join(["%s"] * len(colnames))

        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        # 🔥 Convert (JSON fix)
        converted_rows = []
        for row in rows:
            new_row = []
            for val in row:
                if isinstance(val, list):
                    new_row.append(json.dumps(val))
                else:
                    new_row.append(val)
            converted_rows.append(tuple(new_row))

        # Insert
        execute_batch(render_cur, insert_query, converted_rows)
        render_conn.commit()

        print(f"✅ Done: {table_name} ({len(rows)} rows)")

    except Exception as e:
        render_conn.rollback()
        print(f"❌ Error in {table_name}: {e}")
        continue

# ==============================
# 🔹 CLOSE
# ==============================

local_cur.close()
render_cur.close()
local_conn.close()
render_conn.close()

print("\n🎉 Migration completed (Smart Mode)!")
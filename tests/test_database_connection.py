from src.database import get_connection
with get_connection() as con:
    print(con.execute("SELECT COUNT(*) FROM cost_records").fetchone())
    print(con.execute("SELECT COUNT(*) FROM valid_cost_records").fetchone())
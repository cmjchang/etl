"""Recover a fixed CSV from the existing raw snapshot, without downloading."""
from pathlib import Path
import duckdb
project=Path(__file__).resolve().parent
csv=project/'data/df_VEH0160_UK.csv'
if csv.exists(): raise SystemExit('Existing CSV preserved: '+str(csv))
csv.parent.mkdir(parents=True,exist_ok=True)
with duckdb.connect(str(project.parent/'my_database.duckdb'),read_only=True) as con:
    old_exists=con.execute("select 1 from information_schema.tables where table_schema='src' and table_name='veh0160_raw'").fetchone()
    source='src.veh0160_raw' if old_exists else 'raw.raw_dvla__vehicle_registrations'
    con.execute("copy (select * exclude (source_file, loaded_at) from "+source+") to '"+csv.as_posix().replace("'","''")+"' (format csv, header true)")
print('Recovered static source CSV from the existing database snapshot:',csv)

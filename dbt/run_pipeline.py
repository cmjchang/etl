"""Manually build, validate, export to a fresh batch, then publish a manifest."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import duckdb

PROJECT = Path(__file__).resolve().parent
NAMES = ['annual_model_registrations', 'annual_model_rankings', 'annual_best_models']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--export-root', default='')
    args = parser.parse_args()
    os.chdir(PROJECT)
    root = Path(args.export_root).resolve() if args.export_root else PROJECT.parent / 'exports'
    batch = root / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    dbt = PROJECT / '.venv/Scripts/dbt.exe'
    subprocess.run([str(dbt), 'build', '--profiles-dir', '.', '--exclude', 'tag:export'], check=True)
    batch.mkdir(parents=True)
    variables = json.dumps({'export_dir': batch.as_posix()})
    subprocess.run([str(dbt), 'build', '--profiles-dir', '.', '--select', 'tag:export', '--vars', variables], check=True)
    db = Path(os.environ.get('VEHICLE_DB_PATH', '../my_database.duckdb')).resolve()
    result = validate_exports(db, batch)
    manifest = {'database': str(db), 'batch': str(batch), 'validated_files': result}
    (batch / '_SUCCESS.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    temp = root / ('latest-' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    os.replace(temp, root / 'latest.json')
    print('Validated and published nine files:', batch)

def validate_exports(db, batch):
    result = {}
    with duckdb.connect(str(db), read_only=True) as con:
        for name in NAMES:
            relation = 'drv.' + name
            columns = con.sql('describe ' + relation).fetchall()
            # JSON and CSV readers infer types; normalize to the exact drv schema.
            for fmt in ['csv', 'json', 'parquet']:
                path = batch / (name + '.' + fmt)
                if fmt == 'json':
                    data = json.loads(path.read_text(encoding='utf-8'))
                    if not isinstance(data, list):
                        raise ValueError('JSON output must be an array')
                    if not data:
                        if con.sql('select count(*) from ' + relation).fetchone()[0] != 0:
                            raise ValueError('Unexpected empty JSON')
                        result[path.name] = 0
                        continue
                reader = f"read_{fmt}('{path.as_posix()}'" + (", header=true, all_varchar=true)" if fmt == 'csv' else ')')
                projection = ', '.join('cast("' + c[0] + '" as ' + c[1] + ') as "' + c[0] + '"' for c in columns)
                con.execute('create or replace temp view export_check as select ' + projection + ' from ' + reader)
                mismatch = con.sql('(select * from ' + relation + ' except all select * from export_check) union all (select * from export_check except all select * from ' + relation + ')').fetchone()
                if mismatch is not None:
                    raise ValueError('Export mismatch: ' + str(path))
                result[path.name] = con.sql('select count(*) from export_check').fetchone()[0]
    return result

if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, Exception) as exc:
        print('Pipeline failed; latest completed export batch is unchanged:', exc, file=sys.stderr)
        sys.exit(1)

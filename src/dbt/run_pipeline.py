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
ARTIFACTS = PROJECT.parents[1] / '.artifacts'
NAMES = ['annual_model_registrations', 'annual_model_rankings', 'annual_best_models']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default=str(PROJECT / 'data/sample_vehicle_registrations.csv'))
    parser.add_argument('--database', default=os.environ.get('VEHICLE_DB_PATH', str(ARTIFACTS / 'vehicle-demo.duckdb')))
    parser.add_argument('--export-root', default='')
    args = parser.parse_args()
    source = args.source
    if not source.startswith(('https://', 'http://')):
        source = str(Path(source).expanduser().resolve(strict=True))
    db = Path(args.database).expanduser().resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, VEHICLE_DB_PATH=str(db))
    root = Path(args.export_root).expanduser().resolve() if args.export_root else ARTIFACTS / 'exports'
    batch = root / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    variables = {'source_csv_path': source}
    command = [sys.executable, '-m', 'dbt.cli.main', 'build', '--profiles-dir', str(PROJECT)]
    subprocess.run(command + ['--exclude', 'tag:export', '--vars', json.dumps(variables),
                   '--target-path', str(ARTIFACTS / 'dbt/build'),
                   '--log-path', str(ARTIFACTS / 'logs/build')],
                   cwd=PROJECT, env=environment, check=True)
    batch.mkdir(parents=True)
    variables['export_dir'] = batch.as_posix()
    subprocess.run(command + ['--select', 'tag:export', '--vars', json.dumps(variables),
                   '--target-path', str(ARTIFACTS / 'dbt/exports'),
                   '--log-path', str(ARTIFACTS / 'logs/exports')],
                   cwd=PROJECT, env=environment, check=True)
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
            relation = 'reporting.rpt_' + name
            columns = con.sql('describe ' + relation).fetchall()
            # JSON and CSV readers infer types; normalize to the exact reporting schema.
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
                escaped_path = path.as_posix().replace("'", "''")
                reader = f"read_{fmt}('{escaped_path}'" + (", header=true, all_varchar=true)" if fmt == 'csv' else ')')
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

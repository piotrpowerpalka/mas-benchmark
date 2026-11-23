#!/usr/bin/env python3
"""Aggregate MAS benchmark run directories and/or ZIP bundles by configuration.

Outputs one row per seed (runs.csv) and one row per seed-free configuration
(<configuration>.csv), plus all_configurations.csv.
Uses Python standard library only.
"""
import argparse
import csv
import io
import math
import re
import statistics as st
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SEED = re.compile(r'-seed[^/\\]+$')
LOG_RE = re.compile(r'^(?:.*?\|\s*)?(agent[^;\s]+);(agent[^;\s]+);([^;]+);([^;]+);([^;]+);([SR]);(\d{4}-\d\d-\d\dT[^;\s]+)\s*$')
NUMBER = re.compile(r'^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)')
CFG_RE = re.compile(r'^logs_(.+)-seed([^/\\]+)$')


def number(value):
    if value is None:
        return None
    m = NUMBER.match(str(value))
    return float(m.group(1)) if m else None


def avg(values):
    return st.mean(values) if values else None


def quantile(values, q):
    if not values:
        return None
    seq = sorted(values)
    pos = (len(seq)-1)*q
    lo, hi = math.floor(pos), math.ceil(pos)
    return seq[lo] + (seq[hi]-seq[lo])*(pos-lo)


def config_seed(folder):
    name = Path(folder).name
    m = CFG_RE.fullmatch(name)
    if m:
        return m.group(1), m.group(2)
    if '-seed' in name:
        lhs, seed = name.rsplit('-seed', 1)
        return lhs.removeprefix('logs_'), seed
    return name.removeprefix('logs_'), ''


def parse_stats(contents):
    out = {}
    section = None
    for line in contents.splitlines():
        line = line.strip()
        if line.startswith('Message latency ('):
            section = 'message'
        elif line.startswith('Conversation latency ('):
            section = 'conversation'
        elif line.startswith('Run-level metrics'):
            section = None
        if line.startswith('Messages sent:'):
            out['messages_sent'] = number(line.split(':', 1)[1])
        elif line.startswith('Messages successful:'):
            out['messages_successful'] = number(line.split(':', 1)[1])
        elif line.startswith('Messages lost:'):
            out['messages_lost'] = number(line.split(':', 1)[1])
        elif line.startswith('Conversations sent:'):
            out['conversations_sent'] = number(line.split(':', 1)[1])
        elif line.startswith('Conversations successful:'):
            out['conversations_successful'] = number(line.split(':', 1)[1])
        elif line.startswith('Conversations lost:'):
            out['conversations_lost'] = number(line.split(':', 1)[1])
        elif line.startswith('Git commit:'):
            out['git_commit'] = line.split(':', 1)[1].strip()
        elif line.startswith('Git worktree dirty:'):
            out['git_dirty'] = line.split(':', 1)[1].strip()
        elif section and ':' in line:
            key, value = line.split(':', 1)
            if key in ('p50', 'p90', 'p95', 'p99', 'mean', 'median', 'std', 'count'):
                out[f'{section}_{key}_ms' if key != 'count' else f'{section}_count'] = (
                    number(value)/1000 if key != 'count' and number(value) is not None else number(value)
                )
    return out


def parse_rtt(raw_log, workload):
    # RTT = time from sending the request to receiving its corresponding response
    # at the original sender. One RTT per (conversation, requester, responder).
    # Query: query(S) -> inform(R); CFP: cfp(S) -> propose/refuse(R).
    workload = (workload or '').lower()
    if workload not in ('query', 'cfp'):
        return {'rtt_supported': 0, 'rtt_count': 0}
    request = 'query' if workload == 'query' else 'cfp'
    answers = {'inform'} if workload == 'query' else {'propose', 'refuse'}
    # Index request by (conversation, original_sender, original_recipient)
    sent = {}
    responses = {}
    for line in raw_log.splitlines():
        m = LOG_RE.match(line)
        if not m:
            continue
        sender, recipient, performative, reply_with, cid, direction, ts = m.groups()
        if direction == 'S' and performative == request:
            key = (cid, sender, recipient)
            if key not in sent:
                sent[key] = datetime.fromisoformat(ts)
        elif direction == 'R' and performative in answers:
            # R log records the original source of the response (sender) and
            # its recipient (request initiator).
            key = (cid, recipient, sender)
            if key not in responses:
                responses[key] = datetime.fromisoformat(ts)
    rtts = [(recv - sent[key]).total_seconds()*1000
            for key, recv in responses.items()
            if key in sent and recv >= sent[key]]
    return {
        'rtt_supported': 1, 'rtt_count': len(rtts),
        'rtt_requests': len(sent),
        'rtt_response_rate_pct': len(rtts)/len(sent)*100 if sent else None,
        'rtt_mean_ms': avg(rtts),
        'rtt_median_ms': st.median(rtts) if rtts else None,
        'rtt_p95_ms': quantile(rtts, .95),
        'rtt_p99_ms': quantile(rtts, .99),
        'rtt_min_ms': min(rtts) if rtts else None,
        'rtt_max_ms': max(rtts) if rtts else None,
    }


def analyze_one(folder, csv_bytes, other_files, rtt_enabled):
    config, seed = config_seed(folder)
    rows = list(csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig', errors='replace'))))
    if not rows:
        raise ValueError('empty benchmark_results.csv')
    data = rows[0]
    workload = data.get('int protocol', '')
    record = dict(configuration=config, seed=seed or data.get('seed', ''), run=folder,
                  platform=data.get('platform', ''), workload=workload,
                  agents=number(data.get('agents')),
                  containers=number(data.get('containers')),
                  repetitions=number(data.get('repetitions')),
                  message_size_bytes=number(data.get('message size')))
    columns = {
        'Initialization time [s]': 'initialization_s',
        'Simulation time [s]': 'simulation_s',
        'latency [µs]': 'latency_mean_ms',
        'Median latency [µs]': 'latency_median_ms',
        'Stddev [µs]': 'latency_within_run_std_ms',
        'Max memory [MiB]': 'memory_max_mib',
        'Avg memory [MiB]': 'memory_avg_mib',
        'CPU in top 5% [threshold %]': 'cpu_top5_threshold_pct',
        'Messages lost': 'messages_lost',
        'Messages successful': 'messages_successful',
    }
    for source, target in columns.items():
        val = number(data.get(source))
        if val is not None and '[µs]' in source:
            val /= 1000
        record[target] = val
    for filename, content in other_files.items():
        if filename.startswith('stats_logs') and filename.endswith('.txt'):
            record.update(parse_stats(content.decode('utf-8', errors='replace')))
            break
    success = record.get('messages_successful')
    lost = record.get('messages_lost')
    sent = record.get('messages_sent')
    if sent is None and success is not None and lost is not None:
        sent = success + lost
        record['messages_sent'] = sent
    # Counted application-level delivery, NOT broker ACK / network packet delivery.
    record['delivery_reliability_pct'] = (100*success/sent) if sent and success is not None else None
    if (record.get('simulation_s') or 0) > 0 and success is not None:
        record['throughput_msg_s'] = success/record['simulation_s']
    cs = record.get('conversations_sent')
    cc = record.get('conversations_successful')
    record['conversation_reliability_pct'] = (100*cc/cs) if cs and cc is not None else None
    record['rtt_supported'] = int(workload.lower() in ('query', 'cfp'))
    if rtt_enabled:
        for filename, content in other_files.items():
            if filename.startswith('logs_docker-compose-') and filename.endswith('.log'):
                record.update(parse_rtt(content.decode('utf-8', errors='replace'), workload))
                break
    return record


def iter_runs(paths):
    seen = set()
    for root_path in paths:
        path = Path(root_path)
        if path.is_file() and path.suffix.lower() == '.zip':
            with zipfile.ZipFile(path) as z:
                groups = defaultdict(dict)
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    parts = Path(info.filename).parts
                    # Supports archives with or without an outer folder.
                    idx = next((i for i, part in enumerate(parts[:-1]) if part.startswith('logs_') and '-seed' in part), None)
                    if idx is None:
                        continue
                    folder = parts[idx]
                    groups[folder][parts[-1]] = info.filename
                for folder, files in sorted(groups.items()):
                    if 'benchmark_results.csv' not in files:
                        continue
                    if folder in seen:
                        print(f'WARNING: duplicate folder skipped: {folder}', file=sys.stderr)
                        continue
                    seen.add(folder)
                    yield folder, z.read(files['benchmark_results.csv']), {
                        n: z.read(p) for n, p in files.items()
                        if n.startswith('stats_logs') or n.startswith('logs_docker-compose-')
                    }
        elif path.is_dir():
            files = list(path.rglob('benchmark_results.csv'))
            for csv_path in sorted(files):
                folder = csv_path.parent.name
                if folder in seen:
                    print(f'WARNING: duplicate folder skipped: {folder}', file=sys.stderr)
                    continue
                seen.add(folder)
                base = csv_path.parent
                other = {}
                for glob_pattern in ('stats_logs*.txt', 'logs_docker-compose-*.log'):
                    for f in base.glob(glob_pattern):
                        other[f.name] = f.read_bytes()
                yield folder, csv_path.read_bytes(), other
        else:
            print(f'WARNING: unsupported or missing input: {path}', file=sys.stderr)


def write_csv(path, records):
    if not records:
        return
    fields = list(dict.fromkeys(k for r in records for k in r))
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(records)


def aggregate(group, config):
    output = {'configuration': config, 'n_runs': len(group),
              'seeds': '|'.join(str(r['seed']) for r in group),
              'platform': group[0]['platform'], 'workload': group[0]['workload'],
              'agents': group[0]['agents'], 'containers': group[0]['containers'],
              'repetitions': group[0]['repetitions'], 'message_size_bytes': group[0]['message_size_bytes']}
    measurements = [
        'initialization_s','simulation_s', 'latency_mean_ms', 'latency_median_ms',
        'message_p90_ms','message_p95_ms','message_p99_ms',
        'conversation_mean_ms','conversation_p95_ms','conversation_p99_ms',
        'throughput_msg_s','memory_avg_mib','memory_max_mib','cpu_top5_threshold_pct',
        'delivery_reliability_pct','conversation_reliability_pct',
        'rtt_mean_ms','rtt_median_ms','rtt_p95_ms','rtt_p99_ms','rtt_response_rate_pct',
    ]
    for metric in measurements:
        values = [r[metric] for r in group if r.get(metric) is not None and math.isfinite(r[metric])]
        output[f'{metric}_n'] = len(values)
        output[f'{metric}_mean'] = avg(values)
        output[f'{metric}_sd'] = st.stdev(values) if len(values) > 1 else None
        output[f'{metric}_median'] = st.median(values) if values else None
        output[f'{metric}_min'] = min(values) if values else None
        output[f'{metric}_max'] = max(values) if values else None
    for col in ('messages_sent','messages_successful','messages_lost',
                'conversations_sent','conversations_successful','conversations_lost',
                'rtt_requests','rtt_count'):
        numbers = [r[col] for r in group if r.get(col) is not None]
        output[f'{col}_sum'] = sum(numbers) if numbers else None
    if output.get('messages_sent_sum'):
        output['delivery_reliability_pooled_pct'] = 100*output['messages_successful_sum']/output['messages_sent_sum']
    if output.get('conversations_sent_sum') and output.get('conversations_successful_sum') is not None:
        output['conversation_reliability_pooled_pct'] = 100*output['conversations_successful_sum']/output['conversations_sent_sum']
    if output.get('rtt_requests_sum') and output.get('rtt_count_sum') is not None:
        output['rtt_response_rate_pooled_pct'] = 100*output['rtt_count_sum']/output['rtt_requests_sum']
    output['rtt_supported'] = int(any(r.get('rtt_supported') for r in group))
    output['git_commits'] = '|'.join(sorted(set(str(r['git_commit']) for r in group if r.get('git_commit'))))
    output['git_dirty_any'] = int(any(r.get('git_dirty', '').lower() == 'yes' for r in group))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', help='Input roots and/or ZIP archives')
    parser.add_argument('-o','--output', default='mas-aggregated', help='Output directory')
    parser.add_argument('--skip-rtt', action='store_true', help='Skip parsing raw log for RTT')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    runs = []
    for folder, csv_bytes, files in iter_runs(args.inputs):
        try:
            record = analyze_one(folder, csv_bytes, files, not args.skip_rtt)
            runs.append(record)
            print(f"OK: {folder}, RTT count={record.get('rtt_count', 'n/a')}")
        except (ValueError, OSError, UnicodeError) as exc:
            print(f'ERROR {folder}: {exc}', file=sys.stderr)
    if not runs:
        sys.exit('No valid runs found')
    write_csv(out/'runs.csv', runs)
    grouped = defaultdict(list)
    for r in runs:
        grouped[r['configuration']].append(r)
    summary = []
    for config, group in sorted(grouped.items()):
        result = aggregate(group, config)
        summary.append(result)
        write_csv(out/(config+'.csv'), [result])
    write_csv(out/'all_configurations.csv', summary)
    print(f'Processed {len(runs)} runs across {len(summary)} configurations. Output: {out}')


if __name__ == '__main__':
    main()

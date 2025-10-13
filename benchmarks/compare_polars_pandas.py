"""
Performance Benchmark: Polars vs Pandas

This script compares the performance of Polars and Pandas when processing
the same security log analytics pipeline on 50,000 records.

Run with: python benchmarks/compare_polars_pandas.py
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️  Pandas not installed. Skipping Pandas benchmark.")

import polars as pl


def benchmark_pandas(csv_file: str) -> dict:
    """Benchmark Pandas pipeline."""
    if not PANDAS_AVAILABLE:
        return {}

    print("\n🐼 Benchmarking Pandas...")

    # Read CSV
    start = time.perf_counter()
    df = pd.read_csv(csv_file)
    read_time = (time.perf_counter() - start) * 1000

    # Type conversion
    start = time.perf_counter()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    convert_time = (time.perf_counter() - start) * 1000

    # Filtering & Aggregation
    start = time.perf_counter()
    attacks_df = df[df['action'].isin(['geo_blocked', 'path_blocked', 'bot_blocked'])]
    legitimate_df = df[df['action'] == 'legitimate']
    top_countries = attacks_df['country'].value_counts().head(5).to_dict()
    suspicious_ips = attacks_df['ip'].value_counts()
    suspicious_ips = suspicious_ips[suspicious_ips > 5].head(8).to_dict()
    avg_latency = df['response_time_ms'].mean()
    agg_time = (time.perf_counter() - start) * 1000

    total_time = read_time + convert_time + agg_time

    return {
        'read': read_time,
        'convert': convert_time,
        'aggregate': agg_time,
        'total': total_time
    }


def benchmark_polars(csv_file: str) -> dict:
    """Benchmark Polars pipeline."""
    print("⚡ Benchmarking Polars...")

    # Read CSV
    start = time.perf_counter()
    df = pl.read_csv(csv_file)
    read_time = (time.perf_counter() - start) * 1000

    # Type conversion
    start = time.perf_counter()
    df = df.with_columns(pl.col('timestamp').str.strptime(pl.Datetime))
    convert_time = (time.perf_counter() - start) * 1000

    # Filtering & Aggregation
    start = time.perf_counter()
    attacks_df = df.filter(pl.col('action').is_in(['geo_blocked', 'path_blocked', 'bot_blocked']))
    legitimate_df = df.filter(pl.col('action') == 'legitimate')
    top_countries = attacks_df.group_by('country').len().sort('len', descending=True).head(5)
    suspicious_ips = attacks_df.group_by('ip').len().filter(pl.col('len') > 5).sort('len', descending=True).head(8)
    avg_latency = df.select(pl.col('response_time_ms').mean()).item()
    agg_time = (time.perf_counter() - start) * 1000

    total_time = read_time + convert_time + agg_time

    return {
        'read': read_time,
        'convert': convert_time,
        'aggregate': agg_time,
        'total': total_time
    }


def print_results(pandas_times: dict, polars_times: dict):
    """Print formatted benchmark results."""
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS: Polars vs Pandas (50,000 log records)")
    print("=" * 70)

    if not pandas_times:
        print("\n⚠️  Pandas benchmark skipped (not installed)")
        print("\nPolars Results:")
        print(f"  Read CSV:              {polars_times['read']:>8.2f}ms")
        print(f"  Type Conversion:       {polars_times['convert']:>8.2f}ms")
        print(f"  Filtering & Agg:       {polars_times['aggregate']:>8.2f}ms")
        print(f"  Total:                 {polars_times['total']:>8.2f}ms")
        return

    print(f"\n{'Metric':<25} {'Pandas':>12} {'Polars':>12} {'Speedup':>12}")
    print("-" * 70)

    for metric in ['read', 'convert', 'aggregate', 'total']:
        pandas_val = pandas_times[metric]
        polars_val = polars_times[metric]
        speedup = pandas_val / polars_val if polars_val > 0 else 0

        metric_name = {
            'read': 'Read CSV',
            'convert': 'Type Conversion',
            'aggregate': 'Filtering & Agg',
            'total': 'TOTAL'
        }[metric]

        marker = "🚀 " if metric == 'total' else "  "
        print(f"{marker}{metric_name:<22} {pandas_val:>11.2f}ms {polars_val:>11.2f}ms {speedup:>11.1f}x")

    print("=" * 70)


def main():
    csv_file = Path(__file__).parent.parent / "data" / "mock_logs.csv"

    if not csv_file.exists():
        print(f"❌ Error: Mock data file not found at {csv_file}")
        print("   Run: python src/main.py --use-mock-data (to generate mock data)")
        sys.exit(1)

    print(f"📊 Processing: {csv_file} ({csv_file.stat().st_size / (1024*1024):.1f}MB)")

    pandas_times = benchmark_pandas(str(csv_file))
    polars_times = benchmark_polars(str(csv_file))

    print_results(pandas_times, polars_times)


if __name__ == "__main__":
    main()

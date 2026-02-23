"""
Script to format raw CSV files into standardized benchmarking format.
Creates formatted CSV files matching Rails application format for comparison.
"""
import csv
import os
import glob
import argparse
from pathlib import Path


def format_response_time_metrics(stats_file, output_file):
    """Create response_time_metrics.csv from locust stats."""
    metrics = []
    
    with open(stats_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract all response time metrics
            if row['Name'] and row['Name'] != 'Aggregated':
                endpoint = row['Name']
                
                # Add each metric type
                if row.get('Median Response Time'):
                    metrics.append({
                        'Metric': f'Median Response Time - {endpoint}',
                        'Value (ms)': float(row['Median Response Time'])
                    })
                
                if row.get('Average Response Time'):
                    metrics.append({
                        'Metric': f'Average Response Time - {endpoint}',
                        'Value (ms)': float(row['Average Response Time'])
                    })
                
                if row.get('95%'):
                    metrics.append({
                        'Metric': f'95th Percentile - {endpoint}',
                        'Value (ms)': float(row['95%'])
                    })
                
                if row.get('99%'):
                    metrics.append({
                        'Metric': f'99th Percentile - {endpoint}',
                        'Value (ms)': float(row['99%'])
                    })
    
    # Write formatted CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Metric', 'Value (ms)'])
        writer.writeheader()
        writer.writerows(metrics)
    
    print(f"✓ Created {output_file} with {len(metrics)} metrics")


def format_scalability_metrics(raw_file, output_file):
    """Create scalability_metrics.csv from raw metrics."""
    rows = []
    
    with open(raw_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                'timestamp': row.get('timestamp', ''),
                'elapsed_seconds': row.get('elapsed_seconds', ''),
                'active_users': row.get('active_users', '0'),
                'requests_per_second': row.get('requests_per_second', '0'),
                'total_requests': row.get('total_requests', '0')
            })
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'elapsed_seconds', 'active_users', 
            'requests_per_second', 'total_requests'
        ])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Created {output_file} with {len(rows)} rows")


def format_memory_usage_metrics(raw_file, output_file):
    """Create memory_usage_metrics.csv from raw metrics."""
    rows = []
    
    with open(raw_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                'timestamp': row.get('timestamp', ''),
                'elapsed_seconds': row.get('elapsed_seconds', ''),
                'memory_usage_mb': row.get('memory_usage_mb', '0'),
                'memory_percent': row.get('memory_percent', '0'),
                'cpu_percent': row.get('cpu_percent', '0')
            })
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'elapsed_seconds', 'memory_usage_mb',
            'memory_percent', 'cpu_percent'
        ])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Created {output_file} with {len(rows)} rows")


def fix_exceptions_csv(exceptions_file):
    """Fix exceptions CSV to use 'Message' instead of 'Msg'."""
    if not os.path.exists(exceptions_file):
        return
    
    rows = []
    with open(exceptions_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                'Count': row.get('Count', '0'),
                'Message': row.get('Msg', row.get('Message', '')),
                'Traceback': row.get('Traceback', '')
            })
    
    with open(exceptions_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Count', 'Message', 'Traceback'])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Fixed {exceptions_file}")


def process_single_directory(results_dir):
    """Format CSV files in a single directory."""
    results_dir = Path(results_dir)
    
    # Find stats and metrics files
    stats_files = sorted(glob.glob(str(results_dir / 'locust_*_stats.csv')), reverse=True)
    if not stats_files:
        stats_files = sorted(glob.glob(str(results_dir / 'locust_stats.csv')), reverse=True)
    
    metrics_files = sorted(glob.glob(str(results_dir / 'metrics_memory_scalability_*.csv')), reverse=True)
    exceptions_files = glob.glob(str(results_dir / 'locust_*_exceptions.csv'))
    if not exceptions_files:
        exceptions_files = glob.glob(str(results_dir / 'locust_exceptions.csv'))
    
    if stats_files:
        latest_stats = stats_files[0]
        format_response_time_metrics(
            latest_stats,
            results_dir / 'response_time_metrics.csv'
        )
    
    if metrics_files:
        latest_metrics = metrics_files[0]
        format_scalability_metrics(
            latest_metrics,
            results_dir / 'scalability_metrics.csv'
        )
        format_memory_usage_metrics(
            latest_metrics,
            results_dir / 'memory_usage_metrics.csv'
        )
    
    if exceptions_files:
        fix_exceptions_csv(exceptions_files[0])


def create_combined_summary(test_run_dir):
    """Create a combined summary CSV with all test results."""
    test_run_dir = Path(test_run_dir)
    combined_rows = []
    
    # Find all test subdirectories
    for subdir in sorted(test_run_dir.iterdir()):
        if not subdir.is_dir():
            continue
        
        test_id = subdir.name
        
        # Read stats file
        stats_file = subdir / 'locust_stats.csv'
        if not stats_file.exists():
            continue
        
        # Read test info
        test_info = {}
        info_file = subdir / 'test_info.json'
        if info_file.exists():
            import json
            with open(info_file) as f:
                test_info = json.load(f)
        
        # Parse stats
        with open(stats_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Type') == 'Aggregated' or row.get('Name') == 'Aggregated':
                    combined_rows.append({
                        'test_id': test_id,
                        'users': test_info.get('users', ''),
                        'duration': test_info.get('duration', ''),
                        'total_requests': row.get('Request Count', row.get('# Requests', '')),
                        'failures': row.get('Failure Count', row.get('# Failures', '')),
                        'avg_response_time_ms': row.get('Average Response Time', ''),
                        'median_response_time_ms': row.get('Median Response Time', ''),
                        'p95_response_time_ms': row.get('95%', ''),
                        'p99_response_time_ms': row.get('99%', ''),
                        'max_response_time_ms': row.get('Max Response Time', ''),
                        'requests_per_sec': row.get('Requests/s', '')
                    })
                    break
    
    if combined_rows:
        output_file = test_run_dir / 'combined_results.csv'
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'test_id', 'users', 'duration', 'total_requests', 'failures',
                'avg_response_time_ms', 'median_response_time_ms',
                'p95_response_time_ms', 'p99_response_time_ms',
                'max_response_time_ms', 'requests_per_sec'
            ])
            writer.writeheader()
            writer.writerows(combined_rows)
        print(f"✓ Created {output_file} with {len(combined_rows)} test results")


def main():
    """Format all CSV files in results directory."""
    parser = argparse.ArgumentParser(description='Format CSV files for benchmarking')
    parser.add_argument('--input-dir', '-i', type=str, default='results',
                        help='Input directory containing test results')
    args = parser.parse_args()
    
    results_dir = Path(args.input_dir)
    
    if not results_dir.exists():
        print(f"Results directory not found: {results_dir}")
        return
    
    # Check if this is a test run directory (contains subdirectories with test results)
    subdirs = [d for d in results_dir.iterdir() if d.is_dir() and 'users_' in d.name]
    
    if subdirs:
        # Process each test subdirectory
        print(f"Processing test run directory: {results_dir}")
        print(f"Found {len(subdirs)} test directories")
        print()
        
        for subdir in sorted(subdirs):
            print(f"Processing: {subdir.name}")
            process_single_directory(subdir)
        
        # Create combined summary
        print()
        create_combined_summary(results_dir)
    else:
        # Process as single directory (legacy behavior)
        print(f"Processing single directory: {results_dir}")
        
        stats_files = sorted(glob.glob(str(results_dir / 'locust_*_stats.csv')), reverse=True)
        metrics_files = sorted(glob.glob(str(results_dir / 'metrics_memory_scalability_*.csv')), reverse=True)
        
        if not stats_files:
            print("No locust stats files found!")
            return
        
        if not metrics_files:
            print("No metrics files found!")
            return
        
        latest_stats = stats_files[0]
        latest_metrics = metrics_files[0]
        
        print(f"Processing files:")
        print(f"  Stats: {latest_stats}")
        print(f"  Metrics: {latest_metrics}")
        print()
        
        process_single_directory(results_dir)
    
    print()
    print("✓ All formatted CSV files created:")
    print("  - response_time_metrics.csv (per test)")
    print("  - scalability_metrics.csv (per test)")
    print("  - memory_usage_metrics.csv (per test)")
    if subdirs:
        print("  - combined_results.csv (summary of all tests)")


if __name__ == '__main__':
    main()


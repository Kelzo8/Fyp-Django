"""
Custom metrics collector for Locust that tracks memory usage and scalability metrics.
This module collects additional metrics beyond Locust's default response time metrics.
"""
import csv
import time
import psutil
import os
from datetime import datetime
from locust import events
import threading


class MetricsCollector:
    """Collects memory usage and scalability metrics during load tests."""
    
    def __init__(self, django_pid=None, output_dir="results", environment=None):
        self.django_pid = django_pid or self._find_django_process()
        self.output_dir = output_dir
        self.environment = environment
        self.metrics_file = None
        self.csv_writer = None
        self.start_time = None
        self.running = False
        self.metrics_lock = threading.Lock()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Register Locust event handlers
        events.test_start.add_listener(self.on_test_start)
        events.test_stop.add_listener(self.on_test_stop)
    
    def _find_django_process(self):
        """Find the Django process PID by looking for manage.py runserver."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'manage.py' in ' '.join(cmdline) and 'runserver' in ' '.join(cmdline):
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return None
    
    def on_test_start(self, environment, **kwargs):
        """Called when the test starts."""
        self.start_time = time.time()
        self.running = True
        
        # Open CSV file for writing
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_path = os.path.join(self.output_dir, f"metrics_memory_scalability_{timestamp}.csv")
        self.metrics_file = open(metrics_path, 'w', newline='')
        self.csv_writer = csv.writer(self.metrics_file)
        
        # Write header
        self.csv_writer.writerow([
            'Timestamp',
            'Elapsed_Time_Seconds',
            'Active_Users',
            'Total_Requests',
            'Requests_Per_Second',
            'Memory_Usage_MB',
            'Memory_Percent',
            'CPU_Percent',
            'Total_Posts_In_DB'
        ])
        
        # Start background thread to collect metrics
        self.collector_thread = threading.Thread(target=self._collect_metrics_loop, daemon=True)
        self.collector_thread.start()
        
        print(f"Metrics collector started. Django PID: {self.django_pid}")
        print(f"Metrics will be saved to: {metrics_path}")
    
    def on_test_stop(self, environment, **kwargs):
        """Called when the test stops."""
        self.running = False
        if self.metrics_file:
            self.metrics_file.close()
        print("Metrics collection stopped.")
    
    def _collect_metrics_loop(self):
        """Background thread that collects metrics every second."""
        while self.running:
            try:
                self._collect_metrics()
                time.sleep(1)  # Collect every second
            except Exception as e:
                print(f"Error collecting metrics: {e}")
                time.sleep(1)
    
    def _collect_metrics(self):
        """Collect current metrics and write to CSV."""
        if not self.csv_writer:
            return
        
        timestamp = datetime.now()
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        # Get Locust stats
        stats = self._get_locust_stats()
        active_users = stats.get('active_users', 0)
        total_requests = stats.get('total_requests', 0)
        rps = stats.get('rps', 0)
        
        # Get memory and CPU usage
        memory_mb = 0
        memory_percent = 0
        cpu_percent = 0
        
        if self.django_pid:
            try:
                process = psutil.Process(self.django_pid)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
                memory_percent = process.memory_percent()
                cpu_percent = process.cpu_percent(interval=0.1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Get total posts in database (scalability metric)
        total_posts = self._get_total_posts()
        
        # Write to CSV
        with self.metrics_lock:
            self.csv_writer.writerow([
                timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                f"{elapsed_time:.2f}",
                active_users,
                total_requests,
                f"{rps:.2f}",
                f"{memory_mb:.2f}",
                f"{memory_percent:.2f}",
                f"{cpu_percent:.2f}",
                total_posts
            ])
            self.metrics_file.flush()
    
    def _get_locust_stats(self):
        """Get current Locust statistics."""
        try:
            if self.environment and hasattr(self.environment, 'stats'):
                stats = self.environment.stats
                active_users = 0
                if hasattr(self.environment, 'runner') and self.environment.runner:
                    if hasattr(self.environment.runner, 'user_count'):
                        active_users = self.environment.runner.user_count
                
                return {
                    'active_users': active_users,
                    'total_requests': stats.total.num_requests,
                    'rps': stats.total.current_rps
                }
        except Exception as e:
            pass
        return {'active_users': 0, 'total_requests': 0, 'rps': 0}
    
    def _get_total_posts(self):
        """Get total number of posts in the database."""
        try:
            # Try to query the database directly
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM books_post")
                count = cursor.fetchone()[0]
                conn.close()
                return count
        except Exception:
            pass
        return 0


# Global instance
_metrics_collector = None

def init_metrics_collector(django_pid=None, output_dir="results", environment=None):
    """Initialize the metrics collector."""
    global _metrics_collector
    _metrics_collector = MetricsCollector(django_pid=django_pid, output_dir=output_dir, environment=environment)
    return _metrics_collector


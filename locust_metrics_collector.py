"""
Locust metrics collector: memory and scalability (Django process + system).
"""
import csv
import time
import os
from datetime import datetime
from locust import events
import threading

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available. Memory metrics will be limited.")


class MetricsCollector:
    def __init__(self, django_pid=None, output_dir="results", environment=None):
        self.output_dir = output_dir
        self.environment = environment
        self.metrics_file = None
        self.csv_writer = None
        self.start_time = None
        self.running = False
        self.metrics_lock = threading.Lock()
        self.psutil_working = PSUTIL_AVAILABLE
        self.django_pid = django_pid
        if not self.django_pid and self.psutil_working:
            self.django_pid = self._find_django_process()
        os.makedirs(output_dir, exist_ok=True)
        events.test_start.add_listener(self.on_test_start)
        events.test_stop.add_listener(self.on_test_stop)
    
    def _find_django_process(self):
        if not self.psutil_working:
            return None
        try:
            best_pid = None
            best_rss = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if not cmdline:
                        continue
                    cmdline_str = ' '.join(str(c) for c in cmdline)
                    if 'manage.py' not in cmdline_str or 'runserver' not in cmdline_str:
                        continue
                    pid = proc.info['pid']
                    p = psutil.Process(pid)
                    rss = p.memory_info().rss
                    if rss > best_rss:
                        best_rss = rss
                        best_pid = pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return best_pid
        except (PermissionError, OSError) as e:
            print(f"Warning: Cannot enumerate processes: {e}")
            print("Django process memory metrics will not be available.")
            self.psutil_working = False
        except Exception as e:
            print(f"Warning: Error finding Django process: {e}")
            self.psutil_working = False
        return None
    
    def on_test_start(self, environment, **kwargs):
        self.start_time = time.time()
        self.running = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_path = os.path.join(self.output_dir, f"metrics_memory_scalability_{timestamp}.csv")
        self.metrics_file = open(metrics_path, 'w', newline='')
        self.csv_writer = csv.writer(self.metrics_file)
        self.csv_writer.writerow([
            'timestamp', 'elapsed_seconds', 'active_users', 'total_requests',
            'requests_per_second', 'memory_usage_mb', 'memory_percent', 'cpu_percent',
            'system_memory_mb', 'system_memory_percent', 'system_cpu_percent'
        ])
        self.collector_thread = threading.Thread(target=self._collect_metrics_loop, daemon=True)
        self.collector_thread.start()
        
        print(f"Metrics collector started (Django PID: {self.django_pid})")
    
    def on_test_stop(self, environment, **kwargs):
        self.running = False
        if self.metrics_file:
            self.metrics_file.close()
        print("Metrics collector stopped.")
    
    def _collect_metrics_loop(self):
        while self.running:
            try:
                self._collect_metrics()
                time.sleep(1)
            except Exception as e:
                print(f"Error collecting metrics: {e}")
                time.sleep(1)
    
    def _collect_metrics(self):
        if not self.csv_writer:
            return
        timestamp = datetime.now()
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        stats = self._get_locust_stats()
        active_users = stats.get('active_users', 0)
        total_requests = stats.get('total_requests', 0)
        rps = stats.get('rps', 0)
        memory_mb = 0
        memory_percent = 0
        cpu_percent = 0
        if self.django_pid and self.psutil_working:
            try:
                process = psutil.Process(self.django_pid)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                memory_percent = process.memory_percent()
                cpu_percent = process.cpu_percent(interval=0.1)
            except (PermissionError, OSError):
                self.psutil_working = False
            except Exception:
                pass
        system_memory_mb = 0
        system_memory_percent = 0
        system_cpu_percent = 0
        if self.psutil_working:
            try:
                system_memory = psutil.virtual_memory()
                system_memory_mb = system_memory.used / (1024 * 1024)
                system_memory_percent = system_memory.percent
                system_cpu_percent = psutil.cpu_percent(interval=0.1)
            except (PermissionError, OSError):
                self.psutil_working = False
            except Exception:
                pass
        with self.metrics_lock:
            self.csv_writer.writerow([
                timestamp.isoformat(),
                f"{elapsed_time:.2f}",
                active_users,
                total_requests,
                f"{rps:.2f}",
                f"{memory_mb:.2f}",
                f"{memory_percent:.2f}",
                f"{cpu_percent:.2f}",
                f"{system_memory_mb:.2f}",
                f"{system_memory_percent:.2f}",
                f"{system_cpu_percent:.2f}"
            ])
            self.metrics_file.flush()
    
    def _get_locust_stats(self):
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
        try:
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


_metrics_collector = None

def init_metrics_collector(django_pid=None, output_dir="results", environment=None):
    global _metrics_collector
    _metrics_collector = MetricsCollector(django_pid=django_pid, output_dir=output_dir, environment=environment)
    return _metrics_collector


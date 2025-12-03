# Quick Testing Guide

## Step-by-Step Load Testing

### Step 1: Start Django Server

Open **Terminal 1** and run:
```bash
cd /Users/jameskelly/Fyp-Django2
python3 manage.py runserver
```

Keep this terminal open. You should see:
```
Starting development server at http://127.0.0.1:8000/
```

### Step 2: Run Load Test

Open **Terminal 2** (new terminal window) and run:

#### Option A: Quick Test (30 seconds, 5 users)
```bash
cd /Users/jameskelly/Fyp-Django2
locust --headless \
    --host=http://127.0.0.1:8000 \
    --users=5 \
    --spawn-rate=1 \
    --run-time=30s \
    --csv=results/locust_test
```

#### Option B: Full Test (5 minutes, 20 users)
```bash
cd /Users/jameskelly/Fyp-Django2
locust --headless \
    --host=http://127.0.0.1:8000 \
    --users=20 \
    --spawn-rate=2 \
    --run-time=5m \
    --csv=results/locust_test
```

#### Option C: Use the Script
```bash
cd /Users/jameskelly/Fyp-Django2
./run_load_test.sh
```

### Step 3: Check Results

After the test completes, check the `results/` directory in your project:

```bash
cd /Users/jameskelly/Fyp-Django2
ls -lh results/
```

You should see:
- `locust_test_stats.csv` - Response times and throughput
- `locust_test_failures.csv` - Any failures
- `locust_test_exceptions.csv` - Exceptions
- `metrics_memory_scalability_TIMESTAMP.csv` - Memory and scalability metrics

**All CSV files will be saved in:** `/Users/jameskelly/Fyp-Django2/results/`

### Step 4: View the Data

Open the CSV files in Excel, Google Sheets, or Python:

```bash
# View first few lines
head -20 results/locust_test_stats.csv
head -20 results/metrics_memory_scalability_*.csv
```

## What to Expect

✅ **If everything works:**
- You'll see "✓ Memory and scalability metrics collector initialized" message
- Test will run for the specified duration
- CSV files will be created in `results/` directory
- No errors in the output

❌ **If there are issues:**
- Make sure Django is running first
- Check that port 8000 is not in use
- Ensure you have some posts in the database (create a few manually first)

## Quick Verification Test

Run this 10-second test to verify everything works:

```bash
locust --headless \
    --host=http://127.0.0.1:8000 \
    --users=2 \
    --spawn-rate=1 \
    --run-time=10s \
    --csv=results/quick_test
```

Then check:
```bash
ls results/quick_test*
```

You should see CSV files with your metrics!


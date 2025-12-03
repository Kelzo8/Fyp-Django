#!/bin/bash
# Script to run Locust load tests and export metrics to CSV

# Default values
HOST="http://127.0.0.1:8000"
USERS=10
SPAWN_RATE=2
DURATION="5m"
OUTPUT_DIR="results"

# Create output directory if it doesn't exist
mkdir -p $OUTPUT_DIR

# Generate timestamp for unique filenames
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "Starting Locust load test..."
echo "Host: $HOST"
echo "Users: $USERS"
echo "Spawn Rate: $SPAWN_RATE users/second"
echo "Duration: $DURATION"
echo "Results will be saved to: $OUTPUT_DIR/"
echo ""

# Run Locust in headless mode with CSV export (with timestamp to avoid overwriting)
locust \
    --headless \
    --host=$HOST \
    --users=$USERS \
    --spawn-rate=$SPAWN_RATE \
    --run-time=$DURATION \
    --csv=$OUTPUT_DIR/locust_$TIMESTAMP \
    --html=$OUTPUT_DIR/locust_report_$TIMESTAMP.html

echo ""
echo "Load test completed!"
echo "CSV files saved in $OUTPUT_DIR/:"
echo "  - locust_${TIMESTAMP}_stats.csv (request statistics)"
echo "  - locust_${TIMESTAMP}_failures.csv (failure details)"
echo "  - locust_${TIMESTAMP}_exceptions.csv (exceptions)"
echo "  - locust_report_${TIMESTAMP}.html (HTML report)"


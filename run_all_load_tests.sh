#!/bin/bash
# Comprehensive load test script for Django CRUD application
# Runs tests for multiple user counts and durations

# Configuration
HOST="http://127.0.0.1:8000"
SPAWN_RATE=10  # Users spawned per second
OUTPUT_DIR="results"

# Test parameters
USER_COUNTS=(5 50 100 500 1000)
DURATIONS=("30s" "1m" "5m" "10m" "20m")
DURATION_LABELS=("30sec" "1min" "5min" "10min" "20min")

# Create output directory structure
mkdir -p $OUTPUT_DIR

# Generate master timestamp for this test run
MASTER_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_RUN_DIR="${OUTPUT_DIR}/test_run_${MASTER_TIMESTAMP}"
mkdir -p "$TEST_RUN_DIR"

# Log file for the entire test run
LOG_FILE="${TEST_RUN_DIR}/test_run.log"

# Function to log messages
log_message() {
    echo "$1" | tee -a "$LOG_FILE"
}

# Function to calculate human readable duration
get_duration_seconds() {
    local duration=$1
    case $duration in
        "30s") echo 30 ;;
        "1m")  echo 60 ;;
        "5m")  echo 300 ;;
        "10m") echo 600 ;;
        "20m") echo 1200 ;;
        *)     echo 60 ;;
    esac
}

# Print test plan
log_message "========================================"
log_message "Django CRUD Load Test Suite"
log_message "========================================"
log_message "Started at: $(date)"
log_message "Host: $HOST"
log_message "Test Run ID: $MASTER_TIMESTAMP"
log_message ""
log_message "Test Matrix:"
log_message "  User Counts: ${USER_COUNTS[*]}"
log_message "  Durations: ${DURATIONS[*]}"
log_message "  Total Tests: $((${#USER_COUNTS[@]} * ${#DURATIONS[@]}))"
log_message ""
log_message "Results will be saved to: $TEST_RUN_DIR"
log_message "========================================"
log_message ""

# Check if Django server is running
if ! curl -s "$HOST" > /dev/null 2>&1; then
    log_message "ERROR: Django server is not running at $HOST"
    log_message "Please start the server with: python manage.py runserver"
    exit 1
fi

log_message "✓ Django server is running at $HOST"
log_message ""

# Counter for test progress
TEST_NUM=0
TOTAL_TESTS=$((${#USER_COUNTS[@]} * ${#DURATIONS[@]}))

# Run tests for each combination
for users in "${USER_COUNTS[@]}"; do
    for i in "${!DURATIONS[@]}"; do
        duration="${DURATIONS[$i]}"
        duration_label="${DURATION_LABELS[$i]}"
        
        TEST_NUM=$((TEST_NUM + 1))
        
        # Create unique identifier for this test
        TEST_ID="${users}users_${duration_label}"
        TEST_SUBDIR="${TEST_RUN_DIR}/${TEST_ID}"
        mkdir -p "$TEST_SUBDIR"
        
        log_message "========================================"
        log_message "Test $TEST_NUM of $TOTAL_TESTS"
        log_message "Users: $users | Duration: $duration"
        log_message "Test ID: $TEST_ID"
        log_message "Started at: $(date)"
        log_message "========================================"
        
        # Set environment variable for metrics output directory
        export LOCUST_METRICS_DIR="$TEST_SUBDIR"
        
        # Adjust spawn rate based on user count (don't spawn faster than user count)
        if [ $users -lt $SPAWN_RATE ]; then
            effective_spawn_rate=$users
        else
            effective_spawn_rate=$SPAWN_RATE
        fi
        
        # Run Locust test
        locust \
            --headless \
            --host=$HOST \
            --users=$users \
            --spawn-rate=$effective_spawn_rate \
            --run-time=$duration \
            --csv="${TEST_SUBDIR}/locust" \
            --html="${TEST_SUBDIR}/report.html" \
            2>&1 | tee -a "$LOG_FILE"
        
        # Check if test completed successfully
        if [ $? -eq 0 ]; then
            log_message "✓ Test $TEST_ID completed successfully"
        else
            log_message "✗ Test $TEST_ID failed"
        fi
        
        # Save test metadata
        cat > "${TEST_SUBDIR}/test_info.json" << EOF
{
    "test_id": "$TEST_ID",
    "users": $users,
    "duration": "$duration",
    "duration_seconds": $(get_duration_seconds $duration),
    "spawn_rate": $effective_spawn_rate,
    "host": "$HOST",
    "timestamp": "$(date -Iseconds)",
    "test_number": $TEST_NUM,
    "total_tests": $TOTAL_TESTS
}
EOF
        
        log_message "Results saved to: $TEST_SUBDIR"
        log_message ""
        
        # Brief pause between tests to let system stabilize
        if [ $TEST_NUM -lt $TOTAL_TESTS ]; then
            log_message "Pausing 5 seconds before next test..."
            sleep 5
        fi
    done
done

log_message "========================================"
log_message "All tests completed!"
log_message "Finished at: $(date)"
log_message "========================================"
log_message ""

# Generate summary report
log_message "Generating summary report..."

SUMMARY_FILE="${TEST_RUN_DIR}/summary.csv"
echo "test_id,users,duration,total_requests,failures,avg_response_time_ms,median_response_time_ms,p95_response_time_ms,p99_response_time_ms,max_response_time_ms,requests_per_sec" > "$SUMMARY_FILE"

for users in "${USER_COUNTS[@]}"; do
    for i in "${!DURATIONS[@]}"; do
        duration="${DURATIONS[$i]}"
        duration_label="${DURATION_LABELS[$i]}"
        TEST_ID="${users}users_${duration_label}"
        STATS_FILE="${TEST_RUN_DIR}/${TEST_ID}/locust_stats.csv"
        
        if [ -f "$STATS_FILE" ]; then
            # Extract aggregated stats (last row with "Aggregated" type)
            AGGREGATED=$(grep "Aggregated" "$STATS_FILE" | tail -1)
            if [ -n "$AGGREGATED" ]; then
                # Parse CSV fields (this is a simplified extraction)
                echo "${TEST_ID},${users},${duration_label},${AGGREGATED}" | \
                    awk -F',' '{print $1","$2","$3","$5","$6","$8","$10","$14","$15","$17","$18}' >> "$SUMMARY_FILE"
            fi
        fi
    done
done

log_message "Summary saved to: $SUMMARY_FILE"
log_message ""

# Format CSV files for benchmarking analysis
log_message "Formatting CSV files for benchmarking analysis..."
python3 format_csv_files.py --input-dir "$TEST_RUN_DIR"

log_message ""
log_message "========================================"
log_message "TEST RUN COMPLETE"
log_message "========================================"
log_message "All results are in: $TEST_RUN_DIR"
log_message ""
log_message "Files generated per test:"
log_message "  - locust_stats.csv         (Request statistics)"
log_message "  - locust_stats_history.csv (Time-series stats)"
log_message "  - locust_failures.csv      (Failure details)"
log_message "  - metrics_memory_*.csv     (Memory & scalability)"
log_message "  - report.html              (Visual HTML report)"
log_message "  - test_info.json           (Test configuration)"
log_message ""
log_message "Summary files:"
log_message "  - summary.csv              (All tests summary)"
log_message "  - test_run.log             (Complete log)"
log_message "========================================"

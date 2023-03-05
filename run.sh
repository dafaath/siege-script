#!/bin/bash

HOST=10.104.0.2
PORT=3000
TEST_TIME=60s
SLEEP_TIME=120
TIMEOUT=600 # 10 minutes
ITERATION=5
CONCURENCY=(200 400 600 800 1000)
AUTH_METHOD=jwt
USERNAME="perftest"
PASSWORD="perftest"

init_db() {
    PGPASSWORD=postgres psql -h $HOST -U postgres postgres <dump.sql
}

drop_table_db() {
    PGPASSWORD=postgres psql -h $HOST -U postgres postgres -c "DROP TABLE user_person, hardware, node, sensor, channel;"
}

rollback_db() {
    drop_table_db
    init_db
}

perftest() {
    local method=$1
    local endpoint=$2
    local data=$3
    local do_rollback=$4
    for concurrent in "${CONCURENCY[@]}"; do
        echo "$(TZ=UTC-7 date -R) ($(date +%s))"
        for i in $(seq 1 $ITERATION); do
            echo "$(TZ=UTC-7 date -R) ($(date +%s))"
            echo "[ $method $endpoint $concurrent][$i]"

            # Run command with timeout, if timeout hit, restart
            while true; do
                if [ $method == "GET" ] || [ $method == "DELETE" ]; then
                    timeout --signal=SIGKILL $TIMEOUT siege -t$TEST_TIME -c$concurrent "$HOST:$PORT$endpoint" --header="$HEADER"
                elif [ $method == "PUT" ] || [ $method == "POST" ]; then
                    timeout --signal=SIGKILL $TIMEOUT siege -t$TEST_TIME -c$concurrent "$HOST:$PORT$endpoint $method $data" --header="$HEADER" --content-type "application/json"
                fi

                if [[ $? -eq 137 ]]; then # If Timeout restart the loop
                    echo "Timeout hit, restarting... $(TZ=UTC-7 date -R) ($(date +%s))"
                    continue
                else
                    break
                fi
            done
            echo "Sleeping $SLEEP_TIME seconds..."
            sleep $SLEEP_TIME
            if $do_rollback; then
                rollback_db >/dev/null
            fi
        done
    done
}

auth() {
    if [ $AUTH_METHOD == "jwt" ]; then
        # HEADER="Authorization: Bearer $(http $HOST:$PORT/auth/login username=admin password=admin | jq -r '.token')"
        HEADER="Authorization: Bearer $(http --ignore-stdin $HOST:$PORT/user/login username=$USERNAME password=$PASSWORD -p b)"
    elif [ $AUTH_METHOD == "basic" ]; then
        HEADER="Authorization: Basic $(echo -n $USERNAME:$PASSWORD | base64)"
    fi
    echo "Success auth $HEADER"
}

rollback_db
auth

## perftest METHOD ENDPOINT DATA DO_ROLLBACK
perftest "GET" "/node" "" false
perftest "GET" "/node/1" "" false
perftest "GET" "/sensor" "" false
perftest "GET" "/sensor/1" "" false
perftest "POST" "/channel" "{\"value\": 1.33, \"id_sensor\": 1}" true
perftest "PUT" "/node/1" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware\":1 }" true
perftest "POST" "/node" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware\":1 }" true

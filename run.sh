#!/bin/bash

HOST=10.104.0.2
PORT=3000
TEST_TIME=60s
SLEEP_TIME=60
ITERATION=5
CONCURENCY=(200 400 600 800 1000)
AUTH_METHOD=jwt
USERNAME="admin"
PASSWORD="admin"

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
            if [ $method == "GET" ] || [ $method == "DELETE" ]; then
                siege -t$TEST_TIME -c$concurrent "$HOST:$PORT$endpoint" --header="$HEADER"
            elif [ $method == "PUT" ] || [ $method == "POST" ]; then
                siege -t$TEST_TIME -c$concurrent "$HOST:$PORT$endpoint $method $data" --header="$HEADER" --content-type "application/json"
            fi
            sleep $SLEEP_TIME
            if $do_rollback; then
                rollback_db >/dev/null
            fi
            echo "$(TZ=UTC-7 date -R) ($(date +%s))"
        done
        echo "$(TZ=UTC-7 date -R) ($(date +%s))"
    done
}

auth() {
    if [ $AUTH_METHOD == "jwt" ]; then
        # HEADER="Authorization: Bearer $(http $HOST:$PORT/auth/login username=admin password=admin | jq -r '.token')"
        HEADER="Authorization: Bearer $(http $HOST:$PORT/user/login username=$USERNAME password=$PASSWORD -p b)"
    elif [ $AUTH_METHOD == "basic" ]; then
        HEADER="Authorization: Basic $(echo -n $USERNAME:$PASSWORD | base64)"
    fi
}

rollback_db
auth

## perftest METHOD ENDPOINT DATA DO_ROLLBACK
# perftest "POST" "/channel" "{\"value\": 1.33, \"id_sensor\": 1}" true
perftest "GET" "/node" "" false
perftest "GET" "/node/1" "" false
perftest "POST" "/channel" "{\"value\": 1.33, \"id_sensor\": 1}" true
#salah perftest "PUT" "/node/1" "{\"name\": \"testedit\", \"location\": \"testlocedittt\", \"id_hardware\": 1}" false
perftest "PUT" "/node/1" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware\":1 }" true
# perftest "PUT" "/node/1" true
# perftest "DELETE" "/node/2" "" true

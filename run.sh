#!/bin/bash

TYPE=$1

if [ "$TYPE" == "dafav1" ] || [ "$TYPE" == "dafav2" ]; then
    HOST=10.104.0.2
    PORT=3000
    AUTH_METHOD=jwt
elif [ "$TYPE" == "alvinv1" ] || [ "$TYPE" == "alvinv2" ]; then
    HOST=10.104.0.4
    PORT=8000
    AUTH_METHOD=jwt
elif [ "$TYPE" == "hanin" ]; then
    HOST=10.104.0.4
    PORT=5000
    AUTH_METHOD=basic
elif [ "$TYPE" == "" ]; then
    echo "Missing parameter, usage ./run.sh [dafav1|dafav2|alvinv1|alvinv2|hanin]"
    exit 1
else
    echo "Invalid parameter $TYPE, must be dafav1, dafav2, alvinv1, alvinv2, or hanin"
    exit 1
fi

TEST_TIME=60s
SLEEP_TIME=120
TIMEOUT=600 # 10 minutes
ITERATION=5
CONCURENCY=(200 400 600 800 1000)

if [ "$TYPE" == "alvinv2" ] || [ "$TYPE" == "dafav2" ]; then
    USERNAME="admin"
    PASSWORD="admin"
else
    USERNAME="perftest"
    PASSWORD="perftest"
fi

echo "Host: $HOST:$PORT"
echo "Test time: $TEST_TIME"
echo "Sleep time: $SLEEP_TIME"
echo "Timeout: $TIMEOUT"
echo "Iteration: $ITERATION"
echo "Concurency:" "${CONCURENCY[@]}"
echo "Auth method: $AUTH_METHOD"
echo "Username: $USERNAME"
echo "Password: $PASSWORD"

init_db() {
    if [ "$TYPE" == "alvinv2" ] || [ "$TYPE" == "dafav2" ]; then
        PGPASSWORD=postgres psql -h $HOST -U postgres postgres <version2.sql
    else
        PGPASSWORD=postgres psql -h $HOST -U postgres postgres <version1.sql
    fi
}

drop_table_db() {
    PGPASSWORD=postgres psql -h $HOST -U postgres postgres -c "DROP TABLE IF EXISTS user_person, hardware, node, sensor, channel;"
}

rollback_db() {

    drop_table_db
    init_db
}

test_connection() {
    local method=$1
    local endpoint=$2
    local data=$3
    local do_rollback=$4
    if [ $method == "GET" ] || [ $method == "DELETE" ]; then
        local STATUS="$(curl -s -o /dev/null -w "%{http_code}" "$HOST:$PORT$endpoint" --header "$HEADER" | xargs)"
        local EXIT_CODE=$?
    else
        local STATUS="$(curl -s -o /dev/null -w "%{http_code}" "$HOST:$PORT$endpoint" -X $method --header "$HEADER" --header "Content-type: application/json" -d "$data" | xargs)"
        local EXIT_CODE=$?
    fi

    if [ "$STATUS" -ge 400 ] || [[ "$EXIT_CODE" != 0 ]]; then
        echo "Connection test failed, status code $STATUS for $HOST:$PORT$endpoint $method $data"
        exit 1
    fi
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
            # Restart the postgresql server for the IoT Server
            # iot_test_server is the private key for the IoT Server VM
            ssh -i ~/iot_test_server root@$HOST sudo systemctl restart postgresql

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
        if [ "$TYPE" == "alvinv2" ] || [ "$TYPE" == "alvinv1" ]; then
            HEADER="Authorization: Bearer $(http --ignore-stdin $HOST:$PORT/auth/login username=admin password=admin | jq -r '.token')"
        else
            HEADER="Authorization: Bearer $(http --ignore-stdin $HOST:$PORT/user/login username=$USERNAME password=$PASSWORD -p b)"
        fi
    elif [ $AUTH_METHOD == "basic" ]; then
        HEADER="Authorization: Basic $(echo -n $USERNAME:$PASSWORD | base64)"
    fi
    echo "Success auth $HEADER"
}

rollback_db
auth

echo "Testing connection..."
test_connection "GET" "/node" "" false
test_connection "GET" "/node/1" "" false
if [ "$TYPE" == "alvinv2" ] || [ "$TYPE" == "dafav2" ]; then
    test_connection "PUT" "/node/1" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware_node\":1, \"id_hardware_sensor\" : [3, 4, 4, 17, 8, 7, 3,  4 , 5 ,7], \"field_sensor\": [\"test\", \"asd\", \"sensor3\",\"sensor4\", \"sensor5\", \"sensor6\", \"sensor7\", \"sensor8\", \"sensor9\", \"sensor10\"] }" true
    test_connection "POST" "/node" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware_node\":1, \"id_hardware_sensor\" : [3, 4, 4, 17, 8, 7, 3,  4 , 5 ,7], \"field_sensor\": [\"test\", \"asd\", \"sensor3\",\"sensor4\", \"sensor5\", \"sensor6\", \"sensor7\", \"sensor8\", \"sensor9\", \"sensor10\"] }" true
    test_connection "POST" "/channel" "{\"value\": [3.21, 3.14, 8.39, 9.12, 3.94, 13.23, 183.2, 192.3, 72.3, 93.2], \"id_node\": 1}" true
else
    test_connection "GET" "/sensor" "" false
    test_connection "GET" "/sensor/1" "" false
    test_connection "PUT" "/node/1" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware\":1 }" true
    test_connection "POST" "/node" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware\":1 }" true
    test_connection "POST" "/channel" "{\"value\": 1.33, \"id_sensor\": 1}" true
fi
echo "Connection test success"

## perftest METHOD ENDPOINT DATA DO_ROLLBACK
perftest "GET" "/node" "" false
perftest "GET" "/node/1" "" false
if [ "$TYPE" == "alvinv2" ] || [ "$TYPE" == "dafav2" ]; then
    perftest "PUT" "/node/1" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware_node\":1, \"id_hardware_sensor\" : [3, 4, 4, 17, 8, 7, 3,  4 , 5 ,7], \"field_sensor\": [\"test\", \"asd\", \"sensor3\",\"sensor4\", \"sensor5\", \"sensor6\", \"sensor7\", \"sensor8\", \"sensor9\", \"sensor10\"] }" true
    perftest "POST" "/node" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware_node\":1, \"id_hardware_sensor\" : [3, 4, 4, 17, 8, 7, 3,  4 , 5 ,7], \"field_sensor\": [\"test\", \"asd\", \"sensor3\",\"sensor4\", \"sensor5\", \"sensor6\", \"sensor7\", \"sensor8\", \"sensor9\", \"sensor10\"] }" true
    perftest "POST" "/channel" "{\"value\": [3.21, 3.14, 8.39, 9.12, 3.94, 13.23, 183.2, 192.3, 72.3, 93.2], \"id_node\": 1}" true
else
    perftest "GET" "/sensor" "" false
    perftest "GET" "/sensor/1" "" false
    perftest "PUT" "/node/1" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware\":1 }" true
    perftest "POST" "/node" "{ \"name\":\"test\",\"location\":\"test\",\"id_hardware\":1 }" true
    perftest "POST" "/channel" "{\"value\": 1.33, \"id_sensor\": 1}" true
fi

#!/bin/bash

BASE_DIR="/sys/class/thermal"

DESIRED_STATE=$1

COOLING_DEVICE=$(paste <(ls "${BASE_DIR}" | grep cooling) <(cat ${BASE_DIR}/cooling_device*/type) <(cat ${BASE_DIR}/cooling_device*/cur_state) <(cat ${BASE_DIR}/cooling_device*/max_state) | grep pwm-fan | tr "\t" " " | cut -d " " -f1)

COOLING_DEVICE_PATH="${BASE_DIR}/${COOLING_DEVICE}"
COOLING_DEVICE_MAX_STATE="${BASE_DIR}/${COOLING_DEVICE}/max_state"
COOLING_DEVICE_CUR_STATE="${BASE_DIR}/${COOLING_DEVICE}/cur_state"
COOLING_DEVICE_TRANS_TABLE="${BASE_DIR}/${COOLING_DEVICE}/stats/trans_table"
COOLING_DEVICE_TIME_IN_STATE_MS="${BASE_DIR}/${COOLING_DEVICE}/stats/time_in_state_ms"

echo "COOLING_DEVICE_PATH: ${COOLING_DEVICE_PATH}"

MAX_STATE=$(cat ${COOLING_DEVICE_MAX_STATE})
CUR_STATE=$(cat ${COOLING_DEVICE_CUR_STATE})


if [ "${DESIRED_STATE}" != "" ]
then
    echo ${DESIRED_STATE} > ${COOLING_DEVICE_CUR_STATE}
    echo "Desired state set to: ${DESIRED_STATE}"
else
    # show current state and max state
    echo "Current state: ${CUR_STATE} (max: ${MAX_STATE})"
    cat ${COOLING_DEVICE_TRANS_TABLE}
    cat ${COOLING_DEVICE_TIME_IN_STATE_MS}
fi



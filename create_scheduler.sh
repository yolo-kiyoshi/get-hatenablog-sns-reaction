#!/usr/bin/env bash

set -eu

# read command parameter
. .param

gcloud scheduler jobs create pubsub ${JOB_NAME} \
    --schedule "${SCHEDULE}" \
    --topic ${TOPIC} \
    --time-zone JST \
    --message-body "{}"
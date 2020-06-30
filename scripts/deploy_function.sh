#!/usr/bin/env bash

set -eu

function_name=${1:-}
topic=${2:-}

# read command parameter
. .param
# read environment file
env=$(cat ./.env  | tr '\n' ',' | sed -e 's/,$/\n/g')

gcloud functions deploy ${FUNCTION_NAME} \
    --runtime python37 \
    --entry-point main \
    --trigger-resource ${TOPIC} \
    --trigger-event google.pubsub.topic.publish \
    --region asia-northeast1 \
    --update-env-vars ${env} \
    --allow-unauthenticated

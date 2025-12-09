#!/bin/sh

echo "Waiting for Elasticsearch..."
until curl -s http://elasticsearch:9200 >/dev/null 2>&1; do
  sleep 3
done

echo "Loading pipelines..."

for file in /pipelines/*.json; do
  name=$(basename "$file" .json)

  echo "Loading pipeline: $name"

  curl -s -X PUT "http://elasticsearch:9200/_ingest/pipeline/$name" \
    -H "Content-Type: application/json" \
    -d @"$file"

  echo ""
done

echo "Pipelines loaded."

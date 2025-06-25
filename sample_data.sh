#! /bin/sh

# Generate some errors
for i in {1..5}; do curl http://localhost:80/error; done
for i in {1..10}; do curl http://localhost:80/random; done

# Simple load test
for i in {1..20}; do
  curl http://localhost:80/users/$((RANDOM % 2000)) &
done
wait
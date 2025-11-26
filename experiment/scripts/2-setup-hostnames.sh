#!/bin/sh
set -x

ssh broker-1 "sudo tee -a /etc/hosts > /dev/null" < for-remote/hosts
ssh broker-2 "sudo tee -a /etc/hosts > /dev/null" < for-remote/hosts
ssh broker-3 "sudo tee -a /etc/hosts > /dev/null" < for-remote/hosts
ssh coordinator "sudo tee -a /etc/hosts > /dev/null" < for-remote/hosts

set +x

#!/bin/sh

set -x

# Check all VMs completed cloud-init
ssh broker-1 "cat ~/cloud-init-complete.txt"
ssh broker-2 "cat ~/cloud-init-complete.txt"
ssh broker-3 "cat ~/cloud-init-complete.txt"
ssh coordinator "cat ~/cloud-init-complete.txt"

# Verify NVMe is mounted on brokers
ssh broker-1 "df -h /data && cat ~/nvme-info.txt"
ssh broker-2 "df -h /data && cat ~/nvme-info.txt"
ssh broker-3 "df -h /data && cat ~/nvme-info.txt"

# Check Docker is running
ssh broker-1 "docker ps"
ssh broker-2 "docker ps"
ssh broker-3 "docker ps"
ssh coordinator "docker ps"

set +x

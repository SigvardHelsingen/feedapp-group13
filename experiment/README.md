# Setting up a cluster and running experiments

The experiment provisions 4 storage optimized (NVMe storage), 8 vCPU 64GB RAM VMs on Microsoft Azure.
3 of these VMs are for brokers, and the 4th is a coordinator VM running the benchmarks against the brokers,
and collecting Prometheus metrics.

## Infrastructure

This creates the VMs on Azure, with Docker installed.

1. Set up the Azure CLI on your machine, and log in to your account.
  You might need to up the vCPU quota for `standardLASv3Family` to 32 vCPUs on your Azure account
2. Create an RSA ssh pubkey named `~/.ssh/azure_rsa`
3. Run `terraform apply`
4. Take the output named `ssh_config` and append it to your `~/.ssh/config`
5. Take the output named `remote_hosts_file` and put it in `scripts/for-remote/hosts`

## Verification scripts

Change directory into `scripts`, and run the verification scripts locally in order and verify that they give sane outputs.

1. `1-verify-provisioning.sh`
2. `2-setup-hostnames.sh`
3. `3-check-brokers.sh`

## Setting up the coordinator node

### OpenMessaging Benchmark install

1. SSH into `coordinator`
2. Get the OpenMessaging Benchmark from GitHub: `git clone https://github.com/openmessaging/benchmark.git`
3. Checkout our specific commit: `git checkout 60f6c5bcb32846b10b10eeafbc1df432a90ed542`
4. Build the benchmark code: `mvn clean verify -DskipTests`

### Prometheus setup

1. Copy the files `docker/coordinator.yml` and `docker/coordinator-config/prometheus.yml` to `coordinator:.`
  (`scp docker/{coordinator,coordinator-config/prometheus}.yml coordinator:.`)
2. SSH into `coordinator`
3. `docker-compose -f coordinator.yml up -d`
4. Verify that the jobs are picked up, and the "node" jobs are all healthy:
  `curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, instance: .labels.instance, health: .health}'`

## Set up Kafka

1. Copy `docker/kafka-broker.yml` to all three broker nodes.
  **IMPORTANT**: change the `KAFKA_NODE_ID` environment variable to 2 and 3 for the latter two brokers. 
  Also change `KAFKA_ADVERTISED_LISTENERS` similarly.
2. On each node `docker-compose -f kafka-broker.yml up -d` (make sure that you do this at approximately the same time for all nodes)
3. You might need to `sudo chmod 777 /data/kafka`
4. Verify that all three containers (kafka, cadvisor, node_exporter) are running with `docker ps`
5. On the coordinator node, verify that they've formed a cluster:
  `docker run --rm --network host confluentinc/cp-kafka:7.6.0 kafka-broker-api-versions --bootstrap-server broker1:9092 | grep 'broker'`.
  You should see all three brokers.
6. You can also rerun the Prometheus curl command to verify all collector jobs (except redpanda of course) are healthy now.
7. Run your benchmarks. Profit.

## Set up Redpanda

0. Make sure Kafka is properly torn down on all nodes: `docker-compose -f kafka-broker.yml down`
1. Copy `docker/redpanda-broker.yml` to all three broker nodes.
  **IMPORTANT**: change the `--node-id`, `--advertise-kafka-addr` (internal and external),
  and `--advertise-rpc-addr` parameters on the latter two brokers.
2. On each node `docker-compose -f kafka-broker.yml up -d`
3. You might need to `sudo chmod 777 /data/redpanda`
4. Refer to steps 4-7 for Kafka

## Run a basic benchmark

1. On the coordinator, go to `benchmark/` and change the bootstrap server to `broker1:9092` in `driver-kafka/kafka-sync.yaml`
2. `bin/benchmark --drivers driver-kafka/kafka-sync.yaml workloads/simple-workload.yaml`
  This takes approximately 5-6 minutes. Don't worry if error messages about offset committing are flying across your screen
3. You might need to verify that the JSON file it writes is fully written, then stop the benchmark program manually.

### Extract the data for analysis locally (preliminary)

1. SSH to the coordinator, go to the benchmark directory.
2. Install `sudo apt install python-is-python3 python3-pygal`
3. Run `bin/create_charts.py [json-file]`
4. SCP the resulting SVGs (and the JSON file) to your local computer
5. Go to `~`, stop the Prometheus container: `docker-compose -f coordinator.yml down`
6. `sudo cp -r /var/lib/docker/volumes/azureuser_prometheus-data/_data/ prom-[YOUR DATE OR INDENTIFIER]`
7. rsync the resulting folder to your local computer, for example `rsync -a -e ssh coordinator:prom-2025-11-26-16-10-00 results/`
8. Set up a local Prometheus instance based on that data
  Example local Prometheus:
  ```sh
  docker run -d \
    --name prometheus-local \
    -p 9090:9090 \
    -v $(pwd)/results/prom-2025-11-26-16-10-00:/prometheus \
    prom/prometheus:v3.7.3 \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/prometheus \
    --storage.tsdb.retention.size=1TB
  ```
9. Tear down the Azure VMs with `terraform destroy` in the `infra` directory

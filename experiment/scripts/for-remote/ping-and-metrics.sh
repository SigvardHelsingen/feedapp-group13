set +x

ping -c 2 broker1
ping -c 2 broker2
ping -c 2 broker3

curl -s http://broker1:9100/metrics | head -5
curl -s http://broker2:9100/metrics | head -5
curl -s http://broker3:9100/metrics | head -5

set -x

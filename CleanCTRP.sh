#!/bin/bash

echo "Start clean..."
echo "Clean Application data"
cd /home/uctf/services/CTR1PANEL
docker-compose down
chown -R uctf:uctf /home/uctf/services/CTR1PANEL
rm -rf /home/uctf/services/CTR1PANEL/db
rm -rF /home/uctf/services/CTR1PANEL/logs

docker-compose up -d
echo "Finish clean..."
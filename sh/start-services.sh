#!/usr/bin/env bash
cd ${bx_bizx_repo_path}/bizx-docker-dev
docker-compose up -d zookeeper kafka hana2

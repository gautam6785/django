#!/bin/bash

celery beat -A mobbo -l info --logfile=logs/celery-beat.log &
celery worker -A mobbo -l info --logfile=logs/celery-worker.log &

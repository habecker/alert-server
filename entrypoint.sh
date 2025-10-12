#!/bin/sh

uvicorn alert.app:app --host 0.0.0.0 --proxy-headers --port 8080 --workers 8

#!/bin/bash

test -f "$TFVARS_FILE" && echo "TFVARS_FILE OK"
test -f "$SYNTHETIC_PDF" && echo "SYNTHETIC_PDF OK"
test -n "$AUTH_TOKEN" && echo "AUTH_TOKEN OK"

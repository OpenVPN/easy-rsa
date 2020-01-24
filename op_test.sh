#!/bin/sh
#
# Downloads the run_unit_tests.sh file from easyrsa-unit-tests repo
# and executes that - allows for disconnected testing from the easy-rsa
# repo with TravisCI.

# EG: Set in Travis: CUSTOM CONFIG
# env: ERSA_UTEST_CURL_TARGET="tincantech/easyrsa-unit-tests"
# env: ERSA_UTEST_VERB_LEVEL="-v" (or "-vv")

export ERSA_UTEST_CURL_TARGET="${ERSA_UTEST_CURL_TARGET:-OpenVPN/easyrsa-unit-tests}"

curl -O "https://raw.githubusercontent.com/$ERSA_UTEST_CURL_TARGET/master/easyrsa-unit-tests.sh"
EXIT_CODE=1

if [ -e "easyrsa-unit-tests.sh" ];
then
	EXIT_CODE=0
	ERSA_UTEST_VERB_LEVEL="${ERSA_UTEST_VERB_LEVEL:-"-v"}"
	sh easyrsa-unit-tests.sh "$ERSA_UTEST_VERB_LEVEL" || EXIT_CODE=1
	rm easyrsa-unit-tests.sh
fi

exit "$EXIT_CODE"

#!/bin/sh
#
# Downloads the run_unit_tests.sh file from easyrsa-unit-tests repo
# and executes that - allows for disconnected testing from the easy-rsa
# repo with TravisCI.

verb="${1:-'-v'}"

if [ ! -e "easyrsa-unit-tests.sh" ]; then
	curl -O 'https://raw.githubusercontent.com/OpenVPN/easyrsa-unit-tests/master/easyrsa-unit-tests.sh'

	if [ -e "easyrsa-unit-tests.sh" ]; then
		sh easyrsa-unit-tests.sh "$verb"
		estat=$?
	fi
	rm -f easyrsa-unit-tests.sh
else
	sh easyrsa-unit-tests.sh "$verb"
	estat=$?
fi

exit $estat

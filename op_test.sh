#!/bin/sh
#
# Downloads the run_unit_tests.sh file from easyrsa-unit-tests repo
# and executes that - allows for disconnected testing from the easy-rsa
# repo with TravisCI.

curl -O 'https://raw.githubusercontent.com/OpenVPN/easyrsa-unit-tests/master/easyrsa-unit-tests.sh'

if [ -e "easyrsa-unit-tests.sh" ];
then
	sh easyrsa-unit-tests.sh -v
	estat=$?
fi

rm -f easyrsa-unit-tests.sh

exit $estat

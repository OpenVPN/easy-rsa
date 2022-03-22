#!/bin/sh
#
# Downloads the run_unit_tests.sh file from easyrsa-unit-tests repo
# and executes that - allows for disconnected testing from the easy-rsa
# repo with TravisCI.

case "$1" in
-v)		verb='-v' ;;
-vv)	verb='-vv' ;;
*)		verb='-v'
esac

estat=0

if [ -e "easyrsa-unit-tests.sh" ]; then
	sh easyrsa-unit-tests.sh "$verb"
	estat=$?
else
	curl -O 'https://raw.githubusercontent.com/OpenVPN/easyrsa-unit-tests/master/easyrsa-unit-tests.sh'
	[ -e "easyrsa-unit-tests.sh" ] || { echo "Unit-test download failed."; exit 9; }
	sh easyrsa-unit-tests.sh "$verb"
	estat=$?
	rm -f easyrsa-unit-tests.sh
fi

echo "estat: $estat"
exit $estat

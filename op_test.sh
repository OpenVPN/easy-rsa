#!/bin/sh
#
# Downloads the run_unit_tests.sh file from easyrsa-unit-tests repo
# and executes that - allows for disconnected testing from the easy-rsa
# repo with TravisCI.

github_url='https://raw.githubusercontent.com'

if [ -e "shellcheck" ] && [ "$EASYRSA_NIX" ]; then
	chmod +x shellcheck
	./shellcheck -V
	./shellcheck easyrsa3/easyrsa
elif [ "$EASYRSA_NIX" ]; then
	github_target='OpenVPN/easyrsa-unit-tests/master/shellcheck'
	curl -O "${github_url}/${github_target}"
	[ -e "shellcheck" ] || { echo "shellcheck download failed."; exit 9; }
	chmod +x shellcheck
	./shellcheck -V
	./shellcheck easyrsa3/easyrsa
	rm -f ./shellcheck
fi

case "$1" in
-v)		verb='-v' ;;
-vv)	verb='-vv' ;;
*)		verb='-v'
esac

estat=0

if [ -e "easyrsa-unit-tests.sh" ]; then
	if sh easyrsa-unit-tests.sh "$verb"; then
		: # ok
	else
		estat=1
	fi
else
	github_target='OpenVPN/easyrsa-unit-tests/master/easyrsa-unit-tests.sh'
	curl -O "${github_url}/${github_target}"
	[ -e "easyrsa-unit-tests.sh" ] || { echo "Unit-test download failed."; exit 9; }
	if sh easyrsa-unit-tests.sh "$verb"; then
		: # ok
	else
		estat=1
	fi
	rm -f easyrsa-unit-tests.sh
fi

echo "estat: $estat"
exit $estat

#!/bin/sh
#
# Downloads the run_unit_tests.sh file from easyrsa-unit-tests repo
# and executes that - allows for disconnected testing from the easy-rsa
# repo with TravisCI.

verb='-v'
enable_shellcheck=1

while [ -n "$1" ]; do
	case "$1" in
	-v)		verb='-v' ;;
	-vv)	verb='-vv' ;;
	-scoff)	unset -v enable_shellcheck ;;
	*)		verb='-v'
	esac
	shift
done

github_url='https://raw.githubusercontent.com'

if [ "$enable_shellcheck" ]; then

if [ -e "shellcheck" ] && [ "$EASYRSA_NIX" ]; then
	chmod +x shellcheck
	./shellcheck -V
	if [ -e easyrsa3/easyrsa ];then
		./shellcheck easyrsa3/easyrsa
	else
		echo "* easyrsa binary not present, using path, no shellcheck"
	fi
elif [ "$EASYRSA_NIX" ]; then
	github_target='OpenVPN/easyrsa-unit-tests/master/shellcheck'
	curl -O "${github_url}/${github_target}"
	[ -e "shellcheck" ] || { echo "shellcheck download failed."; exit 9; }
	chmod +x shellcheck
	./shellcheck -V
	if [ -e easyrsa3/easyrsa ];then
		./shellcheck easyrsa3/easyrsa
	else
		echo "* easyrsa binary not present, using path, no shellcheck"
	fi
	rm -f ./shellcheck
fi

else
	# shellcheck is disabled
	:
fi


estat=0

if [ -e "easyrsa-unit-tests.sh" ]; then
	if sh easyrsa-unit-tests.sh "$verb"; then
		if [ "$EASYRSA_NIX" ] && [ "$EASYRSA_BY_TINCANTECH" ]; then
			sh easyrsa-unit-tests.sh "$verb" -x || estat=2
		fi
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

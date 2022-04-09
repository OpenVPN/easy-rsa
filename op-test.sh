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

# disable 'shellcheck' in favour of 'openssl3'
unset -v enable_shellcheck
if [ "$enable_shellcheck" ]; then

if [ -e "shellcheck" ] && [ "$EASYRSA_NIX" ]; then
	chmod +x shellcheck
	./shellcheck -V
	if [ -e easyrsa3/easyrsa ]; then
		./shellcheck -s sh -S warning -x easyrsa3/easyrsa
		echo "* shellcheck completed *"
	else
		echo "* easyrsa binary not present, using path, no shellcheck"
	fi
elif [ "$EASYRSA_NIX" ]; then
	github_target='OpenVPN/easyrsa-unit-tests/master/shellcheck'
	curl -f -O "${github_url}/${github_target}" || {
		echo "shellcheck download failed."
		exit 9
		}
	chmod +x shellcheck
	./shellcheck -V
	if [ -e easyrsa3/easyrsa ]; then
		./shellcheck -s sh -S warning -x easyrsa3/easyrsa
		echo "* shellcheck completed *"
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


	if : ; then



# sh easyrsa-unit-tests.sh "$verb"; then



		if [ "$EASYRSA_NIX" ] && [ "$EASYRSA_BY_TINCANTECH" ]; then


			# two tests in one: x509-alt and ossl-3
			# Not without --x509-alt, waiting for merge

			# openssl v3
			if [ ! -e ./openssl ]; then
				github_target='OpenVPN/easyrsa-unit-tests/master/openssl'
				curl -f -O "${github_url}/${github_target}" || {
					echo "openssl download failed."
					exit 9
					}
			fi
			chmod +x openssl
			./openssl version
			export EASYRSA_OPENSSL="${PWD}/openssl"
			sh easyrsa-unit-tests.sh "$verb" || estat=2
			#rm ./openssl
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

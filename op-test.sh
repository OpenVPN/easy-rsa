#!/bin/sh
#
# Downloads the run_unit_tests.sh file from easyrsa-unit-tests repo
# and executes that - allows for disconnected testing from the easy-rsa
# repo with TravisCI.

# log
log () {
	[ "$disable_log" ] && return
	if printf '%s\n' "* $*"; then
		return
	else
		echo "printf failed"
		exit 9
	fi
} # => log ()

# clean up
clean_up () {
	if [ "$no_delete" ]; then
		log "saved final state.."
	else
		log "op-test: clean_up"
		if [ "$EASYRSA_NIX" ]; then
			[ "$keep_eut" ] || rm -f "$utest_bin"
			[ "$keep_sc" ] || rm -f "$sc_bin"
			[ "$keep_ssl" ] || rm -f "$ssl_bin"
		fi
	fi
} # => clean_up ()

# curl download and openssl hash
# wing it ..
curl_it () {
	#log "BEGIN: curl_it"
	if [ "$#" -eq 2 ]; then
		file="$1"
		hash="$2"
	else
		log "> Usage: <file> <hash>"
		return 1
	fi

	if [ "$enable_curl" ]; then
		: # ok
	else
		log "> curl disabled"
		return 0
	fi

	# valid target
	case "$file" in
	easyrsa-unit-tests.sh|easyrsa-unit-tests-help.sh)
		unset -v require_hash
	;;
	shellcheck|openssl)
		require_hash=1
	;;
	*)
		log "> invalid target: $file"
		return 1
	esac

	# download
	if [ "$enable_curl" ]; then
		log "> download: ${gh_url}/${file}"
		curl -SO "${gh_url}/${file}" || \
			log "> download failed: ${file}"
	else
		log "> curl disabled"
	fi

	# hash download
	if [ "${require_hash}" ]; then
		if [ -e "${file}" ]; then
			log "> hash ${file}"
			temp_hash="$(openssl sha256 "${file}")"
			#log "temp_hash: $temp_hash"
			#log "hash     : $hash"
			if [ "$temp_hash" = "$hash" ]; then
				: # OK - hash is good
			else
				log "> hash failed: ${file}"
				return 1
			fi
		else
			log "> file missing: ${file}"
			return 1
		fi
	else
		if [ -e "${file}" ]; then
			: # ok - file is here
		else
			log "> file missing: ${file}"
			return 1
		fi
	fi
} # => curl_it ()

################################################################################

# RUN unit test
run_unit_test ()
{
	if [ "${utest_bin_ok}" ]; then

		# Start unit tests
		log ">>> BEGIN unit tests:"
		[ "$no_delete" ] && export SAVE_PKI=1

		if [ "${dry_run}" ]; then
			log "<<dry-run>> sh ${utest_bin} ${verb} $use_passwords"
			estat=1
		else
			log ">>>>>>: sh ${utest_bin} ${verb}"
			if sh "${utest_bin}" "${verb}" "$use_passwords"; then
				log "OK"
				estat=0
				if [ "$EASYRSA_BY_TINCANTECH" ]; then
					sh "${utest_help_bin}" "${help_verb}" "$use_passwords"
				fi
			else
				log "FAIL"
				estat=1
			fi
		fi
		log "<<< END unit tests:"
		unset SAVE_PKI
	else
		log "unit-test abandoned"
		estat=1
	fi
} # => run_unit_test ()

########################################

## DOWNLOAD unit-test
download_unit_test () {
	# if not present then download unit-test
	target_file="${utest_file}"
	target_hash="${utest_hash}"
	if [ "$enable_unit_test" ]; then
		if [ -e "${ERSA_UT}/${target_file}" ]; then
			[ -x "${ERSA_UT}/${target_file}" ] || \
				chmod +x "${ERSA_UT}/${target_file}"
			# version check
			if "${ERSA_UT}/${target_file}" version; then
				utest_bin="${ERSA_UT}/${target_file}"
				utest_bin_ok=1
				export ERSA_UTEST_CURL_TARGET=localhost
			else
				log "version check failed: ${ERSA_UT}/${target_file}"
			fi
		else
			# download and basic check
			log "curl_it ${target_file}"
			if curl_it "${target_file}" "${target_hash}"; then
				[ -x "${ERSA_UT}/${target_file}" ] || \
					chmod +x "${ERSA_UT}/${target_file}"
				# functional check - version check
				if "${ERSA_UT}/${target_file}" version; then
					utest_bin="${ERSA_UT}/${target_file}"
					utest_bin_ok=1
					export ERSA_UTEST_CURL_TARGET=online
					unset -v keep_eut
				else
					log "version check failed: ${target_file}"
				fi
			else
				log "curl_it ${target_file} - failed"
			fi
		fi
		[ "$utest_bin_ok" ] || log "undefined: utest_bin_ok"
		log "setup unit-test - ok"
	else
		log "unit-test disabled"
	fi # => shellcheck
}
## DOWNLOAD unit-test

## DOWNLOAD unit-test-help
download_unit_test_help () {
	# if not present then download unit-test-help
	target_file="${utest_help_file}"
	target_hash="${utest_hash}"
	if [ "$enable_unit_test" ]; then
		if [ -e "${ERSA_UT}/${target_file}" ]; then
			[ -x "${ERSA_UT}/${target_file}" ] || \
				chmod +x "${ERSA_UT}/${target_file}"
			# version check
			if "${ERSA_UT}/${target_file}" version; then
				utest_help_bin="${ERSA_UT}/${target_file}"
				utest_help_bin_ok=1
				export ERSA_UTEST_CURL_TARGET=localhost
			else
				log "version check failed: ${ERSA_UT}/${target_file}"
			fi
		else
			# download and basic check
			log "curl_it ${target_file}"
			if curl_it "${target_file}" "${target_hash}"; then
				[ -x "${ERSA_UT}/${target_file}" ] || \
					chmod +x "${ERSA_UT}/${target_file}"
				# functional check - version check
				if "${ERSA_UT}/${target_file}" version; then
					utest_help_bin="${ERSA_UT}/${target_file}"
					utest_help_bin_ok=1
					export ERSA_UTEST_CURL_TARGET=online
					unset -v keep_eut
				else
					log "version check failed: ${target_file}"
				fi
			else
				log "curl_it ${target_file} - failed"
			fi
		fi
		[ "$utest_help_bin_ok" ] || log "undefined: utest_help_bin_ok"
		log "setup unit-test-help - ok"
	else
		log "unit-test-help disabled"
	fi # => shellcheck
}
## DOWNLOAD unit-test-help

################################################################################

## USE shellcheck

# Run shellcheck
run_shellcheck () {
	sc_bin=shellcheck
	if [ "$enable_shellcheck" ] && [ "$EASYRSA_NIX" ]; then
		# shell-check easyrsa3/easyrsa
		if [ -e easyrsa3/easyrsa ]; then
			if "${sc_bin}" -s sh -S warning -x easyrsa3/easyrsa; then
				log "shellcheck easyrsa3/easyrsa completed - ok"
			else
				log "shellcheck easyrsa3/easyrsa completed - FAILED"
			fi
		else
			log "easyrsa binary not present, not using shellcheck"
		fi

		# shell-check dev/easyrsa-tools.lib
		if [ -e dev/easyrsa-tools.lib ]; then
			if "${sc_bin}" -s sh -S warning -x dev/easyrsa-tools.lib; then
				log "shellcheck dev/easyrsa-tools.lib completed - ok"
			else
				log "shellcheck dev/easyrsa-tools.lib completed - FAILED"
			fi
		else
			log "dev/easyrsa-tools.lib not present, not using shellcheck"
		fi

		# shell-check easyrsa-unit-tests.sh
		if [ -e easyrsa-unit-tests.sh ]; then
			if "${sc_bin}" -s sh -S warning -x easyrsa-unit-tests.sh; then
				log "shellcheck easyrsa-unit-tests.sh completed - ok"
			else
				log "shellcheck easyrsa-unit-tests.sh completed - FAILED"
			fi
		else
			log "easyrsa-unit-tests.sh binary not present, not using shellcheck"
		fi
	else
		log "shellcheck abandoned"
	fi
}
## USE shellcheck

########################################

## DOWNLOAD shellcheck
download_shellcheck () {
	# if not present then download shellcheck
	target_file="${sc_file}"
	target_hash="${sc_hash}"
	if [ "$enable_shellcheck" ] && [ "$EASYRSA_NIX" ]; then
		log "setup shellcheck"
		if [ -e "${ERSA_UT}/${target_file}" ]; then
			[ -x "${ERSA_UT}/${target_file}" ] || \
				chmod +x "${ERSA_UT}/${target_file}"
			"${ERSA_UT}/${target_file}" -V || \
				log "version check failed: ${ERSA_UT}/${target_file}"
			sc_bin="${ERSA_UT}/${target_file}"
			sc_bin_ok=1
			log "shellcheck enabled"
		else
			# download and basic check
			log "curl_it ${target_file}"
			if curl_it "${target_file}" "${target_hash}"; then
				log "curl_it ${target_file} - ok"
				[ -x "${ERSA_UT}/${target_file}" ] || \
					chmod +x "${ERSA_UT}/${target_file}"
				# functional check
				if "${ERSA_UT}/${target_file}" -V; then
					sc_bin="${ERSA_UT}/${target_file}"
					sc_bin_ok=1
					unset -v keep_sc
				else
					log "version check failed: ${ERSA_UT}/${target_file}"
				fi
				log "shellcheck enabled"
			else
				log "curl_it ${target_file} - failed"
			fi
		fi
	fi

	## DOWNLOAD shellcheck
}

################################################################################

## DOWNLOAD openssl-3
download_opensslv3 () {
	# if not present then download and then use openssl3
	target_file="${ssl_file}"
	target_hash="${ssl_hash}"
	if [ "$enable_openssl3" ] && [ "$EASYRSA_NIX" ]; then
		if [ -e "${ERSA_UT}/${target_file}" ]; then
			[ -x "${ERSA_UT}/${target_file}" ] || \
				chmod +x "${ERSA_UT}/${target_file}"
			# version check 'openssl version'
			"${ERSA_UT}/${target_file}" version || \
				log "version check failed: ${ERSA_UT}/${target_file}"
			ssl_bin="${ERSA_UT}/${target_file}"
			ssl_bin_ok=1
			# Set up Easy-RSA Unit-Test for OpenSSL-v3
			export EASYRSA_OPENSSL="${ssl_bin}"
		else
			# download and basic check
			log "curl_it ${target_file}"
			if curl_it "${target_file}" "${target_hash}"; then
				log "curl_it ${target_file} - ok"
				[ -x "${ERSA_UT}/${target_file}" ] || \
					chmod +x "${ERSA_UT}/${target_file}"
				# functional check - version check 'openssl version'
				if "${ERSA_UT}/${target_file}" version; then
					ssl_bin="${ERSA_UT}/${target_file}"
					ssl_bin_ok=1
					unset -v keep_ssl
					# Set up Easy-RSA Unit-Test for OpenSSL-v3
					export EASYRSA_OPENSSL="${ssl_bin}"
				else
					log "version check failed: ${ERSA_UT}/${target_file}"
				fi
			else
				log "curl_it ${target_file} - failed"
			fi
		fi

			log "OpenSSL-v3 enabled"

	else
		if [ "$EASYRSA_NIX" ]; then
			log "System SSL enabled"
			ssl_bin="openssl"
			ssl_bin_ok=1
		else
			log "Windows, no OpenSSL-v3"
			log "System SSL enabled"
			ssl_bin="openssl"
			ssl_bin_ok=1
		fi
	fi
} # => ## DOWNLOAD openssl-3

################################################################################

	# Register clean_up on EXIT
	#trap "exited 0" 0
	# When SIGHUP, SIGINT, SIGQUIT, SIGABRT and SIGTERM,
	# explicitly exit to signal EXIT (non-bash shells)
	trap "clean_up" 1
	trap "clean_up" 2
	trap "clean_up" 3
	trap "clean_up" 6
	trap "clean_up" 15


unset -v disable_log verb no_delete \
		enable_unit_test enable_shellcheck enable_openssl3

keep_sc=1
keep_ssl=1
keep_eut=1

# Set by default
enable_unit_test=1
enable_curl=1
EASYRSA_NIX=1

while [ -n "$1" ]; do
	case "$1" in
	--no-log)			disable_log=1 ;;
	'')					verb='-v' ;;
	-v)					verb='-v' ;;
	-vv)				verb='-vv' ;;
	-sc)				enable_shellcheck=1 ;;
	-o3)				: ;; # ignored
	-p)					use_passwords='-p' ;;
	-dr)				dry_run=1 ;;
	-nt|--no-test)		unset -v enable_unit_test ;;
	-nc|--no-curl)		unset -v enable_curl ;;
	-nd|--no-delete)	no_delete=1 ;;
	-w|--windows)		export EASYRSA_WIN=1; unset -v EASYRSA_NIX ;;
	*)
		log "Unknown option: $1"
		exit 9
	esac
	shift
done

log "Easy-RSA Unit Tests:"

# Layout
ERSA_UT="${PWD}"

# Sources
gh_url='https://raw.githubusercontent.com/OpenVPN/easyrsa-unit-tests/master'

utest_file='easyrsa-unit-tests.sh'
unset -v utest_bin utest_bin_ok
utest_hash='no-hash'

utest_help_file='easyrsa-unit-tests-help.sh'
unset -v utest_help_bin utest_help_bin_ok
#utest_hash='no-hash'
help_verb="-vv"

sc_file='shellcheck'
unset -v sc_bin sc_bin_ok
# v 0.8.0
#sc_hash='SHA256(shellcheck)= f4bce23c11c3919c1b20bcb0f206f6b44c44e26f2bc95f8aa708716095fa0651'

# v 0.9.0
sc_hash='SHA256(shellcheck)= 7087178d54de6652b404c306233264463cb9e7a9afeb259bb663cc4dbfd64149'

ssl_file='openssl'
unset -v ssl_bin ssl_bin_ok
# v 3.0.3
#ssl_hash='SHA256(openssl)= a0aed8b4aec1b72ca17c8a9ab04e10d829343a12cb5e7f8f6ae73e6f2ce026fd'

# v 3.0.5
#ssl_hash='SHA256(openssl)= 341d278423aeecbaa2b057b84b5501dd492c8f7e192c5bb9c66a260dbc022a4c'

# v 3.0.7
#ssl_hash='SHA256(openssl)= 606f8fb9d6ac7993c2f68efba8c4f022e128a8e9ab1a0921e4941d9f88a7bb5b'

# v 3.1.0
ssl_hash='SHA256(openssl)= 85b562891087d4c64868d8d1f0a381407d8e23fb66c37ce9baad55cf57edbc04'

# Here we go ..

#download_shellcheck
#download_opensslv3
download_unit_test
download_unit_test_help

run_shellcheck
run_unit_test

# No trap required..
clean_up

################################################################################

log "estat: $estat ${dry_run:+<<dry run>>}"
exit $estat

# vim: no

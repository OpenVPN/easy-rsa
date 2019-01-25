#!/bin/sh
#
# Runs operational testing

set -e

usage ()
{
cat << __EOF__

	Actions taken:
	* standard ca
	* standard server
	* standard server with SAN
	* standard serverClient
	* standard client
	* standard sign imported server
	* standard sign imported serverClient
	* standard sign imported client
	* standard sign imported ca
	* subca to origin
	* subca sign server
	* subca sign serverClient
	* subca sign client
	* revoke
	* CRLs

	EASYRSA_*
	* All standard EASYRSA vars are avaiable.

	Todo:
	* test renew ()

	Will not do:
	* libressl
	* openssl-dev
	Do not burden Travis with these unnecessary stages.
	Relevant hooks left for local implementations.

	Note:
	* Currently always completes, until easyrsa-prog_exit is fixed.
	  https://github.com/OpenVPN/easy-rsa/issues/282

	Suggested options:
	* "./op_test.sh -v" (verbose)
	* "ERSA_OUT=0 ./op_test.sh -vv" (very verbose but no SSL output)

__EOF__
exit 0
}

init ()
{
	ROOT_DIR="$(pwd)"
	export TEMP_DIR="$ROOT_DIR/temp"
	DIE=1
	VERBOSE="${VERBOSE:-0}"
	VVERBOSE="${VVERBOSE:-0}"
	FIRST_RUN=1
	ERSA_OUT="${ERSA_OUT:-0}"
	ERSA_BIN="./easyrsa"
	CUSTOM_VARS="${CUSTOM_VARS:-1}"
	UNSIGNED_PKI="${UNSIGNED_PKI:-1}"
	SYS_SSL_ENABLE="${SYS_SSL_ENABLE:-1}"
	BROKEN_PKI="${BROKEN_PKI:-0}"
	SAVE_PKI="${SAVE_PKI:-0}"
	CUSTOM_OPTS="${CUSTOM_OPTS:-0}"
	export EASYRSA_CA_EXPIRE="${EASYRSA_CA_EXPIRE:-1}"
	export EASYRSA_CERT_EXPIRE="${EASYRSA_CERT_EXPIRE:-1}"
	export OPENSSL_ENABLE="${OPENSSL_ENABLE:-0}"
	export OPENSSL_BUILD="${OPENSSL_BUILD:-0}"
	export OPENSSL_VERSION="${OPENSSL_VERSION:-git}"
	export OSSL_LIBB="${OSSL_LIBB:-"$TEMP_DIR/openssl-dev/bin/openssl"}"
	export LIBRESSL_ENABLE="${LIBRESSL_ENABLE:-0}"
	export LIBRESSL_BUILD="${LIBRESSL_BUILD:-0}"
	export LIBRESSL_VERSION="${LIBRESSL_VERSION:-2.8.3}"
	export LSSL_LIBB="${LSSL_LIBB:-"$TEMP_DIR/libressl/usr/local/bin/openssl"}"
}

# Wrapper around printf - clobber print since it's not POSIX anyway
print() { printf "%s\n" "$1"; }

newline ()
{
	[ $((VVERBOSE)) -eq 1 ] || return 0
	if [ "$1" = "1" ]
	then
		print "|| ============================================================================"
	else
		print
	fi
}

verbose ()
{
	# currently not used
	[ $((VERBOSE)) -eq 1 ] || return 0
	print "|| :: $1 .. OK"
}

completed ()
{
	[ $((VERBOSE)) -eq 1 ] || return 0
	MSG="$(print "$1" | sed -e s/^--.*0\ //g -e s\`/.*/\`\`g -e s/nopass//g)"
	print "$MSG .. ok"
}

warn ()
{
	print "|| >> $1"
}

die ()
{
	warn "$0 FATAL ERROR! exit 1: $1"
	[ $((DIE)) -eq 1 ] && tear_down && exit 1
	warn "Ignored"
	return 0
}

vverbose ()
{
	[ $((VVERBOSE)) -eq 1 ] || return 0
	MSG="$(print "$1" | sed -e s/^--.*0\ //g -e s\`/.*/\`\`g -e s/nopass//g)"
	print "|| :: $MSG"
}

vdisabled ()
{
	[ $((VVERBOSE)) -eq 1 ] || return 0
	print "|| -- DISABLED OPTION: $1"
}

vcompleted ()
{
	[ $((VVERBOSE)) -eq 1 ] || return 0
	MSG="$(print "$1" | sed -e s/^--.*0\ //g -e s\`/.*/\`\`g -e s/nopass//g)"
	print "|| ++ $MSG .. ok"
}

verb_on ()
{
	VERBOSE="$SAVE_VERB"
	VVERBOSE="$SAVE_VVERB"
	ERSA_OUT="$SAVE_EOUT"
}

verb_off ()
{
	SAVE_VERB="$VERBOSE"
	VERBOSE=0
	SAVE_VVERB="$VVERBOSE"
	VVERBOSE=0
	SAVE_EOUT="$ERSA_OUT"
	ERSA_OUT=0
}

setup ()
{
	newline 1
	vverbose "Setup"

	[ -d easyrsa3 ] && cd easyrsa3
	vverbose "Working dir: $(pwd)"

	destroy_data

	STEP_NAME="vars"
	if [ $((CUSTOM_VARS)) -eq 1 ]
	then
		vverbose "$STEP_NAME"
		cp vars.example vars || die "cp vars.example vars"
		create_vars >> vars || die "create_vars"
	else
		vdisabled "$STEP_NAME"
	fi

	STEP_NAME="Custom opts"
	if [ $((CUSTOM_OPTS)) -eq 1 ]
	then
		# https://github.com/OpenVPN/easy-rsa/pull/278
		export CUSTOM_EASYRSA_REQ_ORG2="Custom Option"
		export LIBRESSL_ENABLE=0
		[ -f ./openssl-easyrsa.cnf ] || die "Cannot find ./openssl-easyrsa.cnf"
		cp ./openssl-easyrsa.cnf ./openssl-easyrsa.cnf.orig || die "Cannot copy ./openssl-easyrsa.cnf"
		create_custom_opts > ./openssl-easyrsa.cnf_custom || die "Cannot create ./openssl-easyrsa.cnf_custom"
		mv -f ./openssl-easyrsa.cnf_custom ./openssl-easyrsa.cnf || die "Cannot move ./openssl-easyrsa.cnf_custom"
		vcompeleted "$STEP_NAME"
	fi

	STEP_NAME="Sample requests"
	if [ $((UNSIGNED_PKI)) -eq 1 ] && [ $((SYS_SSL_ENABLE + OPENSSL_ENABLE + LIBRESSL_ENABLE)) -ne 0 ]
	then
		vverbose "$STEP_NAME"
		verb_off
		NEW_PKI="pki-req"
		create_req || die "$STEP_NAME"
		mv "$TEMP_DIR/$NEW_PKI" "$TEMP_DIR/pki-bkp" || die "$STEP_NAME"
		verb_on
	else
		vdisabled "$STEP_NAME"
	fi
}

destroy_data ()
{
	if [ $((SAVE_PKI)) -ne 1 ] || [ $((FIRST_RUN)) -eq 1 ]
	then
		rm -f vars
		for i in pki-req pki-bkp pki-dssl pki-ossl pki-lssl pki-empty pki-error
		do
			TARGET="$TEMP_DIR/$i"
			rm -rf "$TARGET"
		done
		[ -d "$TEMP_DIR" ] && rmdir --ignore-fail-on-non-empty "$TEMP_DIR"
		[ -f ./openssl-easyrsa.cnf.orig ] && mv -f ./openssl-easyrsa.cnf.orig ./openssl-easyrsa.cnf
	fi
	FIRST_RUN=0
}

secure_key ()
{
	rm -f "$EASYRSA_PKI/private/$REQ_name.key"
}

tear_down ()
{
	destroy_data
	cd ..
}

create_vars ()
{
	print ' set_var EASYRSA_DN "org"'
	print '# Unsupported characters:'
	print '# `'
	print '# $'
	print '# "'
	print "# '"
	print '# #'
	print '# & (Win)'
	print ' set_var EASYRSA_REQ_COUNTRY   "00"'
	print ' set_var EASYRSA_REQ_PROVINCE  "test"'
	print ' set_var EASYRSA_REQ_CITY      "TEST ,./<>  ?;:@~  []!%^  *()-=  _+| (23) TEST"'
	print ' set_var EASYRSA_REQ_ORG       "example.org"'
	print ' set_var EASYRSA_REQ_EMAIL     "me@example.net"'
	print ' set_var EASYRSA_REQ_OU        "TEST esc \{ \} \£ \¬ (4) TEST"'
}

create_custom_opts ()
{
	head -n 91 ./openssl-easyrsa.cnf
	print "1.organizationName		= Second Organization Name"
	print "1.organizationName_default 	= \$ENV::CUSTOM_EASYRSA_REQ_ORG2"
	tail -n +91 ./openssl-easyrsa.cnf
}

create_req ()
{
	export EASYRSA_PKI="$TEMP_DIR/$NEW_PKI"

	STEP_NAME="init-pki"
	action

	export EASYRSA_BATCH=1
	export EASYRSA_REQ_CN="maximilian"
	STEP_NAME="build-ca nopass subca"
	action
	[ -f "$EASYRSA_PKI/reqs/ca.req" ] && REQ_ca="$EASYRSA_PKI/reqs/ca.req"

	export EASYRSA_REQ_CN="specter"
	STEP_NAME="gen-req $EASYRSA_REQ_CN nopass"
	action
	secure_key
	[ -f "$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req" ] && REQ_server="$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req"

	export EASYRSA_REQ_CN="meltdown"
	STEP_NAME="gen-req $EASYRSA_REQ_CN nopass"
	action
	secure_key
	[ -f "$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req" ] && REQ_client="$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req"

	export EASYRSA_REQ_CN="heartbleed"
	STEP_NAME="gen-req $EASYRSA_REQ_CN nopass"
	action
	secure_key
	[ -f "$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req" ] && REQ_serverClient="$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req"

	unset EASYRSA_REQ_CN
	unset EASYRSA_BATCH
}

restore_req ()
{
	STEP_NAME="Restore sample requests"
	vverbose "$STEP_NAME"
	rm -rf "$TEMP_DIR/pki-req"
	cp -Rf "$TEMP_DIR/pki-bkp" "$TEMP_DIR/pki-req" >/dev/null 2>&1 || die "$STEP_NAME"
}

move_ca ()
{
	newline 1
	STEP_NAME="Send ca to origin"
	mv "$EASYRSA_PKI/issued/$REQ_name.crt" "$TEMP_DIR/pki-req/ca.crt" >/dev/null 2>&1 || die "$STEP_NAME"
	completed "$STEP_NAME"
	vcompleted "$STEP_NAME"

	STEP_NAME="Change PKI to origin"
	export EASYRSA_PKI="$TEMP_DIR/pki-req"
	completed "$STEP_NAME"
	vcompleted "$STEP_NAME"
}

action ()
{
	if [ $((ERSA_OUT)) -eq 1 ]
	then
		"$ERSA_BIN" $STEP_NAME || die "$STEP_NAME"
	else
		"$ERSA_BIN" $STEP_NAME >/dev/null 2>&1 || die "$STEP_NAME"
	fi
	completed "$STEP_NAME"
}

init_pki ()
{
	STEP_NAME="init-pki"
	vverbose "$STEP_NAME"
	action
}

build_ca ()
{
	STEP_NAME="build-ca nopass"
	export EASYRSA_REQ_CN="penelope"
	vverbose "$STEP_NAME"
	action
	unset EASYRSA_REQ_CN
}

show_ca ()
{
	STEP_NAME="show-ca"
	vverbose "$STEP_NAME"
	SAVE_VERB="$VERBOSE"
	VERBOSE=0
	action
	newline
	VERBOSE="$SAVE_VERB"
}

build_full ()
{
	newline 1
	STEP_NAME="build-$REQ_type-full $REQ_name nopass"
	vverbose "$STEP_NAME"
	action
	secure_key
}

build_san_full ()
{
	newline 1
	STEP_NAME="--subject-alt-name=IP:0.0.0.0 build-server-full $REQ_name nopass"
	vverbose "$STEP_NAME"
	action
	secure_key
}

import_req ()
{
	case "$REQ_type" in
		ca)		REQ_file="$REQ_ca" ;;
		server)		REQ_file="$REQ_server" ;;
		client)		REQ_file="$REQ_client" ;;
		serverClient)	REQ_file="$REQ_serverClient";;
		*) 		DIE=1 die "Unknown certificate type $REQ_type" ;;
	esac

	newline 1
	STEP_NAME="import-req $REQ_file $REQ_name"
	vverbose "$STEP_NAME"
	action
}

sign_req ()
{
	newline 1
	STEP_NAME="sign-req $REQ_type $REQ_name nopass"
	vverbose "$STEP_NAME"
	action
}

show_cert ()
{
	STEP_NAME="show-cert $REQ_name"
	vverbose "$STEP_NAME"
	SAVE_VERB="$VERBOSE"
	VERBOSE=0
	action
	VERBOSE="$SAVE_VERB"
	newline
}

renew_cert ()
{
	# https://github.com/OpenVPN/easy-rsa/pull/286
	vverbose "Todo: renew_cert"
	return 0

	STEP_NAME="renew $REQ_name nopass"
	vverbose "$STEP_NAME"
	action
}

revoke_cert ()
{
	STEP_NAME="revoke $REQ_name"
	CAT_THIS="$EASYRSA_PKI/index.txt"
	verb_off
	action
	verb_on
}

gen_crl ()
{
	newline 1
	STEP_NAME="gen-crl"
	vverbose "$STEP_NAME"
	action
	CAT_THIS="$EASYRSA_PKI/crl.pem"
	cat_file
}

cat_file ()
{
	[ $((ERSA_OUT)) -eq 1 ] || return 0
	newline
	vverbose "cat $CAT_THIS"
	newline
	[ -f "$CAT_THIS" ] || die "cat $CAT_THIS"
	[ $((VVERBOSE)) -eq 1 ] && [ -f "$CAT_THIS" ] && cat "$CAT_THIS"
	newline
}

create_pki ()
{
	newline 1
	vverbose "$STAGE_NAME"

	restore_req

	export EASYRSA_PKI="$TEMP_DIR/$NEW_PKI"
	if [ "$EASYRSA_PKI" = "$TEMP_DIR/pki-empty" ] || [ "$EASYRSA_PKI" = "$TEMP_DIR/pki-error" ]
	then
		vverbose "OMITTING init-pki"
	else
		init_pki
	fi
	export EASYRSA_BATCH=1

	build_ca
	show_ca

	REQ_type="server"
	REQ_name="s01"
	build_full
	show_cert
	revoke_cert

	REQ_type="server"
	REQ_name="s02"
	build_san_full
	show_cert
	revoke_cert

	REQ_type="serverClient"
	REQ_name="s03"
	build_full
	show_cert
	revoke_cert

	REQ_type="client"
	REQ_name="c01"
	build_full
	show_cert
	revoke_cert

	REQ_type="server"
	REQ_name="specter"
	import_req
	sign_req
	show_cert
	revoke_cert

	REQ_type="serverClient"
	REQ_name="heartbleed"
	import_req
	sign_req
	show_cert
	revoke_cert

	REQ_type="client"
	REQ_name="meltdown"
	import_req
	sign_req
	show_cert
	revoke_cert

	gen_crl

	REQ_type="ca"
	REQ_name="maximilian"
	import_req
	sign_req

	# goto origin
	move_ca
	show_ca

	REQ_type="server"
	REQ_name="specter"
	sign_req
	show_cert
	revoke_cert

	REQ_type="serverClient"
	REQ_name="heartbleed"
	sign_req
	show_cert
	revoke_cert

	REQ_type="client"
	REQ_name="meltdown"
	sign_req
	show_cert
	revoke_cert

	gen_crl

	unset EASYRSA_BATCH
	unset EASYRSA_PKI
	vcompleted "$STAGE_NAME"
	newline 1
}


######################################

	for i in $1
	do
		case $i in
		-u|-h|--help)	usage ;;
		-v)		VERBOSE=1 ;;
		-vv)		VVERBOSE=1; ERSA_OUT="${ERSA_OUT:-1}" ;;
		-b)		BROKEN_PKI=1; SYS_SSL_ENABLE="${SYS_SSL_ENABLE:-0}"; VVERBOSE=1; ERSA_OUT="${ERSA_OUT:-1}" ;;
		*)		print "Unknown option: $i"; exit 1 ;;
		esac
	done

	init

	[ -f "$TEMP_DIR/openssl.sh" ] || export OPENSSL_ENABLE=0
	[ $((OPENSSL_ENABLE)) -eq 1 ] && "$TEMP_DIR/openssl.sh"

	[ -f "$TEMP_DIR/libressl.sh" ] || export LIBRESSL_ENABLE=0
	[ $((LIBRESSL_ENABLE)) -eq 1 ] && "$TEMP_DIR/libressl.sh"

	setup

	STAGE_NAME="Default ssl"
	if [ $((SYS_SSL_ENABLE)) -eq 1 ]
	then
		NEW_PKI="pki-dssl"
		create_pki
	else
		vdisabled "$STAGE_NAME"
	fi

	STAGE_NAME="openssl"
	if [ $((OPENSSL_ENABLE)) -eq 1 ]
	then
		[ -f "$OSSL_LIBB" ] || DIE=1 die "$0: missing openssl: $OSSL_LIBB"
		export EASYRSA_OPENSSL="$OSSL_LIBB"
		NEW_PKI="pki-ossl"
		create_pki
		unset EASYRSA_OPENSSL
	else
		vdisabled "$STAGE_NAME"
	fi

	STAGE_NAME="libressl"
	if [ $((LIBRESSL_ENABLE)) -eq 1 ]
	then
		[ -f "$LSSL_LIBB" ] || DIE=1 die "$0: missing libressl: $LSSL_LIBB"
		export EASYRSA_OPENSSL="$LSSL_LIBB"
		NEW_PKI="pki-lssl"
		create_pki
		unset EASYRSA_OPENSSL
	else
		vdisabled "$STAGE_NAME"
	fi

	STAGE_NAME="Common errors (Does *not* die on errors)"
	if [ $((BROKEN_PKI)) -eq 1 ]
	then
		NEW_PKI="pki-empty"
		#restore_req
		DIE=0 create_pki
	else
		vdisabled "$STAGE_NAME"
	fi

	tear_down

completed "Completed"
vcompleted "Completed"
exit 0

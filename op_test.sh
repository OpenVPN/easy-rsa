#!/bin/sh
#
# Copyright (c) 2019, Richard Bonhomme
#
# tincanteksup@gmail.com
#
# https://github.com/TinCanTech
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
# Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# VERSION: 1.0

# Runs operational testing

set -e
#set -x

usage ()
{
cat << UTXT

	Actions taken:
	* Remove old data (Forced)
	* Creat custom vars (CUSTOM_VARS=1)
	* Create unsigned PKI with default SSL lib for later signing (UNSIGNED_PKI=1)
	* Create standard PKI with default SSL lib (SYS_SSL_ENABLE=1)
	* Test common errors with with default SSL lib (BROKEN_PKI=1)
	* Create deliberate error (Unless TRAVIS=1)
	* Delete test data (Unless SAVE_PKI=1)

	Standard PKI includes:
	* standard ca (penelope)
	* standard server "s01"
	* standard server with SAN "s02"
	* standard serverClient "heartbleed"
	* standard client "c01"
	* standard subca (maximilian)
	* standard sign imported server "specter"
	* standard sign imported serverClient "heartbleed"
	* standard sign imported client "meltdown"
	* send subca to origin
	* subca sign server "specter"
	* subca sign serverClient "heartbleed"
	* subca sign client "meltdown"
	* revoke all certificates
	* Create a CRL

	EASYRSA_*
	* All standard EASYRSA vars are avaiable in the normal way.

	* SAVE_PKI=1

	This is only a general guide ..
	(penelope and maximilian are just names;-)

	Todo: (maybe)
	libressl
	* LIBRESSL_ENABLE=1
	* download libressl (Version required, default 2.8.3} (LIBRESSL_ENABLE=1)
	* build libressl (LIBRESSL_ENABLE=1 to enable)
	* LIBRESSL_VERSION="0.6.0" etc.
	* LIBRESSL_BUILD=1 to force building libressl.
	* libressl source is not deleted once built.
	* libressl will be rebuilt automatically if a new version is downloaded.
	* Create standard PKI with libressl (if available) (LIBRESSL_ENABLE=1)
	openssl
	* OPENSSL_ENABLE=1
	* Create standard PKI with openssl-dev (if already available) (OPENSSL_DEV_ENABLE=1)
	Shecllcheck (Temporarily moved to travis.yml)
	* SC_ENABLE=1
	* download shellcheck (Version required, default "latest") (SC_ENABLE=1)
	* SC_DOWNLOAD=1 to force download of shellcheck
	* SC_VERSION="latest" | "stable" | "0.6.0" etc.
	* shellcheck binary is deleted after use.
	* shellcheck archive is retained for next use.
	* shellcheck easyrsa3/easyrsa (SC_ENABLE=1)
	* shellcheck op_test.sh (SC_ENABLE=1)

UTXT
exit 0
}

init ()
{
	ROOT_DIR="$(pwd)"
	export ROOT_DIR
	Errors=0
	export DIE=0
	export VERBOSE="${VERBOSE:-0}"
	export STAGE_NO=0
	export STEP_NO=0
	export STAGE_NAME=""
	[ $((VERBOSE)) -eq 1 ] && STAGE_NAME="init"
	verbose "Begin: op_test.sh"
	stage

	FIRST_RUN=1
	ERSA_OUT="${ERSA_OUT:-0}"
	CUSTOM_VARS="${CUSTOM_VARS:-1}"
	SAVE_PKI="${SAVE_PKI:-0}"
	UNSIGNED_PKI="${UNSIGNED_PKI:-1}"
	CUSTOM_OPTS="${CUSTOM_OPTS:-0}"
	BROKEN_PKI="${BROKEN_PKI:-0}"
	DELIBERATE_ERROR="${DELIBERATE_ERROR:-0}"
	SYS_SSL_ENABLE="${SYS_SSL_ENABLE:-1}"
	export OPENSSL_ENABLE="${OPENSSL_ENABLE:-0}"
	export OPENSSL_BUILD="${LIBRESSL_BUILD:-0}"
	export OPENSSL_VERSION="${LIBRESSL_VERSION:-2.8.3}"
	export OSSL_LIBB="${OSSL_LIBB:-"$ROOT_DIR/openssl/openssl-dev/bin/openssl"}"
	export LIBRESSL_ENABLE="${LIBRESSL_ENABLE:-0}"
	export LIBRESSL_BUILD="${LIBRESSL_BUILD:-0}"
	export LIBRESSL_VERSION="${LIBRESSL_VERSION:-2.8.3}"
	export LSSL_LIBB="${LSSL_LIBB:-"$ROOT_DIR/libressl/usr/local/bin/openssl"}"
	export SC_ENABLE="${SC_ENABLE:-0}"
	export SC_VERSION="${SC_VERSION:-latest}"
	export SC_DOWNLOAD="${SC_DOWNLOAD:-0}"
	export SC_OUT="${SC_OUT:-0}"
	verbose "Operating variables"
# ="${:-}"

	IFS=' '
	verbose "IFS=' '"

	# Only required for
	# https://github.com/OpenVPN/easy-rsa/pull/278
	[ $((CUSTOM_OPTS)) -eq 1 ] && export CUSTOM_OPTION="These_options_are_not_within_the_scope_of_easyrsa"
	[ $((CUSTOM_OPTS)) -eq 1 ] && verbose "export CUSTOM_OPTION=\"These_options_are_not_within_the_scope_of_easyrsa\""
	[ $((CUSTOM_OPTS)) -eq 1 ] && export LIBRESSL_ENABLE=0 && warn "Libressl test disabled for CUSTOM_OPTS"

	unstage
}

setup ()
{
	[ $((VERBOSE)) -eq 1 ] && STAGE_NAME="setup"
	stage

	STEP_NAME="cd easyrsa3"
	step
	[ -d easyrsa3 ] && cd easyrsa3
	verbose "PASS: $STEP_NAME -- Working dir: $(pwd)"

	destroy_data

	STEP_NAME="Create custom vars"
	step
	if [ $((CUSTOM_VARS)) -eq 1 ]
	then
		cp vars.example vars || DIE=1 die "cp vars.example vars"
		create_vars >> vars || DIE=1 die "create_vars"
		verbose "PASS: $STEP_NAME"
	else
		disabled "$STEP_NAME"
	fi

	STEP_NAME="Add custom options to openssl-easyrsa.cnf"
	step
	if [ $((CUSTOM_OPTS)) -eq 1 ]
	then
		[ -f ./openssl-easyrsa.cnf ] || DIE=1 die "Cannot find ./openssl-easyrsa.cnf"
		cp ./openssl-easyrsa.cnf ./openssl-easyrsa.cnf.orig || DIE=1 die "Cannot copy ./openssl-easyrsa.cnf"
		echo "custom_option = \$ENV::CUSTOM_OPTION" >> ./openssl-easyrsa.cnf
		verbose "PASS: $STEP_NAME"
	else
		disabled "$STEP_NAME"
	fi

	STEP_NAME="Create sample requests for import/sign"
	step
	if [ $((UNSIGNED_PKI)) -eq 1 ]
	then
		NEW_PKI="pki-req"
		DIE=1 create_req
		mv "$NEW_PKI" "pki-bkp" || DIE=1 die "Failed to create backup of sample PKI"
		verbose "PASS: $STEP_NAME"
	else
		disabled "$STEP_NAME"
	fi

	unstage
}

destroy_data ()
{
	STEP_NAME="Destroy test data"
	if [ $((SAVE_PKI)) -ne 1 ] || [ $(( FIRST_RUN )) -eq 1 ]
	then
		for i in vars pki-req pki-bkp pki-dssl pki-ossl pki-lssl pki-empty pki-error
		do
			rm -rf "$i" # && verbose "Destroyed: $i"
		done
		[ -f ./openssl-easyrsa.cnf.orig ] && mv -f ./openssl-easyrsa.cnf.orig ./openssl-easyrsa.cnf
		verbose "$STEP_NAME"
	else
		disabled "$STEP_NAME"
	fi
	FIRST_RUN=0
}

tear_down ()
{
	[ $((VERBOSE)) -eq 1 ] && STAGE_NAME="Tear down"
	stage

	unset IFS
	destroy_data
	unstage
}

create_vars ()
{
	echo ' set_var EASYRSA_DN "org"'
	echo '# Unsupported characters:'
	echo '# `'
	echo '# $'
	echo '# "'
	echo "# '"
	echo '# #'
	echo '# & (Win)'
	echo ' set_var EASYRSA_REQ_COUNTRY   "00"'
	echo ' set_var EASYRSA_REQ_PROVINCE  "test"'
	echo ' set_var EASYRSA_REQ_CITY      "TEST ,./<>  ?;:@~  []!%^  *()-=  _+| (23) TEST"'
	echo ' set_var EASYRSA_REQ_ORG       "example.org"'
	echo ' set_var EASYRSA_REQ_EMAIL     "me@example.net"'
	echo ' set_var EASYRSA_REQ_OU        "TEST esc \{ \} \£ \¬ (4) TEST"'
}

create_req ()
{
	export EASYRSA_PKI="$PWD/$NEW_PKI"
	SAVE_STEP="$STEP_NAME"

	STEP_NAME="./easyrsa init-pki"
	action

	export EASYRSA_REQ_CN="maximilian"
	STEP_NAME="./easyrsa --batch build-ca nopass subca"
	action
	[ -f "$EASYRSA_PKI/reqs/ca.req" ] && REQ_subca="$EASYRSA_PKI/reqs/ca.req"

	export EASYRSA_REQ_CN="specter"
	STEP_NAME="./easyrsa --batch gen-req $EASYRSA_REQ_CN nopass"
	action
	[ -f "$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req" ] && REQ_server="$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req"

	export EASYRSA_REQ_CN="meltdown"
	STEP_NAME="./easyrsa --batch gen-req $EASYRSA_REQ_CN nopass"
	action
	[ -f "$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req" ] && REQ_client="$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req"

	export EASYRSA_REQ_CN="heartbleed"
	STEP_NAME="./easyrsa --batch gen-req $EASYRSA_REQ_CN nopass"
	action
	[ -f "$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req" ] && REQ_serverClient="$EASYRSA_PKI/reqs/$EASYRSA_REQ_CN.req"

	STEP_NAME="$SAVE_STEP"
	unset EASYRSA_REQ_CN
	STEP_NO=0
}

restore_req ()
{
	verbose "Restore sample requests for re-use with $NEW_PKI"
	rm -rf "pki-req"
	cp -Rf "pki-bkp" "pki-req" || DIE=1 die "Failed to restore backup of sample PKI"
}

import_sign_subca ()
{
	REQ_type="ca"
	STEP_NAME="./easyrsa import-req $REQ_subca $REQ_name"
	step
	action
	STEP_NAME="./easyrsa --batch sign-req $REQ_type $REQ_name nopass"
	step
	action
}

move_show_subca ()
{
	STEP_NAME="mv -vf "$EASYRSA_PKI/issued/$REQ_name.crt" "$PWD/pki-req/ca.crt" "
	step
	action

	STEP_NAME="./easyrsa show-ca"
	step
	export EASYRSA_PKI="$PWD/pki-req"
	action
}

action ()
{
	if [ $((ERSA_OUT)) -eq 1 ]
	then
		verbose "$STEP_NAME"
		$STEP_NAME || die "$STEP_NAME"
	else
		$STEP_NAME >/dev/null 2>&1 || die "$STEP_NAME"
		#$STEP_NAME || die "$STEP_NAME"
	fi
	verbose "OK"
}

init_pki ()
{
	STEP_NAME="./easyrsa init-pki"
	step
	action
}

build_ca ()
{
	STEP_NAME="./easyrsa --batch build-ca nopass"
	export EASYRSA_REQ_CN="penelope"
	step
	action
	unset EASYRSA_REQ_CN
}

show_ca ()
{
	STEP_NAME="./easyrsa show-ca"
	step
	action
}

build_full ()
{
	STEP_NAME="./easyrsa --batch build-$REQ_type-full $REQ_name nopass"
	step
	action
}

build_san_full ()
{
	STEP_NAME="./easyrsa --subject-alt-name=IP:10.0.0.1 build-server-full $REQ_name nopass"
	step
	action
}

import_req ()
{
	case "$REQ_type" in
		server)			REQ_file="$REQ_server" ;;
		client)			REQ_file="$REQ_client" ;;
		serverClient)	REQ_file="$REQ_serverClient";;
		*) 				DIE=1 die "Unknown certificate type $REQ_type" ;;
	esac

	STEP_NAME="./easyrsa import-req $REQ_file $REQ_name"
	step
	action
}

sign_req ()
{
	STEP_NAME="./easyrsa --batch sign-req $REQ_type $REQ_name nopass"
	step
	action
}

show_cert ()
{
	STEP_NAME="./easyrsa show-cert $REQ_name"
	step
	action
}

revoke_cert ()
{
	STEP_NAME="./easyrsa --batch revoke $REQ_name"
	CAT_THIS="$EASYRSA_PKI/index.txt"
	step
	CAT_THIS="$EASYRSA_PKI/index.txt"
	cat_file
	action
	cat_file
}

gen_crl ()
{
	STEP_NAME="./easyrsa gen-crl"
	step
	action
	CAT_THIS="$EASYRSA_PKI/crl.pem"
	cat_file
}

cat_file ()
{
	[ $((ERSA_OUT)) -eq 1 ] || return 0
	verbose
	verbose "cat $CAT_THIS"
	verbose
	[ -f "$CAT_THIS" ] || die "cat $CAT_THIS"
	[ $((VERBOSE)) -eq 1 ] && cat "$CAT_THIS"
	verbose
}

create_pki ()
{
	stage
	restore_req

	export EASYRSA_PKI="$PWD/$NEW_PKI"

	if [ "$NEW_PKI" = "pki-empty" ] || [ "$NEW_PKI" = "pki-error" ]
	then
		verbose "OMITTING init-pki"
	else
		init_pki
	fi

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
	REQ_name="heartbleed"
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

	REQ_type="client"
	REQ_name="meltdown"
	import_req
	sign_req
	show_cert
	revoke_cert

	gen_crl

	REQ_name="maximilian"
	import_sign_subca
	move_show_subca

	verbose "Change PKI to $PWD/pki-req"
	export EASYRSA_PKI="$PWD/pki-req"

	REQ_type="server"
	REQ_name="specter"
	STEP_NAME="./easyrsa sign-req $REQ_name"
	sign_req
	show_cert
	revoke_cert

	REQ_type="client"
	REQ_name="meltdown"
	STEP_NAME="./easyrsa sign-req $REQ_name"
	sign_req
	show_cert
	revoke_cert

	REQ_type="serverClient"
	REQ_name="heartbleed"
	sign_req
	show_cert
	revoke_cert

	gen_crl

	STEP_NO=0
	unset EASYRSA_PKI
	unstage
}

stage ()
{
	export STAGE_NO=$((STAGE_NO + 1))
	[ $((VERBOSE)) -ne 1 ] && return 0
	echo "=="
	echo "||================================================================================"
	echo "||==== STAGE ($STAGE_NO): $STAGE_NAME"
	echo "||"
}

unstage ()
{
	[ $((VERBOSE)) -ne 1 ] && unset STAGE_NAME && return 0
	echo "||"
	echo "||==== COMPLETE ($STAGE_NO): $STAGE_NAME"
	echo "||================================================================================"
	echo "=="
	unset STAGE_NAME
}

step ()
{
	export STEP_NO=$((STEP_NO + 1))
	[ $((VERBOSE)) -ne 1 ] && return 0
	#echo "||"
	echo "||--------------------------------------------------------------------------------"
	echo "||-- STAGE ($STAGE_NO): $STAGE_NAME"
	echo "|| -- STEP ($STEP_NO): $STEP_NAME"
	#echo "||"
	#echo
	# Don't use this:
	#unset STEP_NAME
}

verbose ()
{
	[ $((VERBOSE)) -eq 1 ] || return 0
	echo "|| ++ $1"
}

note ()
{
	# Currently not used
	echo "????? $1"
}

disabled ()
{
	[ $((VERBOSE)) -eq 1 ] || return 0
	echo "|| ++ DISABLED OPTION: $1"
}

warn ()
{
	echo "***** $1"
}

die ()
{
	{ [ $((VERBOSE)) -eq 1 ] || [ $DIE -eq 1 ]; } && warn "$0 FATAL ERROR! exit 1: $1"
	[ $DIE -eq 1 ] && tear_down && exit 1
	[ $((VERBOSE)) -eq 1 ] && warn "Ignored .."
	return 0
}


######################################

	for i in $1
	do
		case $i in
			-u)		usage ;;
			-v)		VERBOSE=1 ;;
			-vv)	ERSA_OUT=1; VERBOSE=1 ;;
			-b)		BROKEN_PKI=1; SYS_SSL_ENABLE=0; VERBOSE=1 ;;
			-l)		ERSA_OUT=1; LIBRESSL_ENABLE=1; SYS_SSL_ENABLE=0; VERBOSE=1 ;;
			-o)		ERSA_OUT=1; OPENSSL_ENABLE=1; SYS_SSL_ENABLE=0; VERBOSE=1 ;;
			-s)		SC_OUT=1; SC_ENABLE=1; VERBOSE=1 ;;
			-f) 	ERSA_OUT=1; OPENSSL_ENABLE=1; LIBRESSL_ENABLE=1; SC_OUT=1; SC_ENABLE=1; VERBOSE=1 ;;
			*)		DIE=1 die "Unknown option: $i" ;;
		esac
	done

	init

	[ -f openssl/openssl.sh ] || export OPENSSL_ENABLE=0
	[ $((OPENSSL_ENABLE)) -eq 1 ] && DIE=1 openssl/openssl.sh

	[ -f libressl/libressl.sh ] || export LIBRESSL_ENABLE=0
	[ $((LIBRESSL_ENABLE)) -eq 1 ] && DIE=1 libressl/libressl.sh

	[ -f shellcheck/shellcheck.sh ] || export SC_ENABLE=0
	[ $((SC_ENABLE)) -eq 1 ] && DIE=1 shellcheck/shellcheck.sh

	setup

	STAGE_NAME="Default ssl"
	if [ $((SYS_SSL_ENABLE)) -eq 1 ]
	then
		NEW_PKI="pki-dssl"
		DIE=1 create_pki
	else
		disabled "$STAGE_NAME"
	fi

	STAGE_NAME="openssl"
	if [ $((OPENSSL_ENABLE)) -eq 1 ]
	then
		[ -f "$OSSL_LIBB" ] || DIE=1 die "$0: missing openssl: $OSSL_LIBB"
		export EASYRSA_OPENSSL="$OSSL_LIBB"
		NEW_PKI="pki-ossl"
		DIE=1 create_pki
		unset EASYRSA_OPENSSL
	else
		disabled "$STAGE_NAME"
	fi

	STAGE_NAME="libressl"
	if [ $((LIBRESSL_ENABLE)) -eq 1 ]
	then
		[ -f "$LSSL_LIBB" ] || DIE=1 die "$0: missing libressl: $LSSL_LIBB"
		export EASYRSA_OPENSSL="$LSSL_LIBB"
		NEW_PKI="pki-lssl"
		DIE=1 create_pki
		unset EASYRSA_OPENSSL
	else
		disabled "$STAGE_NAME"
	fi

	STAGE_NAME="Common errors (Does *not* die on errors)"
	if [ $((BROKEN_PKI)) -eq 1 ]
	then
		NEW_PKI="pki-empty"
			#restore_req
		DIE=0 create_pki
	else
		disabled "$STAGE_NAME"
	fi

	STAGE_NAME="Common errors (*Does* die on errors)"
	if [ $((DELIBERATE_ERROR)) -eq 1 ]
	then
		NEW_PKI="pki-error"
		DIE=1 create_pki
	else
		disabled "$STAGE_NAME."
	fi

	tear_down

#./op_test.sh -u

verbose "Complete, cumulative errors: $((Errors))"
exit $((Errors))

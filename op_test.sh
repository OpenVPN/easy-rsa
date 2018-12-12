#!/bin/sh

# Runs some basic operational testing

cd easyrsa3 || exit 1
echo "===> Init-PKI"
sh -x easyrsa init-pki
echo "===> Build-CA"
sh -x easyrsa --batch build-ca nopass
echo "===> Build-Server"
sh -x easyrsa --batch build-server full s01 nopass
sh -x easyrsa show-cert s01
echo "===> Build-Client"
sh -x easyrsa --batch build-client-full c01 nopass
sh -x easyrsa show-cert c01

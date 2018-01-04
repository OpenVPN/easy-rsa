#!/bin/sh

# Runs some basic operational testing

cd easyrsa3 || exit 1
sh -x easyrsa init-pki

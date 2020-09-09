Easy-RSA Advanced Reference
=============================

This is a technical reference for advanced users familiar with PKI processes. If
you need a more detailed description, see the `EasyRSA-Readme` or `Intro-To-PKI`
docs instead.

Configuration Reference
-----------------------

#### Configuration Sources

  There are 3 possible ways to perform external configuration of Easy-RSA,
  selected in the following order where the first defined result wins:

  1. Command-line option
  2. Environmental variable
  3. 'vars' file, if one is present (see `vars Autodetection` below)
  4. Built-in default

  Note that not every possible config option can be set everywhere, although any
  env-var can be added to the 'vars' file even if it's not shown by default.

#### vars Autodetection

  A 'vars' file is a file named simply `vars` (without an extension) that
  Easy-RSA will source for configuration. This file is specifically designed
  *not* to replace variables that have been set with a higher-priority method
  such as CLI opts or env-vars.

  The following locations are checked, in this order, for a vars file. Only the
  first one found is used:

  1. The file referenced by the `--vars` CLI option
  2. The file referenced by the env-var named `EASYRSA_VARS_FILE`
  3. The directory referenced by the `EASYRSA_PKI` env-var
  4. The default PKI directory at `$PWD/pki`
  4. The directory referenced by the `EASYRSA` env-var
  5. The directory containing the easyrsa program

  Defining the env-var `EASYRSA_NO_VARS` will override the sourcing of the vars
  file in all cases, including defining it subsequently as a global option.

#### OpenSSL Config

  Easy-RSA is tightly coupled to the OpenSSL config file (.cnf) for the
  flexibility the script provides. It is required that this file be available,
  yet it is possible to use a different OpenSSL config file for a particular
  PKI, or even change it for a particular invocation.

  The OpenSSL config file is searched for in the following order:

  1. The env-var `EASYRSA_SSL_CONF`
  2. The 'vars' file (see `vars Autodetection` above)
  3. The `EASYRSA_PKI` directory with a filename of `openssl-easyrsa.cnf`
  4. The `EASYRSA` directory with a filename of `openssl-easyrsa.cnf`

Advanced extension handling
---------------------------

Normally the cert extensions are selected by the cert type given on the CLI
during signing; this causes the matching file in the x509-types subdirectory to
be processed for OpenSSL extensions to add. This can be overridden in a
particular PKI by placing another x509-types dir inside the `EASYRSA_PKI` dir
which will be used instead.

The file named `COMMON` in the x509-types dir is appended to every cert type;
this is designed for CDP usage, but can be used for any extension that should
apply to every signed cert.

Additionally, the contents of the env-var `EASYRSA_EXTRA_EXTS` is appended with
its raw text added to the OpenSSL extensions. The contents are appended as-is to
the cert extensions; invalid OpenSSL configs will usually result in failure.

Environmental Variables Reference
---------------------------------

A list of env-vars, any matching global option (CLI) to set/override it, and a
possible terse description is shown below:

 *  `EASYRSA` - should point to the Easy-RSA top-level dir, where the easyrsa
    script is located.
 *  `EASYRSA_OPENSSL` - command to invoke openssl
 *  `EASYRSA_SSL_CONF` - the openssl config file to use
 *  `EASYRSA_PKI` (CLI: `--pki-dir`) - dir to use to hold all PKI-specific
    files, defaults to `$PWD/pki`.
 *  `EASYRSA_DN` (CLI: `--dn-mode`) - set to the string `cn_only` or `org` to
    alter the fields to include in the req DN
 *  `EASYRSA_REQ_COUNTRY` (CLI: `--req-c`) - set the DN country with org mode
 *  `EASYRSA_REQ_PROVINCE` (CLI: `--req-st`) - set the DN state/province with
    org mode
 *  `EASYRSA_REQ_CITY` (CLI: `--req-city`) - set the DN city/locality with org
    mode
 *  `EASYRSA_REQ_ORG` (CLI: `--req-org`) - set the DN organization with org mode
 *  `EASYRSA_REQ_EMAIL` (CLI: `--req-email`) - set the DN email with org mode
 *  `EASYRSA_REQ_OU` (CLI: `--req-ou`) - set the DN organizational unit with org
    mode
 *  `EASYRSA_KEY_SIZE` (CLI: `--key-size`) - set the key size in bits to
    generate
 *  `EASYRSA_ALGO` (CLI: `--use-algo`) - set the crypto alg to use: rsa or ec
 *  `EASYRSA_CURVE` (CLI: `--curve`) - define the named EC curve to use
 *  `EASYRSA_EC_DIR` - dir to store generated ecparams
 *  `EASYRSA_CA_EXPIRE` (CLI: `--days`) - set the CA expiration time in days
 *  `EASYRSA_CERT_EXPIRE` (CLI: `--days`) - set the issued cert expiration time
    in days
 *  `EASYRSA_CRL_DAYS` (CLI: `--days`) - set the CRL 'next publish' time in days
 *  `EASYRSA_NS_SUPPORT` (CLI: `--ns-cert`) - string 'yes' or 'no' fields to
    include the deprecated Netscape extensions
 *  `EASYRSA_NS_COMMENT` (CLI: `--ns-comment`) - string comment to include when
    using the deprecated Netscape extensions
 *  `EASYRSA_TEMP_FILE` - a temp file to use when dynamically creating req/cert
    extensions
 *  `EASYRSA_REQ_CN` (CLI: `--req-cn`) - default CN, necessary to set in BATCH
    mode
 *  `EASYRSA_DIGEST` (CLI: `--digest`) - set a hash digest to use for req/cert
    signing
 *  `EASYRSA_BATCH` (CLI: `--batch`) - enable batch (no-prompt) mode; set
    env-var to non-zero string to enable (CLI takes no options)
 *  `EASYRSA_PASSIN` (CLI: `--passin`) - allows to specify a source for
    password using any openssl password options like pass:1234 or env:var
 *  `EASYRSA_PASSOUT` (CLI: `--passout`) - allows to specify a source for
    password using any openssl password options like pass:1234 or env:var
    
**NOTE:** the global options need to be provided before the actual commands.

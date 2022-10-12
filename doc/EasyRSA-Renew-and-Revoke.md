Easy-RSA 3 Certificate Renewal and Revocation Documentation
===========================================================

This document explains how the **differing versions** of Easy-RSA 3 work
with Renewal and Revocation of Certificates and Private keys.

Thanks to _good luck_, _hard work_ and _co-operation_, these version dependent
differences have been _smoothed-over_. Since version `3.1.1`, Easy-RSA has the
tools required to renew and/or revoke all verified and Valid certifiicates.

**UPDATE**:
The changes noted for Easy-RSA version 3.1.2 have all been included with
Easy-RSA version 3.1.1 - See https://github.com/OpenVPN/easy-rsa/pull/688

Command Details: `renew`
------------------------

    easyrsa renew file-name-base [ cmd-opts ]

`renew` is **only** available since Easy-RSA version `3.0.6`

#### `renew` has three different versions:

 *  `renew` **Version 1**: Easy-RSA version `3.0.6`, `3.0.7` and `3.0.8`.
    - Both certificate and private key are rebuilt.
    - Once a certificate has been renewed it **cannot** be revoked.

 *  `renew` **Version 2**: Easy-RSA version `3.0.9` and `3.1.0`.
    - Both certificate and private key are rebuilt.
    - Once a certificate has been renewed it **can** be revoked.
    - Use command:

        `revoke-renewed file-name-base [ reason ]`

 *  `renew` **Version 3**: Easy-RSA version `3.1.1+`.
    - Only certificate is renewed.
    - The original `renew` command has been renamed to `rebuild`, which
      rebuilds both certificate and private key.


Resolving issues with `renew` version 1
---------------------------------------

#### Upgrade Easy-RSA to version `3.1.1+` is required.

`renew` version 1 **rebuilds** the certificate and private key.

Once a certificate has been renewed by version 1, the files are saved in the
`renewed/` storage area by `serialNumber`. These files must be recovered by
using command:

    easyrsa rewind-renew serialNumber

Command `rewind-renew` is available since Easy-RSA version `3.1.1`

Once `rewind-renew` has recovered the files, the certificate can be revoked:

    easyrsa revoke-renewed file-name-base [ reason ]


Using `renew` version 2
-----------------------

#### Upgrade Easy-RSA to version `3.1.1+` is required.

`renew` version 2 **rebuilds** the certificate and private key.

Renewed certificate can be revoked:

    easyrsa revoke-renewed file-name-base [ reason ]


Using `renew` version 3
-----------------------

#### Upgrade Easy-RSA to version `3.1.1+` is required.

`renew` version 3 **renews** the certificate only.

Renewed certificate can be revoked:

    easyrsa revoke-renewed file-name-base [ reason ]

This is the preferred method to renew a certificate because the original
private key is still valid.

`renew` version 3 is **only** available since Easy-RSA version `3.1.1+`.


Easy-RSA Reporting tools for certificate status
-----------------------------------------------

Easy-RSA version `3.1.x`, also has the following tools to keep track of
certificate staus:

    easyrsa [ --days=# ] show-expire [ file-name-base ]

  `show-expire` shows all certificates which will expire in given `--days`.

    easyrsa show-renew [ file-name-base ]

  `show-renew` shows all certificates which have been renewed, where the old
  certificate has not been revoked.

    easyrsa show-revoke [ file-name-base ]

  `show-revoke` shows all certificates which have been revoked.


Reason codes available for revoke commands
------------------------------------------

The follow is an exhaustive list of available `reason` codes:
- `unspecified`
- `keyCompromise`
- `CACompromise`
- `affiliationChanged`
- `superseded`
- `cessationOfOperation`
- `certificateHold`

  `reason` must be one of these codes, otherwise not be used.


About command `rebuild`
-----------------------

If `rebuild` is used then the output directory of old certificate, key and
request is also the `renewed` directory.  Use **`revoke-renewed`** to revoke
an old certificate/key pair, which has been _rebuilt_ by command `rebuild`.

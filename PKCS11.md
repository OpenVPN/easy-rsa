PKCS#11 support for EasyRSA
============================

OpenSSL only ever operates on one key at time for any given command.  Leveraging this fact we can
provide support for private keys stored in PKCS#11 tokens with a relatively simple configuration.
In order to use this capability, you must install the OpenSSL PKCS#11 engine for you operating system.  

This version of the capability does not persist your PIN number automatically.  If you would like to do
this and are aware of the security implications of doing so, see the end of this document.

To build the CA on a token use the `pkcs11` parameter when calling `build-ca`.  If desired you can also use the `subca` command.  The following environment variables can be used and they have equivalant command line
arguments.

Environment Variables

* `PKCS11_MODULE` - The pkcs module to load
* `PKCS11_SLOT` - The slot to load objects from
* `PKCS11_PINPAD` -  Boolean, set to `true` to enable pin entry directly from PINPAD reader.
* `PKCS11_PIN` - *INSECURE* useful for testing and automatically logs the user in
* `PKCS11_LABEL` - The label of the key to use.  (Not de-duplicated!!)

Once you've created your CA, `./pki/private/ca.key` will not be a normal PEM key file.  Instead it will look
like the following:

```bash
# EasyRSA variables pointing to the private key object
PKCS11_MODULE_PATH=/usr/lib/libsofthsm2.so
PKCS11_SLOT=0x23aa5c05
PKCS11_LABEL=Fancy-SoftHSM-CA
```

If desired you can also include the `PKCS11_PIN` variable.  Note: This is a big risk for sensitive keys but very useful for automation.

Now all operations for that CA operate on the token and the only extra interaction will be entering the token PIN.

Smartcard HSM - Nitrokey HSM
----------------------------
0. Required settings:
```
set_var PKCS11_SLOT	"0x0"
```
1. Initialize the token. Choose one option:
    - Simple initialization: (No DKEK shares, meaning no possibility to export a backup)
    ```bash
    #Initialize the token
    sc-hsm-tool --initialize
    ```
    - Initialization with DKEK share(s): (Enable to export encrypted backup --> more info)
    ```bash
    # Generate DKEK share
    sc-hsm-tool --create-dkek-share dkek-share-1.pbe
    # Initialize the token with 1 DKEK share
    sc-hsm-tool --initialize --dkek-shares 1
    # Import your DKEK share
    sc-hsm-tool --import-dkek-share dkek-share-1.pbe
    ```
2. Build the CA
```bash
easyrsa build-ca pkcs11
```

SoftHSM2
--------

Initialize a token

`softhsm2-util --init-token --free --label test-token --so-pin 123456 --pin 1234`

Build the CA

`easyrsa build-ca pkcs11`

You'll be asked for the slot which isn't going to be the slot number used when initializing the token, instead it's a longer 32 bit hexidecimal number like `0x23aa5c05` as you see in the example above.

YubiKey
-----------

TODO: Add instructions for hosting a CA on the YubiKey

Notes
-----

* EasyRSA creates a CA and creation is the perfect time to define everything we need to point to the key on the token
* OpenSSL should be able to do all key operations on PKCS#11 but not all algorithms will be available with each token.  Good error messages will be important for debugging.

TODO
----

* [x] Create a self signed CA on a token
* [x] Create a CA CSR with a key on a token
* [x] Sign a server certificate
* [x] Sign a client certificate
* [x] Revoke a certificate
* [x] Renew a certificate
* [x] Get PKCS11 module information from key file (if configured)
* [ ] Add extra `pkcs11-tool` arguments to support different implementation (i.i Yubikeys' need for `--login-type so`)
* [ ] If a key is being created on a device, ensure the label isn't already used by the same type of key
* [ ] Add check to ensure openssl pkcs11 engine is installed and library able to be found.
* [ ] Create command to extract a certificate from a key and bootstrap a new CA (maybe ask the user if that is what they want if the slot has everything that is needed)

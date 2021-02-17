PKCS#11 support for EasyRSA
============================

OpenSSL only ever operates on one key at time for any given command. Leveraging this fact we can provide support for private keys stored in PKCS#11 tokens with a relatively simple configuration.
In order to use this capability, you must install the OpenSSL PKCS#11 engine for you operating system.  

This version of the capability does not persist your PIN number automatically.  If you would like to do this and are aware of the security implications of doing so, see the end of this document.

To build the CA on a token use the `pkcs11` parameter when calling `build-ca`.  If desired you can also use the `subca` command.  The following environment variables can be used and they have equivalant command line arguments.

Environment Variables

* `PKCS11_MODULE_PATH` - The pkcs module to load
* `PKCS11_SLOT` - The slot to load objects from
* `PKCS11_PINPAD` -  Boolean, set to `true` to enable pin entry directly from PINPAD reader.
* `PKCS11_PIN` - *INSECURE* useful for testing and automatically logs the user in
* `PKCS11_LABEL` - The label of the key to use.  (Not de-duplicated!!)
* `PKCS11_EXTRA_OPTIONS` - Extra options for `pkcs11-tool` (i.e. `--id` for Yubikeys). *Use with caution!*
* `PKCS11_REQUIRE_SOPIN` - Boolean, set to `true` for devices which require SO PIN login to generate keypairs (i.e. Yubikeys)
*  `PKCS11_SO_PIN` - *HIGLY INSECURE* useful for testing,  automatically logs the SO user in.

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
set_var PKCS11_MODULE_PATH "path/to/opensc-pkcs11.so"
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

YubiKey (4, 5)
-----------
The following guide has been adapted from [Yubico Dev Pages](https://developers.yubico.com/yubico-piv-tool/YKCS11/Supported_applications/pkcs11tool.html). It was tested on Yubikey 5 NFC, but should work on other models as well.

Following Yubikey's [PIV Certificate slots description](https://developers.yubico.com/PIV/Introduction/Certificate_slots.html), I would suggest using slot `9c` (id: `2`, label: `Private key for Digital Signature`) to store your CA keys.

Other slots requiring PIN should be valid, too. Nonetheless, take into account necessary id and label changes. Object labels for Yubikey's slots are fixed, so check [Key Alias per Slot and Object Type](https://developers.yubico.com/yubico-piv-tool/YKCS11/Functions_and_values.html) section and change it accordingly.



0. Required settings:
```bash
set_var PKCS11_SLOT	"0x0"
set_var PKCS11_MODULE_PATH	"path/to/libykcs11.so"
set_var PKCS11_LABEL	"Private key for Digital Signature"
set_var PKCS11_EXTRA_OPTIONS	"--id 2"
set_var PKCS11_REQUIRE_SOPIN true
# WARNING: Following settings are for test purpose only.
# Writing PIN and SO PIN to config is highly discouraged for security reasons.
set_var PKCS11_SO_PIN "010203040506070801020304050607080102030405060708"
set_var PKCS11_PIN 123456
```

1. Initialize the key, changing PIN and SO PIN.

2. Build CA
```bash
easyrsa build-ca pkcs11
```
Note: Yubikeys might require a second PIN entry during signing operations, even when `PKCS11_PIN` var is set.

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
* [x] Add SO login and extra options support for different implementations (i.e. Yubikey)
* [ ] Test support with Nitrokeys
* [ ] If a key is being created on a device, ensure the label isn't already used by the same type of key
* [ ] Add check to ensure openssl pkcs11 engine is installed and library able to be found.
* [ ] Create command to extract a certificate from a key and bootstrap a new CA (maybe ask the user if that is what they want if the slot has everything that is needed)

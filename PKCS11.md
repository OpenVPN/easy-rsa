PKCS#11 support for EasyRSA
============================

OpenSSL only ever operates on one key at time for any given command. Leveraging this fact we can provide support for private keys stored in PKCS#11 tokens with a relatively simple configuration.
In order to use this capability, you must install the OpenSSL PKCS#11 engine for you operating system.  

This version of the capability does not persist your PIN number automatically.  If you would like to do this and are aware of the security implications of doing so, see the end of this document.

To build the CA on a token use the `pkcs11` parameter when calling `build-ca`.  If desired you can also use the `subca` command.  The following environment variables can be used and they have equivalant command line arguments.

Environment Variables

* `PKCS11_MODULE_PATH` (Required) - The pkcs module to load.
* `PKCS11_TOKEN_URI` (Required) - The PKCS11 token URI to load objects from  (according to [RFC 7512](https://tools.ietf.org/html/rfc7512)).

  **Important**: terminate it with a `;`.
  Check below examples for various commercial tokens, otherwise verify its value by checking the output of `p11tool --list-tokens` command (you might need to install gnutls-bin package).
* `PKCS11_SLOT` (Required) - The Slot ID (in hex) to be used for key storage and certificate signing.

  **Important**: Format is a sequence of an even number of hex character, without leading `0x`. (i.e. Valid examples: `01`,`012A`,`123A`; Invalid examples: `1`,`0x1`, `123`)
* `PKCS11_PINPAD` (Optional) -  Boolean, set to `true` to enable pin entry directly from PINPAD reader.
* `PKCS11_LABEL` - The label of the key to use.  (Not de-duplicated!!)
* `PKCS11_EXTRA_OPTIONS` (Optional) - *Use with caution!* Extra options for `pkcs11-tool` (might be useful for non-standard implementation).
* `PKCS11_REQUIRE_SOPIN` (Optional) - Boolean, set to `true` for devices which require SO PIN login to generate keypairs (i.e. Yubikeys)
* `PKCS11_PIN` (Test/Automation only - *INSECURE*)-  useful for testing and automatically logs the user in
*  `PKCS11_SO_PIN` (Test/Automation only - *HIGHLY INSECURE*) -  useful for testing,  automatically logs the SO user in.

Once you've created your CA, `./pki/private/ca.key` will not be a normal PEM key file.  Instead it will look like the following:

```bash
# EasyRSA variables pointing to the private key object
PKCS11_MODULE_PATH=/usr/lib/libsofthsm2.so
PKCS11_TOKEN_URI="pkcs11:model=SoftHSM%20v2;manufacturer=SoftHSM%20project;serial=bcc3ef4e731fb246;token=test-token;"
PKCS11_SLOT=0x23aa5c05
PKCS11_LABEL=Fancy-SoftHSM-CA
```

If desired you can also include the `PKCS11_PIN` variable.  Note: This is a big risk for sensitive keys but very useful for automation.

Now all operations for that CA operate on the token and the only extra interaction will be entering the token PIN.

Nitrokey HSM - Smartcard HSM
----------------------------
 The [SmartCard-HSM](https://www.smartcard-hsm.com/) is a lightweight hardware security module in a smart card form factor.
 The [Nitrokey HSM](https://www.nitrokey.com/#comparison) is a lightweight hardware security module in a USB key form factor containing the SmartCard-HSM. The [SmartCard-HSM](https://www.smartcard-hsm.com/#comparison) is available as USB key, ID-1 card with contact/contactless interface, as ID-000 plug-in and MicroSD card. Both are 100% compatible and provide a remote-manageable secure key store for RSA and ECC keys.
(Adapted from [OpenSC Wiki](https://github.com/OpenSC/OpenSC/wiki/SmartCardHSM)).
0. Initialize the token. Choose one option:
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
1. Required settings:
Set `PKCS11_TOKEN_URI` according to your device serial, choose `PKCS11_LABEL` and `PKCS11_SLOT`.
```bash
set_var PKCS11_MODULE_PATH	"path/to/opensc-pkcs11.so"
set_var PKCS11_TOKEN_URI	"pkcs11:model=PKCS%2315%20emulated;manufacturer=www.CardContact.de;serial=DENK0000000;token=SmartCard-HSM%20%28UserPIN%29%00%00%00%00%00%00%00%00%00;"
set_var PKCS11_LABEL	"test-CA-key"
set_var PKCS11_SLOT "123456"
# Only for testing & automation purpose.
# Never write your production PIN to file.
#set_var PKCS11_PIN 123456
```

2. Build the CA
```bash
easyrsa build-ca pkcs11
```

Nitrokey Pro
------------
[Nitrokey Pro](https://www.nitrokey.com/#comparison)is an open-source USB key used to enable the secure encryption and signing of data. Among other features, it provides two emulated PKCS15 card, one using OpenPGP and one Using S/MIME. It can store 3 keys (more specifically, one identity, 3 subkeys).

0. Initialize the token.
IMPORTANT: CA Keypair generation using `pkcs11-tool` on Nitrokey Pro only works if no keys are present on the device. You might need to factory reset it.
There is possibility to add a feature to EasyRSA in the future to enable signing CA certificate using existing keys from PKCS11 token (without keypair generation).

1. Required settings:
Set `PKCS11_TOKEN_URI` according to your device serial, choose `PKCS11_LABEL`.

  `PKCS11_SLOT` should not be changed.
```bash
set_var PKCS11_MODULE_PATH	"path/to/opensc-pkcs11.so"
set_var PKCS11_TOKEN_URI "pkcs11:model=PKCS%2315%20emulated;manufacturer=ZeitControl;serial=123456789123;token=OpenPGP%20card%20%28User%20PIN%20%28sig%29%29%00%00%00;"
set_var PKCS11_LABEL "test-CA-key"
set_var PKCS11_SLOT "01"
set_var PKCS11_REQUIRE_SOPIN true
# Only for testing & automation purpose.
# Never write your production PIN to file.
#set_var PKCS11_PIN 123456
#set_var PKCS11_SO_PIN "12345678"
```

2. Build the CA
```bash
easyrsa build-ca pkcs11
```

SoftHSM2
--------

[SoftHSM](https://www.opendnssec.org/softhsm/) is an implementation of a cryptographic store accessible through a PKCS #11 interface. You can use it to explore PKCS #11 without having a Hardware Security Module. It is being developed as a part of the OpenDNSSEC project. SoftHSM uses Botan for its cryptographic operations. (Adapted from [OpenDNSSEC wiki](https://www.opendnssec.org/softhsm/))

0. Initialize a token
`softhsm2-util --init-token --free --label my-test-token --so-pin 123456 --pin 1234`

1. Required settings:
Set `PKCS11_TOKEN_URI` according to your device serial, choose `PKCS11_LABEL` and `PKCS11_SLOT`.
```bash
set_var PKCS11_MODULE_PATH "/usr/lib/softhsm/libsofthsm2.so"
set_var PKCS11_TOKEN_URI "pkcs11:model=SoftHSM%20v2;manufacturer=SoftHSM%20project;serial=f609a0b66832b468;token=my-test-token;"
set_var PKCS11_SLOT "01"
set_var PKCS11_LABEL "test-CA-key"
# Only for testing & automation purpose.
# Never write your production PIN to file.
#set_var PKCS11_PIN "1234"
```

2. Build the CA
```bash
easyrsa build-ca pkcs11
```


YubiKey
-----------
[Yubikey](https://www.yubico.com/products/) is a Hardware authentication device manufactured by [Yubico](https://www.yubico.com/).
The following guide has been adapted from [Yubico Dev Pages](https://developers.yubico.com/yubico-piv-tool/YKCS11/Supported_applications/pkcs11tool.html). It was tested on Yubikey 5 NFC, but should work on other models as well.

Following Yubikey's [PIV Certificate slots description](https://developers.yubico.com/PIV/Introduction/Certificate_slots.html), I would suggest using slot `9c` (`PKCS11_SLOT`: `02`, `PKCS11_LABEL`: `Private key for Digital Signature`) to store your CA keys.

I could not find a `PKCS11_TOKEN_URI` which is working apart from an empty one (`"pkcs11:"`), so please be do not connect other PKCS11 tokens during EasyRSA operation.

Other slots requiring PIN should be valid, too. Nonetheless, take into account necessary URI and label changes. Object labels for Yubikey's slots are fixed, so check [Key Alias per Slot and Object Type](https://developers.yubico.com/yubico-piv-tool/YKCS11/Functions_and_values.html) section and change it accordingly.



0. Initialize the key, changing PIN and SO PIN.

1. Required settings:
```bash
set_var PKCS11_MODULE_PATH	"path/to/libykcs11.so"
set_var PKCS11_LABEL	"Private key for Digital Signature"
set_var PKCS11_TOKEN_URI	"pkcs11:"
set_var PKCS11_SLOT "02"
set_var PKCS11_REQUIRE_SOPIN true
# Only for testing & automation purpose.
# Never write your production PIN to file.
#set_var PKCS11_SO_PIN "010203040506070801020304050607080102030405060708"
#set_var PKCS11_PIN 123456
```

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
* [x] Test support with Nitrokeys
* [ ] If a key is being created on a device, ensure the label isn't already used by the same type of key
* [ ] Add check to ensure openssl pkcs11 engine is installed and library able to be found.
* [ ] Create command to extract a certificate from a key and bootstrap a new CA (maybe ask the user if that is what they want if the slot has everything that is needed)

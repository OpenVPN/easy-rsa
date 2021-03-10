PKCS#11 support for EasyRSA
============================

OpenSSL only ever operates on one key at time for any given command. Leveraging this fact we can provide support for private keys stored in PKCS#11 tokens with a relatively simple configuration.

This version of the capability does not persist your PIN number automatically.  If you would like to do this and are aware of the security implications of doing so, see the end of this document.

Requirements
------------
In order to use this capability, you must install the OpenSSL PKCS#11 engine for you operating system as well as GnuTLS binaries (in particular, `p11tool`).
On an Ubuntu/Debian machine, you could achieve it running:
```sh
sudo apt-get install gnutls-bin libengine-pkcs11-openssl1.1
```


Configuration
-------------
The following environment variables can be used and they have equivalent command line arguments:

* `PKCS11_MODULE_PATH` (Required) - The pkcs module to load.
* `PKCS11_TOKEN_URI` (Required) - The PKCS11 token URI to load objects from  (according to [RFC 7512](https://tools.ietf.org/html/rfc7512)). It is a unique identifier of your token. If not specified, the program will list available ones in the system and prompt you for selection.

  Check below examples for various commercial tokens, otherwise verify its value by checking the output of `p11tool --list-tokens` command.
* `PKCS11_KEY_ID` (Required) - The Key CKA_ID (in hex) to be used for key storage and certificate signing.

  Public/Private keypair share the same CKA_ID.
When using pre-existing key from a token, you can check the ID value of the corresponding public key by running `pkcs11-tool -O|grep -A4 "Public Key Object"` (or from `p11tool --list-all <your PKCS11_TOKEN_URI here>`, modifying the format to remove all semicolons).

  **Important**: Format is a sequence of an even number of hex characters, without leading `0x`. (i.e. Valid examples: `01`,`012A`,`123A`; Invalid examples: `1`,`0x1`, `123`)

* `PKCS11_KEY_LABEL` - The label of the key to use.  
This is required for key generation.  
When using an existing key, the script uses it to check and warns of any label mismatch before proceeding. Depending on token type, it is generally NOT an unique identifier.
* `PKCS11_PINPAD` (Optional) -  Boolean, set to `true` to enable pin entry directly from PINPAD reader.

* `PKCS11_PIN` (Test/Automation only - *INSECURE*)-  useful for testing and automatically logs the user in.

The following extra option might be useful for generating keys using `buildca` option on some token which requires Admin/SO PIN (i.e. Yubikey, Nitrokey Pro, etc).  
**Important:** Please consider that these tokens are usually not a complete HSM solution (and -in some cases- they follow special key-generation procedure). For that reason,  I would instead recommend to first generate the keys following the manufacturer instructions (or specific application).  
Generated keys could than be selected for usage with easy-RSA using the previous options.
* `PKCS11_REQUIRE_SOPIN` (Optional) - Boolean, set to `true` for devices which require SO PIN login to generate keypairs (i.e. Yubikeys)
*  `PKCS11_SO_PIN` (Test/Automation only - *HIGHLY INSECURE*) -  useful for testing,  automatically logs the SO user in.


Usage
-----
To build the CA on a token use the `pkcs11` parameter when calling `build-ca`.  If desired you can also use the `subca` command.
```sh
./easyrsa build-ca pkcs11tool
```

Once you've created your CA, `./pki/private/ca.key` will not be a normal PEM key file.  Instead it will look like the following:

```sh
# EasyRSA variables pointing to the private key object
PKCS11_MODULE_PATH=/usr/lib/libsofthsm2.so
PKCS11_TOKEN_URI="pkcs11:model=SoftHSM%20v2;manufacturer=SoftHSM%20project;serial=bcc3ef4e731fb246;token=test-token"
PKCS11_KEY_ID=23aa5c05
PKCS11_KEY_LABEL=Fancy-SoftHSM-CA
```

If desired you can also include the `PKCS11_PIN` variable.  Note: This is a big risk for sensitive keys but very useful for automation.

After building the CA, you can proceed as usual to generate new server/client certificates.
Now all operations for that CA operate on the token and the only extra interaction will be entering the token PIN.

Specific configurations examples
================================

Nitrokey HSM - Smartcard HSM
----------------------------
 The [SmartCard-HSM](https://www.smartcard-hsm.com/) is a lightweight hardware security module in a smart card form factor.
 The [Nitrokey HSM](https://www.nitrokey.com/#comparison) is a lightweight hardware security module in a USB key form factor containing the SmartCard-HSM. The [SmartCard-HSM](https://www.smartcard-hsm.com/#comparison) is available as USB key, ID-1 card with contact/contactless interface, as ID-000 plug-in and MicroSD card. Both are 100% compatible and provide a remote-manageable secure key store for RSA and ECC keys.
(Adapted from [OpenSC Wiki](https://github.com/OpenSC/OpenSC/wiki/SmartCardHSM)).
0. Initialize the token. Choose one option:
    - Simple initialization: (No DKEK shares, meaning no possibility to export a backup)
    ```sh
    #Initialize the token
    sc-hsm-tool --initialize
    ```
    - Initialization with DKEK share(s): (Enable to export encrypted backup --> more info)
    ```sh
    # Generate DKEK share
    sc-hsm-tool --create-dkek-share dkek-share-1.pbe
    # Initialize the token with 1 DKEK share
    sc-hsm-tool --initialize --dkek-shares 1
    # Import your DKEK share
    sc-hsm-tool --import-dkek-share dkek-share-1.pbe
    ```
1. Suggested settings:
Set `PKCS11_TOKEN_URI` according to your device serial or select it from the list during execution; choose fresh `PKCS11_KEY_LABEL` and `PKCS11_KEY_ID` for key generation or set them according to your existing keys.
```sh
set_var PKCS11_MODULE_PATH	"path/to/opensc-pkcs11.so"
set_var PKCS11_TOKEN_URI	"pkcs11:model=PKCS%2315%20emulated;manufacturer=www.CardContact.de;serial=DENK0000000;token=SmartCard-HSM%20%28UserPIN%29%00%00%00%00%00%00%00%00%00"
set_var PKCS11_KEY_LABEL	"test-CA-key"
set_var PKCS11_KEY_ID "123456"
# Only for testing & automation purpose.
# Never write your production PIN to file.
#set_var PKCS11_PIN 123456
```


2. Build the CA
```sh
easyrsa build-ca pkcs11
```

Nitrokey Pro
------------
[Nitrokey Pro](https://www.nitrokey.com/#comparison)is an open-source USB key used to enable the secure encryption and signing of data. Among other features, it provides two emulated PKCS15 card, one using OpenPGP and one Using S/MIME. It can store 3 keys (more specifically, one identity, 3 subkeys).

0. Initialize the token.  
We suggest to [initialize the token](https://www.nitrokey.com/documentation/installation#p:nitrokey-pro) and [generate your keys](https://www.nitrokey.com/documentation/openpgp-email-encryption) following the respective manufacturer guides.

1. Suggested settings:  
Nitrokey Pro shows up as 2 different slots:
  * The first one labeled `(OpenPGP card (User PIN)`, containing subkeys for Encryption and Authentication (CKA_ID 02 and 03, respectively);

  * The second one labeled `(OpenPGP card (User PIN (sig))`, containing the subkey for Signature (CKA_ID=01) we are looking for.  
Select `PKCS11_TOKEN_URI` according to your device serial, choose `PKCS11_KEY_LABEL`.

  Set `PKCS11_TOKEN_URI` to the second one (or choose it interactively); `PKCS11_KEY_ID` should not be set to `01`.
```sh
set_var PKCS11_MODULE_PATH	"path/to/opensc-pkcs11.so"
set_var PKCS11_TOKEN_URI "pkcs11:model=PKCS%2315%20emulated;manufacturer=ZeitControl;serial=123456789123;token=OpenPGP%20card%20%28User%20PIN%20%28sig%29%29%00%00%00;"
set_var PKCS11_KEY_LABEL "Signature key"
set_var PKCS11_KEY_ID "01"
# Only for testing & automation purpose.
# Never write your production PIN to file.
#set_var PKCS11_PIN 123456
```

2. Build the CA
```sh
easyrsa build-ca pkcs11
```

SoftHSM2
--------

[SoftHSM](https://www.opendnssec.org/softhsm/) is an implementation of a cryptographic store accessible through a PKCS #11 interface. You can use it to explore PKCS #11 without having a Hardware Security Module. It is being developed as a part of the OpenDNSSEC project. SoftHSM uses Botan for its cryptographic operations. (Adapted from [OpenDNSSEC wiki](https://www.opendnssec.org/softhsm/))

0. Initialize a token
```sh
softhsm2-util --init-token --free --label my-test-token --so-pin 123456 --pin 1234
```
  **Important:** Verify your user has sufficient permissions on `/var/lib/softhsm/tokens/`.

1. Required settings:  
Select `PKCS11_TOKEN_URI` according to your device serial and token name, choose `PKCS11_KEY_LABEL` and `PKCS11_KEY_ID`.

  ```sh
set_var PKCS11_MODULE_PATH "/usr/lib/softhsm/libsofthsm2.so"
set_var PKCS11_TOKEN_URI "pkcs11:model=SoftHSM%20v2;manufacturer=SoftHSM%20project;serial=f609a0b66832b468;token=my-test-token;"
set_var PKCS11_KEY_ID "01"
set_var PKCS11_KEY_LABEL "test-CA-key"
# Only for testing & automation purpose.
# Never write your production PIN to file.
#set_var PKCS11_PIN "1234"
```

2. Build the CA
```sh
easyrsa build-ca pkcs11
```


YubiKey
-----------
[Yubikey](https://www.yubico.com/products/) is a Hardware authentication device manufactured by [Yubico](https://www.yubico.com/).
The following guide has been adapted from [Yubico Dev Pages](https://developers.yubico.com/yubico-piv-tool/YKCS11/Supported_applications/pkcs11tool.html). It was tested on Yubikey 5 NFC, but should work on other models as well.

Following Yubikey's [PIV Certificate slots description](https://developers.yubico.com/PIV/Introduction/Certificate_slots.html), I would suggest using slot `9c` (`PKCS11_KEY_ID`: `02`, `PKCS11_KEY_LABEL`: `Private key for Digital Signature`) to store your CA keys.


Other slots requiring PIN should be valid, too. Nonetheless, take into account necessary URI and label changes. Object labels for Yubikey's slots are fixed, so check [Key Alias per Slot and Object Type](https://developers.yubico.com/yubico-piv-tool/YKCS11/Functions_and_values.html) section and change it accordingly.



0. Initialize the key. Use Yubikey Manager to change PIN/SO PIN and to generate the required keys (Digital Signature).
  **Important:** Possibly a Yubikey bug, but serial in PKCS11 URI appear as 00000000000000 until you generate keys from Yubikey Manager.

1. Required settings:  
Use `opensc-pkcs11.so`, select your device `PKCS11_TOKEN_URI`, do not change `PKCS11_KEY_LABEL` and `PKCS11_KEY_ID` unless you are using a different key.
```sh
set_var PKCS11_MODULE_PATH	"path/to/opensc-pkcs11.so"
set_var PKCS11_KEY_LABEL	"SIGN"
set_var PKCS11_TOKEN_URI	"pkcs11:model=PKCS%2315%20emulated;manufacturer=piv_II;serial=0123456789abcdef;token=testkey
"
set_var PKCS11_KEY_ID "02"
# Only for testing & automation purpose.
# Never write your production PIN to file.
#set_var PKCS11_PIN 123456
```

2. Build CA
```sh
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
* [ ] Add sanity checks
  - [x] if no `PKCS11_URI` is selected, list available ones and ask the user to select
  - [x] check to ensure GnuTLS is installed
  - [ ] check to ensure openssl pkcs11 engine is installed and library is able to be found
  - [ ] check to ensure token exists
  - [ ] check to ensure token is connected
  - [ ] check to ensure key type and size are supported by the token
  - [x] check to ensure if corresponding public key exist; ask to use it instead or print an error

* [ ] if supported (verify how to check it), save the generated CA certificate to HSM (might ask the user fro confirmation)
* [ ] Create command to extract a certificate from a key and bootstrap a new CA (maybe ask the user if that is what they want if the slot has everything that is needed)
* [x] Move key generation from `pkcs11-tool` to GNU-tls `p11tool` (single dependency)

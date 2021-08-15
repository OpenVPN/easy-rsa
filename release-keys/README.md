Easy-RSA 3 release GPG keys
===

This document contains the GPG Key IDs used to sign official releases starting
with the 3.x series. These release-keys are available on public keyserver
mirrors, such as pgp.mit.edu.

Current keys
---

These keys are currently valid:

* Key ID [0x9D7367F3](https://keys.openpgp.org/vks/v1/by-fingerprint/6F4056821152F03B6B24F2FCF8489F839D7367F3)
  * Owner: Eric Crist <ecrist@secure-computing.net>
  * Key fingerprint: 6F40 5682 1152 F03B 6B24  F2FC F848 9F83 9D73 67F3

Former keys
---

These keys were once valid but are now expired or revoked:

* Key ID 0x606FD463
  * Owner: Josh Cepek <josh.cepek@usa.net>
  * Key fingerprint: 65FF 3F24 AA08 E882 CB44  4C94 D731 D97A 606F D463
  * Member is no longer active with EasyRSA.

Verifying Signatures
===
You can verify the signatures provided by downloading the public key for the current key (above) and adding it to your keychain. Then you can verify with the following command:
```
ecrist@marvin:~/Downloads-> gpg --verify EasyRSA-3.0.8.tgz.sig EasyRSA-3.0.8.tgz
gpg: Signature made Wed Sep  9 16:00:35 2020 CDT
gpg:                using RSA key C8FCA3E7F787072CDEB91D2F72964219390D0D0E
gpg: Good signature from "Eric F Crist <ecrist@secure-computing.net>"
```

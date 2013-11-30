Easy-RSA 3 Hacking Guide
===

This is a brief document aimed at programmers looking to improve on the existing
codebase.

Compatibility
---

The `easyrsa` code is written in POSIX shell (and any cases where it is not is
considered a bug to be fixed.) The only exceptions are the `local` keyword and
the construct `export FOO=baz`, both well-supported.

As such, modifications to the code should also be POSIX; platform-specific code
should be placed under the `distro/` dir and listed by target platform.

Coding conventions
---

While there aren't strict syntax standards associated with the project, please
follow the existing format and flow when possible; however, specific exceptions
can be made if there is a significant reason or benefit.

Do try to:

  * Keep variables locally-scoped when possible
  * Comment sections of code for readability
  * Use the conventions for prefixes on global variables

Keeping code, docs, and examples in sync
---

Changes that adjust, add, or remove features should have relevant docs, help
output, and examples updated at the same time.

Release versioning
---

A point-release bump (eg: 3.0 to 3.1) is required when the frontend interface
changes in a non-backwards compatible way. Always assume someone has an
automated process that relies on the current functionality for official
(non-beta, non-rc) releases. A possible exception exists for bugfixes that do
break backwards-compatibility; caution is to be used in such cases.

The addition of a new command may or may not require a point-release depending
on the significance of the feature; the same holds true for additional optional
arguments to commands.

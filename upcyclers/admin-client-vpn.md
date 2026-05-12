# Upcyclers Admin Client VPN PKI Runbook

This EasyRSA fork is used as the tool source for managing Upcyclers admin AWS
Client VPN certificates. It is not the source of truth for generated VPN
credentials.

Do not commit generated PKI state, `.ovpn` files, private keys, certificate
revocation lists, or encrypted PKI archives to Git.

## Responsibility

The associated admin technical owner, CTO, or delegated infrastructure developer
is responsible for admin VPN certificate operations.

That owner is responsible for:

- Maintaining the encrypted EasyRSA `pki/` archive in 1Password.
- Generating one client certificate per team member or client.
- Creating personalized `.ovpn` profiles.
- Sending `.ovpn` files only through approved secure channels.
- Revoking certificates when access should be removed.
- Importing updated CRLs into AWS Client VPN.

Clients and regular team members should not run EasyRSA. They should only
install AWS VPN Client, import the provided `.ovpn` profile, connect, and open
the admin dashboard.

## Storage Model

This repository stores only EasyRSA source code and Upcyclers operating
instructions.

Sensitive state lives in 1Password:

```text
1Password item: Admin Client VPN PKI
```

The 1Password item should store encrypted PKI archives, for example:

```text
admin-stage-client-vpn-pki.zip
admin-prod-client-vpn-pki.zip
```

The generated `pki/` directory is the actual certificate authority state. It
contains the CA key, issued certificates, client private keys, serial/index
database, and CRL state. Losing it makes per-user issuance and revocation
difficult; leaking it compromises VPN access.

The upstream EasyRSA `.gitignore` already ignores:

```text
easyrsa3/pki
```

Do not bypass that ignore rule.

## Restoring PKI State

To issue or revoke VPN certificates, restore the correct environment PKI archive
from 1Password:

```bash
cd "<easy_rsa_fork>/easyrsa3"
unzip "<path_to_downloaded_pki_zip>"
```

After extraction, this directory should exist:

```text
easyrsa3/pki/
```

Confirm expected PKI files are present:

```bash
ls pki
```

Expected examples:

```text
ca.crt
index.txt
issued
private
serial
```

Do not commit the restored `pki/` directory.

## Creating A Client VPN Profile

Create a separate certificate for each person:

```bash
cd "<easy_rsa_fork>/easyrsa3"
./easyrsa build-client-full <client-name> nopass
```

When prompted, type:

```text
yes
```

This creates:

```text
pki/issued/<client-name>.crt
pki/private/<client-name>.key
```

Download the base Client VPN configuration from AWS:

```text
VPC -> Client VPN endpoints -> <admin-vpn-endpoint> -> Download client configuration
```

Copy the base `.ovpn` and append the person's certificate and private key:

```ovpn
<cert>
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
</cert>

<key>
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
</key>
```

The resulting `.ovpn` file is a credential. Send it through a secure channel and
do not commit it to Git.

After issuing a certificate, create a fresh encrypted archive of the updated
`pki/` directory and replace the corresponding 1Password attachment:

```bash
cd "<easy_rsa_fork>/easyrsa3"
zip -er admin-stage-client-vpn-pki.zip pki
```

Use the relevant environment name in the archive filename.

## Client Onboarding

Send clients or team members these instructions:

1. Install AWS VPN Client from `https://aws.amazon.com/vpn/client-vpn-download/`.
2. Open AWS VPN Client.
3. Add a profile named `Upcyclers Admin`.
4. Import the provided `.ovpn` file.
5. Click **Connect**.
6. Open the relevant admin dashboard.

For staging:

```text
https://staging-admin.upcyclers.com
```

For production:

```text
https://admin.upcyclers.com
```

## Revoking Access

When someone leaves or no longer needs access, revoke only that person's client
certificate.

```bash
cd "<easy_rsa_fork>/easyrsa3"
./easyrsa revoke <client-name>
./easyrsa gen-crl
```

When prompted to confirm revocation, type:

```text
yes
```

This updates:

```text
pki/crl.pem
```

Import the CRL into AWS:

```text
VPC -> Client VPN endpoints -> <admin-vpn-endpoint> -> Actions -> Import client certificate CRL
```

Upload:

```text
pki/crl.pem
```

The revoked user's `.ovpn` stops working while other users remain unaffected.

After revocation, create and upload a fresh encrypted `pki/` archive to
1Password so the stored CA state remains current.

## DNS And Access Model

Staging admin uses a public Route 53 DNS record pointing to an internal ALB. The
hostname can resolve publicly to private `10.x.x.x` addresses, but the dashboard
is reachable only through AWS Client VPN or from inside the VPC.

We use this model because private-only DNS caused split-DNS friction on macOS
AWS VPN Client, while full-tunnel VPN would route client internet traffic
through AWS and add NAT Gateway cost and support overhead.

Expected behavior:

- VPN disconnected: DNS may resolve, but HTTPS should time out.
- VPN connected: HTTPS should reach the internal admin ALB.
- `403` with `server: awselb/2.0`: check the admin WAF allowlist and sampled
  requests.

The WAF allowlist values are managed outside this repository in AWS Secrets
Manager and AWS WAF. Do not store allowlist secret values here.

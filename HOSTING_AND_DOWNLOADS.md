# Hosted service and desktop downloads

## Current availability

- [Open the online demo](https://marketprice-bhrdabpr.streamlit.app/) for synthetic data. Files are processed on the hosting server. The app may sleep after inactivity and its startup time is not guaranteed.
- A standalone Mac or Windows installer is **not available yet**. The source launchers require Python and dependency installation; they are not customer-ready installers.
- An [experimental desktop build](desktop/README.md) is available for developers to investigate; it is unsigned and is not an installer or a supported customer download.
- The current app has no application accounts, tenant authorization, or verified isolation boundary. Do not use the public demo for confidential seller files or advertise it as a secure multi-tenant service.

## Gates for confidential hosted use

1. Choose the intended customer and access model. Design identity, authorization, revocation, and tenant isolation before accepting private data. A shared Streamlit process and separate browser sessions are not, by themselves, a tenant security boundary. Consider isolated per-customer processes or equivalent reviewed controls.
2. Run behind TLS and an authenticated, WebSocket-capable gateway. Restrict direct backend access. Set request, upload, rate, connection, execution-time, CPU, and memory limits. Verify actual proxy behavior rather than assuming the sample container provides these controls.
3. Document and verify the data lifecycle, including application memory, temporary export files, OS swap, backups, proxy and application logs, crash reports, browser downloads, and third-party hosting. Use protected ephemeral storage and a tested deletion process. Do not log catalog contents or credentials.
4. Test authorization failures, cross-user and cross-tenant isolation, concurrent uploads and exports, denial of service, restarts, and incident recovery in the real deployment. Independently review the deployment and model before accepting confidential data.
5. Confirm hosting terms, data location, retention, support, and operating costs. Free hosting does not guarantee uptime, startup speed, or resources. Document tested capacity and communicate limitations to users.

`scripts/browser_session_isolation.py` is one local, synthetic two-browser regression check. Even if it passes, it does not establish multi-user security, authorize public hosting, or replace the tests above.

## Gates for customer downloads

Build self-contained Mac and Windows packages that bundle a supported runtime and dependencies, bind the local server only to loopback, and expose a clear quit mechanism. Test startup, sample input and export, offline use, shutdown, upgrades and clean installations on each supported OS and architecture. Review package contents and publish checksums and provenance.

For macOS, sign with a Developer ID and submit for notarization before recommending the app to customers. This needs an appropriate Apple developer account and release credentials. For Windows, sign the installer and test the experience on clean systems; SmartScreen may still warn on a new app. Do not commit signing credentials. Publish download links only after actual artifacts exist and these checks pass; an unsigned test build is not a finished release.

See [DEPLOYMENT.md](DEPLOYMENT.md), [SECURITY.md](SECURITY.md), and [TESTING.md](TESTING.md) for existing controls and limitations.

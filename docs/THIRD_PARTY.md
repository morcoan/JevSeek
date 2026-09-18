# Third-party notices

JevSeek has an original identity. It does not reuse DeepSeek/TypeSafe logos or
claim endorsement by those companies or Microsoft.

The Windows build includes Python and its installed runtime dependencies. The
build script collects supplied license/notice files and a dependency inventory
under `THIRD_PARTY_NOTICES`, both inside the EXE and alongside it. This inventory
also lists build-environment packages and is not a minimal software bill of
materials. React/production JS notices and bundled font SIL OFL notices are
preserved. The OpenHands SDK/tools wheels omit a standalone license file, so the
MIT license from the upstream **v1.49.1** tag is included separately:

https://github.com/OpenHands/software-agent-sdk/blob/v1.49.1/LICENSE

The browser is Microsoft's **Fixed Version WebView2 Runtime**, acquired directly
from Microsoft's published download endpoint, pinned by version/checksum and
checked for Microsoft Authenticode signing. It is Microsoft software, not
relicensed as JevSeek code. Its runtime component notices are kept intact.

- Official runtime/distribution guidance:
  https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution
- Official product/download page:
  https://developer.microsoft.com/en-us/microsoft-edge/webview2/
- Microsoft privacy: https://aka.ms/privacy
- SmartScreen privacy:
  https://learn.microsoft.com/en-us/microsoft-edge/privacy-whitepaper#smartscreen

The bundled readable copy of **MICROSOFT EDGE WEBVIEW2 RUNTIME (FIXED VERSION)**
terms is at `frontend/public/legal/Microsoft-WebView2-Fixed-Version.txt` and is
shown before first use of the EXE. It was extracted without substantive changes
from this publicly provided Microsoft-terms PDF mirror:

https://www.bluecrestinc.com/hubfs/PDFs/legal/SFTW/WebView2-MS-LICENSE-TERMS.pdf

No executable was acquired from that mirror. Runtime binaries come only from
Microsoft. Maintainers should review current upstream terms when refreshing the
runtime or distributing a binary, preserve all notices and required SmartScreen
privacy disclosures, and not distribute the runtime as a separate product.

JevSeek's own source is licensed under the [MIT License](../LICENSE).
Third-party components retain their respective licenses; the project license does
not replace those terms. These notices do not constitute a legal compliance
certification for every possible distribution/use.

# BeatQuay 1.0.0

BeatQuay is Trieflow LLC's music-creation application, based on LMMS. The candidate
includes project export checks, safely staged export results, and two original
starter arrangements using the approved AudioFileProcessor, Kicker and Triple
Oscillator plugin set. This development source is undergoing Windows packaging
and installed-application qualification; it is not a Store release announcement.

[Product](https://beatquay.trieflow.com) ·
[Privacy](https://beatquay.trieflow.com/privacy) ·
[Support](https://beatquay.trieflow.com/support)

Default settings and projects use BeatQuay-specific locations. Upstream LMMS
settings are not automatically read or migrated. An explicitly selected config
or compatible project remains supported. The internal Windows host is still
`lmms.exe`, which the instrument DLLs require; customer-facing identity is
BeatQuay. Project/schema versions remain separate from the product version.

See [product identity and runtime qualification](distribution/product-identity.md),
[starter arrangements](distribution/starter-arrangements.md), and the other
source-bound qualification documents in `distribution/` for build instructions
and evidence limits. Native audio/device, installed GUI, source/license closure
and Store qualification are separate gates.

This application preserves the LMMS authors' copyrights and is distributed under
GPL-2.0-or-later; see [COPYING](COPYING), [LICENSE.txt](LICENSE.txt), and
[AUTHORS](doc/AUTHORS). Original upstream documentation is preserved verbatim in
[UPSTREAM_README.md](doc/UPSTREAM_README.md). Its upstream plugin inventory,
release badges and community links describe LMMS, not this candidate's scope.

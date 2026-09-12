# BeatSprig 1.0.1

BeatSprig is Trieflow LLC's music-creation application, based on LMMS. The candidate
includes project export checks, safely staged export results, and two original
starter arrangements using the approved AudioFileProcessor, Kicker and Triple
Oscillator plugin set. This development source is undergoing Windows packaging
and installed-application qualification; it is not a Store release announcement.

[Product](https://beatsprig.trieflow.com) ·
[Privacy](https://beatsprig.trieflow.com/privacy) ·
[Support](https://beatsprig.trieflow.com/support)

Existing settings and working folders remain `.beatquayrc.xml`, Documents
`BeatQuay`, and portable `beatquay-workspace` for compatibility. An explicitly
selected config or compatible project remains supported. The Windows host is
`beatsprig.exe`; its instrument DLLs are rebuilt against that exact host name.
Project/schema versions remain separate from the product version. The assigned
Store package identity `1659hashfunction.BeatQuay` and ApplicationId `BeatQuay`
remain unchanged. Fresh BeatSprig native/installed qualification is pending.

See [product identity and runtime qualification](distribution/product-identity.md),
[starter arrangements](distribution/starter-arrangements.md), and the other
source-bound qualification documents in `distribution/` for build instructions
and evidence limits. Native audio/device, installed GUI, source/license closure
and Store qualification are separate gates.

Original LMMS source remains GPL-2.0-or-later, with [LICENSE.txt](LICENSE.txt) and
[AUTHORS](doc/AUTHORS) preserved. The combined BeatSprig executable includes
GPLv3 ringbuffer code and is conveyed under [GPLv3 terms](distribution/native-source/COMBINED-LICENSE.md).
See the [exact source/archive and rebuild guide](distribution/native-source/SOURCE.md);
prepared archives do not imply verified public delivery. Original upstream documentation is preserved verbatim in
[UPSTREAM_README.md](doc/UPSTREAM_README.md). Its upstream plugin inventory,
release badges and community links describe LMMS, not this candidate's scope.

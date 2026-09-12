# Original BeatSprig starter arrangements

These are the existing Trieflow CC0 arrangements, renamed from BeatQuay for BeatSprig 1.0.1. Musical notes, timing, voices, synthesis parameters and schema remain identical. Only the two menu filenames, the source-generator creator label and the provenance comment changed. This rename does not claim new native GUI/render qualification.

Current generated source inputs:

| Current file | SHA-256 |
| --- | --- |
| `data/projects/templates/BeatSprig-Drum-Grid.mpt` | `ae6fd8059509cfc7690be2ba505513f165761b66140ade0ff2d5504b668c6a86` |
| `data/projects/templates/BeatSprig-Bassline-Sketch.mpt` | `8f77628fe6b0897a0c4c51562b68cc1cd5422f447fdcc13e7e1cd59b47d6a3dc` |
| `distribution/generate_starters.py` | `0c28426aa9df7851a9042b59adb0369b08d42cbcce04d1faa1e4244dbd9a0e64` |

The unchanged CC0 dedication and original authorship/source record follow. Their BeatQuay names and original digests refer to historical source, retained in Git before the rename; they are not digests of the renamed files.

## Historical original authorship record

# Original BeatQuay starter arrangements

The note, timing, velocity and synthesizer parameter data in `BeatQuay-Drum-Grid.mpt` and `BeatQuay-Bassline-Sketch.mpt` were authored by Codex for Trieflow LLC on September 11, 2026 under the approved BeatQuay development task. These arrangements were created from explicit new musical choices in `distribution/generate_starters.py`. No LMMS demo, preset, sample pack, commercial work or third-party composition was used as musical input.

These are source-authored XML arrangements, not files saved through a qualified graphical application. They use native format version 31 as inspected at candidate `1c7ab3af1b4c54673177c87185d323e3b07f1607`. `distribution/starter-arrangements.md` describes the exact choices and pending native load/save/render/menu checks. A generated document alone is not evidence that those checks passed.

The four-bar Drum Grid contains 55 notes across three synthesized Kicker voices at 112 BPM. The eight-bar Bassline Sketch contains 40 notes in a Triangle/sub-oscillator bass voice at 108 BPM. All sound is synthesized by the native Kicker or TripleOscillator code. There are no samples, user waveforms, SoundFonts, VSTs, external effects, device bindings or embedded audio. Noise synthesis can vary between renders; the XML bytes are reproducible.

To the extent rights exist in these newly authored arrangement data, Trieflow dedicates them under **CC0-1.0**, provided in `CC0-1.0.txt`. Users may use and modify the arrangement data in their own projects. This dedication covers only the two new `.mpt` files; the generator, application, synthesizers and third-party dependencies retain their own licenses and notices. No claim of complete runtime/source/license clearance is made.

| Input or artifact | SHA-256 |
| --- | --- |
| BeatQuay-Drum-Grid.mpt | `dce15e9b6b1bc7f024411fe959bc351aca69cb3f61624bdeaff2c979e90ff8ec` |
| BeatQuay-Bassline-Sketch.mpt | `1d7e6fc3d25efdca89e98aa7ba071f9d42b80b3913dfa00df8821826ae8ba552` |
| distribution/generate_starters.py | `a47d9c85e5ef272f967d4122b178d3279ac110925940afb51a8ec537582ffe70` |
| plugins/kicker/Kicker.cpp | `81c20c6e039c238435d27312abc513e20a2ec2220b700137168d4c25eca048ea` |
| plugins/TripleOscillator/TripleOscillator.cpp | `46f27100600cc4e573052ddc358b1f16374416b477966ae54f0153bd0ed2ba65` |
| src/core/DataFile.cpp | `f6f304723c9a3a4675ce6018fe517f982dd8f6bcd59ed1737f21d2f2a45a5429` |
| src/tracks/MidiClip.cpp | `e9d0866954a32ddb1546022f2051122d4be7bd7c939d7f1ddc24fdd519149340` |
| src/core/Note.cpp | `22fe92c84dc38bf2ba7df64382f064e308eeedc583edc7b1606e498c00d4a2cb` |
| CC0-1.0.txt | `a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499` |

The CC0 legal text was obtained from [Creative Commons](https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt) on September 11, 2026. Source schema and synth code were read to choose valid parameters; no upstream musical content was copied. `python distribution/generate_starters.py --check` compares exact generated arrangement bytes without modifying files.

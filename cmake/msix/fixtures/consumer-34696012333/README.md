These are exact selected files from Windows run 34696012333. The original
consumer workflow passed its real UI/project/audio checks, but installation
qualification FAILED during the subsequent module-origin check. Normal close
and full qualification were not achieved. `manifest.json` records every original
file's SHA256 and size. JSON is gzip-compressed only for repository size; decoded
bytes are verified before tests use them. PNG and project files are unchanged.

The policy tests generate explicitly synthetic completed-state metadata only in
temporary directories. Those fixtures exercise acceptance/refusal logic; they
are never public or historical Windows success evidence. No original receipt is
rewritten in this fixture directory.

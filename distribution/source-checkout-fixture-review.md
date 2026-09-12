# Source checkout fixture topology correction

Windows run 34698292653 stopped before dependency bootstrap or compilation. The
source-checkout fixture extracted the production preflight statements into a
root-level `preflight.ps1`, but those statements now load the exact
`../cmake/msix/qualification-bindings.ps1` helper. The fixture had neither that
relative layout nor the helper. This is a fixture setup failure; the run did not
reach installed consumer acceptance or collect new module-rejection evidence.

The fixture now places its extracted statements under an owned temporary
`harness/distribution` and copies the original helper bytes to the matching
`harness/cmake/msix` path. The harness stays outside the Git checkout under test.
Its child process receives explicit generated run/attempt identifiers; two
negative cases exercise the real helper's missing-run/invalid-attempt refusals.
Production code and all existing clean-source assertions are unchanged.

Validation: the original local real-Git/PowerShell subprocess suite reproduced
three failing tests/five failures at the missing helper. After the fixture-only
change, all four tests/seven cases pass, including the original clean checkout,
three unexpected files, modified tracked source, and both run-binding refusals.

```sh
BEATQUAY_TEST_PWSH=/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh python3 tests/scripted/test_source_checkout.py -v
```

The original private Windows log remains outside source at
`/private/tmp/beatsprig-34698292653-failed.log`, SHA256
`6937b5c30dc093a20da2552ed77566c33985a0e97eeebe73f21fada6971060bd`.
Actual Windows rerun remains pending. Exporter work is isolated in stash
`01f990adb958b61b8f7ec9d3f3fe3c536384776b` and is not part of this correction.

# Java OneOf examples

From the Limbo root in PowerShell, use the already prepared toolchains:

```powershell
. .\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
$env:JAVA_TOOL_OPTIONS = '-Dfile.encoding=UTF-8'
python taut-dev\taut\dev-docs\examples\java-oneof\verify_examples.py
```

The script builds a local foundation-only jar from canonical sources, generates
source and package consumers in fresh temporary directories, compiles all
sources with `javac --release 8`, and runs Conformance.java on JDK17. It saves
identical report corpora, content/provenance inventories and an engine-free
codec/descriptor result under results/. No package installation or publication
occurs. The enabled/disabled goldens record the deliberate mandatory-descriptor
migration and optional thin validation wrappers.

Conformance.java shows invalid draft serialization and repair, recursive/local
reports, canonical keyed paths, shared-child paths, cycles, snapshots, open
application diagnostics, configuration rejection and descriptor queries. The
Python comparator in test_java_oneof.py checks normalized code/rule/path/deferred,
validity/completeness and scope against the actual reference engine.

Generated messages retain their existing package-private visibility. Application
code using them shares package taut; reports/descriptors remain public shared
foundation types. There is no native Java JSON serializer; the existing dense
CBOR codec remains the structural route. See INTEGRATION.md for the concrete ABI,
binding and independent child/parent compilation contract.

# JavaScript oneof and explicit validation

Activate the existing Limbo toolchains, then run from `taut-dev/taut`:

```powershell
. D:\projects\limbo\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
python dev-docs/examples/js-oneof/verify_examples.py
```

This creates temporary source bundles and a local `npm pack --ignore-scripts`
artifact, runs real CommonJS applications, compares both report streams and
checks package/source bytes against the canonical foundation. Nothing is
installed or published. Temporary artifacts stay under Limbo via the activated
TEMP setting. `example.js` shows a mutable invalid draft, lossless serialization,
repair, a retained report snapshot and deliberately incomplete virtual validation.

Generate normal application files with:

```powershell
python -m taut.cli gen dev-docs/examples/js-oneof/content.taut.py --lang js --api-only --runtime source --with-validation --out D:\projects\limbo\js-oneof-demo
node dev-docs/examples/js-oneof/example.js D:\projects\limbo\js-oneof-demo\js\api.js D:\projects\limbo\js-oneof-demo\js\cbor.js
```

`new Content({kind:Kind.number,number:0n})` preserves the existing object constructor
and BigInt field representation. Every message exports `ContentDescriptor` and
`Content.descriptor()` in either mode. `--with-validation` adds `validate(options)`
and `isValid(options)` to every message; defaults are recursive. `{recursive:false}`
checks root rules only. `isValid()` means the report is both valid and complete.
Reports own immutable snapshots; application messages remain mutable.

The two goldens attribute mandatory descriptor/import/export migration in both
modes; only enabled output imports the engine and defines validation methods.
JS's existing structural CBOR projection stays dense. It has no native JSON codec;
the separate TypeScript projection supports its existing IR-driven codec routes.

See [INTEGRATION.md](INTEGRATION.md) for one-owner bindings and separate generation.

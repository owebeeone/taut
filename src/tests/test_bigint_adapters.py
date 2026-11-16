"""Customer adapter examples and native arithmetic bindings."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'src/taut/gen/runtime'
EXAMPLE = ROOT / 'examples/bigint'
VALUES = ['0', '-1', '5', '-5', '256', '-256', str(2**64), str(-2**64-1), str(2**8192), str(-2**8192)]


def run(args, cwd):
    result = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def magnitude_rows():
    for text in VALUES:
        n = int(text)
        yield n < 0, list(abs(n).to_bytes((abs(n).bit_length()+7)//8, "big"))


def test_cpp_customer_adapter(tmp_path):
    compiler = shutil.which('clang++') or shutil.which('c++') or shutil.which('g++')
    if not compiler: pytest.skip('C++ compiler missing')
    rows = ','.join('{'+str(negative).lower()+', {'+','.join(map(str, b))+'}}' for negative,b in magnitude_rows())
    (tmp_path/'taut').mkdir()
    for name in ('descriptors.hpp', 'foundation.hpp'):
        shutil.copyfile(RUNTIME/name, tmp_path/'taut'/name)
    (tmp_path/'main.cpp').write_text('''
#include "cbor.hpp"
#include "taut/descriptors.hpp"
#include "CustomerBigIntAdapter.hpp"
#include <cassert>
struct Row { bool negative; std::vector<std::uint8_t> bytes; };
int main() {
    for (auto row : std::vector<Row>{''' + rows + '''}) {
        auto original = CustomerBigInt::fromMagnitude(row.negative, row.bytes);
        auto carrier = taut::BigIntValue::from<CustomerBigIntAdapter>(original);
        auto view = taut::ValueRef::borrow(carrier);
        assert(view.kind() == taut::TypeKind::BigInt && &view.bigint() == &carrier);
        taut::Buf encoded; encoded.bigint(carrier);
        auto wire = encoded.encoded_bytes();
        auto decoded = taut::try_decode(std::string_view(reinterpret_cast<const char*>(wire.data()), wire.size()));
        assert(decoded.ok);
        auto value = decoded.value.try_bigint(); assert(value.ok);
        assert(value.value.to<CustomerBigIntAdapter>() == original);
        assert(original.magnitudeBytes() == row.bytes && original.isNegative() == row.negative);
    }
}
''')
    binary = tmp_path/('test.exe' if os.name == 'nt' else 'test')
    run([compiler,'-std=c++23','-I'+str(RUNTIME),'-I'+str(tmp_path),'-I'+str(EXAMPLE),'main.cpp','-o',binary],tmp_path)
    run([binary],tmp_path)


def test_swift_customer_cpp_interop(tmp_path):
    compiler = shutil.which('swiftc')
    if not compiler: pytest.skip('Swift compiler missing')
    rows = ','.join('('+str(negative).lower()+', ['+','.join(map(str,b))+'])' for negative,b in magnitude_rows())
    (tmp_path/'main.swift').write_text('''
import CustomerBigIntBridge
let rows: [(Bool, [UInt8])] = [''' + rows + ''']
for (negative, bytes) in rows {
    let original = CustomerBigIntAdapter.fromMagnitude(negative: negative, bytes: bytes)
    let carrier = try BigIntValue.from(original, using: CustomerBigIntAdapter.self)
    let encoded = encode(.bigint(carrier))
    let decoded = try Cbor.tryDecode(encoded).tryBigInt()
    let restored = decoded.value(using: CustomerBigIntAdapter.self)
    precondition(CustomerBigIntAdapter.isNegative(restored) == negative)
    precondition(CustomerBigIntAdapter.magnitude(restored) == bytes)
}
''')
    binary = tmp_path/('test.exe' if os.name == 'nt' else 'test')
    run([compiler,'-cxx-interoperability-mode=default','-Xcc','-std=c++23','-I',EXAMPLE,RUNTIME/'cbor.swift',EXAMPLE/'CustomerBigIntAdapter.swift','main.swift','-o',binary],tmp_path)
    run([binary],tmp_path)


def test_rust_optional_num_bigint_adapter(tmp_path):
    cargo = shutil.which('cargo')
    if not cargo: pytest.skip('Rust toolchain missing')
    (tmp_path/'src').mkdir()
    (tmp_path/'Cargo.toml').write_text('''[package]
name="taut-bigint-adapter-test"
version="0.0.0"
edition="2021"
[dependencies]
taut-foundation={path="'''+(ROOT/'rust/taut-foundation').as_posix()+'''",features=["num-bigint"]}
num-bigint={version="0.4",default-features=false}
''')
    quoted = ','.join('"'+n+'"' for n in VALUES)
    (tmp_path/'src/main.rs').write_text('''
use taut_foundation::cbor::{BigIntValue, NumBigIntAdapter, Cbor, encode, try_decode};
fn main() {
    for text in [''' + quoted + '''] {
        let original: num_bigint::BigInt = text.parse().unwrap();
        let value = BigIntValue::from_adapter::<NumBigIntAdapter>(&original).unwrap();
        let wire = encode(&Cbor::BigInt(value));
        let decoded = try_decode(&wire).unwrap().try_bigint().unwrap();
        assert_eq!(decoded.to_adapter::<NumBigIntAdapter>(), original);
    }
}
''')
    run([cargo,'run','--quiet'],tmp_path)

@pytest.mark.parametrize('target', ['java', 'kotlin', 'go', 'js', 'typescript'])
def test_native_arithmetic_values_match_python_wire(tmp_path, target):
    from taut.wire import cbor
    expected = [cbor.dumps(cbor.Bignum(int(n))).hex() for n in VALUES]
    quoted = ','.join('"'+n+'"' for n in VALUES)
    if target == 'java':
        if not shutil.which('javac'): pytest.skip('Java missing')
        shutil.copyfile(RUNTIME/'Cbor.java',tmp_path/'Cbor.java')
        (tmp_path/'Main.java').write_text('''package taut;
public class Main { public static void main(String[] args) {
for(String text : new String[]{'''+quoted+'''}) {
java.math.BigInteger n=new java.math.BigInteger(text);
byte[] bytes=Cbor.encode(Cbor.bigint(n));
if(!Cbor.decode(bytes).asBigInt().equals(n)) throw new AssertionError();
if(!n.toString().equals(text)) throw new AssertionError();
for(byte b:bytes) System.out.printf("%02x",b&255);System.out.println();
}}}''')
        run(['javac','-d','.', 'Cbor.java','Main.java'],tmp_path)
        output=run(['java','-cp','.', 'taut.Main'],tmp_path)
    elif target == 'kotlin':
        compiler = os.environ.get('KOTLINC') or shutil.which('kotlinc')
        if not compiler: pytest.skip('Kotlin missing')
        shutil.copyfile(RUNTIME/'cbor.kt',tmp_path/'cbor.kt')
        (tmp_path/'Main.kt').write_text('''package taut
fun main() {
for(text in listOf('''+quoted+''')) {
val original=java.math.BigInteger(text)
val carrier=BigIntValue.from(original,JvmBigIntAdapter)
val bytes=encode(Cbor.bigint(carrier))
check(decode(bytes).bigintVal.to(JvmBigIntAdapter)==original)
check(original.toString()==text)
println(bytes.joinToString(""){"%02x".format(it.toInt() and 255)})
}}
''')
        run([compiler,'cbor.kt','Main.kt','-include-runtime','-d','main.jar'],tmp_path)
        output=run(['java','-jar','main.jar'],tmp_path)
    elif target == 'go':
        if not shutil.which('go'): pytest.skip('Go missing')
        runtime=(RUNTIME/'cbor.go').read_text().replace('package taut','package main')
        (tmp_path/'cbor.go').write_text(runtime)
        (tmp_path/'main.go').write_text('''package main
import("fmt";"math/big")
func main(){for _,text:=range []string{'''+quoted+'''}{
n,ok:=new(big.Int).SetString(text,10);if !ok {panic("parse")}
wire:=Encode(CBigInt(*n)); decoded,err:=TryDecode(wire);if err!=nil{panic(err)}
v,err:=decoded.TryBigInt();if err!=nil || v.Cmp(n)!=0 || n.String()!=text{panic("roundtrip/mutation")}
fmt.Printf("%x\\n",wire)
}}
''')
        output=run(['go','run','main.go','cbor.go'],tmp_path)
    else:
        if not shutil.which('node'): pytest.skip('Node missing')
        if target=='js':
            shutil.copyfile(RUNTIME/'cbor.js',tmp_path/'cbor.js')
            start='const {CBigInt,expectBigInt,encode,decode}=require("./cbor.js");\n'
            encode='CBigInt(n)';decoded='expectBigInt(decode(bytes))'
        else:
            shutil.copyfile(RUNTIME/'typescript/cbor.ts',tmp_path/'cbor.ts')
            start='import {CborBigInt,encode,decode} from "./cbor.ts";\n'
            encode='new CborBigInt(n)';decoded='(decode(bytes) as CborBigInt).value'
        suffix='ts' if target=='typescript' else 'js'
        (tmp_path/('main.'+suffix)).write_text(start+'''for(const text of ['''+quoted+''']) {
const n=BigInt(text); const bytes=encode('''+encode+''');
if ('''+decoded+'''!==n) throw new Error("roundtrip");
console.log(Buffer.from(bytes).toString("hex"));
}''')
        output=run(['node','--experimental-strip-types','main.'+suffix],tmp_path)
    assert output.strip().splitlines()==expected

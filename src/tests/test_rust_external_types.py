"""Generated consumers share dependency types rather than copying wire vocabularies."""
import subprocess

import pytest

from taut.gen.scaffold import emit, rust_api
from taut.ir.dsl import BYTES, INT, Enum, F, Msg, Ref, schema


def objects():
    dependency = schema(Kind=Enum(data=1), Packet=Msg(kind=F(1, Ref.Kind), data=F(2, BYTES)))
    consumer = schema(*dependency.enums.values(), *dependency.messages.values(),
                      Request=Msg(id=F(1, INT), packet=F(2, Ref.Packet)))
    return dependency, consumer


def test_external_types_compile_and_preserve_identity(tmp_path):
    dependency, consumer = objects()
    emit(dependency, tmp_path / 'owner', langs=['rust'], services=[], runtime=True)
    imports = {'Kind': 'owner::api::Kind', 'Packet': 'owner::api::Packet'}
    emit(consumer, tmp_path / 'consumer', langs=['rust'], services=[], rust_external_types=imports)
    text = (tmp_path / 'consumer/rust/api.rs').read_text()
    assert 'pub struct Packet' not in text
    assert 'pub enum Kind' not in text
    owner = tmp_path / 'owner/rust/lib.rs'
    owner.write_text('extern crate alloc; pub mod cbor; pub mod api;')
    lib = tmp_path / 'libowner.rlib'
    subprocess.run(['rustc', '--edition=2024', '--crate-name=owner', '--crate-type=lib',
                    str(owner), '-o', str(lib)], check=True)
    main = tmp_path / 'consumer/rust/main.rs'
    main.write_text('''pub use owner::cbor;
mod api;
fn main() {
    let packet = owner::api::Packet { kind: owner::api::Kind::Data, data: vec![0, 255] };
    let request = api::Request { id: 7, packet };
    let bytes = cbor::encode(&request.to_cbor());
    let decoded = api::Request::from_cbor(&cbor::try_decode(&bytes).unwrap()).unwrap();
    let shared: owner::api::Packet = decoded.packet;
    assert_eq!(shared.data, vec![0, 255]);
}
''')
    exe = tmp_path / 'consumer-proof'
    subprocess.run(['rustc', '--edition=2024', str(main), '--extern', f'owner={lib}',
                    '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)


@pytest.mark.parametrize('imports', [
    {'Missing': 'owner::api::Missing'}, {'Packet': 'owner::Packet; panic!()'},
    {'Packet': 'owner::'}, {'Packet': 'crate::self'},
])
def test_invalid_external_mapping_refuses(imports):
    _, consumer = objects()
    with pytest.raises(ValueError):
        rust_api(consumer, fail_closed=True, external_types=imports)


def test_external_mapping_is_explicitly_rust_only(tmp_path):
    _, consumer = objects()
    with pytest.raises(ValueError, match='Rust'):
        emit(consumer, tmp_path, langs=['python'], rust_external_types={'Packet': 'owner::Packet'})


@pytest.mark.parametrize('langs', [['rust'], ['rust', 'python']])
def test_external_types_refuse_vendored_runtime_before_writing(langs, tmp_path):
    _, consumer = objects()
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='external Rust types.*runtime'):
        emit(
            consumer,
            output,
            langs=langs,
            services=[],
            runtime=True,
            rust_external_types={'Packet': 'owner::api::Packet'},
        )
    assert not output.exists()

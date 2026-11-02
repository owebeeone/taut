use api::*;
use foundation::validation::{ValidationOptions, ValidationReport};

fn show(name: &str, report: ValidationReport, fast: bool) {
    println!("{name}: valid={} complete={} fast={} scope={}",
        report.is_valid(), report.is_complete(), fast, report.scope());
    for issue in report.issues() {
        let path = issue.path().iter().map(|part| match part.kind() {
            "field" => part.field_name().unwrap().to_owned(),
            "index" => format!("[{}]", part.index().unwrap()),
            _ => format!("[{}:{}]", part.key_type().unwrap(), part.key_cbor_base64().unwrap()),
        }).collect::<Vec<_>>().join(".");
        println!("  {} {} at {path}", issue.rule(), issue.code());
    }
    for deferred in report.deferred_checks() {
        println!("  {} {} at {}", deferred.rule(), deferred.reason_code(),
            deferred.path()[0].field_name().unwrap());
    }
}

fn main() {
    for (name, value) in [
        ("zero", Content { kind: ContentKind::Number, number: Some(0), ..Default::default() }),
        ("false", Content { kind: ContentKind::Flag, flag: Some(false), ..Default::default() }),
        ("empty text", Content { kind: ContentKind::Text, text: Some(String::new()), ..Default::default() }),
        ("empty list", Content { kind: ContentKind::Items, items: Some(Vec::new()), ..Default::default() }),
        ("payload-free", Content { kind: ContentKind::Empty, ..Default::default() }),
    ] {
        assert!(value.is_valid());
        show(name, value.validate(), value.is_valid());
    }

    let mut draft = Content { kind: ContentKind::Number, text: Some("extra".into()), ..Default::default() };
    let snapshot = draft.validate();
    let wire = foundation::cbor::encode(&draft.to_cbor());
    println!("draft_cbor={}", wire.iter().map(|b| format!("{b:02x}")).collect::<String>());
    draft = Content::decode(&wire).unwrap();
    assert_eq!(draft.text.as_deref(), Some("extra"));
    show("invalid round-trip", draft.validate(), draft.is_valid());
    draft.text = None; draft.number = Some(42);
    show("repaired", draft.validate(), draft.is_valid());
    assert_eq!(snapshot.issues().len(), 2);
    println!("snapshot still has {} original issues", snapshot.issues().len());

    let child = Content { kind: ContentKind::Number, ..Default::default() };
    let envelope = Envelope { content: child.clone() };
    let local = ValidationOptions { recursive: false };
    show("child local", envelope.validate_with_options(local), envelope.is_valid_with_options(local));
    show("child recursive", envelope.validate(), envelope.is_valid());
    let mut virtual_root = VirtualEnvelope { content: Some(child) };
    show("virtual plus invalid child", virtual_root.validate(), virtual_root.is_valid());
    virtual_root.content.as_mut().unwrap().number = Some(0);
    show("virtual after child repair", virtual_root.validate(), virtual_root.is_valid());
    assert!(!virtual_root.is_valid());
    assert!(virtual_root.validate().is_valid());
    assert!(!virtual_root.validate().is_complete());
    assert!(core::ptr::eq(Content::descriptor(), Content::descriptor()));
    println!("descriptor {}: {} fields, contract {}", Content::descriptor().name(),
        Content::descriptor().fields().len(), Content::descriptor().descriptor_contract_version());
}

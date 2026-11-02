// Generated from oneof_fields.taut.py by the isolated syntax probe.
// Validation is explicit; constructors and codecs do not call it.
#[derive(Debug, PartialEq, Eq)]
pub enum ProbeValidationError { InvalidPayload(&'static str) }

fn probe_payload_content(value: &r::Content) -> Result<(), ProbeValidationError> {
    let active = 0 + usize::from(value.number.is_some()) + usize::from(value.text.is_some());
    match value.kind {
        r::ContentKind::Empty => {
            if active != 0 {
                return Err(ProbeValidationError::InvalidPayload("Content"));
            }
        }
        r::ContentKind::Number => {
            if active != 1 || value.number.is_none() {
                return Err(ProbeValidationError::InvalidPayload("Content"));
            }
        }
        r::ContentKind::Text => {
            if active != 1 || value.text.is_none() {
                return Err(ProbeValidationError::InvalidPayload("Content"));
            }
        }
    }
    Ok(())
}

pub fn validate_content(value: &r::Content) -> Result<(), ProbeValidationError> {
    probe_payload_content(value)
}

use bytes::{BufMut, Bytes, BytesMut};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Default)]
pub struct StreamOutput {
    bytes: BytesMut,
}

impl StreamOutput {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn write_byte(&mut self, value: u8) {
        self.bytes.put_u8(value);
    }

    pub fn write_bool(&mut self, value: bool) {
        self.write_byte(if value { 1 } else { 0 });
    }

    pub fn write_i32(&mut self, value: i32) {
        self.bytes.put_i32(value);
    }

    pub fn write_i64(&mut self, value: i64) {
        self.bytes.put_i64(value);
    }

    pub fn write_bytes_reference(&mut self, value: &[u8]) {
        self.write_vint(value.len() as i32);
        self.bytes.put_slice(value);
    }

    pub fn write_vint(&mut self, value: i32) {
        let mut value = value as u32;
        while (value & !0x7f) != 0 {
            self.write_byte(((value & 0x7f) as u8) | 0x80);
            value >>= 7;
        }
        self.write_byte(value as u8);
    }

    pub fn write_vlong(&mut self, mut value: i64) {
        while (value & !0x7f) != 0 {
            self.write_byte(((value & 0x7f) as u8) | 0x80);
            value >>= 7;
        }
        self.write_byte(value as u8);
    }

    pub fn write_zlong(&mut self, value: i64) {
        let mut value = ((value as u64) << 1) ^ ((value >> 63) as u64);
        while (value & !0x7f) != 0 {
            self.write_byte(((value & 0x7f) as u8) | 0x80);
            value >>= 7;
        }
        self.write_byte(value as u8);
    }

    pub fn write_string(&mut self, value: &str) {
        let units: Vec<u16> = value.encode_utf16().collect();
        self.write_vint(units.len() as i32);
        for unit in units {
            self.write_java_utf16_unit(unit);
        }
    }

    pub fn write_optional_string(&mut self, value: Option<&str>) {
        if let Some(value) = value {
            self.write_bool(true);
            self.write_string(value);
        } else {
            self.write_bool(false);
        }
    }

    pub fn write_string_array(&mut self, values: &[String]) {
        self.write_vint(values.len() as i32);
        for value in values {
            self.write_string(value);
        }
    }

    pub fn write_string_map(&mut self, values: &BTreeMap<String, String>) {
        self.write_vint(values.len() as i32);
        for (key, value) in values {
            self.write_string(key);
            self.write_string(value);
        }
    }

    pub fn write_string_set_map(&mut self, values: &BTreeMap<String, BTreeSet<String>>) {
        self.write_vint(values.len() as i32);
        for (key, set) in values {
            self.write_string(key);
            self.write_vint(set.len() as i32);
            for value in set {
                self.write_string(value);
            }
        }
    }

    pub fn freeze(self) -> Bytes {
        self.bytes.freeze()
    }

    fn write_java_utf16_unit(&mut self, unit: u16) {
        if unit <= 0x007f {
            self.write_byte(unit as u8);
        } else if unit > 0x07ff {
            self.write_byte((0xe0 | ((unit >> 12) & 0x0f)) as u8);
            self.write_byte((0x80 | ((unit >> 6) & 0x3f)) as u8);
            self.write_byte((0x80 | (unit & 0x3f)) as u8);
        } else {
            self.write_byte((0xc0 | ((unit >> 6) & 0x1f)) as u8);
            self.write_byte((0x80 | (unit & 0x3f)) as u8);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::StreamInput;

    #[test]
    fn roundtrips_basic_values() {
        let mut output = StreamOutput::new();
        output.write_i32(123);
        output.write_i64(456);
        output.write_vint(789);
        output.write_vint(-1);
        output.write_string("steelsearch 검색");

        let mut input = StreamInput::new(output.freeze());
        assert_eq!(input.read_i32().unwrap(), 123);
        assert_eq!(input.read_i64().unwrap(), 456);
        assert_eq!(input.read_vint().unwrap(), 789);
        assert_eq!(input.read_vint().unwrap(), -1);
        assert_eq!(input.read_string().unwrap(), "steelsearch 검색");
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn decodes_java_signed_vint_negative_one() {
        let mut input = StreamInput::new(Bytes::from_static(&[0xff, 0xff, 0xff, 0xff, 0x0f]));

        assert_eq!(input.read_vint().unwrap(), -1);
        assert_eq!(input.remaining(), 0);
    }

    #[test]
    fn encodes_java_signed_vint_negative_one() {
        let mut output = StreamOutput::new();
        output.write_vint(-1);

        assert_eq!(output.freeze().as_ref(), &[0xff, 0xff, 0xff, 0xff, 0x0f]);
    }

    #[test]
    fn encodes_zig_zag_long_values() {
        let mut output = StreamOutput::new();
        output.write_zlong(0);
        output.write_zlong(-1);
        output.write_zlong(1);
        output.write_zlong(30);

        assert_eq!(output.freeze().as_ref(), &[0, 1, 2, 60]);
    }

    #[test]
    fn encodes_strings_with_java_char_count() {
        let mut output = StreamOutput::new();
        output.write_string("😀");
        let bytes = output.freeze();

        assert_eq!(bytes[0], 2);

        let mut input = StreamInput::new(bytes);
        assert_eq!(input.read_string().unwrap(), "😀");
    }
}

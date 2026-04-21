use bytes::{Buf, Bytes};
use std::collections::{BTreeMap, BTreeSet};
use thiserror::Error;

#[derive(Debug)]
pub struct StreamInput {
    bytes: Bytes,
}

impl StreamInput {
    pub fn new(bytes: Bytes) -> Self {
        Self { bytes }
    }

    pub fn remaining(&self) -> usize {
        self.bytes.remaining()
    }

    pub fn read_byte(&mut self) -> Result<u8, StreamInputError> {
        self.ensure(1)?;
        Ok(self.bytes.get_u8())
    }

    pub fn read_bool(&mut self) -> Result<bool, StreamInputError> {
        match self.read_byte()? {
            0 => Ok(false),
            1 => Ok(true),
            value => Err(StreamInputError::InvalidBoolean(value)),
        }
    }

    pub fn read_bytes(&mut self, len: usize) -> Result<Bytes, StreamInputError> {
        self.ensure(len)?;
        Ok(self.bytes.copy_to_bytes(len))
    }

    pub fn read_i32(&mut self) -> Result<i32, StreamInputError> {
        self.ensure(4)?;
        Ok(self.bytes.get_i32())
    }

    pub fn read_i64(&mut self) -> Result<i64, StreamInputError> {
        self.ensure(8)?;
        Ok(self.bytes.get_i64())
    }

    pub fn read_bytes_reference(&mut self) -> Result<Bytes, StreamInputError> {
        let len = self.read_vint()?;
        if len < 0 {
            return Err(StreamInputError::NegativeLength(len));
        }
        let len = len as usize;
        self.ensure(len)?;
        Ok(self.bytes.copy_to_bytes(len))
    }

    pub fn read_vint(&mut self) -> Result<i32, StreamInputError> {
        let mut byte = self.read_byte()?;
        let mut value = (byte & 0x7f) as i32;
        if byte & 0x80 == 0 {
            return Ok(value);
        }

        byte = self.read_byte()?;
        value |= ((byte & 0x7f) as i32) << 7;
        if byte & 0x80 == 0 {
            return Ok(value);
        }

        byte = self.read_byte()?;
        value |= ((byte & 0x7f) as i32) << 14;
        if byte & 0x80 == 0 {
            return Ok(value);
        }

        byte = self.read_byte()?;
        value |= ((byte & 0x7f) as i32) << 21;
        if byte & 0x80 == 0 {
            return Ok(value);
        }

        byte = self.read_byte()?;
        if byte & 0x80 != 0 {
            return Err(StreamInputError::VarIntTooLarge);
        }
        Ok(value | (((byte & 0x7f) as i32) << 28))
    }

    pub fn read_vlong(&mut self) -> Result<i64, StreamInputError> {
        let mut shift = 0;
        let mut result: i64 = 0;
        loop {
            if shift >= 64 {
                return Err(StreamInputError::VarIntTooLarge);
            }
            let byte = self.read_byte()?;
            result |= ((byte & 0x7f) as i64) << shift;
            if byte & 0x80 == 0 {
                return Ok(result);
            }
            shift += 7;
        }
    }

    pub fn read_string(&mut self) -> Result<String, StreamInputError> {
        let char_count = self.read_vint()?;
        if char_count < 0 {
            return Err(StreamInputError::NegativeLength(char_count));
        }
        let mut units = Vec::with_capacity(char_count as usize);
        for _ in 0..char_count {
            units.push(self.read_java_utf16_unit()?);
        }
        String::from_utf16(&units).map_err(StreamInputError::InvalidUtf16)
    }

    pub fn read_optional_string(&mut self) -> Result<Option<String>, StreamInputError> {
        if self.read_bool()? {
            Ok(Some(self.read_string()?))
        } else {
            Ok(None)
        }
    }

    pub fn read_string_array(&mut self) -> Result<Vec<String>, StreamInputError> {
        let len = self.read_vint()?;
        if len < 0 {
            return Err(StreamInputError::NegativeLength(len));
        }
        let mut values = Vec::with_capacity(len as usize);
        for _ in 0..len {
            values.push(self.read_string()?);
        }
        Ok(values)
    }

    pub fn read_string_map(&mut self) -> Result<BTreeMap<String, String>, StreamInputError> {
        let len = self.read_vint()?;
        if len < 0 {
            return Err(StreamInputError::NegativeLength(len));
        }
        let mut values = BTreeMap::new();
        for _ in 0..len {
            values.insert(self.read_string()?, self.read_string()?);
        }
        Ok(values)
    }

    pub fn read_string_set_map(
        &mut self,
    ) -> Result<BTreeMap<String, BTreeSet<String>>, StreamInputError> {
        let len = self.read_vint()?;
        if len < 0 {
            return Err(StreamInputError::NegativeLength(len));
        }
        let mut values = BTreeMap::new();
        for _ in 0..len {
            let key = self.read_string()?;
            let set_len = self.read_vint()?;
            if set_len < 0 {
                return Err(StreamInputError::NegativeLength(set_len));
            }
            let mut set = BTreeSet::new();
            for _ in 0..set_len {
                set.insert(self.read_string()?);
            }
            values.insert(key, set);
        }
        Ok(values)
    }

    fn read_java_utf16_unit(&mut self) -> Result<u16, StreamInputError> {
        let first = self.read_byte()?;
        match first >> 4 {
            0..=7 => Ok(first as u16),
            12 | 13 => {
                let second = self.read_byte()?;
                if second & 0xc0 != 0x80 {
                    return Err(StreamInputError::InvalidJavaString);
                }
                Ok((((first & 0x1f) as u16) << 6) | ((second & 0x3f) as u16))
            }
            14 => {
                let second = self.read_byte()?;
                let third = self.read_byte()?;
                if second & 0xc0 != 0x80 || third & 0xc0 != 0x80 {
                    return Err(StreamInputError::InvalidJavaString);
                }
                Ok((((first & 0x0f) as u16) << 12)
                    | (((second & 0x3f) as u16) << 6)
                    | ((third & 0x3f) as u16))
            }
            _ => Err(StreamInputError::InvalidJavaString),
        }
    }

    fn ensure(&self, needed: usize) -> Result<(), StreamInputError> {
        if self.bytes.remaining() < needed {
            Err(StreamInputError::UnexpectedEof {
                needed,
                remaining: self.bytes.remaining(),
            })
        } else {
            Ok(())
        }
    }
}

#[derive(Debug, Error)]
pub enum StreamInputError {
    #[error("unexpected EOF: need {needed} bytes, have {remaining}")]
    UnexpectedEof { needed: usize, remaining: usize },
    #[error("variable-length integer is too large")]
    VarIntTooLarge,
    #[error("negative length: {0}")]
    NegativeLength(i32),
    #[error("invalid Java-style UTF-16 string")]
    InvalidJavaString,
    #[error("invalid UTF-16 string")]
    InvalidUtf16(#[source] std::string::FromUtf16Error),
    #[error("invalid boolean byte: {0}")]
    InvalidBoolean(u8),
}

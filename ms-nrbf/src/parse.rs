use crate::enums::{BinaryArrayType, BinaryType, PrimitiveType, RecordType};
use chrono::{NaiveDateTime, NaiveTime};
use num_enum::TryFromPrimitiveError;
use std::{
    io::{self, Read},
    string::FromUtf8Error,
};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ParseError {
    #[error("failed to read buffer")]
    IoError(#[from] io::Error),
    #[error("failed to parse string")]
    StringError(#[from] FromUtf8Error),
    #[error("failed to parse primitive type")]
    InvalidPrimitiveType(#[from] TryFromPrimitiveError<PrimitiveType>),
    #[error("failed to parse binary type")]
    InvalidBinaryType(#[from] TryFromPrimitiveError<BinaryType>),
    #[error("failed to parse record type")]
    InvalidRecordType(#[from] TryFromPrimitiveError<RecordType>),
    #[error("failed to parse binary array type")]
    InvalidBinaryArrayType(#[from] TryFromPrimitiveError<BinaryArrayType>),
    #[error("failed to parse utf-8 char")]
    InvalidChar,
    #[error("failed to parse timespan")]
    InvalidTimeSpan,
    #[error("failed to parse datetime")]
    InvalidDateTime,
    #[error("not enough info to parse: {0:?}")]
    NotEnoughInfo(RecordType),
}

pub(crate) trait ParseFrom<R: Read>
where
    Self: Sized,
{
    fn parse_from(reader: &mut R) -> Result<Self, ParseError>;
}

pub(crate) trait ParseFromSized<R: Read>
where
    Self: Sized,
{
    fn parse_from_sized(reader: &mut R, size: usize) -> Result<Self, ParseError>;
}

pub(crate) trait ParseFromTyped<R: Read, T: ParseFrom<R>>
where
    Self: Sized,
{
    fn parse_from_typed(reader: &mut R, enum_type: T) -> Result<Self, ParseError>;
}

impl<R: Read> ParseFrom<R> for u8 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let mut byte_buf = [0; 1];
        reader.read_exact(&mut byte_buf)?;
        Ok(byte_buf[0])
    }
}

impl<R: Read> ParseFrom<R> for u16 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let mut byte_buf = [0; 2];
        reader.read_exact(&mut byte_buf)?;
        Ok(u16::from_le_bytes(byte_buf))
    }
}

impl<R: Read> ParseFrom<R> for u32 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let mut byte_buf = [0; 4];
        reader.read_exact(&mut byte_buf)?;
        Ok(u32::from_le_bytes(byte_buf))
    }
}

impl<R: Read> ParseFrom<R> for u64 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let mut byte_buf = [0; 8];
        reader.read_exact(&mut byte_buf)?;
        Ok(u64::from_le_bytes(byte_buf))
    }
}

impl<R: Read> ParseFrom<R> for i8 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(reader.parse::<u8>()? as i8)
    }
}

impl<R: Read> ParseFrom<R> for i16 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(reader.parse::<u16>()? as i16)
    }
}

impl<R: Read> ParseFrom<R> for i32 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(reader.parse::<u32>()? as i32)
    }
}

impl<R: Read> ParseFrom<R> for i64 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(reader.parse::<u64>()? as i64)
    }
}

impl<R: Read> ParseFrom<R> for f32 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(f32::from_bits(reader.parse()?))
    }
}

impl<R: Read> ParseFrom<R> for f64 {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(f64::from_bits(reader.parse()?))
    }
}

impl<R: Read> ParseFrom<R> for char {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let mut byte: u32 = reader.parse::<u8>()? as u32;

        let iterations = {
            if byte & 0x80 == 0 {
                0
            } else if byte & 0xE0 == 0xC0 {
                1
            } else if byte & 0xF0 == 0xE0 {
                2
            } else {
                3
            }
        };

        for _ in 0..iterations {
            byte <<= 8;
            byte |= reader.parse::<u8>()? as u32;
        }

        char::from_u32(byte).ok_or(ParseError::InvalidChar)
    }
}

impl<R: Read> ParseFrom<R> for String {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let mut length: usize = 0;

        for i in 0..5 {
            let byte = reader.parse::<u8>()?;
            length += ((byte & 0x7F) << (7 * i)) as usize;
            if byte & 0x80 == 0 {
                break;
            }
        }

        let mut string_buf = vec![0; length];
        reader.read_exact(string_buf.as_mut_slice())?;

        Ok(String::from_utf8(string_buf)?)
    }
}

impl<R: Read> ParseFrom<R> for NaiveTime {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let hundred_nanoseconds = (reader.parse::<i64>()?).unsigned_abs();
        let nano = (hundred_nanoseconds * 100) as u32;
        let sec = (hundred_nanoseconds / 1000000000) as u32;
        let min = sec / 60;
        let hour = min / 60;

        NaiveTime::from_hms_nano_opt(hour, min, sec, nano).ok_or(ParseError::InvalidTimeSpan)
    }
}

impl<R: Read> ParseFrom<R> for NaiveDateTime {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let hundred_nanoseconds = (reader.parse::<u64>()? & 0xFFFFFFFFFFFFFFFC) as i64;

        NaiveDateTime::from_timestamp_micros(hundred_nanoseconds / 10)
            .ok_or(ParseError::InvalidDateTime)
    }
}

impl<R: Read, T: ParseFrom<R>> ParseFromSized<R> for Vec<T> {
    fn parse_from_sized(reader: &mut R, size: usize) -> Result<Self, ParseError> {
        let mut vec = vec![];

        for _ in 0..size {
            vec.push(reader.parse()?);
        }

        Ok(vec)
    }
}

pub(crate) trait Parse<R: Read> {
    fn parse<T: ParseFrom<R>>(&mut self) -> Result<T, ParseError>;
}

impl<R: Read> Parse<R> for R {
    fn parse<T: ParseFrom<R>>(&mut self) -> Result<T, ParseError> {
        T::parse_from(self)
    }
}

pub(crate) trait ParseSized<R: Read> {
    fn parse_sized<T: ParseFromSized<R>>(&mut self, size: usize) -> Result<T, ParseError>;
}

impl<R: Read> ParseSized<R> for R {
    fn parse_sized<T: ParseFromSized<R>>(&mut self, size: usize) -> Result<T, ParseError> {
        T::parse_from_sized(self, size)
    }
}

pub(crate) trait ParseTyped<R: Read, E: ParseFrom<R>> {
    fn parse_typed<T: ParseFromTyped<R, E>>(&mut self, length: E) -> Result<T, ParseError>;
}

impl<R: Read, E: ParseFrom<R>> ParseTyped<R, E> for R {
    fn parse_typed<T: ParseFromTyped<R, E>>(&mut self, enum_type: E) -> Result<T, ParseError> {
        T::parse_from_typed(self, enum_type)
    }
}

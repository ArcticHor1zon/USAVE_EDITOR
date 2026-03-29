use crate::{
    common::ClassTypeInfo,
    parse::{Parse, ParseError, ParseFrom, ParseFromTyped, ParseTyped},
    records::{
        ArraySingleObject, ArraySinglePrimitive, ArraySingleString, BinaryArray, BinaryLibrary,
        BinaryMethodCall, BinaryMethodReturn, BinaryObjectString, ClassWithId, ClassWithMembers,
        ClassWithMembersAndTypes, SerializationHeader, SystemClassWithMembers,
        SystemClassWithMembersAndTypes,
    },
    unparse::{Unparse, UnparseTo},
};
use chrono::{NaiveDateTime, NaiveTime};
use num_enum::TryFromPrimitive;
use std::{
    io::{self, Read, Write},
    ops::{BitAnd, BitOrAssign},
};

#[repr(u8)]
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone, Copy, TryFromPrimitive)]
pub enum PrimitiveType {
    Boolean = 1,
    Byte = 2,
    Char = 3,
    Decimal = 5,
    Double = 6,
    Int16 = 7,
    Int32 = 8,
    Int64 = 9,
    SByte = 10,
    Single = 11,
    TimeSpan = 12,
    DateTime = 13,
    UInt16 = 14,
    UInt32 = 15,
    UInt64 = 16,
    Null = 17,
    String = 18,
}

impl<R: Read> ParseFrom<R> for PrimitiveType {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self::try_from_primitive(
            reader.parse()?,
        )?)
    }
}

impl<W: Write> UnparseTo<W> for PrimitiveType {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self as u8)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub enum Primitive {
    Boolean(bool),
    Byte(u8),
    Char(char),
    Decimal(String),
    Double(f64),
    Int16(i16),
    Int32(i32),
    Int64(i64),
    SByte(i8),
    Single(f32),
    TimeSpan(NaiveTime),
    DateTime(NaiveDateTime),
    UInt16(u16),
    UInt32(u32),
    UInt64(u64),
    Null,
    String(String),
}

impl Primitive {
    pub(crate) fn get_type(&self) -> PrimitiveType {
        match self {
            Primitive::Boolean(_) => PrimitiveType::Boolean,
            Primitive::Byte(_) => PrimitiveType::Byte,
            Primitive::Char(_) => PrimitiveType::Char,
            Primitive::Decimal(_) => PrimitiveType::Decimal,
            Primitive::Double(_) => PrimitiveType::Double,
            Primitive::Int16(_) => PrimitiveType::Int16,
            Primitive::Int32(_) => PrimitiveType::Int32,
            Primitive::Int64(_) => PrimitiveType::Int64,
            Primitive::SByte(_) => PrimitiveType::SByte,
            Primitive::Single(_) => PrimitiveType::Single,
            Primitive::TimeSpan(_) => PrimitiveType::TimeSpan,
            Primitive::DateTime(_) => PrimitiveType::DateTime,
            Primitive::UInt16(_) => PrimitiveType::UInt16,
            Primitive::UInt32(_) => PrimitiveType::UInt32,
            Primitive::UInt64(_) => PrimitiveType::UInt64,
            Primitive::Null => PrimitiveType::Null,
            Primitive::String(_) => PrimitiveType::String,
        }
    }
}

impl<R: Read> ParseFromTyped<R, PrimitiveType> for Primitive {
    fn parse_from_typed(reader: &mut R, primitive_type: PrimitiveType) -> Result<Self, ParseError> {
        Ok(match primitive_type {
            PrimitiveType::Boolean => Self::Boolean(reader.parse::<u8>()? > 0),
            PrimitiveType::Byte => Self::Byte(reader.parse()?),
            PrimitiveType::Char => Self::Char(reader.parse()?),
            PrimitiveType::Decimal => Self::Decimal(reader.parse()?),
            PrimitiveType::Double => Self::Double(reader.parse()?),
            PrimitiveType::Int16 => Self::Int16(reader.parse()?),
            PrimitiveType::Int32 => Self::Int32(reader.parse()?),
            PrimitiveType::Int64 => Self::Int64(reader.parse()?),
            PrimitiveType::SByte => Self::SByte(reader.parse()?),
            PrimitiveType::Single => Self::Single(reader.parse()?),
            PrimitiveType::TimeSpan => Self::TimeSpan(reader.parse()?),
            PrimitiveType::DateTime => Self::DateTime(reader.parse()?),
            PrimitiveType::UInt16 => Self::UInt16(reader.parse()?),
            PrimitiveType::UInt32 => Self::UInt32(reader.parse()?),
            PrimitiveType::UInt64 => Self::UInt64(reader.parse()?),
            PrimitiveType::Null => Self::Null,
            PrimitiveType::String => Self::String(reader.parse()?),
        })
    }
}

impl<W: Write> UnparseTo<W> for Primitive {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        match self {
            Self::Boolean(value) => writer.unparse(value as u8),
            Self::Byte(value) => writer.unparse(value),
            Self::Char(value) => writer.unparse(value),
            Self::Decimal(value) => writer.unparse(value),
            Self::Double(value) => writer.unparse(value),
            Self::Int16(value) => writer.unparse(value),
            Self::Int32(value) => writer.unparse(value),
            Self::Int64(value) => writer.unparse(value),
            Self::SByte(value) => writer.unparse(value),
            Self::Single(value) => writer.unparse(value),
            Self::TimeSpan(value) => writer.unparse(value),
            Self::DateTime(value) => writer.unparse(value),
            Self::UInt16(value) => writer.unparse(value),
            Self::UInt32(value) => writer.unparse(value),
            Self::UInt64(value) => writer.unparse(value),
            Self::Null => Ok(()),
            Self::String(value) => writer.unparse(value),
        }
    }
}

#[repr(u8)]
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone, Copy, TryFromPrimitive)]
pub enum BinaryType {
    Primitive_ = 0,
    String = 1,
    Object = 2,
    SystemClass = 3,
    Class = 4,
    ObjectArray = 5,
    StringArray = 6,
    PrimitiveArray = 7,
}

impl<R: Read> ParseFrom<R> for BinaryType {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self::try_from_primitive(
            reader.parse()?,
        )?)
    }
}

impl<W: Write> UnparseTo<W> for BinaryType {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self as u8)
    }
}

#[repr(u8)]
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone, Copy, TryFromPrimitive)]
pub enum RecordType {
    SerializedStreamHeader = 0,
    ClassWithId = 1,
    SystemClassWithMembers = 2,
    ClassWithMembers = 3,
    SystemClassWithMembersAndTypes = 4,
    ClassWithMembersAndTypes = 5,
    BinaryObjectString = 6,
    BinaryArray = 7,
    MemberTypedPrimitive = 8,
    MemberReference = 9,
    ObjectNull = 10,
    MessageEnd = 11,
    BinaryLibrary = 12,
    ObjectNullMultiple256 = 13,
    ObjectNullMultiple = 14,
    ArraySinglePrimitive = 15,
    ArraySingleObject = 16,
    ArraySingleString = 17,
    MethodCall = 21,
    MethodReturn = 22,
}

impl<R: Read> ParseFrom<R> for RecordType {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self::try_from_primitive(
            reader.parse()?,
        )?)
    }
}

impl<W: Write> UnparseTo<W> for RecordType {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self as u8)
    }
}

#[derive(Debug, PartialEq, Clone)]
#[allow(dead_code)]
pub(crate) enum Record {
    SerializationHeader(SerializationHeader),
    ClassWithId(ClassWithId),
    SystemClassWithMembers(SystemClassWithMembers),
    ClassWithMembers(ClassWithMembers),
    SystemClassWithMembersAndTypes(SystemClassWithMembersAndTypes),
    ClassWithMembersAndTypes(ClassWithMembersAndTypes),
    BinaryObjectString(BinaryObjectString),
    BinaryArray(BinaryArray),
    MemberPrimitiveUnTyped(Primitive),
    MemberTypedPrimitive { value: Primitive },
    MemberReference { id: i32 },
    ObjectNull,
    MessageEnd,
    ObjectNullMultiple256 { null_count: u8 },
    ObjectNullMultiple { null_count: i32 },
    BinaryLibrary(BinaryLibrary),
    ArraySinglePrimitive(ArraySinglePrimitive),
    ArraySingleObject(ArraySingleObject),
    ArraySingleString(ArraySingleString),
    MethodCall(BinaryMethodCall),
    MethodReturn(BinaryMethodReturn),
}

impl<R: Read> ParseFromTyped<R, RecordType> for Record {
    fn parse_from_typed(reader: &mut R, record_type: RecordType) -> Result<Self, ParseError> {
        Ok(match record_type {
            RecordType::SerializedStreamHeader => Self::SerializationHeader(reader.parse()?),
            RecordType::ClassWithId => Self::ClassWithId(reader.parse()?),
            RecordType::SystemClassWithMembersAndTypes => {
                Self::SystemClassWithMembersAndTypes(reader.parse()?)
            }
            RecordType::ClassWithMembersAndTypes => Self::ClassWithMembersAndTypes(reader.parse()?),
            RecordType::BinaryObjectString => Self::BinaryObjectString(reader.parse()?),
            RecordType::BinaryArray => Self::BinaryArray(reader.parse()?),
            RecordType::MemberTypedPrimitive => {
                let primitive_type = reader.parse()?;
                Self::MemberTypedPrimitive {
                    value: reader.parse_typed(primitive_type)?,
                }
            }
            RecordType::MemberReference => Self::MemberReference {
                id: reader.parse()?,
            },
            RecordType::ObjectNull => Self::ObjectNull,
            RecordType::MessageEnd => Self::MessageEnd,
            RecordType::ObjectNullMultiple256 => Self::ObjectNullMultiple256 {
                null_count: reader.parse()?,
            },
            RecordType::ObjectNullMultiple => Self::ObjectNullMultiple {
                null_count: reader.parse()?,
            },
            RecordType::BinaryLibrary => Self::BinaryLibrary(reader.parse()?),
            RecordType::ArraySinglePrimitive => Self::ArraySinglePrimitive(reader.parse()?),
            RecordType::ArraySingleString => Self::ArraySingleString(reader.parse()?),
            RecordType::MethodCall => Self::MethodCall(reader.parse()?),
            RecordType::MethodReturn => Self::MethodReturn(reader.parse()?),
            other => Err(ParseError::NotEnoughInfo(other))?,
        })
    }
}

impl<R: Read> ParseFrom<R> for Vec<Record> {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let mut records = vec![];

        loop {
            let record_type = reader.parse()?;
            let record = reader.parse_typed(record_type)?;
            let is_message_end = record == Record::MessageEnd;

            records.push(record);

            if is_message_end {
                break;
            }
        }

        Ok(records)
    }
}

impl<W: Write> UnparseTo<W> for Record {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        match self {
            Self::SerializationHeader(value) => writer.unparse(value),
            Self::ClassWithId(value) => writer.unparse(value),
            Self::SystemClassWithMembers(value) => writer.unparse(value),
            Self::ClassWithMembers(value) => writer.unparse(value),
            Self::SystemClassWithMembersAndTypes(value) => writer.unparse(value),
            Self::ClassWithMembersAndTypes(value) => writer.unparse(value),
            Self::BinaryObjectString(value) => writer.unparse(value),
            Self::BinaryArray(value) => writer.unparse(value),
            Self::MemberReference { id } => {
                writer.unparse(RecordType::MemberReference)?;
                writer.unparse(id)
            }
            Self::ObjectNull => writer.unparse(RecordType::ObjectNull),
            Self::MessageEnd => writer.unparse(RecordType::MessageEnd),
            Self::ObjectNullMultiple256 { null_count } => {
                writer.unparse(RecordType::ObjectNullMultiple256)?;
                writer.unparse(null_count)
            }
            Self::ObjectNullMultiple { null_count } => {
                writer.unparse(RecordType::ObjectNullMultiple)?;
                writer.unparse(null_count)
            }
            Self::BinaryLibrary(value) => writer.unparse(value),
            Self::ArraySinglePrimitive(value) => writer.unparse(value),
            Self::ArraySingleObject(value) => writer.unparse(value),
            Self::ArraySingleString(value) => writer.unparse(value),
            Self::MethodCall(value) => writer.unparse(value),
            Self::MethodReturn(value) => writer.unparse(value),
            Self::MemberPrimitiveUnTyped(value) => writer.unparse(value),
            Self::MemberTypedPrimitive { value } => {
                writer.unparse(RecordType::MemberTypedPrimitive)?;
                writer.unparse(value.get_type())?;
                writer.unparse(value)
            }
        }
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) enum AdditionalInfo {
    Primitive(PrimitiveType),
    SystemClass(String),
    Class(ClassTypeInfo),
    PrimitiveArray(PrimitiveType),
}

impl<R: Read> ParseFromTyped<R, BinaryType> for Option<AdditionalInfo> {
    fn parse_from_typed(reader: &mut R, enum_type: BinaryType) -> Result<Self, ParseError> {
        Ok(match enum_type {
            BinaryType::Primitive_ => Some(AdditionalInfo::Primitive(
                reader.parse()?,
            )),
            BinaryType::PrimitiveArray => Some(AdditionalInfo::PrimitiveArray(
                reader.parse()?,
            )),
            BinaryType::SystemClass => Some(AdditionalInfo::SystemClass(
                reader.parse()?,
            )),
            BinaryType::Class => Some(AdditionalInfo::Class(reader.parse()?)),
            _ => None,
        })
    }
}

impl<W: Write> UnparseTo<W> for AdditionalInfo {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        match self {
            Self::Primitive(value) => writer.unparse(value),
            Self::PrimitiveArray(value) => writer.unparse(value),
            Self::Class(value) => writer.unparse(value),
            Self::SystemClass(value) => writer.unparse(value),
        }
    }
}

#[repr(u8)]
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Clone, Copy, TryFromPrimitive)]
pub enum BinaryArrayType {
    Single = 0,
    Jagged = 1,
    Rectangular = 2,
    SingleOffset = 3,
    JaggedOffset = 4,
    RectangularOffset = 5,
}

impl<R: Read> ParseFrom<R> for BinaryArrayType {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self::try_from_primitive(
            reader.parse()?,
        )?)
    }
}

impl<W: Write> UnparseTo<W> for BinaryArrayType {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self as u8)
    }
}

#[repr(u32)]
pub(crate) enum MessageFlagEnum {
    NoArgs = 0x0001,
    ArgsInline = 0x0002,
    ArgsIsArray = 0x0004,
    ArgsInArray = 0x0008,
    NoContext = 0x0010,
    ContextInline = 0x0020,
    ContextInArray = 0x0040,
    MethodSignatureInArray = 0x0080,
    PropertiesInArray = 0x0100,
    NoReturnValue = 0x0200,
    ReturnValueVoid = 0x0400,
    ReturnValueInline = 0x0800,
    ReturnValueInArray = 0x1000,
    ExceptionInArray = 0x2000,
    GenericMethod = 0x8000,
}

impl BitAnd<u32> for MessageFlagEnum {
    type Output = u32;

    #[inline(always)]
    fn bitand(self, rhs: u32) -> Self::Output {
        self as u32 & rhs
    }
}

impl BitAnd<MessageFlagEnum> for u32 {
    type Output = u32;

    #[inline(always)]
    fn bitand(self, rhs: MessageFlagEnum) -> Self::Output {
        rhs & self
    }
}

impl BitOrAssign<MessageFlagEnum> for u32 {
    #[inline(always)]
    fn bitor_assign(&mut self, rhs: MessageFlagEnum) {
        *self |= rhs as u32;
    }
}

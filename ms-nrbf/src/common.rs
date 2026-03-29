use crate::{
    enums::{AdditionalInfo, BinaryType, MessageFlagEnum, Primitive, PrimitiveType},
    parse::{Parse, ParseError, ParseFrom, ParseFromSized, ParseSized, ParseTyped},
    unparse::{Unparse, UnparseTo},
};
use std::io::{self, Read, Write};

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ClassInfo {
    pub object_id: i32,
    pub name: String,
    pub member_count: i32,
    pub member_names: Vec<String>,
}

impl<R: Read> ParseFrom<R> for ClassInfo {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let object_id = reader.parse()?;
        let name = reader.parse()?;
        let member_count = reader.parse()?;

        let mut member_names = vec![];

        for _ in 0..member_count {
            member_names.push(reader.parse()?)
        }

        Ok(Self {
            object_id,
            name,
            member_count,
            member_names,
        })
    }
}

impl<W: Write> UnparseTo<W> for ClassInfo {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.object_id)?;
        writer.unparse(self.name)?;
        writer.unparse(self.member_count)?;
        writer.unparse(self.member_names)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct MemberTypeInfo {
    pub member_types: Vec<BinaryType>,
    pub additional_info: Vec<AdditionalInfo>,
}

impl<R: Read> ParseFromSized<R> for MemberTypeInfo {
    fn parse_from_sized(reader: &mut R, member_count: usize) -> Result<Self, ParseError> {
        let member_types: Vec<BinaryType> = reader.parse_sized(member_count)?;
        let mut additional_info = vec![];

        for member_type in &member_types {
            if let Some(info) = reader.parse_typed(*member_type)? {
                additional_info.push(info)
            }
        }

        Ok(Self {
            member_types,
            additional_info,
        })
    }
}

impl<W: Write> UnparseTo<W> for MemberTypeInfo {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.member_types)?;
        writer.unparse(self.additional_info)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ArrayInfo {
    pub object_id: i32,
    pub length: i32,
}

impl<R: Read> ParseFrom<R> for ArrayInfo {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self {
            object_id: reader.parse()?,
            length: reader.parse()?,
        })
    }
}

impl<W: Write> UnparseTo<W> for ArrayInfo {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.object_id)?;
        writer.unparse(self.length)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ClassTypeInfo {
    pub type_name: String,
    pub library_id: i32,
}

impl<R: Read> ParseFrom<R> for ClassTypeInfo {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self {
            type_name: reader.parse()?,
            library_id: reader.parse()?,
        })
    }
}

impl<W: Write> UnparseTo<W> for ClassTypeInfo {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.type_name)?;
        writer.unparse(self.library_id)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ValueWithCode(pub Primitive);

impl<R: Read> ParseFrom<R> for ValueWithCode {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let primitive_type: PrimitiveType = reader.parse()?;

        Ok(Self(
            reader.parse_typed(primitive_type)?,
        ))
    }
}

impl<W: Write> UnparseTo<W> for ValueWithCode {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.0.get_type())?;
        writer.unparse(self.0)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct StringValueWithCode(pub String);

impl<R: Read> ParseFrom<R> for StringValueWithCode {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        assert_eq!(
            reader.parse::<u8>()?,
            BinaryType::String as u8
        );
        Ok(Self(reader.parse()?))
    }
}

impl<W: Write> UnparseTo<W> for StringValueWithCode {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(BinaryType::String)?;
        writer.unparse(self.0)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ArrayOfValueWithCode(pub Vec<ValueWithCode>);

impl<R: Read> ParseFrom<R> for ArrayOfValueWithCode {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let length: i32 = reader.parse()?;

        Ok(Self(
            reader.parse_sized(length as usize)?,
        ))
    }
}

impl<W: Write> UnparseTo<W> for ArrayOfValueWithCode {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.0.len() as i32)?;
        writer.unparse(self.0)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct MessageFlags {
    pub no_args: bool,
    pub args_inline: bool,
    pub args_is_array: bool,
    pub args_in_array: bool,
    pub no_context: bool,
    pub context_inline: bool,
    pub context_in_array: bool,
    pub method_signature_in_array: bool,
    pub properties_in_array: bool,
    pub no_return_value: bool,
    pub return_value_void: bool,
    pub return_value_inline: bool,
    pub return_value_in_array: bool,
    pub exception_in_array: bool,
    pub generic_method: bool,
}

impl<R: Read> ParseFrom<R> for MessageFlags {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let int: u32 = reader.parse()?;

        Ok(Self {
            no_args: MessageFlagEnum::NoArgs & int != 0,
            args_inline: MessageFlagEnum::ArgsInline & int != 0,
            args_is_array: MessageFlagEnum::ArgsIsArray & int != 0,
            args_in_array: MessageFlagEnum::ArgsInArray & int != 0,
            no_context: MessageFlagEnum::NoContext & int != 0,
            context_inline: MessageFlagEnum::ContextInline & int != 0,
            context_in_array: MessageFlagEnum::ContextInArray & int != 0,
            method_signature_in_array: MessageFlagEnum::MethodSignatureInArray & int != 0,
            properties_in_array: MessageFlagEnum::PropertiesInArray & int != 0,
            no_return_value: MessageFlagEnum::NoReturnValue & int != 0,
            return_value_void: MessageFlagEnum::ReturnValueVoid & int != 0,
            return_value_inline: MessageFlagEnum::ReturnValueInline & int != 0,
            return_value_in_array: MessageFlagEnum::ReturnValueInArray & int != 0,
            exception_in_array: MessageFlagEnum::ExceptionInArray & int != 0,
            generic_method: MessageFlagEnum::GenericMethod & int != 0,
        })
    }
}

impl<W: Write> UnparseTo<W> for MessageFlags {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        let mut int: u32 = 0;

        if self.no_args {
            int |= MessageFlagEnum::NoArgs
        }
        if self.args_inline {
            int |= MessageFlagEnum::ArgsInline
        }
        if self.args_is_array {
            int |= MessageFlagEnum::ArgsIsArray
        }
        if self.args_in_array {
            int |= MessageFlagEnum::ArgsInArray
        }
        if self.no_context {
            int |= MessageFlagEnum::NoContext
        }
        if self.context_inline {
            int |= MessageFlagEnum::ContextInline
        }
        if self.context_in_array {
            int |= MessageFlagEnum::ContextInArray
        }
        if self.method_signature_in_array {
            int |= MessageFlagEnum::MethodSignatureInArray
        }
        if self.properties_in_array {
            int |= MessageFlagEnum::PropertiesInArray
        }
        if self.no_return_value {
            int |= MessageFlagEnum::NoReturnValue
        }
        if self.return_value_void {
            int |= MessageFlagEnum::ReturnValueVoid
        }
        if self.return_value_inline {
            int |= MessageFlagEnum::ReturnValueInline
        }
        if self.return_value_in_array {
            int |= MessageFlagEnum::ReturnValueInArray
        }
        if self.exception_in_array {
            int |= MessageFlagEnum::ExceptionInArray
        }
        if self.generic_method {
            int |= MessageFlagEnum::GenericMethod
        }

        writer.unparse(int)
    }
}

use crate::{
    common::{
        ArrayInfo, ArrayOfValueWithCode, ClassInfo, MemberTypeInfo, MessageFlags,
        StringValueWithCode, ValueWithCode,
    },
    enums::{
        AdditionalInfo, BinaryArrayType, BinaryType, Primitive, PrimitiveType, Record, RecordType,
    },
    parse::{Parse, ParseError, ParseFrom, ParseFromSized, ParseSized, ParseTyped},
    unparse::{Unparse, UnparseTo},
};
use std::io::{self, Read, Write};

fn read_references<R: Read>(
    reader: &mut R,
    additional_info: &Vec<AdditionalInfo>,
) -> Result<Vec<Record>, ParseError> {
    let mut member_references = vec![];

    for info in additional_info {
        member_references.push(match info {
            AdditionalInfo::Primitive(primitive_type) => {
                Record::MemberPrimitiveUnTyped(reader.parse_typed(*primitive_type)?)
            }
            _ => {
                // TODO: This probably doesn't work, I should check this. Will I? I don't know.
                let record_type = reader.parse()?;
                reader.parse_typed(record_type)?
            }
        })
    }

    Ok(member_references)
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct SerializationHeader {
    pub root_id: i32,
    pub header_id: i32,
    pub major_version: i32,
    pub minor_version: i32,
}

impl<R: Read> ParseFrom<R> for SerializationHeader {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self {
            root_id: reader.parse()?,
            header_id: reader.parse()?,
            major_version: reader.parse()?,
            minor_version: reader.parse()?,
        })
    }
}

impl<W: Write> UnparseTo<W> for SerializationHeader {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::SerializedStreamHeader)?;
        writer.unparse(self.root_id)?;
        writer.unparse(self.header_id)?;
        writer.unparse(self.major_version)?;
        writer.unparse(self.minor_version)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct BinaryLibrary {
    pub library_id: i32,
    pub library_name: String,
}

impl<R: Read> ParseFrom<R> for BinaryLibrary {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self {
            library_id: reader.parse()?,
            library_name: reader.parse()?,
        })
    }
}

impl<W: Write> UnparseTo<W> for BinaryLibrary {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::BinaryLibrary)?;
        writer.unparse(self.library_id)?;
        writer.unparse(self.library_name)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ClassWithMembersAndTypes {
    pub class_info: ClassInfo,
    pub member_type_info: MemberTypeInfo,
    pub library_id: i32,
    pub member_references: Vec<Record>,
}

impl<R: Read> ParseFrom<R> for ClassWithMembersAndTypes {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let class_info: ClassInfo = reader.parse()?;
        let member_type_info: MemberTypeInfo =
            reader.parse_sized(class_info.member_count as usize)?;
        let library_id = reader.parse()?;
        let member_references = read_references(
            reader,
            &member_type_info.additional_info,
        )?;

        Ok(Self {
            class_info,
            member_type_info,
            library_id,
            member_references,
        })
    }
}

impl<W: Write> UnparseTo<W> for ClassWithMembersAndTypes {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::ClassWithMembersAndTypes)?;
        writer.unparse(self.class_info)?;
        writer.unparse(self.member_type_info)?;
        writer.unparse(self.library_id)?;
        writer.unparse(self.member_references)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ArraySinglePrimitive {
    pub array_info: ArrayInfo,
    pub primitive_type: PrimitiveType,
    pub members: Vec<Primitive>,
}

impl<R: Read> ParseFrom<R> for ArraySinglePrimitive {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let array_info: ArrayInfo = reader.parse()?;
        let primitive_type = reader.parse()?;
        let mut members = vec![];

        for _ in 0..array_info.length {
            members.push(reader.parse_typed(primitive_type)?)
        }

        Ok(Self {
            array_info,
            primitive_type,
            members,
        })
    }
}

impl<W: Write> UnparseTo<W> for ArraySinglePrimitive {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::ArraySinglePrimitive)?;
        writer.unparse(self.array_info)?;
        writer.unparse(self.primitive_type)?;
        writer.unparse(self.members)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ClassWithId {
    pub object_id: i32,
    pub metadata_id: i32,
}

impl<R: Read> ParseFrom<R> for ClassWithId {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self {
            object_id: reader.parse()?,
            metadata_id: reader.parse()?,
        })
    }
}

impl<W: Write> UnparseTo<W> for ClassWithId {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::ClassWithId)?;
        writer.unparse(self.object_id)?;
        writer.unparse(self.metadata_id)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct SystemClassWithMembersAndTypes {
    pub class_info: ClassInfo,
    pub member_type_info: MemberTypeInfo,
    pub member_references: Vec<Record>,
}

impl<R: Read> ParseFrom<R> for SystemClassWithMembersAndTypes {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let class_info: ClassInfo = reader.parse()?;
        let member_type_info: MemberTypeInfo =
            reader.parse_sized(class_info.member_count as usize)?;
        let member_references = read_references(
            reader,
            &member_type_info.additional_info,
        )?;

        Ok(Self {
            class_info,
            member_type_info,
            member_references,
        })
    }
}

impl<W: Write> UnparseTo<W> for SystemClassWithMembersAndTypes {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::SystemClassWithMembersAndTypes)?;
        writer.unparse(self.class_info)?;
        writer.unparse(self.member_type_info)?;
        writer.unparse(self.member_references)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct BinaryObjectString {
    pub object_id: i32,
    pub value: String,
}

impl<R: Read> ParseFrom<R> for BinaryObjectString {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        Ok(Self {
            object_id: reader.parse()?,
            value: reader.parse()?,
        })
    }
}

impl<W: Write> UnparseTo<W> for BinaryObjectString {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::BinaryObjectString)?;
        writer.unparse(self.object_id)?;
        writer.unparse(self.value)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct BinaryArray {
    pub object_id: i32,
    pub binary_array_type: BinaryArrayType,
    pub rank: i32,
    pub lengths: Vec<i32>,
    pub lower_bounds: Option<Vec<i32>>,
    pub binary_type: BinaryType,
    pub additional_info: Vec<AdditionalInfo>,
    pub members: Vec<Record>,
}

impl<R: Read> ParseFrom<R> for BinaryArray {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let object_id = reader.parse()?;
        let binary_array_type = reader.parse()?;
        let rank: i32 = reader.parse()?;
        let lengths = reader.parse_sized(rank as usize)?;
        let lower_bounds = match binary_array_type {
            BinaryArrayType::SingleOffset
            | BinaryArrayType::JaggedOffset
            | BinaryArrayType::RectangularOffset => Some(reader.parse_sized(rank as usize)?),
            _ => None,
        };
        let binary_type = reader.parse()?;
        let mut additional_info = vec![];

        for _ in 0..rank {
            if let Some(info) = reader.parse_typed(binary_type)? {
                additional_info.push(info)
            }
        }

        let members = read_references(reader, &additional_info)?;

        Ok(Self {
            object_id,
            binary_array_type,
            rank,
            lengths,
            lower_bounds,
            binary_type,
            additional_info,
            members,
        })
    }
}

impl<W: Write> UnparseTo<W> for BinaryArray {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::BinaryArray)?;
        writer.unparse(self.object_id)?;
        writer.unparse(self.binary_array_type)?;
        writer.unparse(self.rank)?;
        writer.unparse(self.lengths)?;
        writer.unparse(self.lower_bounds)?;
        writer.unparse(self.binary_type)?;
        writer.unparse(self.additional_info)?;
        writer.unparse(self.members)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ArraySingleString {
    pub array_info: ArrayInfo,
    pub members: Vec<String>,
}

impl<R: Read> ParseFrom<R> for ArraySingleString {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let array_info: ArrayInfo = reader.parse()?;
        let members = reader.parse_sized(array_info.length as usize)?;

        Ok(Self {
            array_info,
            members,
        })
    }
}

impl<W: Write> UnparseTo<W> for ArraySingleString {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::ArraySingleString)?;
        writer.unparse(self.array_info)?;
        writer.unparse(self.members)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct BinaryMethodCall {
    pub message_flags: MessageFlags,
    pub method_name: StringValueWithCode,
    pub type_name: StringValueWithCode,
    pub call_context: Option<StringValueWithCode>,
    pub args: Option<ArrayOfValueWithCode>,
}

impl<R: Read> ParseFrom<R> for BinaryMethodCall {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let message_flags: MessageFlags = reader.parse()?;
        let method_name = reader.parse()?;
        let type_name = reader.parse()?;
        let call_context = if message_flags.context_inline {
            Some(reader.parse()?)
        } else {
            None
        };
        let args = if message_flags.args_inline {
            Some(reader.parse()?)
        } else {
            None
        };

        Ok(Self {
            message_flags,
            method_name,
            type_name,
            call_context,
            args,
        })
    }
}

impl<W: Write> UnparseTo<W> for BinaryMethodCall {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::MethodCall)?;
        writer.unparse(self.message_flags)?;
        writer.unparse(self.method_name)?;
        writer.unparse(self.type_name)?;
        writer.unparse(self.call_context)?;
        writer.unparse(self.args)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct BinaryMethodReturn {
    pub message_flags: MessageFlags,
    pub return_value: Option<ValueWithCode>,
    pub call_context: Option<StringValueWithCode>,
    pub args: Option<ArrayOfValueWithCode>,
}

impl<R: Read> ParseFrom<R> for BinaryMethodReturn {
    fn parse_from(reader: &mut R) -> Result<Self, ParseError> {
        let message_flags: MessageFlags = reader.parse()?;
        let return_value = if message_flags.return_value_inline {
            Some(reader.parse()?)
        } else {
            None
        };
        let call_context = if message_flags.context_inline {
            Some(reader.parse()?)
        } else {
            None
        };
        let args = if message_flags.args_inline {
            Some(reader.parse()?)
        } else {
            None
        };

        Ok(Self {
            message_flags,
            return_value,
            call_context,
            args,
        })
    }
}

impl<W: Write> UnparseTo<W> for BinaryMethodReturn {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::MethodReturn)?;
        writer.unparse(self.message_flags)?;
        writer.unparse(self.return_value)?;
        writer.unparse(self.call_context)?;
        writer.unparse(self.args)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ClassWithMembers {
    pub class_info: ClassInfo,
    pub library_id: i32,
    pub data: Vec<Vec<u8>>,
}

impl<R: Read> ParseFromSized<R> for ClassWithMembers {
    fn parse_from_sized(reader: &mut R, size: usize) -> Result<Self, ParseError> {
        let class_info: ClassInfo = reader.parse()?;
        let library_id = reader.parse()?;
        let mut data = vec![];

        for _ in 0..class_info.member_count {
            let mut member_data = vec![0; size];
            reader.read_exact(member_data.as_mut_slice())?;
            data.push(member_data);
        }

        Ok(Self {
            class_info,
            library_id,
            data,
        })
    }
}

impl<W: Write> UnparseTo<W> for ClassWithMembers {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::ClassWithMembers)?;
        writer.unparse(self.class_info)?;
        writer.unparse(self.library_id)?;
        writer.unparse(self.data)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct SystemClassWithMembers {
    pub class_info: ClassInfo,
    pub data: Vec<Vec<u8>>,
}

impl<R: Read> ParseFromSized<R> for SystemClassWithMembers {
    fn parse_from_sized(reader: &mut R, size: usize) -> Result<Self, ParseError> {
        let class_info: ClassInfo = reader.parse()?;
        let mut data = vec![];

        for _ in 0..class_info.member_count {
            let mut member_data = vec![0; size];
            reader.read_exact(member_data.as_mut_slice())?;
            data.push(member_data);
        }

        Ok(Self { class_info, data })
    }
}

impl<W: Write> UnparseTo<W> for SystemClassWithMembers {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::SystemClassWithMembers)?;
        writer.unparse(self.class_info)?;
        writer.unparse(self.data)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct ArraySingleObject {
    pub array_info: ArrayInfo,
    pub members: Vec<Vec<u8>>,
}

impl<R: Read> ParseFromSized<R> for ArraySingleObject {
    fn parse_from_sized(reader: &mut R, size: usize) -> Result<Self, ParseError> {
        let array_info: ArrayInfo = reader.parse()?;
        let mut members = vec![];

        for _ in 0..array_info.length {
            let mut member_data = vec![0; size];
            reader.read_exact(member_data.as_mut_slice())?;
            members.push(member_data);
        }

        Ok(Self {
            array_info,
            members,
        })
    }
}

impl<W: Write> UnparseTo<W> for ArraySingleObject {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(RecordType::ArraySingleObject)?;
        writer.unparse(self.array_info)?;
        writer.unparse(self.members)
    }
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct MethodCallArray {
    pub input_arguments: Option<Vec<()>>,
    pub generic_type_arguments: Option<Vec<()>>,
    pub method_signature: Option<Vec<()>>,
    pub call_context: Option<()>,
    pub message_properties: Option<Vec<()>>,
}

#[derive(Debug, PartialEq, Clone)]
pub(crate) struct MethodReturnCallArray {
    pub return_value: Option<()>,
    pub output_arguments: Option<Vec<()>>,
    pub exception: Option<()>,
    pub call_context: Option<()>,
    pub message_properties: Option<Vec<()>>,
}

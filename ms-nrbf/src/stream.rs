use crate::{
    common::{ArrayInfo, ClassInfo, ClassTypeInfo, MemberTypeInfo},
    enums::{AdditionalInfo, BinaryType, Primitive, PrimitiveType, Record},
    parse::{Parse, ParseError},
    records::{ArraySinglePrimitive, BinaryLibrary, ClassWithMembersAndTypes, SerializationHeader},
    unparse::Unparse,
};
use chrono::{NaiveDateTime, NaiveTime};
use indexmap::IndexMap;
use std::{
    collections::BTreeMap,
    io::{self, Read, Write},
};

#[derive(Debug)]
pub struct Stream {
    pub root: Class,
}

impl Stream {
    pub fn decode<R: Read>(reader: &mut R) -> Result<Self, ParseError> {
        let records: Vec<Record> = reader.parse()?;

        let mut objects = BTreeMap::new();
        let mut libraries = BTreeMap::new();
        let mut root_id = None;
        let mut root = None;

        for record in records {
            match record {
                Record::SerializationHeader(header) => root_id = Some(header.root_id),
                Record::ClassWithId(class) => {
                    objects.insert(class.object_id, Record::ClassWithId(class));
                }
                Record::BinaryLibrary(library) => {
                    libraries.insert(library.library_id, library.library_name);
                }
                Record::MessageEnd => (),
                Record::ClassWithMembersAndTypes(class) => {
                    if let Some(rid) = root_id {
                        if class.class_info.object_id == rid {
                            root = Some(class.clone());
                        }
                    }

                    objects.insert(
                        class.class_info.object_id,
                        Record::ClassWithMembersAndTypes(class),
                    );
                }
                Record::ArraySinglePrimitive(array) => {
                    objects.insert(
                        array.array_info.object_id,
                        Record::ArraySinglePrimitive(array),
                    );
                }
                Record::BinaryArray(array) => {
                    objects.insert(array.object_id, Record::BinaryArray(array));
                }
                _ => (),
            }
        }

        Ok(Self {
            root: StreamDecoderState { objects, libraries }.decode_class(&root.ok_or_else(
                || io::Error::new(io::ErrorKind::InvalidData, "no root class found"),
            )?),
        })
    }

    pub fn encode<W: Write>(self, writer: &mut W) -> Result<(), io::Error> {
        let mut records = vec![];

        records.push(Record::SerializationHeader(SerializationHeader {
            root_id: 1,
            header_id: -1,
            major_version: 1,
            minor_version: 0,
        }));

        let mut state = StreamEncoderState::new();
        let mut new_records = state.encode_class(self.root);

        for (library_name, library_id) in state.libraries {
            records.push(Record::BinaryLibrary(BinaryLibrary {
                library_id,
                library_name,
            }));
        }

        records.append(&mut new_records);
        records.push(Record::MessageEnd);
        writer.unparse(records)
    }
}

#[derive(Debug, Clone)]
pub struct Class {
    pub library_name: String,
    pub name: String,
    pub fields: IndexMap<String, Field>,
}

#[derive(Debug, PartialEq, Clone)]
pub enum PrimitiveArray {
    Boolean(Vec<bool>),
    Byte(Vec<u8>),
    Char(Vec<char>),
    Decimal(Vec<String>),
    Double(Vec<f64>),
    Int16(Vec<i16>),
    Int32(Vec<i32>),
    Int64(Vec<i64>),
    SByte(Vec<i8>),
    Single(Vec<f32>),
    TimeSpan(Vec<NaiveTime>),
    DateTime(Vec<NaiveDateTime>),
    UInt16(Vec<u16>),
    UInt32(Vec<u32>),
    UInt64(Vec<u64>),
    Null,
    String(Vec<String>),
}

macro_rules! into_field {
    ($primitive_type:ident, $array:expr) => {
        PrimitiveArray::$primitive_type(
            $array
                .iter()
                .map(|primitive| {
                    if let Primitive::$primitive_type(value) = primitive {
                        value.clone()
                    } else {
                        unreachable!()
                    }
                })
                .collect(),
        )
    };
}

macro_rules! from_field {
    ($primitive_type:ident, $value:expr) => {
        $value
            .iter()
            .map(|value| Primitive::$primitive_type(value.clone()))
            .collect()
    };
}

impl PrimitiveArray {
    fn get_type(&self) -> PrimitiveType {
        match self {
            Self::Boolean(_) => PrimitiveType::Boolean,
            Self::Byte(_) => PrimitiveType::Byte,
            Self::Char(_) => PrimitiveType::Char,
            Self::Decimal(_) => PrimitiveType::Decimal,
            Self::Double(_) => PrimitiveType::Double,
            Self::Int16(_) => PrimitiveType::Int16,
            Self::Int32(_) => PrimitiveType::Int32,
            Self::Int64(_) => PrimitiveType::Int64,
            Self::SByte(_) => PrimitiveType::SByte,
            Self::Single(_) => PrimitiveType::Single,
            Self::TimeSpan(_) => PrimitiveType::TimeSpan,
            Self::DateTime(_) => PrimitiveType::DateTime,
            Self::UInt16(_) => PrimitiveType::UInt16,
            Self::UInt32(_) => PrimitiveType::UInt32,
            Self::UInt64(_) => PrimitiveType::UInt64,
            Self::Null => PrimitiveType::Null,
            Self::String(_) => PrimitiveType::String,
        }
    }

    fn into_field(array: Vec<Primitive>, primitive_type: PrimitiveType) -> Self {
        match primitive_type {
            PrimitiveType::Boolean => into_field!(Boolean, array),
            PrimitiveType::Byte => into_field!(Byte, array),
            PrimitiveType::Char => into_field!(Char, array),
            PrimitiveType::Decimal => into_field!(Decimal, array),
            PrimitiveType::Double => into_field!(Double, array),
            PrimitiveType::Int16 => into_field!(Int16, array),
            PrimitiveType::Int32 => into_field!(Int32, array),
            PrimitiveType::Int64 => into_field!(Int64, array),
            PrimitiveType::SByte => into_field!(SByte, array),
            PrimitiveType::Single => into_field!(Single, array),
            PrimitiveType::TimeSpan => into_field!(TimeSpan, array),
            PrimitiveType::DateTime => into_field!(DateTime, array),
            PrimitiveType::UInt16 => into_field!(UInt16, array),
            PrimitiveType::UInt32 => into_field!(UInt32, array),
            PrimitiveType::UInt64 => into_field!(UInt64, array),
            PrimitiveType::Null => Self::Null,
            PrimitiveType::String => into_field!(String, array),
        }
    }
}

impl From<PrimitiveArray> for Vec<Primitive> {
    fn from(value: PrimitiveArray) -> Self {
        match value {
            PrimitiveArray::Boolean(value) => from_field!(Boolean, value),
            PrimitiveArray::Byte(value) => from_field!(Byte, value),
            PrimitiveArray::Char(value) => from_field!(Char, value),
            PrimitiveArray::Decimal(value) => from_field!(Decimal, value),
            PrimitiveArray::Double(value) => from_field!(Double, value),
            PrimitiveArray::Int16(value) => from_field!(Int16, value),
            PrimitiveArray::Int32(value) => from_field!(Int32, value),
            PrimitiveArray::Int64(value) => from_field!(Int64, value),
            PrimitiveArray::SByte(value) => from_field!(SByte, value),
            PrimitiveArray::Single(value) => from_field!(Single, value),
            PrimitiveArray::TimeSpan(value) => from_field!(TimeSpan, value),
            PrimitiveArray::DateTime(value) => from_field!(DateTime, value),
            PrimitiveArray::UInt16(value) => from_field!(UInt16, value),
            PrimitiveArray::UInt32(value) => from_field!(UInt32, value),
            PrimitiveArray::UInt64(value) => from_field!(UInt64, value),
            PrimitiveArray::Null => vec![],
            PrimitiveArray::String(value) => from_field!(String, value),
        }
    }
}

#[derive(Clone, Debug)]
pub enum Field {
    Primitive(Primitive),
    PrimitiveArray(PrimitiveArray),
    Class(Class),
}

struct StreamEncoderState {
    libraries: BTreeMap<String, i32>,
    counter: i32,
}

impl StreamEncoderState {
    fn new() -> Self {
        Self {
            counter: 1,
            libraries: BTreeMap::new(),
        }
    }

    fn encode_class(&mut self, class: Class) -> Vec<Record> {
        let mut records = vec![];
        let mut member_names = vec![];
        let mut member_types = vec![];
        let mut additional_info = vec![];
        let mut member_references = vec![];

        let object_id = self.counter;
        self.counter += 1;

        self.libraries
            .insert(class.library_name.clone(), self.counter);
        self.counter += 1;

        for (field_name, field_value) in class.fields {
            member_names.push(field_name);
            match field_value {
                Field::Primitive(value) => {
                    member_types.push(BinaryType::Primitive_);
                    additional_info.push(AdditionalInfo::Primitive(value.get_type()));
                    member_references.push(Record::MemberPrimitiveUnTyped(value));
                }
                Field::PrimitiveArray(value) => {
                    let primitive_type = value.get_type();
                    let array: Vec<Primitive> = value.into();

                    member_types.push(BinaryType::PrimitiveArray);
                    additional_info.push(AdditionalInfo::PrimitiveArray(primitive_type));
                    member_references.push(Record::MemberReference { id: self.counter });
                    records.push(Record::ArraySinglePrimitive(ArraySinglePrimitive {
                        array_info: ArrayInfo {
                            object_id: self.counter,
                            length: array.len() as i32,
                        },
                        primitive_type,
                        members: array,
                    }));
                    self.counter += 1;
                }
                Field::Class(value) => {
                    records.append(&mut self.encode_class(value.clone()));
                    member_types.push(BinaryType::Class);
                    additional_info.push(AdditionalInfo::Class(ClassTypeInfo {
                        type_name: value.name,
                        library_id: self.libraries[&value.library_name],
                    }));
                    member_references.push(Record::MemberReference { id: self.counter });
                    self.counter += 1;
                }
            }
        }

        records.insert(
            0,
            Record::ClassWithMembersAndTypes(ClassWithMembersAndTypes {
                class_info: ClassInfo {
                    object_id,
                    name: class.name,
                    member_count: member_names.len() as i32,
                    member_names,
                },
                member_type_info: MemberTypeInfo {
                    member_types,
                    additional_info,
                },
                library_id: self.libraries[&class.library_name],
                member_references,
            }),
        );
        self.counter += 1;

        records
    }
}

struct StreamDecoderState {
    objects: BTreeMap<i32, Record>,
    libraries: BTreeMap<i32, String>,
}

impl StreamDecoderState {
    fn decode_class(&self, class: &ClassWithMembersAndTypes) -> Class {
        let field_count = class.class_info.member_count as usize;
        let mut field_names = vec![];
        let mut field_types = vec![];
        let mut field_values: Vec<Field> = vec![];

        let mut ai = 0usize;

        for i in 0..field_count {
            let field_name = &class.class_info.member_names[i];
            let field_type = class.member_type_info.member_types[i];

            match field_type {
                BinaryType::Primitive_ => {
                    if let Record::MemberPrimitiveUnTyped(primitive) = &class.member_references[ai]
                    {
                        field_values.push(Field::Primitive(primitive.clone()));
                    }
                    ai += 1;
                }
                BinaryType::PrimitiveArray => {
                    if let Record::MemberReference { id } = &class.member_references[ai] {
                        if let Record::ArraySinglePrimitive(array) = &self.objects[id] {
                            field_values.push(Field::PrimitiveArray(PrimitiveArray::into_field(
                                array.members.clone(),
                                array.primitive_type,
                            )))
                        }
                    };
                    ai += 1;
                }
                BinaryType::Class => {
                    if let Some(Record::MemberReference { id }) = class.member_references.get(ai) {
                        if let Some(Record::ClassWithMembersAndTypes(class)) = self.objects.get(id)
                        {
                            field_values.push(Field::Class(self.decode_class(class)))
                        }
                    };
                    ai += 1;
                }
                _ => (),
            }

            field_names.push(field_name);
            field_types.push(field_type);
        }

        let mut fields = IndexMap::new();

        for i in 0..field_count {
            if i < field_names.len() && i < field_values.len() {
                fields.insert(field_names[i].clone(), field_values[i].clone());
            }
        }

        Class {
            library_name: self
                .libraries
                .get(&class.library_id)
                .cloned()
                .unwrap_or_default(),
            name: class.class_info.name.clone(),
            fields,
        }
    }
}

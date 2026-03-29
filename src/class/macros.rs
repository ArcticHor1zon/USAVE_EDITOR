use ms_nrbf::{Field, Primitive, PrimitiveArray};

use super::traits::FieldMap;

pub fn read_bool(fields: &FieldMap, name: &str) -> bool {
    fields
        .get(name)
        .and_then(|f| match f {
            Field::Primitive(Primitive::Boolean(v)) => Some(*v),
            _ => None,
        })
        .unwrap_or_default()
}

pub fn read_i32(fields: &FieldMap, name: &str) -> i32 {
    fields
        .get(name)
        .and_then(|f| match f {
            Field::Primitive(Primitive::Int32(v)) => Some(*v),
            _ => None,
        })
        .unwrap_or_default()
}

pub fn read_f32(fields: &FieldMap, name: &str) -> f32 {
    fields
        .get(name)
        .and_then(|f| match f {
            Field::Primitive(Primitive::Single(v)) => Some(*v),
            _ => None,
        })
        .unwrap_or_default()
}

pub fn read_bool_array(fields: &FieldMap, name: &str) -> Vec<bool> {
    fields
        .get(name)
        .and_then(|f| match f {
            Field::PrimitiveArray(PrimitiveArray::Boolean(v)) => Some(v.clone()),
            _ => None,
        })
        .unwrap_or_default()
}

pub fn read_i32_array(fields: &FieldMap, name: &str) -> Vec<i32> {
    fields
        .get(name)
        .and_then(|f| match f {
            Field::PrimitiveArray(PrimitiveArray::Int32(v)) => Some(v.clone()),
            _ => None,
        })
        .unwrap_or_default()
}

pub fn read_f32_array(fields: &FieldMap, name: &str) -> Vec<f32> {
    fields
        .get(name)
        .and_then(|f| match f {
            Field::PrimitiveArray(PrimitiveArray::Single(v)) => Some(v.clone()),
            _ => None,
        })
        .unwrap_or_default()
}

pub fn write_bool(fields: &mut FieldMap, name: &str, value: bool) {
    fields.insert(
        name.to_string(),
        Field::Primitive(Primitive::Boolean(value)),
    );
}

pub fn write_i32(fields: &mut FieldMap, name: &str, value: i32) {
    fields.insert(name.to_string(), Field::Primitive(Primitive::Int32(value)));
}

pub fn write_f32(fields: &mut FieldMap, name: &str, value: f32) {
    fields.insert(name.to_string(), Field::Primitive(Primitive::Single(value)));
}

pub fn write_bool_array(fields: &mut FieldMap, name: &str, value: Vec<bool>) {
    fields.insert(
        name.to_string(),
        Field::PrimitiveArray(PrimitiveArray::Boolean(value)),
    );
}

pub fn write_i32_array(fields: &mut FieldMap, name: &str, value: Vec<i32>) {
    fields.insert(
        name.to_string(),
        Field::PrimitiveArray(PrimitiveArray::Int32(value)),
    );
}

pub fn write_f32_array(fields: &mut FieldMap, name: &str, value: Vec<f32>) {
    fields.insert(
        name.to_string(),
        Field::PrimitiveArray(PrimitiveArray::Single(value)),
    );
}

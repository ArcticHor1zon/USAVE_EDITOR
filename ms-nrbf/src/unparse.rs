use std::io::{self, Write};

use chrono::{NaiveDateTime, NaiveTime};

pub(crate) trait UnparseTo<W: Write>
where
    Self: Sized,
{
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error>;
}

impl<W: Write> UnparseTo<W> for u8 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        Ok(writer.write_all(&[self])?)
    }
}

impl<W: Write> UnparseTo<W> for u16 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        Ok(writer.write_all(&self.to_le_bytes())?)
    }
}

impl<W: Write> UnparseTo<W> for u32 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        Ok(writer.write_all(&self.to_le_bytes())?)
    }
}

impl<W: Write> UnparseTo<W> for u64 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        Ok(writer.write_all(&self.to_le_bytes())?)
    }
}

impl<W: Write> UnparseTo<W> for i8 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self as u8)
    }
}

impl<W: Write> UnparseTo<W> for i16 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self as u16)
    }
}

impl<W: Write> UnparseTo<W> for i32 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self as u32)
    }
}

impl<W: Write> UnparseTo<W> for i64 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self as u64)
    }
}

impl<W: Write> UnparseTo<W> for f32 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.to_bits())
    }
}

impl<W: Write> UnparseTo<W> for f64 {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.to_bits())
    }
}

impl<W: Write> UnparseTo<W> for char {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        let mut buf = vec![0; self.len_utf8()];
        self.encode_utf8(buf.as_mut_slice());
        Ok(writer.write_all(buf.as_slice())?)
    }
}

impl<W: Write> UnparseTo<W> for &str {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        let mut length = self.len();

        for _ in 0..5 {
            let mut byte = (length & 0x7F) as u8;

            length >>= 7;
            if length == 0 {
                writer.unparse(byte)?;
                break;
            } else {
                byte += 0x80;
                writer.unparse(byte)?;
            }
        }

        Ok(writer.write_all(self.as_bytes())?)
    }
}

impl<W: Write> UnparseTo<W> for String {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        writer.unparse(self.as_str())
    }
}

impl<W: Write> UnparseTo<W> for NaiveTime {
    fn unparse_to(self, _writer: &mut W) -> Result<(), io::Error> {
        todo!()
    }
}

impl<W: Write> UnparseTo<W> for NaiveDateTime {
    fn unparse_to(self, _writer: &mut W) -> Result<(), io::Error> {
        todo!()
    }
}

impl<W: Write, T: UnparseTo<W>> UnparseTo<W> for Vec<T> {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        for item in self {
            writer.unparse(item)?;
        }

        Ok(())
    }
}

impl<W: Write, T: UnparseTo<W>> UnparseTo<W> for Option<T> {
    fn unparse_to(self, writer: &mut W) -> Result<(), io::Error> {
        match self {
            Some(value) => writer.unparse(value),
            None => Ok(()),
        }
    }
}

pub(crate) trait Unparse<W: Write> {
    fn unparse<T: UnparseTo<W>>(&mut self, value: T) -> Result<(), io::Error>;
}

impl<W: Write> Unparse<W> for W {
    fn unparse<T: UnparseTo<W>>(&mut self, value: T) -> Result<(), io::Error> {
        T::unparse_to(value, self)
    }
}

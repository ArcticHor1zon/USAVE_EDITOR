use super::{
    helpers::{read_i32, read_i32_array, write_i32, write_i32_array},
    traits::{FieldMap, ParsableClassKeyed, LIBRARY_NAME},
};
use crate::enums::{Difficulty, Level, Lockable};
use indexmap::IndexMap;
use ms_nrbf::{Class, Stream};
use std::{fs::File, io, path::Path};

#[derive(Debug)]
pub struct DifficultyData {
    pub current_level: Level,
    pub prime_levels: Vec<Lockable>,
    pub file_exists: bool,
    pub original_fields: FieldMap,
    pub dirty: bool,
    pub decoded: bool,
}

const CURRENT_LEVEL_FIELD: &str = "levelNum";
const PRIME_LEVELS_FIELD: &str = "primeLevels";

impl ParsableClassKeyed<Difficulty> for DifficultyData {
    const CLASS_NAME: &'static str = "GameProgressMoneyAndGearDifficulty";
    const FILE_PREFIX: &'static str = "difficulty";
    const FILE_SUFFIX: &'static str = "progress.bepis";

    fn get_file_exists(&self) -> bool {
        self.file_exists
    }

    fn set_file_exists(&mut self, exists: bool) {
        self.file_exists = exists;
    }

    fn create_new(_difficulty: &Difficulty) -> Self {
        Self {
            current_level: Level::IntoTheFire,
            prime_levels: vec![Lockable::Locked; 2],
            file_exists: false,
            original_fields: IndexMap::new(),
            dirty: false,
            decoded: false,
        }
    }

    fn parse(class: &Class) -> Option<Self> {
        let fields = &class.fields;
        Some(Self {
            current_level: Level::from_repr(read_i32(fields, CURRENT_LEVEL_FIELD) as u16)
                .unwrap_or(Level::IntoTheFire),
            prime_levels: read_i32_array(fields, PRIME_LEVELS_FIELD)
                .iter()
                .map(|value| Lockable::from_repr(*value as u8).unwrap_or(Lockable::Locked))
                .collect(),
            file_exists: true,
            original_fields: class.fields.clone(),
            dirty: false,
            decoded: true,
        })
    }

    fn unparse(&self, _difficulty: &Difficulty) -> Option<FieldMap> {
        let mut fields = self.original_fields.clone();

        write_i32(&mut fields, CURRENT_LEVEL_FIELD, self.current_level as i32);
        write_i32_array(
            &mut fields,
            PRIME_LEVELS_FIELD,
            self.prime_levels.iter().map(|v| *v as i32).collect(),
        );

        Some(fields)
    }
}

impl DifficultyData {
    pub fn save_to(&self, difficulty: &Difficulty, dir: &Path) -> Result<(), io::Error> {
        let path = dir.join(format!("difficulty{}progress.bepis", *difficulty as u8));
        if let Some(fields) = self.unparse(difficulty) {
            let mut file = File::create(path)?;
            Stream {
                root: Class {
                    library_name: LIBRARY_NAME.to_string(),
                    name: Self::CLASS_NAME.to_string(),
                    fields,
                },
            }
            .encode(&mut file)?;
        }
        Ok(())
    }

    pub fn delete_from(difficulty: &Difficulty, dir: &Path) {
        let path = dir.join(format!("difficulty{}progress.bepis", *difficulty as u8));
        if path.exists() {
            let _ = std::fs::remove_file(path);
        }
    }
}

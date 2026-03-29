use super::{
    macros::{
        read_bool, read_bool_array, read_i32_array, write_bool, write_bool_array, write_i32,
        write_i32_array,
    },
    traits::{FieldMap, ParsableClassKeyed, LIBRARY_NAME},
};
use crate::enums::{Level, LevelRank};
use indexmap::IndexMap;
use ms_nrbf::{Class, Stream};
use std::{fs::File, io, path::Path};

#[derive(Debug)]
pub struct LevelData {
    pub ranks: Vec<LevelRank>,
    pub secrets_found: Vec<bool>,
    pub challenge: bool,
    pub major_assists: Vec<bool>,
    pub file_exists: bool,
    pub original_fields: FieldMap,
    pub dirty: bool,
    pub decoded: bool,
}

const RANKS_FIELD: &str = "ranks";
const SECRETS_AMOUNT_FIELD: &str = "secretsAmount";
const SECRETS_FOUND_FIELD: &str = "secretsFound";
const CHALLENGE_FIELD: &str = "challenge";
const LEVEL_NUMBER_FIELD: &str = "levelNumber";
const MAJOR_ASSISTS_FIELD: &str = "majorAssists";

impl ParsableClassKeyed<Level> for LevelData {
    const CLASS_NAME: &'static str = "RankData";
    const FILE_PREFIX: &'static str = "lvl";
    const FILE_SUFFIX: &'static str = "progress.bepis";

    fn get_file_exists(&self) -> bool {
        self.file_exists
    }

    fn set_file_exists(&mut self, exists: bool) {
        self.file_exists = exists;
    }

    fn create_new(level: &Level) -> Self {
        Self {
            ranks: vec![LevelRank::None; 6],
            secrets_found: vec![false; level.get_secret_count() as usize],
            challenge: false,
            major_assists: vec![false; 6],
            file_exists: false,
            original_fields: IndexMap::new(),
            dirty: false,
            decoded: false,
        }
    }

    fn parse(class: &Class) -> Option<Self> {
        let fields = &class.fields;
        Some(Self {
            ranks: read_i32_array(fields, RANKS_FIELD)
                .iter()
                .map(|value| (*value).into())
                .collect(),
            secrets_found: read_bool_array(fields, SECRETS_FOUND_FIELD),
            challenge: read_bool(fields, CHALLENGE_FIELD),
            major_assists: read_bool_array(fields, MAJOR_ASSISTS_FIELD),
            file_exists: true,
            original_fields: class.fields.clone(),
            dirty: false,
            decoded: true,
        })
    }

    fn unparse(&self, level: &Level) -> Option<FieldMap> {
        let mut fields = self.original_fields.clone();

        write_i32_array(
            &mut fields,
            RANKS_FIELD,
            self.ranks.iter().map(|v| *v as i32).collect(),
        );
        write_i32(
            &mut fields,
            SECRETS_AMOUNT_FIELD,
            self.secrets_found.len() as i32,
        );
        write_bool_array(&mut fields, SECRETS_FOUND_FIELD, self.secrets_found.clone());
        write_bool(&mut fields, CHALLENGE_FIELD, self.challenge);
        write_i32(&mut fields, LEVEL_NUMBER_FIELD, *level as i32);
        write_bool_array(&mut fields, MAJOR_ASSISTS_FIELD, self.major_assists.clone());

        Some(fields)
    }
}

impl LevelData {
    pub fn save_to(&self, level: &Level, dir: &Path) -> Result<(), io::Error> {
        let path = dir.join(format!("lvl{}progress.bepis", *level as u16));
        if let Some(fields) = self.unparse(level) {
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

    pub fn delete_from(level: &Level, dir: &Path) {
        let path = dir.join(format!("lvl{}progress.bepis", *level as u16));
        if path.exists() {
            let _ = std::fs::remove_file(path);
        }
    }
}

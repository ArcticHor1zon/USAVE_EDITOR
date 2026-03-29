use super::{
    helpers::{read_f32_array, read_i32_array, write_f32_array, write_i32, write_i32_array},
    traits::{FieldMap, ParsableClass, LIBRARY_NAME},
};
use indexmap::IndexMap;
use ms_nrbf::{Class, Stream};
use std::{fs::File, io, path::Path};

#[derive(Debug)]
pub struct CybergrindData {
    pub waves: Vec<String>,
    pub kills: Vec<String>,
    pub style: Vec<String>,
    pub times: Vec<String>,
    pub file_exists: bool,
    pub original_fields: FieldMap,
    pub dirty: bool,
    pub decoded: bool,
}

impl Default for CybergrindData {
    fn default() -> Self {
        Self {
            waves: vec!["0.0".to_string(); 6],
            kills: vec!["0".to_string(); 6],
            style: vec!["0".to_string(); 6],
            times: vec!["0.0".to_string(); 6],
            file_exists: false,
            original_fields: IndexMap::new(),
            dirty: false,
            decoded: false,
        }
    }
}

const WAVES_FIELD: &str = "preciseWavesByDifficulty";
const KILLS_FIELD: &str = "bestKillsByDifficulty";
const STYLE_FIELD: &str = "bestStyleByDifficulty";
const TIMES_FIELD: &str = "bestTimesByDifficulty";
const WAVE_INT_FIELD: &str = "wave";

fn to_strings(values: Vec<f32>) -> Vec<String> {
    values.iter().map(|v| v.to_string()).collect()
}

fn to_f32(values: &[String]) -> Vec<f32> {
    values.iter().filter_map(|v| v.parse().ok()).collect()
}

impl ParsableClass for CybergrindData {
    const CLASS_NAME: &'static str = "EndlessProgress";
    const FILE_NAME: &'static str = "endlessprogress.bepis";

    fn get_file_exists(&self) -> bool {
        self.file_exists
    }

    fn set_file_exists(&mut self, exists: bool) {
        self.file_exists = exists;
    }

    fn parse(class: &Class) -> Option<Self> {
        let fields = &class.fields;
        Some(Self {
            waves: to_strings(read_f32_array(fields, WAVES_FIELD)),
            kills: to_strings(
                read_i32_array(fields, KILLS_FIELD)
                    .iter()
                    .map(|v| *v as f32)
                    .collect::<Vec<f32>>(),
            ),
            style: to_strings(
                read_i32_array(fields, STYLE_FIELD)
                    .iter()
                    .map(|v| *v as f32)
                    .collect::<Vec<f32>>(),
            ),
            times: to_strings(read_f32_array(fields, TIMES_FIELD)),
            file_exists: true,
            original_fields: class.fields.clone(),
            dirty: false,
            decoded: true,
        })
    }

    fn unparse(&self) -> Option<FieldMap> {
        let mut fields = self.original_fields.clone();

        write_i32(&mut fields, WAVE_INT_FIELD, 0);
        write_f32_array(&mut fields, WAVES_FIELD, to_f32(&self.waves));
        write_i32_array(
            &mut fields,
            KILLS_FIELD,
            to_f32(&self.kills).iter().map(|v| *v as i32).collect(),
        );
        write_i32_array(
            &mut fields,
            STYLE_FIELD,
            to_f32(&self.style).iter().map(|v| *v as i32).collect(),
        );
        write_f32_array(&mut fields, TIMES_FIELD, to_f32(&self.times));

        Some(fields)
    }
}

impl CybergrindData {
    pub fn save_to(&self, dir: &Path) -> Result<(), io::Error> {
        let path = dir.join(Self::FILE_NAME);
        if let Some(fields) = self.unparse() {
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

    pub fn delete_from(dir: &Path) {
        let path = dir.join(Self::FILE_NAME);
        if path.exists() {
            let _ = std::fs::remove_file(path);
        }
    }
}

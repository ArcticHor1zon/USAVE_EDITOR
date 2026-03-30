use super::{
    cybergrind::CybergrindData, difficulty::DifficultyData, general::GeneralData, level::LevelData,
    traits::LoadableSavable,
};
use crate::{
    debug_log,
    enums::{Difficulty, Level},
};
use std::{collections::BTreeMap, io, path::Path};

type LevelMap = BTreeMap<Level, LevelData>;
type DifficultyMap = BTreeMap<Difficulty, DifficultyData>;

#[derive(Debug)]
pub struct Classes {
    pub levels: LevelMap,
    pub cybergrind: CybergrindData,
    pub difficulty: DifficultyMap,
    pub general: GeneralData,
}

impl Classes {
    pub fn load<P: AsRef<Path>>(save_path: P) -> Option<Self> {
        let path = save_path.as_ref();

        let general = GeneralData::load(path);
        if general.decoded {
            debug_log!("file", "Loaded generalprogress.bepis");
        } else if path.join("generalprogress.bepis").exists() {
            debug_log!(
                "warn",
                "generalprogress.bepis exists but could not be decoded"
            );
        }

        let cybergrind = CybergrindData::load(path);
        if cybergrind.decoded {
            debug_log!("file", "Loaded endlessprogress.bepis");
        } else if path.join("endlessprogress.bepis").exists() {
            debug_log!(
                "warn",
                "endlessprogress.bepis exists but could not be decoded"
            );
        }

        let cybergrind = CybergrindData::load(path);
        if cybergrind.decoded {
            debug_log!("file", "Loaded endlessprogress.bepis");
        } else if path.join("endlessprogress.bepis").exists() {
            debug_log!(
                "warn",
                "endlessprogress.bepis exists but could not be decoded"
            );
        }

        let levels = LevelMap::load(path);
        let loaded_levels = levels.values().filter(|d| d.decoded).count();
        let total_levels = levels.len();
        debug_log!("info", "Levels: {}/{} decoded", loaded_levels, total_levels);

        let difficulty = DifficultyMap::load(path);
        let loaded_diff = difficulty.values().filter(|d| d.decoded).count();
        let total_diff = difficulty.len();
        if total_diff > 0 {
            debug_log!("info", "Difficulty: {}/{} decoded", loaded_diff, total_diff);
        }

        Some(Self {
            levels,
            cybergrind,
            difficulty,
            general,
        })
    }

    pub fn save<P: AsRef<Path>>(&self, save_path: P) -> Result<(), io::Error> {
        self.levels.save(&save_path)?;
        self.cybergrind.save(&save_path)?;
        self.difficulty.save(&save_path)?;
        self.general.save(&save_path)
    }
}

use crate::{
    class::{classes::Classes, general::GeneralData, level::LevelData},
    debug_log,
    enums::{Act, Difficulty, Level, LevelRank, Lockable, SaveSlot, SecretLevel, WeaponType},
};
use eframe::{
    egui::{Button, CentralPanel, ComboBox, Context, Layout, ScrollArea, TextEdit, Ui},
    emath::Align,
    App, CreationContext, Frame,
};
use registry::{Data, Hive, Security};
use std::path::{Path, PathBuf};
use strum::IntoEnumIterator;

pub struct SaveEditorApp {
    save_path: Option<PathBuf>,
    classes: Option<Classes>,

    save_slot: SaveSlot,
    path_edit: String,
    load_enabled: bool,
    difficulty: Difficulty,
}

impl SaveEditorApp {
    fn mark_dirty_if_loaded(&mut self) {
        if let Some(classes) = &mut self.classes {
            if classes.general.file_exists {
                classes.general.dirty = true;
            }
            if classes.cybergrind.file_exists {
                classes.cybergrind.dirty = true;
            }
        }
    }

    fn save_dirty(&self) {
        let save_dir = match self.resolved_save_path() {
            Some(p) => p,
            None => return,
        };
        let classes = match &self.classes {
            Some(c) => c,
            None => return,
        };

        if classes.general.dirty && classes.general.decoded {
            if let Err(e) = classes.general.save_to(&save_dir) {
                debug_log!("error", "Save generalprogress.bepis failed: {}", e);
            }
        }
        if classes.cybergrind.dirty && classes.cybergrind.decoded {
            if let Err(e) = classes.cybergrind.save_to(&save_dir) {
                debug_log!("error", "Save endlessprogress.bepis failed: {}", e);
            }
        }
        for (diff, data) in &classes.difficulty {
            if data.dirty && data.decoded {
                if let Err(e) = data.save_to(diff, &save_dir) {
                    debug_log!(
                        "error",
                        "Save difficulty{}progress.bepis failed: {}",
                        *diff as u8,
                        e
                    );
                }
            }
        }
        for (level, data) in &classes.levels {
            if data.dirty && data.decoded {
                if let Err(e) = data.save_to(level, &save_dir) {
                    debug_log!(
                        "error",
                        "Save lvl{}progress.bepis failed: {}",
                        *level as u16,
                        e
                    );
                }
            }
        }
    }

    fn clear_dirty(&mut self) {
        if let Some(classes) = &mut self.classes {
            classes.general.dirty = false;
            classes.cybergrind.dirty = false;
            for data in classes.difficulty.values_mut() {
                data.dirty = false;
            }
            for data in classes.levels.values_mut() {
                data.dirty = false;
            }
        }
    }

    fn resolved_save_path(&self) -> Option<PathBuf> {
        let path = self.save_path.as_ref()?;
        let slot_folder = format!("Slot{}", self.save_slot as u8);

        if path.ends_with(&slot_folder) {
            Some(path.clone())
        } else {
            Some(path.join(&slot_folder))
        }
    }

    pub fn new(_cc: &CreationContext) -> Self {
        debug_log!("info", "Application starting");

        let save_path = detect_save_path(&SaveSlot::One);
        let load_enabled = save_path.is_some();
        let classes;
        let path_edit;
        match &save_path {
            Some(save_path) => {
                debug_log!("info", "Auto-detected save path: {}", save_path.display());
                classes = Classes::load(save_path);
                if classes.is_some() {
                    debug_log!("info", "Save files loaded successfully");
                } else {
                    debug_log!("warn", "Failed to load save files");
                }
                path_edit = save_path.to_string_lossy().to_string();
            }
            None => {
                debug_log!("info", "No save path detected");
                classes = None;
                path_edit = String::new();
            }
        };

        Self {
            save_path,
            classes,

            save_slot: SaveSlot::One,
            path_edit,
            load_enabled,
            difficulty: Difficulty::Standard,
        }
    }

    fn update_top_bar(&mut self, ui: &mut Ui) {
        ui.horizontal(|ui| {
            ui.add_space(5.0);
            ui.label("Save path: ");

            if ui
                .add(TextEdit::singleline(&mut self.path_edit).desired_width(450.0))
                .changed()
            {
                let path = Path::new(&self.path_edit);
                self.load_enabled = path.exists();
                self.save_path = if path.exists() {
                    debug_log!("action", "Path set: {}", path.display());
                    Some(path.to_path_buf())
                } else {
                    debug_log!("warn", "Path does not exist: {}", path.display());
                    None
                }
            }

            if ui.button("Auto-detect").clicked() {
                debug_log!(
                    "action",
                    "Auto-detect clicked (slot {})",
                    self.save_slot as u8
                );
                if let Some(save_path) = detect_save_path(&self.save_slot) {
                    self.path_edit = save_path.to_string_lossy().to_string();
                    self.save_path = Some(save_path);
                    self.load_enabled = true;
                    debug_log!(
                        "info",
                        "Auto-detected: {}",
                        self.save_path.as_ref().unwrap().display()
                    );
                } else {
                    debug_log!(
                        "warn",
                        "Auto-detect failed for slot {}",
                        self.save_slot as u8
                    );
                }
            }

            ui.add_space(5.0);
            ui.label("Save Slot:");

            let prev_slot = self.save_slot;

            ComboBox::from_id_source("save slot")
                .selected_text((self.save_slot as u8).to_string())
                .width(20.0)
                .show_ui(ui, |ui| {
                    ui.selectable_value(&mut self.save_slot, SaveSlot::One, "1");
                    ui.selectable_value(&mut self.save_slot, SaveSlot::Two, "2");
                    ui.selectable_value(&mut self.save_slot, SaveSlot::Three, "3");
                    ui.selectable_value(&mut self.save_slot, SaveSlot::Four, "4");
                    ui.selectable_value(&mut self.save_slot, SaveSlot::Five, "5");
                });

            if self.save_slot != prev_slot {
                debug_log!(
                    "action",
                    "Slot changed: {} -> {}",
                    prev_slot as u8,
                    self.save_slot as u8
                );
                if let Some(save_path) = detect_save_path(&self.save_slot) {
                    self.path_edit = save_path.to_string_lossy().to_string();
                    self.save_path = Some(save_path);
                    self.load_enabled = true;
                    debug_log!(
                        "info",
                        "Auto-detected path: {}",
                        self.save_path.as_ref().unwrap().display()
                    );
                }
            }

            ui.add_space(5.0);

            if ui
                .add_enabled(self.load_enabled, Button::new("Load"))
                .clicked()
            {
                if let Some(save_path) = self.resolved_save_path() {
                    debug_log!("action", "Load clicked");
                    debug_log!("file", "Loading from: {}", save_path.display());
                    self.classes = Classes::load(&save_path);
                    if self.classes.is_some() {
                        debug_log!("file", "Load successful");
                    } else {
                        debug_log!("error", "Load failed");
                    }
                };
            }

            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                ui.add_space(10.0);

                let prev_diff = self.difficulty;

                ComboBox::from_id_source("difficulty_selector")
                    .selected_text(self.difficulty.to_string())
                    .width(100.0)
                    .show_ui(ui, |ui| {
                        for diff in Difficulty::iter() {
                            ui.selectable_value(&mut self.difficulty, diff, diff.to_string());
                        }
                    });

                if self.difficulty != prev_diff {
                    debug_log!(
                        "action",
                        "Difficulty changed: {} -> {}",
                        prev_diff,
                        self.difficulty
                    );
                }

                ui.label("Difficulty: ");
            });
        });
    }

    fn update_single_level(&mut self, ui: &mut Ui, level: &Level) -> Option<()> {
        let difficulty = self.difficulty as usize;
        let save_dir = self.resolved_save_path();

        let classes = self.classes.as_mut()?;
        let level_data = classes.levels.get_mut(level)?;
        ui.horizontal(|ui| {
            ui.label("Rank: ");

            let rank = level_data.ranks.get_mut(difficulty)?;

            ComboBox::from_id_source(format!("level {} rank", *level as u16))
                .selected_text(rank.to_string())
                .width(70.0)
                .show_ui(ui, |ui| {
                    if ui.selectable_value(rank, LevelRank::None, "None").clicked()
                        || ui.selectable_value(rank, LevelRank::D, "D").clicked()
                        || ui.selectable_value(rank, LevelRank::C, "C").clicked()
                        || ui.selectable_value(rank, LevelRank::B, "B").clicked()
                        || ui.selectable_value(rank, LevelRank::A, "A").clicked()
                        || ui.selectable_value(rank, LevelRank::S, "S").clicked()
                        || ui.selectable_value(rank, LevelRank::P, "P").clicked()
                    {
                        debug_log!("data", "{} rank -> {}", level, *rank);
                        level_data.dirty = true;
                    }

                    Some(())
                });

            Some(())
        });

        if level.is_prime() {
            ui.horizontal(|ui| {
                ui.label("State: ");

                let difficulty_data = classes.difficulty.get_mut(&self.difficulty)?;
                let state = difficulty_data
                    .prime_levels
                    .get_mut(level.get_prime_index()? as usize)?;

                ComboBox::from_id_source(format!("level {} state", *level as u16))
                    .selected_text(state.to_string())
                    .show_ui(ui, |ui| {
                        if ui
                            .selectable_value(state, Lockable::Locked, "Locked")
                            .clicked()
                        {
                            debug_log!("data", "Prime {} state -> Locked", level);
                            difficulty_data.file_exists = true;
                            difficulty_data.dirty = true;
                        }
                        if ui
                            .selectable_value(state, Lockable::Unlocked, "Unlocked")
                            .clicked()
                        {
                            debug_log!("data", "Prime {} state -> Unlocked", level);
                            difficulty_data.file_exists = true;
                            difficulty_data.dirty = true;
                        }
                        if ui
                            .selectable_value(state, Lockable::Completed, "Completed")
                            .clicked()
                        {
                            debug_log!("data", "Prime {} state -> Completed", level);
                            difficulty_data.file_exists = true;
                            difficulty_data.dirty = true;
                        }
                    });

                Some(())
            });
        }

        if !level_data.secrets_found.is_empty() {
            ui.horizontal(|ui| {
                ui.label("Secrets found: ");
                for secret in &mut level_data.secrets_found {
                    ui.checkbox(secret, "");
                }
            });
        }

        ui.horizontal(|ui| {
            if ui
                .add_enabled(!level_data.file_exists, Button::new("Create file"))
                .clicked()
            {
                level_data.file_exists = true;
                if let Some(ref dir) = save_dir {
                    match level_data.save_to(level, dir) {
                        Ok(_) => debug_log!("file", "Created: lvl{}progress.bepis", *level as u16),
                        Err(e) => {
                            debug_log!("error", "Create failed: lvl{} - {}", *level as u16, e)
                        }
                    }
                }
            }

            if ui
                .add_enabled(level_data.file_exists, Button::new("Delete file"))
                .clicked()
            {
                level_data.file_exists = false;
                if let Some(ref dir) = save_dir {
                    LevelData::delete_from(level, dir);
                    debug_log!("file", "Deleted: lvl{}progress.bepis", *level as u16);
                }
            }
        });

        Some(())
    }

    fn update_secret_level(&mut self, ui: &mut Ui, secret_level: &SecretLevel) {
        if !secret_level.is_prime() && !secret_level.is_encore() {
            ui.collapsing(secret_level.to_string(), |ui| {
                ui.horizontal(|ui| {
                    ui.label("State: ");

                    let state = self
                        .classes
                        .as_mut()?
                        .general
                        .secret_missions
                        .get_mut(&secret_level)?;

                    ComboBox::from_id_source(format!("secret_level {} state", *secret_level as u8))
                        .selected_text(state.to_string())
                        .show_ui(ui, |ui| {
                            if ui
                                .selectable_value(state, Lockable::Locked, "Locked")
                                .clicked()
                                || ui
                                    .selectable_value(state, Lockable::Unlocked, "Unlocked")
                                    .clicked()
                                || ui
                                    .selectable_value(state, Lockable::Completed, "Completed")
                                    .clicked()
                            {
                                debug_log!("data", "{} state -> {}", secret_level, *state);
                            }
                        });

                    Some(())
                });
            });
        }
    }

    fn update_levels(&mut self, ui: &mut Ui) {
        let levels_width = (ui.available_width() * 0.35).clamp(250.0, 450.0);

        ui.vertical(|ui| {
            ui.set_width(levels_width);
            ui.heading("Levels");
            ui.separator();

            ScrollArea::vertical()
                .auto_shrink([false, false])
                .show(ui, |ui| {
                    ui.set_width(levels_width);
                    for act in Act::iter() {
                        ui.collapsing(act.to_string(), |ui| {
                            for layer in act.get_layers() {
                                let regular_levels: Vec<_> = layer
                                    .get_levels()
                                    .iter()
                                    .filter(|l| !l.is_prime())
                                    .collect();
                                if !regular_levels.is_empty() {
                                    ui.collapsing(layer.to_string(), |ui| {
                                        for level in regular_levels {
                                            ui.collapsing(level.to_string(), |ui| {
                                                self.update_single_level(ui, level);
                                            });
                                        }
                                        self.update_secret_level(ui, &layer.get_secret_level());
                                    });
                                }
                            }
                        });
                    }

                    ui.collapsing("PRIME SANCTUMS", |ui| {
                        for level in [Level::SoulSurvivor, Level::WaitOfTheWorld] {
                            ui.collapsing(level.to_string(), |ui| {
                                self.update_single_level(ui, &level);
                            });
                        }
                    });
                });
        });
    }

    fn update_general(&mut self, ui: &mut Ui) {
        let save_dir = self.resolved_save_path();

        ui.vertical(|ui| {
            let available_width = ui.available_width();
            ui.heading("General data");
            ui.separator();

            let classes = self.classes.as_mut()?;

            ui.horizontal(|ui| {
                ui.label("Money:");
                if ui
                    .text_edit_singleline(&mut classes.general.money)
                    .changed()
                {
                    validate_u32(&mut classes.general.money);
                    debug_log!("data", "Money -> {}", classes.general.money);
                    classes.general.dirty = true;
                }
            });

            ui.horizontal(|ui| {
                ui.label("Intro seen:");
                if ui.checkbox(&mut classes.general.intro_seen, "").changed() {
                    debug_log!("data", "Intro seen -> {}", classes.general.intro_seen);
                    classes.general.dirty = true;
                }
            });

            ui.horizontal(|ui| {
                ui.label("Tutorial beat:");
                if ui
                    .checkbox(&mut classes.general.tutorial_beat, "")
                    .changed()
                {
                    debug_log!("data", "Tutorial beat -> {}", classes.general.tutorial_beat);
                    classes.general.dirty = true;
                }
            });

            ui.horizontal(|ui| {
                ui.label("Clash mode unlocked:");
                if ui
                    .checkbox(&mut classes.general.clash_mode_unlocked, "")
                    .changed()
                {
                    debug_log!(
                        "data",
                        "Clash mode -> {}",
                        classes.general.clash_mode_unlocked
                    );
                }
            });

            ui.collapsing("Unlockables", |ui| {
                ui.columns(2, |column| {
                    column[0].add_space(1.0);
                    for (unlockable_type, found) in classes.general.unlockables_found.iter_mut() {
                        column[0].label(unlockable_type.to_string() + " Found:");
                        column[0].add_space(4.0);
                        column[1].checkbox(found, "");
                    }
                });
            });

            ui.collapsing("Weapons", |ui| {
                ui.set_max_height(ui.available_height() - 55.0);
                ScrollArea::vertical().show(ui, |ui| {
                    for weapon in WeaponType::iter() {
                        ui.collapsing(weapon.to_string() + "s", |ui| {
                            ui.columns(2, |column| {
                                column[0].add_space(1.0);
                                if let Some(customizable) = weapon.get_customizable() {
                                    column[0]
                                        .with_layout(Layout::right_to_left(Align::Min), |ui| {
                                            ui.label("Customizable:")
                                        });
                                    column[0].add_space(3.625);
                                    column[1].checkbox(
                                        classes
                                            .general
                                            .weapons_customizable
                                            .get_mut(&customizable)?,
                                        "",
                                    );
                                }

                                for variant in weapon.get_unlockable_variants() {
                                    column[0]
                                        .with_layout(Layout::right_to_left(Align::Min), |ui| {
                                            ui.label(variant.to_string() + " Unlocked:")
                                        });
                                    column[0].add_space(3.625);
                                    column[1].checkbox(
                                        classes.general.unlocked_weapons.get_mut(&variant)?,
                                        "",
                                    );
                                }

                                Some(())
                            });
                        });
                    }
                });
            });

            ui.collapsing("Enemies", |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    ui.columns(2, |column| {
                        column[0].add_space(1.0);
                        for (enemy_type, state) in classes.general.enemies_discovered.iter_mut() {
                            column[0].with_layout(Layout::right_to_left(Align::Min), |ui| {
                                ui.label(enemy_type.to_string() + ":")
                            });
                            column[0].add_space(3.625);

                            ComboBox::from_id_source(format!("enemy {} state", *enemy_type as u8))
                                .width(140.0)
                                .selected_text(match state {
                                    Lockable::Locked => "Undiscovered",
                                    Lockable::Unlocked => "Partially Discovered",
                                    Lockable::Completed => "Fully Discovered",
                                })
                                .show_ui(&mut column[1], |ui| {
                                    ui.selectable_value(state, Lockable::Locked, "Undiscovered");
                                    ui.selectable_value(
                                        state,
                                        Lockable::Unlocked,
                                        "Partially Discovered",
                                    );
                                    ui.selectable_value(
                                        state,
                                        Lockable::Completed,
                                        "Fully Discovered",
                                    );

                                    Some(())
                                });
                        }
                    });
                });
            });

            ui.add_space(10.0);

            ui.horizontal(|ui| {
                if ui
                    .add_enabled(!classes.general.file_exists, Button::new("Create file"))
                    .clicked()
                {
                    classes.general.file_exists = true;
                    if let Some(ref dir) = save_dir {
                        match classes.general.save_to(dir) {
                            Ok(_) => debug_log!("file", "Created: generalprogress.bepis"),
                            Err(e) => {
                                debug_log!("error", "Create failed: generalprogress.bepis - {}", e)
                            }
                        }
                    }
                }

                if ui
                    .add_enabled(classes.general.file_exists, Button::new("Delete file"))
                    .clicked()
                {
                    classes.general.file_exists = false;
                    if let Some(ref dir) = save_dir {
                        GeneralData::delete_from(dir);
                        debug_log!("file", "Deleted: generalprogress.bepis");
                    }
                }
            });

            ui.set_height(ui.available_height());
            ui.set_width(available_width);

            Some(())
        });
    }

    fn update_cybergrind(&mut self, ui: &mut Ui) {
        let difficulty = self.difficulty as usize;

        ui.vertical(|ui| {
            ui.heading("Cybergrind");
            ui.separator();

            let classes = self.classes.as_mut()?;
            let wave = classes.cybergrind.waves.get_mut(difficulty)?;
            let kills = classes.cybergrind.kills.get_mut(difficulty)?;
            let style = classes.cybergrind.style.get_mut(difficulty)?;
            let time = classes.cybergrind.times.get_mut(difficulty)?;

            ui.horizontal(|ui| {
                ui.label("Wave:");
                if ui.text_edit_singleline(wave).changed() {
                    validate_f32(wave);
                    debug_log!("data", "Cybergrind wave -> {}", wave);
                }
            });

            ui.horizontal(|ui| {
                ui.label("Kills:");
                if ui.text_edit_singleline(kills).changed() {
                    validate_u32(kills);
                    debug_log!("data", "Cybergrind kills -> {}", kills);
                }
            });

            ui.horizontal(|ui| {
                ui.label("Style:");
                if ui.text_edit_singleline(style).changed() {
                    validate_u32(style);
                    debug_log!("data", "Cybergrind style -> {}", style);
                }
            });

            ui.horizontal(|ui| {
                ui.label("Time (s):");
                if ui.text_edit_singleline(time).changed() {
                    validate_f32(time);
                    debug_log!("data", "Cybergrind time -> {}", time);
                }
            });

            ui.horizontal(|ui| {
                if ui
                    .add_enabled(!classes.cybergrind.file_exists, Button::new("Create file"))
                    .clicked()
                {
                    classes.cybergrind.file_exists = true;
                    debug_log!("file", "Created: endlessprogress.bepis");
                }

                if ui
                    .add_enabled(classes.cybergrind.file_exists, Button::new("Delete file"))
                    .clicked()
                {
                    classes.cybergrind.file_exists = false;
                    debug_log!("file", "Deleted: endlessprogress.bepis");
                }
            });

            Some(())
        });
    }
}

impl App for SaveEditorApp {
    fn update(&mut self, ctx: &Context, _frame: &mut Frame) {
        let interacted = ctx.input(|i| i.pointer.any_click() || !i.events.is_empty());

        CentralPanel::default().show(ctx, |ui| {
            self.update_top_bar(ui);
            ui.separator();

            let available_height = ui.available_height();

            ui.horizontal(|ui| {
                ui.vertical(|ui| {
                    ui.set_height(available_height);
                    self.update_levels(ui)
                });
                ui.vertical(|ui| {
                    self.update_cybergrind(ui);
                    ui.add_space(5.0);
                    self.update_general(ui);
                });
            });
        });

        if interacted {
            self.mark_dirty_if_loaded();
        }
        self.save_dirty();
        self.clear_dirty();
    }
}

fn detect_save_path(save_slot: &SaveSlot) -> Option<PathBuf> {
    let regkey = Hive::LocalMachine
        .open(r"SOFTWARE\WOW6432Node\Valve\Steam", Security::Read)
        .ok()?;

    let data = regkey.value("InstallPath").ok()?;

    match data {
        Data::String(path_str) => {
            let mut path = PathBuf::from(path_str.to_os_string());
            path.push(format!(
                r"steamapps\common\ULTRAKILL\Saves\Slot{}",
                *save_slot as u8
            ));

            if path.try_exists().ok()? {
                Some(path)
            } else {
                None
            }
        }
        _ => None,
    }
}

fn validate_f32(value: &mut String) {
    if !value.is_empty() && value.parse::<f32>().is_err() {
        let mut new_value = String::new();
        let mut encountered_decimal_point = false;

        for char in value.chars() {
            if char.is_digit(10) {
                new_value.push(char);
            } else if char == '.' && !encountered_decimal_point {
                new_value.push('.');
                encountered_decimal_point = true;
            }
        }

        if !new_value.parse::<f32>().is_err() {
            *value = new_value;
        } else {
            *value = String::new();
        }
    }
}

fn validate_u32(value: &mut String) {
    if !value.is_empty() && value.parse::<u32>().is_err() {
        let mut new_value = String::new();

        for char in value.chars() {
            if char.is_digit(10) {
                new_value.push(char);
            }
        }

        if !new_value.parse::<u32>().is_err() {
            *value = new_value;
        } else {
            *value = String::new();
        }
    }
}

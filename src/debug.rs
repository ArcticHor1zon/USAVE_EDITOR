pub static DEBUG: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

pub fn init() {
    DEBUG.store(true, std::sync::atomic::Ordering::Relaxed);
    unsafe {
        extern "system" {
            fn AllocConsole() -> i32;
        }
        AllocConsole();
    }
    println!("╔══════════════════════════════════════════════════════════════╗");
    println!("║  ULTRAKILL Save Editor - Debug Console                     ║");
    println!("╚══════════════════════════════════════════════════════════════╝");
    println!();
}

pub fn is_enabled() -> bool {
    DEBUG.load(std::sync::atomic::Ordering::Relaxed)
}

#[macro_export]
macro_rules! debug_log {
    ("action", $($arg:tt)*) => {
        if $crate::debug::is_enabled() { println!("[ACTION]  {}", format!($($arg)*)); }
    };
    ("info", $($arg:tt)*) => {
        if $crate::debug::is_enabled() { println!("[INFO]    {}", format!($($arg)*)); }
    };
    ("warn", $($arg:tt)*) => {
        if $crate::debug::is_enabled() { println!("[WARN]    {}", format!($($arg)*)); }
    };
    ("error", $($arg:tt)*) => {
        if $crate::debug::is_enabled() { println!("[ERROR]   {}", format!($($arg)*)); }
    };
    ("file", $($arg:tt)*) => {
        if $crate::debug::is_enabled() { println!("[FILE]    {}", format!($($arg)*)); }
    };
    ("data", $($arg:tt)*) => {
        if $crate::debug::is_enabled() { println!("[DATA]    {}", format!($($arg)*)); }
    };
    ($($arg:tt)*) => {
        if $crate::debug::is_enabled() { println!("[DEBUG]   {}", format!($($arg)*)); }
    };
}

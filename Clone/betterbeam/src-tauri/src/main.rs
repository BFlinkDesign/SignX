#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, menu::{Menu, Submenu, MenuItem}, tray::{SystemTray, SystemTrayMenu, SystemTrayEvent}};

mod jobs;
mod pdf;
mod ocr; // placeholder (frontend uses tesseract.js)
mod detect;
mod scale;
mod measure;
mod map;
mod raster;

#[tauri::command]
fn open_in_explorer(path: String) -> Result<(), String> {
  #[cfg(target_os = "windows")]
  {
    tauri_plugin_shell::open::that(path).map_err(|e| e.to_string())
  }
  #[cfg(not(target_os = "windows"))]
  {
    tauri_plugin_shell::open::that(path).map_err(|e| e.to_string())
  }
}

fn make_menu() -> Menu {
  let file = Submenu::new("File", Menu::with_items([
    MenuItem::new("open", "Open…", true, None),
    MenuItem::new("save_as", "Save As…", true, None),
    MenuItem::separator(),
    MenuItem::new("quit", "Quit", true, None),
  ]));

  let view = Submenu::new("View", Menu::with_items([
    MenuItem::new("reload", "Reload", true, None),
    MenuItem::new("toggle_devtools", "Toggle DevTools", true, None),
  ]));

  let help = Submenu::new("Help", Menu::with_items([
    MenuItem::new("about", "About", true, None),
  ]));

  Menu::with_items([file, view, help])
}

fn make_tray() -> SystemTray {
  let tray_menu = SystemTrayMenu::new()
    .add_item(MenuItem::new("show", "Show", true, None))
    .add_item(MenuItem::new("hide", "Hide", true, None))
    .add_native_item(tauri::menu::NativeItem::Separator)
    .add_item(MenuItem::new("quit", "Quit", true, None));

  SystemTray::new().with_menu(tray_menu)
}

fn main() {
  let menu = make_menu();
  let tray = make_tray();

  tauri::Builder::default()
    // Persist window size/position
    .plugin(tauri_plugin_window_state::Builder::default().build())
    // Logging (file & console)
    .plugin(tauri_plugin_log::Builder::default().build())
    // FS + Dialog + Shell
    .plugin(tauri_plugin_fs::init())
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_shell::init())
    // Single instance
    .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
      if let Some(w) = app.get_window("main") { let _ = w.unminimize(); let _ = w.show(); let _ = w.set_focus(); }
    }))
    // UI chrome
    .menu(menu)
    .on_menu_event(|app, e| {
      match e.id().as_ref() {
        "open" => {
          let app = app.clone();
          tauri::async_runtime::spawn(async move {
            if let Some(path) = tauri_plugin_dialog::DialogBuilder::new().pick_file().await {
              let path_str = path.to_string_lossy().to_string();
              let _ = app.emit("file:selected", path_str);
            }
          });
        }
        "save_as" => {
          let app = app.clone();
          tauri::async_runtime::spawn(async move {
            if let Some(path) = tauri_plugin_dialog::DialogBuilder::new().save_file().await {
              let path_str = path.to_string_lossy().to_string();
              let _ = app.emit("file:save_as", path_str);
            }
          });
        }
        "reload" => { if let Some(w) = app.get_window("main") { let _ = w.eval("location.reload()"); } }
        "toggle_devtools" => { if let Some(w) = app.get_window("main") { let _ = w.open_devtools(); } }
        "about" => {
          let _ = tauri_plugin_dialog::MessageDialogBuilder::new("BetterBeam", "BetterBeam\n© YourCo")
            .kind(tauri_plugin_dialog::MessageDialogKind::Info)
            .show(|_| {});
        }
        "quit" => app.exit(0),
        _ => {}
      }
    })
    .system_tray(tray)
    .on_tray_event(|app, event| match event {
      SystemTrayEvent::MenuItemClick { id, .. } => match id.as_ref() {
        "show" => { if let Some(w) = app.get_window("main") { let _ = w.show(); let _ = w.set_focus(); } }
        "hide" => { if let Some(w) = app.get_window("main") { let _ = w.hide(); } }
        "quit" => app.exit(0),
        _ => {}
      },
      _ => {}
    })
    .invoke_handler(tauri::generate_handler![
      open_in_explorer,
      jobs::start_auto_takeoff,
      jobs::job_status,
      jobs::job_result,
      detect::detect_symbols,
      prefetch_view
    ])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

#[tauri::command]
fn prefetch_view(pdf_path:String, page:u32, dpi:u32, x0:f32, y0:f32, x1:f32, y1:f32, tile:f32) -> Result<(), String> {
  std::thread::spawn(move || {
    let pdfium = match pdfium_render::prelude::Pdfium::new(
      pdfium_render::prelude::Pdfium::bind_to_system_library()
        .or_else(|_| pdfium_render::prelude::Pdfium::bind_to_builtin_library())
    ) {
      Ok(p) => p, Err(_) => return,
    };
    let doc = match pdfium.load_pdf_from_file(&pdf_path, None) { Ok(d) => d, Err(_) => return };
    let overlap = 64.0;
    let tile = tile.max(256.0).min(1024.0);
    let step = (tile - overlap).max(256.0);
    let mut ty = y0;
    while ty < y1 {
      let mut tx = x0;
      while tx < x1 {
        let tw = tile.min(x1 - tx).max(0.0);
        let th = tile.min(y1 - ty).max(0.0);
        let _ = (|| -> Result<(), String> { let _ = (tx, ty, tw, th, dpi, page); Ok(()) })();
        tx += step;
      }
      ty += step;
    }
  });
  Ok(())
}



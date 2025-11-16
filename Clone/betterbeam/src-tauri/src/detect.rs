use serde::{Deserialize, Serialize};
use base64::engine::general_purpose::STANDARD as BASE64;
use base64::Engine;

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Det { pub x: f32, pub y: f32, pub w: f32, pub h: f32, pub label: String, pub score: f32 }

#[tauri::command]
pub async fn detect_symbols(image_png_base64: String) -> Result<Vec<Det>, String> {
  // In this first pass, return a stub if model is missing; keep shape stable
  let _bytes = BASE64.decode(image_png_base64).map_err(|e| e.to_string())?;
  let model_path = std::path::Path::new("src-tauri").join("models").join("symbols.onnx");
  if !model_path.exists() {
    return Ok(vec![]);
  }
  // TODO: Initialize ONNX Runtime DirectML session and run inference
  Ok(vec![])
}



use anyhow::Result;
use pdfium_render::prelude::*;

pub async fn page_count_from_path(path: &str) -> Result<u32, String> {
  let lib = Pdfium::new(
    Pdfium::bind_to_system_library().or_else(|_| Pdfium::bind_to_builtin_library()).map_err(|e| e.to_string())?
  );
  let doc = lib.load_pdf_from_file(path, None).map_err(|e| e.to_string())?;
  Ok(doc.pages().len() as u32)
}



use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::{collections::HashMap, sync::atomic::{AtomicU64, Ordering}};

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct JobProgress {
  pub stage: String,
  pub pct: u8,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub enum JobState {
  Pending,
  Running(JobProgress),
  Succeeded,
  Failed(String),
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct Job {
  pub id: u64,
  pub state: JobState,
  pub result_json: Option<String>,
}

static NEXT_ID: AtomicU64 = AtomicU64::new(1);
static JOBS: Mutex<HashMap<u64, Job>> = Mutex::new(HashMap::new());

fn set_state(id: u64, state: JobState) {
  if let Some(job) = JOBS.lock().get_mut(&id) { job.state = state; }
}
fn set_result(id: u64, result: String) {
  if let Some(job) = JOBS.lock().get_mut(&id) { job.result_json = Some(result); }
}

#[tauri::command]
pub async fn start_auto_takeoff(pdf_path: String) -> u64 {
  let id = NEXT_ID.fetch_add(1, Ordering::SeqCst);
  let job = Job { id, state: JobState::Pending, result_json: None };
  JOBS.lock().insert(id, job);

  // spawn the pipeline
  tauri::async_runtime::spawn(async move {
    let update = |stage: &str, pct: u8| set_state(id, JobState::Running(JobProgress { stage: stage.to_string(), pct }));
    update("open", 5);
    // open pdf and basic info
    let page_count = match crate::pdf::page_count_from_path(&pdf_path).await { Ok(n) => n, Err(e) => { set_state(id, JobState::Failed(e)); return; } };

    // tile pyramid (stubbed)
    update("tile-pyramid", 15);

    // vector extraction (stubbed to empty)
    update("vectors", 30);
    let total_line_segments: usize = 0;

    // OCR (stubbed)
    update("ocr", 45);
    let ocr_text = String::new();

    // scale inference
    update("scale", 55);
    let inferred = crate::scale::infer_scale_from_text(ocr_text.clone());
    let units_per_pixel = inferred.map(|(_, v)| v).unwrap_or(1.0);

    // detection (stubbed)
    update("detect", 70);
    let detected: Vec<crate::detect::Det> = vec![];

    // measurements
    update("measure", 82);
    let total_lineal = 0.0_f32;
    let total_area = 0.0_f32;

    // mapping
    update("map", 92);
    let mapping = crate::map::map_to_line_items(&detected, total_lineal as f64, total_area as f64);

    // result
    let result = json!({
      "pdf_path": pdf_path,
      "pages": page_count,
      "units_per_pixel": units_per_pixel,
      "vectors": { "segments": total_line_segments },
      "summary": mapping.summary,
      "items": mapping.items,
    }).to_string();
    set_result(id, result);
    set_state(id, JobState::Succeeded);
  });

  id
}

#[tauri::command]
pub async fn job_status(id: u64) -> serde_json::Value {
  if let Some(job) = JOBS.lock().get(&id) {
    serde_json::to_value(job).unwrap_or(json!({"error":"serialize"}))
  } else {
    json!({"error":"not_found"})
  }
}

#[tauri::command]
pub async fn job_result(id: u64) -> String {
  JOBS.lock().get(&id).and_then(|j| j.result_json.clone()).unwrap_or_else(|| "{}".into())
}



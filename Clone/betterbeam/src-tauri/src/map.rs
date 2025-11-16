use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct MappingSummary {
  pub symbols: serde_json::Value,
  pub lineal_feet: f64,
  pub area_sqft: f64,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct LineItem {
  pub sku: String,
  pub qty: u32,
  pub material: String,
  pub finish: String,
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct MappingResult {
  pub summary: MappingSummary,
  pub items: Vec<LineItem>,
}

pub fn map_to_line_items(_dets: &Vec<crate::detect::Det>, lineal: f64, area: f64) -> MappingResult {
  MappingResult {
    summary: MappingSummary {
      symbols: serde_json::json!({}),
      lineal_feet: lineal,
      area_sqft: area,
    },
    items: vec![],
  }
}



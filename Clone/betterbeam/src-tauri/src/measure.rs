pub fn length_px(points: &[(f32, f32)]) -> f64 {
  let mut sum = 0.0_f64;
  for w in points.windows(2) {
    let (x1, y1) = (w[0].0 as f64, w[0].1 as f64);
    let (x2, y2) = (w[1].0 as f64, w[1].1 as f64);
    sum += ((x2 - x1).powi(2) + (y2 - y1).powi(2)).sqrt();
  }
  sum
}

pub fn area_px(points: &[(f32, f32)]) -> f64 {
  if points.len() < 3 { return 0.0; }
  let mut area = 0.0_f64;
  for i in 0..points.len() {
    let (x1, y1) = (points[i].0 as f64, points[i].1 as f64);
    let (x2, y2) = (points[(i + 1) % points.len()].0 as f64, points[(i + 1) % points.len()].1 as f64);
    area += x1 * y2 - x2 * y1;
  }
  area.abs() * 0.5
}



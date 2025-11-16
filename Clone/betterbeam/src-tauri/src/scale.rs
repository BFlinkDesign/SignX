// very small parser for common scale strings; returns (units, units_per_pixel) when possible
pub fn infer_scale_from_text(text: String) -> Option<(String, f32)> {
  let t = text.to_lowercase();
  // handle metric 1:100, 1:50
  if let Some(pos) = t.find("1:") {
    let rest = &t[pos+2..];
    let mut num = String::new();
    for ch in rest.chars() { if ch.is_ascii_digit() { num.push(ch); } else { break; } }
    if let Ok(n) = num.parse::<f32>() { if n > 0.0 { return Some(("m".into(), 1.0 / n)); } }
  }
  // handle imperial like 1/8" = 1'-0"
  if let Some(eq) = t.find('=') {
    let left = t[..eq].trim();
    if let Some(slash) = left.find('/') {
      let (a, b) = left.split_at(slash);
      let b = &b[1..];
      if let (Ok(na), Ok(nb)) = (a.trim().parse::<f32>(), b.trim_matches(['"',' ']).parse::<f32>()) {
        if nb > 0.0 { return Some(("ft".into(), (na/nb) /* inches per foot */ * (1.0/12.0))); }
      }
    }
  }
  None
}



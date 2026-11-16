use anyhow::{Context, Result};
use rage_formats::{parse_yft, parse_ytd};
use rage_render::{export_glb, Facing, GlbOptions, RenderPart, TextureSet};
use std::{env, fs};

fn main() -> Result<()> {
    let a: Vec<String> = env::args().collect();
    if a.len() < 4 { anyhow::bail!("usage: or2-yft2glb input.yft output.glb texture1.ytd [texture2.ytd ...]"); }
    let frag = parse_yft(&fs::read(&a[1]).with_context(|| format!("read {}",a[1]))?).context("parse YFT")?;
    let mut set=TextureSet::new();
    let mut textures_total=0usize;
    let mut decode_failed_total=0usize;
    for path in &a[3..] {
        let ytd=parse_ytd(&fs::read(path).with_context(|| format!("read {}",path))?).with_context(|| format!("parse YTD {}",path))?;
        textures_total += ytd.len();
        decode_failed_total += set.push_layer(&ytd).len();
    }
    let raw=frag.render_parts();
    let parts: Vec<RenderPart<'_>> = raw.into_iter().map(RenderPart::from).collect();
    let opts=GlbOptions{max_texture:0,jpeg_quality:100,facing:Facing::PositiveY,..Default::default()};
    let (glb,report)=export_glb(&parts,&set,&opts).context("export GLB")?;
    fs::write(&a[2],&glb).with_context(|| format!("write {}",a[2]))?;
    println!("OR2_YFT2GLB_PASS parts={} textures={} layers={} decode_failed={} triangles={} missing_textures={} untextured={} bytes={}",
        parts.len(),textures_total,a.len()-3,decode_failed_total,report.triangles,report.missing_textures.len(),report.untextured_geometries,glb.len());
    if !report.missing_textures.is_empty(){println!("MISSING_TEXTURES {:?}",report.missing_textures);}
    Ok(())
}

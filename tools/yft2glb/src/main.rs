use anyhow::{Context, Result};
use rage_formats::{parse_yft, parse_ytd};
use rage_render::{export_glb, Facing, GlbOptions, RenderPart, TextureSet};
use std::{env, fs};

fn main() -> Result<()> {
    let a: Vec<String> = env::args().collect();
    if a.len() != 4 { anyhow::bail!("usage: or2-yft2glb input.yft textures.ytd output.glb"); }
    let frag = parse_yft(&fs::read(&a[1]).with_context(|| format!("read {}",a[1]))?).context("parse YFT")?;
    let textures = parse_ytd(&fs::read(&a[2]).with_context(|| format!("read {}",a[2]))?).context("parse YTD")?;
    let mut set=TextureSet::new();
    let decode_failed=set.push_layer(&textures);
    let raw=frag.render_parts();
    let parts: Vec<RenderPart<'_>> = raw.into_iter().map(RenderPart::from).collect();
    let opts=GlbOptions{max_texture:0,jpeg_quality:100,facing:Facing::Vehicle,..Default::default()};
    let (glb,report)=export_glb(&parts,&set,&opts).context("export GLB")?;
    fs::write(&a[3],&glb).with_context(|| format!("write {}",a[3]))?;
    println!("OR2_YFT2GLB_PASS parts={} textures={} decode_failed={} triangles={} missing_textures={} untextured={} bytes={}",
        parts.len(),textures.len(),decode_failed.len(),report.triangles,report.missing_textures.len(),report.untextured_geometries,glb.len());
    if !decode_failed.is_empty(){println!("DECODE_FAILED {:?}",decode_failed);}
    if !report.missing_textures.is_empty(){println!("MISSING_TEXTURES {:?}",report.missing_textures);}
    Ok(())
}

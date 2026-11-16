use anyhow::{Context, Result};
use rage_formats::{parse_yft, parse_ytd};
use rage_render::{export_glb, GlbOptions, RenderPart, TextureSet};
use std::{env, fs, path::Path};

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 4 {
        anyhow::bail!("usage: rage-yft-to-glb INPUT.yft INPUT.ytd OUTPUT.glb");
    }

    let yft = fs::read(&args[1]).with_context(|| format!("read {}", args[1]))?;
    let ytd = fs::read(&args[2]).with_context(|| format!("read {}", args[2]))?;
    let fragment = parse_yft(&yft).context("parse YFT")?;
    let external = parse_ytd(&ytd).context("parse YTD")?;

    let raw_parts = fragment.render_parts();
    let parts: Vec<RenderPart<'_>> = raw_parts.iter().copied().map(RenderPart::from).collect();

    let mut textures = TextureSet::new();
    let mut decode_failures = Vec::new();
    for part in &parts {
        if let Some(group) = &part.drawable.shader_group {
            decode_failures.extend(textures.push_layer(&group.textures));
        }
    }
    decode_failures.extend(textures.push_layer(&external));

    let options = GlbOptions {
        max_texture: 2048,
        jpeg_quality: 92,
        ..GlbOptions::default()
    };
    let (glb, report) = export_glb(&parts, &textures, &options).context("export GLB")?;

    let output = Path::new(&args[3]);
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(output, &glb).with_context(|| format!("write {}", output.display()))?;

    println!("YFT_GLTF_PASS");
    println!("fragment={}", fragment.name);
    println!("parts={}", parts.len());
    println!("external_textures={}", external.len());
    println!("decoded_texture_slots={}", textures.len());
    println!("decode_failures={:?}", decode_failures);
    println!("triangles={}", report.triangles);
    println!("geometries={}", report.geometries);
    println!("untextured_geometries={}", report.untextured_geometries);
    println!("geometries_without_diffuse={}", report.geometries_without_diffuse);
    println!("missing_textures={:?}", report.missing_textures);
    println!("faces_positive_y={}", report.faces_positive_y);
    println!("glb_bytes={}", glb.len());
    Ok(())
}

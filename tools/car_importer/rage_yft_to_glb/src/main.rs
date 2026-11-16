use anyhow::{Context, Result};
use rage_formats::{parse_yft, parse_ytd};
use rage_formats::renderware::{dff::Dff, txd::Txd};
use rage_render::{export_glb, GlbOptions, RenderPart, TextureSet};
use std::{env, fs, path::Path};

fn export_parts(parts: &[RenderPart<'_>], textures: &TextureSet, output: &Path) -> Result<rage_render::GlbReport> {
    let options = GlbOptions {
        max_texture: 2048,
        jpeg_quality: 92,
        ..GlbOptions::default()
    };
    let (glb, report) = export_glb(parts, textures, &options).context("export GLB")?;
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(output, &glb).with_context(|| format!("write {}", output.display()))?;
    println!("glb_bytes={}", glb.len());
    Ok(report)
}

fn yft_mode(yft_path: &str, ytd_path: &str, out_path: &str) -> Result<()> {
    let yft = fs::read(yft_path).with_context(|| format!("read {yft_path}"))?;
    let ytd = fs::read(ytd_path).with_context(|| format!("read {ytd_path}"))?;
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

    let mut trimmed_aliases = Vec::new();
    for texture in &external {
        let trimmed = texture.name.trim();
        if trimmed != texture.name && !trimmed.is_empty() && textures.alias(trimmed, &texture.name) {
            trimmed_aliases.push((trimmed.to_string(), texture.name.clone()));
        }
    }

    let report = export_parts(&parts, &textures, Path::new(out_path))?;
    println!("YFT_GLTF_PASS");
    println!("fragment={}", fragment.name);
    println!("parts={}", parts.len());
    println!("external_textures={}", external.len());
    println!("decoded_texture_slots={}", textures.len());
    println!("decode_failures={:?}", decode_failures);
    println!("trimmed_aliases={:?}", trimmed_aliases);
    println!("triangles={}", report.triangles);
    println!("geometries={}", report.geometries);
    println!("untextured_geometries={}", report.untextured_geometries);
    println!("geometries_without_diffuse={}", report.geometries_without_diffuse);
    println!("missing_textures={:?}", report.missing_textures);
    println!("faces_positive_y={}", report.faces_positive_y);
    Ok(())
}

fn dff_mode(dff_path: &str, txd_path: Option<&str>, out_path: &str) -> Result<()> {
    let bytes = fs::read(dff_path).with_context(|| format!("read {dff_path}"))?;
    let dff = Dff::parse(&bytes).context("parse DFF")?;
    let entries = dff.drawables().context("adapt DFF drawables")?;
    anyhow::ensure!(!entries.is_empty(), "DFF contains no renderable drawables");

    let parts: Vec<RenderPart<'_>> = entries.iter().map(|e| RenderPart::new(&e.drawable)).collect();
    let mut textures = TextureSet::new();
    let mut texture_count = 0usize;
    let mut decode_failures = Vec::new();
    if let Some(txd_path) = txd_path {
        let bytes = fs::read(txd_path).with_context(|| format!("read {txd_path}"))?;
        let txd = Txd::parse(&bytes).context("parse TXD")?;
        let decoded = txd.textures().context("decode TXD textures")?;
        texture_count = decoded.len();
        decode_failures.extend(textures.push_layer(&decoded));
    }

    let report = export_parts(&parts, &textures, Path::new(out_path))?;
    println!("DFF_GLTF_PASS");
    println!("frames={}", dff.frames.len());
    println!("geometries_source={}", dff.geometries.len());
    println!("atomics={}", dff.atomics.len());
    println!("render_parts={}", parts.len());
    println!("txd_textures={texture_count}");
    println!("decode_failures={:?}", decode_failures);
    println!("triangles={}", report.triangles);
    println!("geometries={}", report.geometries);
    println!("untextured_geometries={}", report.untextured_geometries);
    println!("geometries_without_diffuse={}", report.geometries_without_diffuse);
    println!("missing_textures={:?}", report.missing_textures);
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    match args.as_slice() {
        [_, yft, ytd, output] => yft_mode(yft, ytd, output),
        [_, mode, dff, output] if mode == "dff" => dff_mode(dff, None, output),
        [_, mode, dff, txd, output] if mode == "dff" => dff_mode(dff, Some(txd), output),
        _ => anyhow::bail!(
            "usage:\n  rage-yft-to-glb INPUT.yft INPUT.ytd OUTPUT.glb\n  rage-yft-to-glb dff INPUT.dff [INPUT.txd] OUTPUT.glb"
        ),
    }
}

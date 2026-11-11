//! `cargo xtask screenshots [name…]`: regenerate the README screenshots in `docs/images/`.
//!
//! Every image is a headless render of the real app (`examples/shot.rs`) showing the showcase
//! PDF. That PDF is built only from the OFL fonts and generated artwork in ATTRIBUTION.toml, so
//! the screenshots are contributor-original and policy-compliant (AGENTS.md §1). Afterwards the
//! `docs/images/*.png` entries in ATTRIBUTION.toml are rewritten with fresh hashes, and
//! ATTRIBUTION.md is regenerated.
//!
//! The document is opened by a *relative* path so no local directory names (user names) can
//! appear in a screenshot.

use std::path::Path;
use std::process::Command;

use anyhow::{Context, Result, bail};

/// (file stem, title, what it shows, shot arguments after the PDF path).
pub const SCENES: &[(&str, &str, &str, &[&str])] = &[
    ("openpdf-viewer", "Viewer with comments", "README hero", &["--panel", "comments", "--zoom", "72"]),
    ("openpdf-dark", "Dark theme", "README: themes", &["--theme", "dark", "--panel", "comments", "--page", "11", "--zoom", "80", "--notice", "off"]),
    ("openpdf-organize", "Organize pages", "README: organize", &["--organize", "on", "--panel", "none", "--select", "5,6,7"]),
    ("openpdf-find", "Find text", "README: search", &["--find", "type", "--page", "4", "--zoom", "90", "--panel", "none", "--notice", "off"]),
    ("openpdf-bookmarks", "Bookmarks", "README: navigation", &["--panel", "bookmarks", "--page", "7", "--zoom", "75", "--notice", "off"]),
    ("openpdf-forms", "Interactive form", "README: forms", &["--page", "13", "--fields", "on", "--zoom", "80", "--panel", "fields"]),
    ("openpdf-layers", "Layers", "README: layers", &["--panel", "layers", "--page", "12", "--zoom", "75", "--notice", "off"]),
    (
        "openpdf-scripts",
        "Scripts of the world",
        "README: rendering",
        &["--page", "7", "--zoom", "125", "--left", "closed", "--panel", "none", "--notice", "off"],
    ),
    ("openpdf-properties", "Document properties", "README: metadata", &["--dialog", "properties", "--notice", "off"]),
    ("openpdf-palette", "Command palette", "README: tools", &["--palette", "page", "--notice", "off"]),
    ("openpdf-split", "Split dialog", "README: split", &["--organize", "on", "--panel", "none", "--dialog", "split", "--notice", "off"]),
    ("openpdf-tools", "All tools", "README: tool catalogue", &["--tools", "expanded", "--home", "on"]),
    (
        "openpdf-twoup",
        "Two-up reading",
        "README: layouts",
        &["--layout", "two-up", "--mode", "read", "--page", "4", "--theme", "dark", "--notice", "off"],
    ),
    ("openpdf-ocr-verify", "OCR Verify screen", "README: OCR review", &["--size", "1680x1000", "--ocr-verify", "on"]),
];

const PDF: &str = "dist/demo/openpdf-showcase.pdf";

pub fn run(args: &[String]) -> Result<()> {
    let root = crate::assets::root();
    if !root.join(PDF).is_file() {
        println!("screenshots: building the showcase PDF first");
        crate::demo_pdf::run(&[])?;
    }
    let status = Command::new(env!("CARGO"))
        .args(["build", "--release", "-p", "openpdf-ui-egui", "--example", "shot"])
        .current_dir(&root)
        .status()
        .context("building the shot example")?;
    if !status.success() {
        bail!("building the shot example failed");
    }
    let target = std::env::var("CARGO_TARGET_DIR").map(std::path::PathBuf::from).unwrap_or_else(|_| root.join("target"));
    let shot = target.join("release/examples").join(if cfg!(windows) { "shot.exe" } else { "shot" });
    std::fs::create_dir_all(root.join("docs/images"))?;
    for (name, _, _, scene) in SCENES {
        if !args.is_empty() && !args.iter().any(|a| a == name) {
            continue;
        }
        let out = format!("docs/images/{name}.png");
        let status = Command::new(&shot)
            .arg(&out)
            .arg(PDF)
            .args(["--size", "1440x900", "--scale", "2", "--width", "1600"])
            .args(*scene)
            // Published images show only the embedded, openly licensed fonts (AGENTS.md §1.2).
            .env("OPENPDF_SYSTEM_FONTS", "0")
            .current_dir(&root)
            .status()
            .with_context(|| format!("running shot for {name}"))?;
        if !status.success() {
            bail!("screenshot {name} failed");
        }
    }
    update_attribution(&root)?;
    crate::assets::run(&["--write".to_string()])
}

/// Refresh the OpenPDF screenshot entries while preserving credits for the upstream screenshots.
fn update_attribution(root: &Path) -> Result<()> {
    let path = root.join("ATTRIBUTION.toml");
    let text = std::fs::read_to_string(&path)?;
    // Split into the header and `[[…]]` blocks; replace only screenshots from this fork.
    let mut parts: Vec<String> = Vec::new();
    for (i, block) in text.split("\n[[").enumerate() {
        let block = if i == 0 { block.to_string() } else { format!("[[{block}") };
        if block.starts_with("[[asset]]") && block.contains("path = \"docs/images/openpdf-") {
            continue;
        }
        parts.push(block);
    }
    let mut out = parts.join("\n");
    if !out.ends_with('\n') {
        out.push('\n');
    }
    let mut images: Vec<_> = std::fs::read_dir(root.join("docs/images"))?.flatten().map(|e| e.file_name().to_string_lossy().into_owned()).collect();
    images.sort();
    for file in images.iter().filter(|f| f.starts_with("openpdf-") && f.ends_with(".png")) {
        let stem = file.trim_end_matches(".png");
        let scene = SCENES.iter().find(|(n, ..)| *n == stem);
        let (title, usage) = scene.map(|(_, t, u, _)| (*t, *u)).unwrap_or(("OpenPDF screenshot", "README"));
        let shows_ocr = scene.is_some_and(|(.., args)| args.windows(2).any(|w| w[0] == "--ocr-verify" && w[1] == "on"));
        let contents = if shows_ocr {
            "Shows only OpenPDF UI, its Lucide icons and a synthetic scanned page built from the embedded fonts, with a real recognition (the OCR models) loaded into the Verify screen"
        } else {
            "Shows only OpenPDF UI, Lucide icons and the showcase PDF built from the [[fetched]] OFL fonts"
        };
        let bytes = std::fs::read(root.join("docs/images").join(file))?;
        out.push_str(&format!(
            "\n[[asset]]\npath = \"docs/images/{file}\"\ntitle = \"OpenPDF screenshot: {title}\"\nauthor = \"OpenPDF contributors (generated by `cargo xtask screenshots`)\"\nsource = \"this repository\"\nlicence = \"MIT OR Apache-2.0\"\nlicence_file = \"LICENSE-MIT\"\nkind = \"image\"\nusage = \"{usage}. {contents}\"\nsha256 = \"{}\"\n",
            crate::assets::sha256_hex(&bytes)
        ));
    }
    std::fs::write(&path, out)?;
    Ok(())
}

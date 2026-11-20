# OpenPDF customizations

This is the fork's record of product and distribution decisions. Use the checks below when an upstream merge, refactor or release touches the corresponding behavior. The linked files are current evidence. Update the links and checks as ownership moves between modules or into shared libraries.

## Product identity and artwork

- Ship as OpenPDF across the desktop app, CLI, packages, repository metadata and user-facing documentation. Direct project and release links to the OpenPDF fork. Preserve upstream credit in About, notices and documentation, including the ArtCraft Team attribution. Check the installed app, CLI help and package metadata as well as the [README](../README.md) and [NOTICE](../NOTICE).
- Keep the original upright document icon with its centered PDF lettering. Use the [vector master](../assets/app-icon/openpdf.svg) for platform exports and the fork's [installer artwork](../packaging/macos/dmg/README.md) for the macOS disk image. Inspect the mounted installer and the app in Finder and the Dock after launch. Check provenance through the asset audit.
- On macOS, users can choose OpenPDF as their default PDF reader while macOS retains control of PDF document icons. Check that the packaged app declares its own icon and PDF-opening support and that its PDF document type omits the document-icon override. See the [bundle template](../packaging/macos/Info.plist.in) and [packaging checks](../xtask/src/gates.rs).

## Desktop layout

| Preserve | How to check |
| --- | --- |
| Document tabs share the top row with Home and Open. Tab icons, filenames and the Open label are centered within their controls. Filenames use the interface typography. The search field, action icons and toolbar below have balanced spacing. Native macOS window buttons have room beside Home. | Open two documents, inspect the chrome at normal and narrow widths, and inspect the native window controls on macOS. Exercise the [UI integration tests](../crates/ui-egui/tests/it/ui.rs). |
| In the Tools sidebar, View more and View less align with the tool rows and show the expansion direction. | Expand and collapse the list. Run the UI test named `tools_expansion_label_aligns_with_tool_labels`. |
| Fill & Sign keeps the lock-on-save control aligned with its label. Add Text and Cross use consistent spacing in the vertical toolbar. Text border options open in a popup and fit within the available column. | Switch between Add Text and Cross, open the border options, change a setting, and toggle lock-on-save. Check for clipped or displaced controls. See the [Fill & Sign tests](../crates/ui-egui/tests/it/fill_sign.rs). |

## Fork governance and distribution

- Maintain an independent release path for OpenPDF, including unsigned packages and ad-hoc signing on macOS. Use upstream versions as a reference when selecting a fork version, verify tag availability and target, and preserve published releases and inherited tags. Check the [release procedure](releasing.md) and the [fork release workflow](../.github/workflows/release.yml) when integrating packaging changes.
- Changes reach main through reviewed project workflow and CI on a pull request. Use purpose-based branch names and group commits by topic. Work involving an external change to an upstream repository requires explicit authorization for that repository and action. The authoritative rules are in [AGENTS.md](../AGENTS.md).

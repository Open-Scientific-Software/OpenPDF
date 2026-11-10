//! Position AppKit's own window controls inside the integrated tab row.
//! All calls use the existing safe objc2 wrappers; native buttons keep their actions.

use objc2_app_kit::{NSApplication, NSWindowButton, NSWindowStyleMask};
use objc2_foundation::NSPoint;

pub(crate) fn align_controls(ctx: &egui::Context, row_height: f32) {
    let Some(mtm) = objc2::MainThreadMarker::new() else { return };
    let Some(window) = NSApplication::sharedApplication(mtm).mainWindow() else { return };
    let style = window.styleMask();
    // Sheets and full-screen windows have their own native layout. Never reposition those.
    if !style.contains(NSWindowStyleMask::FullSizeContentView) || style.contains(NSWindowStyleMask::FullScreen) {
        return;
    }
    let Some(close) = window.standardWindowButton(NSWindowButton::CloseButton) else { return };
    let Some(minimize) = window.standardWindowButton(NSWindowButton::MiniaturizeButton) else { return };
    let Some(parent) = close.ancestorSharedWithView(&minimize) else { return };
    let zoom = f64::from(ctx.zoom_factor());
    // The egui row loses one point to its separator; its icons receive a one-point optical
    // adjustment downwards. Match that centre, including the user's interface zoom.
    let centre = (f64::from(row_height) / 2.0 + 0.5) * zoom;
    let window_height = window.frame().size.height;
    if !centre.is_finite() || centre <= 0.0 || !window_height.is_finite() || window_height <= centre {
        return;
    }
    for (index, kind) in [NSWindowButton::CloseButton, NSWindowButton::MiniaturizeButton, NSWindowButton::ZoomButton].into_iter().enumerate() {
        let Some(button) = window.standardWindowButton(kind) else { continue };
        let frame = button.frame();
        // Verify that the common ancestor uses this button's immediate-parent coordinates.
        // A future AppKit hierarchy change should leave the native layout alone.
        let relative = parent.convertRect_fromView(button.bounds(), Some(&button));
        if (relative.origin.x - frame.origin.x).abs() > 0.5 || (relative.origin.y - frame.origin.y).abs() > 0.5 {
            continue;
        }
        // Preserve the native horizontal group at small interface sizes. Chrome reserves
        // at least its normal physical clearance, independently of egui's scale.
        let target = NSPoint::new(20.5 + index as f64 * 22.0, window_height - centre);
        let local = parent.convertPoint_fromView(target, None);
        let origin = NSPoint::new(local.x - frame.size.width / 2.0, local.y - frame.size.height / 2.0);
        if origin.x.is_finite() && origin.y.is_finite() && ((origin.x - frame.origin.x).abs() > 0.01 || (origin.y - frame.origin.y).abs() > 0.01) {
            button.setFrameOrigin(origin);
            let placed = button.convertRect_toView(button.bounds(), None);
            log::debug!(
                "title button {index}: centre ({:.1}, {:.1}) pt from window top-left",
                placed.origin.x + placed.size.width / 2.0,
                window_height - placed.origin.y - placed.size.height / 2.0
            );
        }
    }
}

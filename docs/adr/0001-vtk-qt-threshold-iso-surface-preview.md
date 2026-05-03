# ADR 0001: Use VTK + Qt For Threshold Iso-surface Preview

Status: Accepted

## Context

Aligner v1 needs a main Threshold Iso-surface Preview for Raw Stack and
Aligned Stack inspection. The preview should let users rotate, zoom, and pan a
solid-looking threshold surface while keeping Orthogonal Preview as the
supporting XY / XZ / YZ slice inspection surface.

The preview remains a visual inspection aid. It must not change Preview Stack
export, modify original TIFF files, or claim metrology-grade 3D reconstruction.

## Decision

Use VTK + Qt for the interactive Threshold Iso-surface Preview inside the
PySide6 desktop UI.

The current implementation adds the rendering shell and widget boundary first.
Full threshold iso-surface extraction, preview-volume downsampling, and rebuild
behavior are separate follow-up work.

## Why

VTK provides established scientific visualization primitives for iso-surface
rendering and a normal 3D camera interaction model. Qt integration lets the
preview live inside the existing PySide6 app instead of introducing a separate
viewer process or a custom rendering stack.

This keeps the normal UI focused on threshold iso-surface preview. It also
supports the product decision to keep opacity-based volume rendering, transfer
functions, material presets, and general rendering controls out of scope for
v1.

## Trade-offs

VTK is a heavier dependency than the existing 2D preview path. It increases
install size, can have stricter GUI runtime requirements, and may need special
handling in headless/offscreen tests.

The benefit is that Aligner gets a purpose-built 3D rendering path for
threshold iso-surface preview without hand-rolling camera interaction,
iso-surface rendering, or low-level OpenGL behavior.

## Consequences

- The app dependency metadata must include VTK.
- VTK integration should stay behind a small Qt widget boundary.
- Automated tests should cover import and UI wiring where practical.
- Manual GUI smoke testing remains necessary for true camera interaction on a
  real desktop display.
- Preview settings, mesh export, screenshots, opacity-based volume rendering,
  and transfer-function controls remain out of scope.

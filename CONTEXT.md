# Aligner Domain Context

This document defines the shared domain language for Aligner v1. It describes product concepts, not implementation contracts. `README.md` remains the source of truth for current project status.

## Preview Alignment

Preview Alignment is Aligner v1's output goal: a visually stabilized stack that helps users inspect continuity across FIB serial slices.

It is not metrology-grade 3D reconstruction. The result is meant for preview, review, and export provenance, not for dimensional measurement claims.

## Raw Stack

Raw Stack is the ordered set of original input TIFF slices loaded from a user-selected folder.

The Raw Stack preserves the original files, natural sort order, original slice index, slice spacing, and XY pixel size. Aligner must not modify these input TIFF files.

## Aligned Stack

Aligned Stack is the preview stack produced after Aligner applies coarse alignment, constrained local alignment, optional preview-only Bad Slice replacement, and a common crop region.

The Aligned Stack keeps the same slice count, original index mapping, and z-position rhythm as the Raw Stack.

## Stack Physical Spacing

Stack Physical Spacing describes the physical scale used to proportion preview views.

In v1, XY pixel size is stored in nm and slice spacing is stored in nm. XY pixel size may come from TIFF metadata or from the user-provided toolbar value when metadata is missing. Slice spacing remains the Z spacing source.

Stack Physical Spacing supports visual preview proportions. It does not make Aligner output metrology-grade 3D reconstruction.

## Bad Slice

Bad Slice is a slice that cannot provide reliable neighboring alignment signal and would break preview continuity if used directly.

In v1, Bad Slice status is derived from alignment signals. Replacement is preview-only and must be recorded in metadata.

## Alignment-Unusable

Alignment-Unusable describes the confirmed state of a suspicious slice after alignment-derived checks show it should not directly drive preview continuity.

This is stronger than one weak confidence value. v1 requires confirmation before preview replacement.

## RAFT Padding

RAFT Padding is the internal padding applied around images so RAFT can run on dimensions compatible with the model.

v1 uses reflect-style padding internally and crops RAFT output back to the original image extent before downstream preview use.

## Aligned Crop Region

Aligned Crop Region is the common valid image area shared by all slices after preview transforms.

Exported aligned TIFFs use this region to avoid empty borders introduced by shifts or warps, and metadata records the crop box.

## Threshold Iso-surface Preview

Threshold Iso-surface Preview is the planned main 3D preview surface for Raw Stack and Aligned Stack inspection.

It uses a brightness threshold in original image intensity units to define which voxels contribute to the display surface. Threshold selection is separate from Preview Stack export and does not change the original input files.

## Orthogonal Preview

Orthogonal Preview is the supporting XY, XZ, and YZ slice inspection surface.

Before alignment it shows the Raw Stack. After alignment it shows the Aligned Stack in the same preview panel.

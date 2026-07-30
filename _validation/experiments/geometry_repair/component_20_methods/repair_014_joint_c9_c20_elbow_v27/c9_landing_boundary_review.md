# V27 C9 landing-boundary necessity review

Result: `PASS_V27_C9_LANDING_BOUNDARY_NECESSITY_AUDIT`

The repeatable read-only authority proves that the exact 11-face landing mask
cannot support a cutter-clear surface while its boundary remains fixed.
Boundary vertices `1542`, `1539`, and `1537` have signed cutter margins
`-9.346299369`, `-12.143722862`, and `-4.560815901 mm`, respectively.

Because a retained triangle incident to any of those vertices necessarily
contains the same failing boundary sample, changing only triangulation or
adding interior controls cannot satisfy the `1.7 mm` gate. Any viable surface
family must first obtain a reviewed expansion into the exact ten outside faces
incident to those three vertices.

The audit recomputed the script hash and semantic fingerprint, confirmed that
the boundary is one simple nine-vertex loop, and verified no mutation,
geometry emission, Blend save, image work, Gate B/D claim, or promotion.

Reviewed authority:
`v27_c9_landing_boundary_authority.json`

Authority SHA-256:
`83b7c5ed527f241a8e4e31b5e125ec395fd8c8ebe9cdc8bcce419bddd53079f6`

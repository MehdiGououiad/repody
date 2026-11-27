"""Automated commercial-license policy gate for ``repody_fraud`` dependencies."""

import importlib.metadata as md

FORBIDDEN_PACKAGES = frozenset({"pymupdf", "fitz", "mrz", "fastmrz", "photoholmes"})
FORBIDDEN_LICENSE_MARKERS = (
    "agpl",
    "gpl-2",
    "gpl-3",
    "gplv2",
    "gplv3",
    "gnu general public license",
    "sspl",
    "noncommercial",
    "non-commercial",
)


def test_no_forbidden_packages_installed() -> None:
    installed = {
        dist.metadata["Name"].lower().replace("_", "-")
        for dist in md.distributions()
        if dist.metadata.get("Name")
    }
    violations = sorted(FORBIDDEN_PACKAGES & installed)
    assert violations == [], f"Forbidden copyleft/NC packages installed: {violations}"


def test_no_gpl_agpl_or_noncommercial_licenses() -> None:
    offenders: list[tuple[str, str]] = []
    for dist in md.distributions():
        name = dist.metadata.get("Name") or "unknown"
        lic_expr = dist.metadata.get("License-Expression")
        classifiers = [
            c.removeprefix("License :: OSI Approved :: ").strip()
            for c in dist.metadata.get_all("Classifier", [])
            if c.startswith("License ::")
        ]
        if lic_expr:
            summary = lic_expr
        elif classifiers:
            summary = "; ".join(classifiers)
        else:
            raw_lic = str(dist.metadata.get("License") or "")
            summary = raw_lic.splitlines()[0][:200] if raw_lic else ""

        lowered = summary.lower()
        # Note: LGPL (e.g. pycountry LGPL-2.1) contains 'gpl'; match 'lgpl' safely first.
        normalized = lowered.replace("lgpl", "lesser_gpl_ok")
        if any(marker in normalized for marker in FORBIDDEN_LICENSE_MARKERS):
            offenders.append((name, summary))

    assert offenders == [], f"Disallowed licenses detected: {offenders}"

#!/usr/bin/env python3
"""
Product manifest loader for recursive resolver.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from boundstate_aegis.config import DATA_DIR


@dataclass(frozen=True)
class ProductCompound:
    product_name: str
    aliases: Tuple[str, ...]
    cas: Optional[str]
    smiles: Optional[str]
    inchi_key: Optional[str]
    compound_classes: Tuple[str, ...]
    pfas_class: bool
    segments: Tuple[str, ...]
    revenue_exposure: str
    manufacturer: str
    components: Tuple[Dict[str, Any], ...] = ()

    def all_names(self) -> Tuple[str, ...]:
        return (self.product_name, *self.aliases)

    def to_product_info(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "manufacturer": self.manufacturer,
            "segments": list(self.segments),
            "revenue_exposure": self.revenue_exposure,
        }


class ProductManifest:
    def __init__(self, *, version: str, manufacturer: str, products: List[ProductCompound]) -> None:
        self.version = version
        self.manufacturer = manufacturer
        self.products = products
        self._name_index: Dict[str, ProductCompound] = {}
        for product in products:
            for raw_name in product.all_names():
                key = self._normalize(raw_name)
                if key and key not in self._name_index:
                    self._name_index[key] = product

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join((value or "").strip().lower().split())

    def lookup_product(self, name: str) -> Optional[ProductCompound]:
        return self._name_index.get(self._normalize(name))

    def list_products(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for product in self.products:
            rows.append(
                {
                    "product_name": product.product_name,
                    "aliases": list(product.aliases),
                    "cas": product.cas,
                    "smiles": product.smiles,
                    "inchi_key": product.inchi_key,
                    "compound_classes": list(product.compound_classes),
                    "pfas_class": product.pfas_class,
                    "segments": list(product.segments),
                    "revenue_exposure": product.revenue_exposure,
                    "components": list(product.components),
                }
            )
        return rows

    def get_all_compounds(self) -> List[ProductCompound]:
        return list(self.products)

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls, path: Optional[Path] = None) -> "ProductManifest":
        manifest_path = path or (DATA_DIR / "chemours_product_manifest.yaml")
        with open(manifest_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

        version = str(raw.get("manifest_version") or "1.0.0")
        manufacturer = str(raw.get("manufacturer") or "unknown")
        products_raw = raw.get("products") or []
        products: List[ProductCompound] = []
        for row in products_raw:
            if not isinstance(row, dict):
                continue
            products.append(
                ProductCompound(
                    product_name=str(row.get("product_name") or "").strip(),
                    aliases=tuple(str(x).strip() for x in (row.get("aliases") or []) if str(x).strip()),
                    cas=(str(row.get("cas")).strip() if row.get("cas") else None),
                    smiles=(str(row.get("smiles")).strip() if row.get("smiles") else None),
                    inchi_key=(str(row.get("inchi_key")).strip() if row.get("inchi_key") else None),
                    compound_classes=tuple(
                        str(x).strip() for x in (row.get("compound_classes") or []) if str(x).strip()
                    ),
                    pfas_class=bool(row.get("pfas_class", False)),
                    segments=tuple(str(x).strip() for x in (row.get("segments") or []) if str(x).strip()),
                    revenue_exposure=str(row.get("revenue_exposure") or ""),
                    manufacturer=manufacturer,
                    components=tuple(x for x in (row.get("components") or []) if isinstance(x, dict)),
                )
            )
        return cls(version=version, manufacturer=manufacturer, products=products)

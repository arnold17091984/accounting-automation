"""
Merchant Lookup Module

Fast lookup of known merchants to categories without using AI.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class MerchantMatch:
    """Result of a merchant lookup."""

    merchant_pattern: str
    account_code: str
    account_name: str
    category: str
    confidence: float
    match_type: str  # 'exact', 'pattern', 'entity_specific'
    entity_hint: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "account_code": self.account_code,
            "account_name": self.account_name,
            "category": self.category,
            "confidence": self.confidence,
            "match_type": self.match_type,
        }


class MerchantLookup:
    """Fast merchant to category lookup using preloaded mappings."""

    def __init__(self, config_dir: Path | str | None = None):
        """Initialize the merchant lookup.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self._exact_matches: dict[str, dict] = {}
        self._pattern_matches: list[dict] = []
        self._entity_specific: dict[str, dict] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        """Load merchant mappings from config file."""
        mappings_file = self.config_dir / "merchant_mappings.json"

        if not mappings_file.exists():
            logger.warning(f"Merchant mappings file not found: {mappings_file}")
            return

        try:
            with open(mappings_file) as f:
                data = json.load(f)

            self._exact_matches = data.get("exact_matches", {})
            self._pattern_matches = data.get("pattern_matches", [])
            self._entity_specific = data.get("entity_specific", {})

            logger.info(
                f"Loaded {len(self._exact_matches)} exact matches, "
                f"{len(self._pattern_matches)} pattern matches"
            )
        except Exception as e:
            logger.error(f"Failed to load merchant mappings: {e}")

    def lookup(
        self,
        merchant: str,
        entity: str | None = None
    ) -> MerchantMatch | None:
        """Look up a merchant in the mappings.

        Args:
            merchant: Merchant name to look up
            entity: Optional entity for entity-specific matching

        Returns:
            MerchantMatch if found, None otherwise
        """
        if not merchant:
            return None

        merchant_upper = merchant.upper().strip()

        # 1. Try exact match first (fastest)
        if merchant_upper in self._exact_matches:
            mapping = self._exact_matches[merchant_upper]
            return MerchantMatch(
                merchant_pattern=merchant_upper,
                account_code=mapping["account_code"],
                account_name=mapping["account_name"],
                category=mapping["category"],
                confidence=mapping.get("confidence", 1.0),
                match_type="exact",
                entity_hint=mapping.get("entity_hint")
            )

        # 2. Try entity-specific patterns
        if entity and entity in self._entity_specific:
            entity_mappings = self._entity_specific[entity]
            for pattern_data in entity_mappings.get("patterns", []):
                pattern = pattern_data["pattern"]
                if re.search(pattern, merchant_upper, re.IGNORECASE):
                    return MerchantMatch(
                        merchant_pattern=pattern,
                        account_code=pattern_data["account_code"],
                        account_name=pattern_data["account_name"],
                        category=pattern_data["category"],
                        confidence=pattern_data.get("confidence", 0.9),
                        match_type="entity_specific",
                        entity_hint=[entity]
                    )

        # 3. Try pattern matches
        for pattern_data in self._pattern_matches:
            pattern = pattern_data["pattern"]
            if re.search(pattern, merchant_upper, re.IGNORECASE):
                # Check entity hint if present
                entity_hint = pattern_data.get("entity_hint")
                if entity_hint and entity and entity not in entity_hint:
                    # Entity doesn't match hint, reduce confidence
                    confidence = pattern_data.get("confidence", 0.8) * 0.7
                else:
                    confidence = pattern_data.get("confidence", 0.8)

                return MerchantMatch(
                    merchant_pattern=pattern,
                    account_code=pattern_data["account_code"],
                    account_name=pattern_data["account_name"],
                    category=pattern_data["category"],
                    confidence=confidence,
                    match_type="pattern",
                    entity_hint=entity_hint
                )

        return None

    def lookup_batch(
        self,
        merchants: list[str],
        entity: str | None = None
    ) -> dict[str, MerchantMatch | None]:
        """Look up multiple merchants.

        Args:
            merchants: List of merchant names
            entity: Optional entity for matching

        Returns:
            Dictionary mapping merchant names to matches
        """
        return {
            merchant: self.lookup(merchant, entity)
            for merchant in merchants
        }

    def get_confidence_threshold(self) -> float:
        """Get the configured low confidence threshold."""
        try:
            with open(self.config_dir / "merchant_mappings.json") as f:
                data = json.load(f)
                return data.get("low_confidence_threshold", 0.7)
        except Exception:
            return 0.7

    def add_mapping(
        self,
        merchant_pattern: str,
        account_code: str,
        account_name: str,
        category: str,
        confidence: float = 0.9,
        is_pattern: bool = False
    ) -> None:
        """Add a new merchant mapping (runtime only, not persisted).

        Args:
            merchant_pattern: Exact merchant name or regex pattern
            account_code: Account code
            account_name: Account name
            category: Category
            confidence: Confidence score
            is_pattern: Whether this is a regex pattern
        """
        mapping = {
            "account_code": account_code,
            "account_name": account_name,
            "category": category,
            "confidence": confidence
        }

        if is_pattern:
            mapping["pattern"] = merchant_pattern
            self._pattern_matches.append(mapping)
        else:
            self._exact_matches[merchant_pattern.upper()] = mapping

        logger.info(f"Added merchant mapping: {merchant_pattern}")

    def suggest_category(
        self,
        merchant: str,
        amount: float,
        entity: str | None = None
    ) -> list[MerchantMatch]:
        """Suggest possible categories for an unknown merchant.

        Args:
            merchant: Merchant name
            amount: Transaction amount (for heuristics)
            entity: Entity context

        Returns:
            List of possible matches, sorted by confidence
        """
        suggestions = []
        merchant_upper = merchant.upper()

        # Look for partial matches in exact mappings
        for known_merchant, mapping in self._exact_matches.items():
            # Check if any word in the merchant matches
            merchant_words = set(merchant_upper.split())
            known_words = set(known_merchant.split())

            common_words = merchant_words & known_words
            if common_words:
                # Calculate similarity based on common words
                similarity = len(common_words) / max(len(merchant_words), len(known_words))
                if similarity >= 0.3:  # At least 30% word overlap
                    suggestions.append(MerchantMatch(
                        merchant_pattern=known_merchant,
                        account_code=mapping["account_code"],
                        account_name=mapping["account_name"],
                        category=mapping["category"],
                        confidence=mapping.get("confidence", 1.0) * similarity,
                        match_type="suggestion",
                        entity_hint=mapping.get("entity_hint")
                    ))

        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)

        return suggestions[:5]  # Return top 5 suggestions

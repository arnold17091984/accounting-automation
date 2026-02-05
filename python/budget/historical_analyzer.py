"""
Historical Budget Analyzer Module

Uses Claude AI to analyze historical spending and suggest optimal budgets.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import anthropic
import yaml

logger = logging.getLogger(__name__)


@dataclass
class BudgetSuggestion:
    """A suggested budget for an account."""

    account_code: str
    account_name: str
    current_budget: Decimal
    recommended_budget: Decimal
    change_percent: float
    rationale: str
    confidence: float
    risk_level: str  # 'low', 'medium', 'high'
    historical_avg: Decimal
    historical_max: Decimal
    seasonal_factor: float = 1.0

    def to_dict(self) -> dict:
        return {
            "account_code": self.account_code,
            "account_name": self.account_name,
            "current_budget": float(self.current_budget),
            "recommended_budget": float(self.recommended_budget),
            "change_percent": self.change_percent,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "historical_avg": float(self.historical_avg),
            "historical_max": float(self.historical_max),
            "seasonal_factor": self.seasonal_factor
        }


@dataclass
class BudgetAnalysisResult:
    """Result of budget analysis."""

    entity: str
    target_period: str
    analysis_date: datetime
    suggestions: list[BudgetSuggestion] = field(default_factory=list)
    total_current: Decimal = Decimal("0")
    total_recommended: Decimal = Decimal("0")
    key_insights: list[str] = field(default_factory=list)
    risks_and_assumptions: list[str] = field(default_factory=list)

    @property
    def total_change_percent(self) -> float:
        if self.total_current > 0:
            return float((self.total_recommended - self.total_current) / self.total_current * 100)
        return 0.0

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "target_period": self.target_period,
            "analysis_date": self.analysis_date.isoformat(),
            "suggestions": [s.to_dict() for s in self.suggestions],
            "total_current": float(self.total_current),
            "total_recommended": float(self.total_recommended),
            "total_change_percent": self.total_change_percent,
            "key_insights": self.key_insights,
            "risks_and_assumptions": self.risks_and_assumptions
        }


class HistoricalAnalyzer:
    """Analyzes historical spending to suggest budgets using Claude AI."""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
    DEFAULT_LOOKBACK_MONTHS = 6
    DEFAULT_INFLATION_RATE = 0.05  # 5%

    def __init__(
        self,
        config_dir: Path | str | None = None,
        api_key: str | None = None,
        model: str | None = None
    ):
        """Initialize the analyzer.

        Args:
            config_dir: Path to configuration directory
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration."""
        config_file = self.config_dir / "budget_thresholds.yaml"
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                self.lookback_months = config.get("budget_suggestions", {}).get(
                    "lookback_months", self.DEFAULT_LOOKBACK_MONTHS
                )
                self.inflation_rate = config.get("budget_suggestions", {}).get(
                    "inflation_rate", self.DEFAULT_INFLATION_RATE
                )
        else:
            self.lookback_months = self.DEFAULT_LOOKBACK_MONTHS
            self.inflation_rate = self.DEFAULT_INFLATION_RATE

        # Load entity config for context
        entity_file = self.config_dir / "entity_config.yaml"
        if entity_file.exists():
            with open(entity_file) as f:
                self.entity_config = yaml.safe_load(f)
        else:
            self.entity_config = {}

    def analyze(
        self,
        entity: str,
        target_month: str,
        historical_data: dict[str, list[dict]],
        current_budgets: dict[str, Decimal] | None = None,
        growth_rate: float = 0.0,
        seasonal_notes: str = ""
    ) -> BudgetAnalysisResult:
        """Analyze historical spending and suggest budgets.

        Args:
            entity: Entity code
            target_month: Target month (YYYY-MM)
            historical_data: Dict of account_code -> list of monthly data
            current_budgets: Current budget amounts by account
            growth_rate: Expected business growth rate (decimal)
            seasonal_notes: Notes about seasonal factors

        Returns:
            BudgetAnalysisResult
        """
        result = BudgetAnalysisResult(
            entity=entity,
            target_period=target_month,
            analysis_date=datetime.now()
        )

        current_budgets = current_budgets or {}

        # Calculate basic statistics first
        account_stats = self._calculate_statistics(historical_data)

        # Prepare data for Claude
        analysis_data = self._prepare_analysis_data(
            entity, target_month, historical_data,
            current_budgets, account_stats, growth_rate, seasonal_notes
        )

        # Get Claude's analysis
        try:
            claude_result = self._get_claude_analysis(analysis_data)

            # Process suggestions
            for suggestion_data in claude_result.get("recommendations", []):
                account_code = suggestion_data.get("account_code", "")
                stats = account_stats.get(account_code, {})

                suggestion = BudgetSuggestion(
                    account_code=account_code,
                    account_name=suggestion_data.get("account_name", ""),
                    current_budget=Decimal(str(current_budgets.get(account_code, 0))),
                    recommended_budget=Decimal(str(suggestion_data.get("recommended_budget", 0))),
                    change_percent=suggestion_data.get("change_percent", 0),
                    rationale=suggestion_data.get("rationale", ""),
                    confidence=suggestion_data.get("confidence", 0.5),
                    risk_level=suggestion_data.get("risk_level", "medium"),
                    historical_avg=Decimal(str(stats.get("avg", 0))),
                    historical_max=Decimal(str(stats.get("max", 0))),
                    seasonal_factor=suggestion_data.get("seasonal_factor", 1.0)
                )

                result.suggestions.append(suggestion)
                result.total_current += suggestion.current_budget
                result.total_recommended += suggestion.recommended_budget

            result.key_insights = claude_result.get("key_insights", [])
            result.risks_and_assumptions = claude_result.get("risks_and_assumptions", [])

        except Exception as e:
            logger.error(f"Claude analysis error: {e}")
            # Fall back to statistical analysis
            result = self._statistical_fallback(
                entity, target_month, historical_data,
                current_budgets, account_stats, growth_rate
            )

        return result

    def _calculate_statistics(
        self,
        historical_data: dict[str, list[dict]]
    ) -> dict[str, dict]:
        """Calculate basic statistics for each account.

        Args:
            historical_data: Historical spending data

        Returns:
            Statistics by account
        """
        stats = {}

        for account_code, monthly_data in historical_data.items():
            amounts = [Decimal(str(m.get("amount", 0))) for m in monthly_data]

            if amounts:
                stats[account_code] = {
                    "avg": sum(amounts) / len(amounts),
                    "max": max(amounts),
                    "min": min(amounts),
                    "trend": self._calculate_trend(amounts),
                    "volatility": self._calculate_volatility(amounts),
                    "months": len(amounts)
                }
            else:
                stats[account_code] = {
                    "avg": Decimal("0"),
                    "max": Decimal("0"),
                    "min": Decimal("0"),
                    "trend": 0,
                    "volatility": 0,
                    "months": 0
                }

        return stats

    def _calculate_trend(self, amounts: list[Decimal]) -> float:
        """Calculate trend (positive = increasing)."""
        if len(amounts) < 2:
            return 0.0

        # Simple linear trend
        first_half = sum(amounts[:len(amounts)//2]) / (len(amounts)//2)
        second_half = sum(amounts[len(amounts)//2:]) / (len(amounts) - len(amounts)//2)

        if first_half > 0:
            return float((second_half - first_half) / first_half)
        return 0.0

    def _calculate_volatility(self, amounts: list[Decimal]) -> float:
        """Calculate coefficient of variation."""
        if len(amounts) < 2:
            return 0.0

        avg = sum(amounts) / len(amounts)
        if avg == 0:
            return 0.0

        variance = sum((a - avg) ** 2 for a in amounts) / len(amounts)
        std_dev = float(variance) ** 0.5

        return std_dev / float(avg)

    def _prepare_analysis_data(
        self,
        entity: str,
        target_month: str,
        historical_data: dict[str, list[dict]],
        current_budgets: dict[str, Decimal],
        account_stats: dict[str, dict],
        growth_rate: float,
        seasonal_notes: str
    ) -> dict:
        """Prepare data for Claude analysis."""
        # Get entity context
        entity_info = self.entity_config.get("entities", {}).get(entity, {})

        return {
            "entity": entity,
            "entity_type": entity_info.get("industry", "unknown"),
            "entity_name": entity_info.get("full_name", entity),
            "target_month": target_month,
            "growth_rate": growth_rate,
            "inflation_rate": self.inflation_rate,
            "seasonal_notes": seasonal_notes,
            "historical_data": {
                code: {
                    "name": data[0].get("name", "") if data else "",
                    "history": [
                        {"month": m.get("month"), "amount": float(m.get("amount", 0))}
                        for m in data
                    ],
                    "current_budget": float(current_budgets.get(code, 0)),
                    "stats": {
                        "avg": float(stats.get("avg", 0)),
                        "max": float(stats.get("max", 0)),
                        "trend": stats.get("trend", 0),
                        "volatility": stats.get("volatility", 0)
                    }
                }
                for code, data in historical_data.items()
                for stats in [account_stats.get(code, {})]
            }
        }

    def _get_claude_analysis(self, data: dict) -> dict:
        """Get budget analysis from Claude."""
        prompt = f"""Analyze historical spending and recommend budgets for {data['entity_name']}.

Target Period: {data['target_month']}
Entity Type: {data['entity_type']}
Growth Rate: {data['growth_rate']*100}%
Inflation Rate: {data['inflation_rate']*100}%
Seasonal Notes: {data['seasonal_notes'] or 'None provided'}

Historical Spending by Account:
{json.dumps(data['historical_data'], indent=2)}

Provide budget recommendations that are:
1. Realistic based on historical patterns
2. Adjusted for trends and seasonality
3. Include a buffer for unexpected expenses (5-10%)
4. Flag any accounts with high variability

Return ONLY valid JSON:
{{
  "recommendations": [
    {{
      "account_code": "string",
      "account_name": "string",
      "recommended_budget": 0.00,
      "change_percent": 0.0,
      "rationale": "string",
      "confidence": 0.95,
      "risk_level": "low|medium|high",
      "seasonal_factor": 1.0
    }}
  ],
  "key_insights": ["insight1", "insight2"],
  "risks_and_assumptions": ["risk1", "risk2"]
}}"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Parse response
        cleaned = response_text.strip()
        cleaned = re.sub(r'^```json\s*', '', cleaned)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)

        return json.loads(cleaned)

    def _statistical_fallback(
        self,
        entity: str,
        target_month: str,
        historical_data: dict[str, list[dict]],
        current_budgets: dict[str, Decimal],
        account_stats: dict[str, dict],
        growth_rate: float
    ) -> BudgetAnalysisResult:
        """Fallback to statistical analysis if Claude fails."""
        result = BudgetAnalysisResult(
            entity=entity,
            target_period=target_month,
            analysis_date=datetime.now()
        )

        for account_code, data in historical_data.items():
            stats = account_stats.get(account_code, {})
            current = current_budgets.get(account_code, Decimal("0"))

            # Calculate recommended budget
            avg = stats.get("avg", Decimal("0"))
            trend = stats.get("trend", 0)

            # Apply growth and inflation
            recommended = avg * Decimal(str(1 + growth_rate + self.inflation_rate))

            # Apply trend adjustment
            if trend > 0:
                recommended *= Decimal(str(1 + min(trend, 0.2)))  # Cap at 20%

            # Add buffer based on volatility
            volatility = stats.get("volatility", 0)
            buffer = Decimal(str(1 + min(volatility * 0.5, 0.15)))  # Cap at 15%
            recommended *= buffer

            # Round to nearest 1000
            recommended = Decimal(str(round(float(recommended) / 1000) * 1000))

            change_pct = float((recommended - current) / current * 100) if current > 0 else 0

            suggestion = BudgetSuggestion(
                account_code=account_code,
                account_name=data[0].get("name", "") if data else "",
                current_budget=current,
                recommended_budget=recommended,
                change_percent=change_pct,
                rationale=f"Based on {stats.get('months', 0)}-month average with growth/inflation adjustment",
                confidence=0.6,  # Lower confidence for statistical fallback
                risk_level="medium" if volatility > 0.3 else "low",
                historical_avg=avg,
                historical_max=stats.get("max", Decimal("0"))
            )

            result.suggestions.append(suggestion)
            result.total_current += current
            result.total_recommended += recommended

        result.key_insights = [
            "Using statistical analysis (AI analysis unavailable)",
            f"Applied {growth_rate*100}% growth rate",
            f"Applied {self.inflation_rate*100}% inflation adjustment"
        ]

        return result

# CC Price Calculator — Claude Subscription Cost Analyzer

> A Claude Code Skill that calculates real-world costs for Claude Pro/Max subscriptions, carpooling (拼车), and relay (中转) pricing. Converts Credits-based quotas into actionable $/day, $/week, $/month metrics and CNY cost-per-dollar benchmarks.

## What This Solves

Claude's subscription tiers (Pro, Max 5×, Max 20×) have complex quota systems based on Credits, 5-hour windows, and weekly caps. It's hard to compare:

- **Carpooling deals** — Is a 3-person Max 20× split at ¥600/month worth it?
- **Relay services** — Is 0.45 元/刀 a good price?
- **Tier selection** — Should I get Max 5× or Max 20×?

This skill does the math instantly and rates the deal on a 1-5 star scale.

## How It Works

```
User Input                    Calculation Engine              Output
┌─────────────────┐    ┌──────────────────────────┐    ┌─────────────────┐
│ 20× 三人拼 ¥550  │───▶│ Look up Credits quota    │───▶│ Daily: $29.76   │
│                 │    │ Divide by # of people    │    │ Weekly: $208.33 │
│                 │    │ Apply cache multiplier   │    │ Monthly: $902   │
│                 │    │ Convert to CNY/USD ratio │    │ 0.61 元/刀 ⭐⭐  │
└─────────────────┘    └──────────────────────────┘    └─────────────────┘
```

## Quick Start

1. Copy `SKILL.md` to `~/.claude/skills/cc-price-calculator/`
2. Use in Claude Code: `/CC价格计算 20× 三人拼 ¥550`

## Usage Examples

### Carpooling Analysis

```
/CC价格计算 20× 三人拼 ¥600
/CC价格计算 5× 双人拼 ¥400
```

Output: per-person daily/weekly/monthly quota, cost in 元/刀 (with and without cache), star rating.

### Relay Pricing Evaluation

```
/CC价格计算 中转 0.45元/刀 缓存80%
```

Output: comparison against subscription baseline (0.53 无缓存 / 0.34 含缓存), value assessment.

## Built-in Data

| Tier | 5h Window (Credits) | Weekly (Credits) | Weekly ($) | Monthly ($) |
|------|---------------------|------------------|------------|-------------|
| Pro $20 | 550,000 | 5,000,000 | $37.50 | $162.50 |
| Max 5× $100 | 3,300,000 | 41,666,700 | $312.50 | $1,354.17 |
| Max 20× $200 | 11,000,000 | 83,333,300 | $625.00 | $2,708.33 |

**Key constants:**
- 1M Credits = $7.5
- Cache reads cost 0 Credits
- Default cache hit rate: 82.9% → multiplier ×1.558

## Rating Scale

| Rating | Price Range (元/刀) | Meaning |
|--------|-------------------|---------|
| ⭐⭐⭐⭐⭐ | < 0.34 | Below theoretical minimum — exceptional deal |
| ⭐⭐⭐⭐ | 0.34 – 0.45 | Better than subscription |
| ⭐⭐⭐ | 0.45 – 0.53 | On par with subscription |
| ⭐⭐ | 0.53 – 0.70 | Slightly expensive, acceptable |
| ⭐ | > 0.70 | Not recommended |

## Data Source

Analysis based on the Linux DO article "让成本透明化，卖的安心，买的放心" which reverse-engineered Claude's Credits system.

## Limitations

- Credits quotas are based on community reverse-engineering, not official Anthropic documentation
- Cache hit rates vary by usage pattern (82.9% is one user's measurement)
- Exchange rate defaults to 7.2 CNY/USD — real rates fluctuate
- Carpooling quota splits assume equal distribution, but real usage is bursty

## License

MIT

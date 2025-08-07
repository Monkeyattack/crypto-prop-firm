# Prop Firm Requirements - Based on Breakout Prop Model

## Overview
This document outlines the requirements and features needed to align our crypto trading system with professional prop firm standards, specifically modeled after Breakout Prop's evaluation criteria.

## Account Tiers & Evaluation Options

### Available Account Sizes
- $5,000
- $10,000
- $25,000
- $50,000
- $100,000

### Evaluation Paths
1. **One-Step Evaluation**: Direct path to funded account
2. **Two-Step Evaluation**: Lower cost entry with two phases

## Risk Management Requirements

### Daily Loss Limits
- **Maximum Daily Loss**: 4-5% of account balance
- **Reset Time**: 0030 UTC daily
- **Calculation**: Based on peak balance of the day

### Maximum Drawdown
- **One-Step**: Static drawdown ($300-$6,000 based on account size)
- **Two-Step**: Trailing drawdown ($400-$8,000 based on account size)
- **Breach**: Immediate account termination if exceeded

### Leverage Limits
- **BTC & ETH**: Maximum 5x leverage
- **Altcoins**: Maximum 2x leverage
- **Position Sizing**: Must respect leverage limits

## Profit Targets

### One-Step Evaluation
| Account Size | Profit Target | Max Drawdown | Fee |
|-------------|---------------|--------------|-----|
| $5,000      | $500 (10%)    | $300 (6%)    | $50 |
| $10,000     | $1,000 (10%)  | $600 (6%)    | $99 |
| $25,000     | $2,500 (10%)  | $1,500 (6%)  | $249 |
| $50,000     | $5,000 (10%)  | $3,000 (6%)  | $499 |
| $100,000    | $10,000 (10%) | $6,000 (6%)  | $999 |

### Two-Step Evaluation
| Account Size | Step 1 Target | Step 2 Target | Max Drawdown | Fee |
|-------------|---------------|---------------|--------------|-----|
| $5,000      | $250 (5%)     | $500 (10%)    | $400 (8%)    | $50 |
| $10,000     | $500 (5%)     | $1,000 (10%)  | $800 (8%)    | $75 |
| $25,000     | $1,250 (5%)   | $2,500 (10%)  | $2,000 (8%)  | $175 |
| $50,000     | $2,500 (5%)   | $5,000 (10%)  | $4,000 (8%)  | $350 |
| $100,000    | $5,000 (5%)   | $10,000 (10%) | $8,000 (8%)  | $725 |

## Trading Rules & Restrictions

### General Rules
- **No time limits** on evaluations
- **No minimum trading days** requirement
- **Weekend trading** allowed
- **News trading** allowed
- **Scalping** allowed
- **Automated trading** allowed (with approval)

### Position Management
- Maximum concurrent positions: Based on risk management
- Position hold time: No restrictions
- Hedging: Allowed
- Martingale/Grid: Prohibited if it violates risk limits

## Profit Split & Scaling

### Initial Profit Split
- Trader: 80-90%
- Firm: 10-20%

### Scaling Plan
- Can reach up to 95% profit split
- Based on consistent profitability
- Account size increases available

## Compliance & Monitoring

### Required Metrics to Track
1. **Daily P&L**: Track against 4-5% daily loss limit
2. **Running Drawdown**: Monitor peak-to-trough
3. **Leverage Usage**: Ensure within limits (5x BTC/ETH, 2x alts)
4. **Profit Progress**: Track towards target
5. **Risk per Trade**: Maintain consistent risk management

### Breach Conditions
- Exceeding daily loss limit
- Exceeding maximum drawdown
- Using excessive leverage
- Suspicious trading patterns

## Implementation Requirements for Our System

### Core Features Needed

#### 1. Account Management
```python
class PropFirmAccount:
    - account_size: float
    - evaluation_type: str (one_step/two_step)
    - current_balance: float
    - peak_balance: float
    - profit_target: float
    - max_drawdown: float
    - daily_loss_limit: float
```

#### 2. Risk Management Module
```python
class RiskManager:
    - check_daily_loss()
    - check_drawdown()
    - calculate_position_size()
    - verify_leverage()
    - can_open_trade()
```

#### 3. Performance Tracking
```python
class PerformanceTracker:
    - daily_pnl: float
    - total_pnl: float
    - win_rate: float
    - average_win: float
    - average_loss: float
    - profit_factor: float
    - sharpe_ratio: float
```

#### 4. Compliance Monitor
```python
class ComplianceMonitor:
    - check_leverage_compliance()
    - check_drawdown_compliance()
    - check_daily_loss_compliance()
    - generate_compliance_report()
```

### Dashboard Requirements

#### Trading Dashboard
- Real-time P&L display
- Drawdown meter (visual warning system)
- Daily loss tracker with UTC reset
- Profit target progress bar
- Leverage usage indicator

#### Analytics Dashboard
- Performance metrics
- Risk metrics
- Trade history
- Compliance status
- Account growth chart

### Alert System
- Near daily loss limit (75%, 90%)
- Near drawdown limit (75%, 90%)
- Profit target achieved
- Compliance violations
- System errors

## Integration Plan

### Phase 1: Core Risk Management (Week 1)
- [ ] Implement daily loss tracking
- [ ] Implement drawdown monitoring
- [ ] Add leverage verification
- [ ] Create position sizing calculator

### Phase 2: Account Management (Week 2)
- [ ] Create account tier system
- [ ] Implement evaluation tracking
- [ ] Add profit target monitoring
- [ ] Build compliance checker

### Phase 3: Dashboard & Reporting (Week 3)
- [ ] Update Streamlit dashboard
- [ ] Add real-time metrics display
- [ ] Create compliance reports
- [ ] Implement alert system

### Phase 4: Advanced Features (Week 4)
- [ ] Add two-step evaluation logic
- [ ] Implement trailing drawdown
- [ ] Create scaling plan tracker
- [ ] Add automated reporting

## Configuration Template

```env
# Prop Firm Configuration
PROP_FIRM_MODE=true
EVALUATION_TYPE=one_step  # one_step or two_step
ACCOUNT_SIZE=10000.00

# Risk Limits
MAX_DAILY_LOSS_PERCENT=5.0
MAX_DRAWDOWN_PERCENT=6.0  # For one-step
TRAILING_DRAWDOWN=false   # true for two-step

# Leverage Limits
MAX_LEVERAGE_BTC_ETH=5.0
MAX_LEVERAGE_ALTCOINS=2.0

# Profit Targets
PROFIT_TARGET_PERCENT=10.0  # Step 1 or one-step
PROFIT_TARGET_STEP2_PERCENT=10.0  # Step 2 only

# Trading Rules
MIN_TRADE_SIZE_USD=10.00
MAX_POSITION_SIZE_PERCENT=2.0
MAX_CONCURRENT_POSITIONS=5

# Alerts
ENABLE_RISK_ALERTS=true
ALERT_DAILY_LOSS_THRESHOLD=75.0  # Alert at 75% of daily loss
ALERT_DRAWDOWN_THRESHOLD=75.0    # Alert at 75% of max drawdown

# Reporting
GENERATE_DAILY_REPORT=true
REPORT_TIME_UTC=0030  # Daily reset time
```

## Success Metrics

### Key Performance Indicators (KPIs)
1. **Risk-Adjusted Return**: Sharpe ratio > 1.5
2. **Win Rate**: > 50%
3. **Profit Factor**: > 1.5
4. **Maximum Drawdown**: < 6%
5. **Daily Loss Frequency**: < 20% of trading days

### Evaluation Milestones
- [ ] Pass Phase 1 (if two-step)
- [ ] Achieve profit target
- [ ] Maintain drawdown limits
- [ ] Complete evaluation
- [ ] Receive funded account

## Notes

1. **Priority**: Daily loss and drawdown monitoring are CRITICAL
2. **UTC Time**: All resets happen at 0030 UTC
3. **Leverage**: Must be checked BEFORE order placement
4. **Documentation**: Keep detailed logs for compliance
5. **Testing**: Thoroughly test in paper mode first

---

*Last Updated: 2025-01-06*
*Based on Breakout Prop requirements*
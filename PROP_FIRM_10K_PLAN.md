# $10,000 One-Step Evaluation Plan

## Account Specifications

### Breakout Prop $10,000 One-Step Requirements
- **Initial Balance**: $10,000
- **Profit Target**: $1,000 (10%)
- **Maximum Drawdown**: $600 (6%)
- **Daily Loss Limit**: $500 (5%)
- **Evaluation Fee**: $99
- **Time Limit**: None
- **Profit Split**: 80-90% (up to 95% with scaling)

### Risk Parameters
- **Maximum Daily Loss**: -$500 (resets at 0030 UTC)
- **Maximum Total Drawdown**: -$600 from peak balance
- **Target Profit**: +$1,000 to pass evaluation
- **Leverage Limits**: 
  - BTC/ETH: 5x maximum
  - Altcoins: 2x maximum

## Trading Strategy Configuration

### Position Sizing Formula
```
Position Size = (Account Balance × Risk Per Trade) / Stop Loss Distance

Where:
- Risk Per Trade = 1-2% ($100-$200)
- Maximum Position Value = $10,000 × 5 = $50,000 (BTC/ETH)
- Maximum Position Value = $10,000 × 2 = $20,000 (Altcoins)
```

### Daily Risk Budget
- **Maximum Daily Risk**: $500 (5%)
- **Recommended Trades Per Day**: 2-5
- **Risk Per Trade**: $100-$200 (1-2%)
- **Safety Buffer**: Keep 1% buffer ($100) for slippage

### Progressive Profit Targets
1. **Week 1**: $200 (2%) - Conservative start
2. **Week 2**: $300 (3%) - Increase confidence
3. **Week 3**: $300 (3%) - Maintain consistency
4. **Week 4**: $200 (2%) - Secure the pass
5. **Total**: $1,000 (10%) - Evaluation passed

## Implementation Checklist

### Phase 1: System Configuration (Day 1)
- [ ] Set up $10,000 paper trading account
- [ ] Configure risk management parameters
- [ ] Set daily loss limit to $500
- [ ] Set maximum drawdown to $600
- [ ] Configure leverage limits (5x BTC/ETH, 2x alts)

### Phase 2: Risk Management Setup (Day 2)
- [ ] Implement position sizing calculator
- [ ] Create daily loss tracker
- [ ] Set up drawdown monitor
- [ ] Configure auto-stop at risk limits
- [ ] Add pre-trade validation checks

### Phase 3: Trading Rules Implementation (Day 3)
- [ ] Signal validation system
- [ ] Leverage compliance checker
- [ ] Position size validator
- [ ] Daily reset mechanism (0030 UTC)
- [ ] Trade execution logger

### Phase 4: Monitoring Dashboard (Day 4)
- [ ] Real-time P&L display
- [ ] Drawdown visualization
- [ ] Daily loss meter
- [ ] Progress to target indicator
- [ ] Risk metrics panel

### Phase 5: Testing & Validation (Day 5-7)
- [ ] Backtest with historical data
- [ ] Simulate edge cases
- [ ] Test risk limit triggers
- [ ] Verify daily reset
- [ ] Validate all calculations

## Key Trading Rules

### Entry Criteria
1. **Signal Quality**: Only high-confidence signals (80%+ accuracy)
2. **Risk Check**: Ensure daily loss budget available
3. **Leverage Check**: Verify within limits
4. **Drawdown Check**: Confirm not near maximum
5. **Position Size**: Calculate based on stop loss

### Position Management
```python
# Example position entry validation
def can_enter_trade(signal, account):
    # Check daily loss limit
    if account.daily_loss >= 400:  # 80% of limit
        return False, "Near daily loss limit"
    
    # Check drawdown
    if account.drawdown >= 500:  # 83% of limit
        return False, "Near maximum drawdown"
    
    # Check leverage
    required_leverage = signal.position_size / account.balance
    max_leverage = 5 if signal.symbol in ['BTC', 'ETH'] else 2
    if required_leverage > max_leverage:
        return False, f"Leverage {required_leverage}x exceeds limit"
    
    # Calculate risk
    trade_risk = signal.stop_loss_amount
    if trade_risk > 200:  # 2% max per trade
        return False, "Trade risk exceeds 2%"
    
    return True, "Trade approved"
```

### Exit Strategy
1. **Take Profit Levels**:
   - TP1: 1.5R (50% position)
   - TP2: 2.5R (30% position)
   - TP3: 4R (20% position)

2. **Stop Loss Management**:
   - Initial: 1-2% risk
   - Breakeven: Move at 1R profit
   - Trailing: 1% after 2R profit

3. **Time-Based Exits**:
   - Close losing trades before daily reset if near limit
   - Reduce exposure on Friday evenings
   - Exit all positions if drawdown > $500

## Daily Routine

### Pre-Market (Before 0030 UTC)
- [ ] Review previous day's performance
- [ ] Check account metrics
- [ ] Verify no breaches occurred
- [ ] Plan day's trading approach
- [ ] Set daily goals

### Trading Hours
- [ ] Monitor Telegram signals
- [ ] Validate each opportunity
- [ ] Execute with proper position sizing
- [ ] Log all trades immediately
- [ ] Track running P&L

### Post-Market
- [ ] Calculate daily performance
- [ ] Update drawdown if needed
- [ ] Review trades for improvements
- [ ] Prepare report
- [ ] Set alerts for overnight

## Performance Tracking

### Daily Metrics to Record
```python
daily_metrics = {
    'date': '2025-01-06',
    'starting_balance': 10000,
    'ending_balance': 10150,
    'daily_pnl': 150,
    'daily_pnl_percent': 1.5,
    'peak_balance': 10200,
    'trough_balance': 10050,
    'max_daily_drawdown': -150,
    'running_drawdown': -50,
    'trades_taken': 3,
    'winning_trades': 2,
    'losing_trades': 1,
    'win_rate': 66.7,
    'average_win': 125,
    'average_loss': -100,
    'profit_factor': 2.5,
    'distance_to_target': 850,
    'progress_percent': 15.0
}
```

### Weekly Review Checklist
- [ ] Total P&L for the week
- [ ] Win rate analysis
- [ ] Risk-reward achieved
- [ ] Drawdown events
- [ ] Best and worst trades
- [ ] Strategy adjustments needed

## Risk Scenarios & Responses

### Scenario 1: Down $400 (80% of daily limit)
**Response**: Stop trading for the day, analyze losses

### Scenario 2: Down $500 (daily limit reached)
**Response**: Automatic trading halt until 0030 UTC

### Scenario 3: Drawdown at $500 (83% of max)
**Response**: Reduce position sizes by 50%, focus on high-probability setups

### Scenario 4: Up $500 (50% to target)
**Response**: Maintain discipline, don't increase risk

### Scenario 5: Up $900 (90% to target)
**Response**: Reduce risk to 0.5% per trade, focus on capital preservation

## Success Metrics

### Minimum Requirements
- **Profit**: ≥ $1,000
- **Drawdown**: < $600
- **Daily Loss**: Never exceed $500
- **Time**: Complete within 30 days (recommended)

### Target Performance
- **Win Rate**: > 60%
- **Profit Factor**: > 2.0
- **Risk-Reward**: > 1:2
- **Daily Profit**: $50-100 average
- **Weekly Profit**: $250 average

## Configuration Files

### .env Settings
```env
# Prop Firm Settings
PROP_FIRM_MODE=true
EVALUATION_TYPE=one_step
ACCOUNT_SIZE=10000.00
PROFIT_TARGET=1000.00
MAX_DRAWDOWN=600.00
MAX_DAILY_LOSS=500.00

# Risk Management
RISK_PER_TRADE_PERCENT=1.5
MAX_POSITION_SIZE_PERCENT=50.0  # 5x leverage on 10k
MAX_CONCURRENT_TRADES=3
STOP_LOSS_PERCENT=1.5

# Leverage
MAX_LEVERAGE_BTC_ETH=5.0
MAX_LEVERAGE_ALTCOINS=2.0

# Safety
AUTO_STOP_AT_DAILY_LIMIT=true
AUTO_STOP_AT_DRAWDOWN=true
REDUCE_SIZE_NEAR_LIMITS=true
WARNING_THRESHOLD_PERCENT=75.0

# Reset
DAILY_RESET_TIME_UTC=0030
TIMEZONE=UTC
```

## Emergency Procedures

### If Daily Limit is Breached
1. Trading automatically stops
2. Notification sent immediately
3. Account locked until reset
4. Review and document cause
5. Adjust strategy if needed

### If Drawdown Limit is Breached
1. Evaluation failed
2. All positions closed
3. Generate final report
4. Analyze failure points
5. Prepare for retry

## Next Steps

1. **Immediate Actions**:
   - [ ] Update config.py with $10,000 parameters
   - [ ] Implement prop_firm_manager.py
   - [ ] Add risk validation to signal_processor.py
   - [ ] Create prop firm dashboard page

2. **Testing Phase**:
   - [ ] Run 7-day paper test
   - [ ] Simulate various market conditions
   - [ ] Test all risk scenarios
   - [ ] Verify calculations accuracy

3. **Go-Live Checklist**:
   - [ ] All risk checks implemented
   - [ ] Dashboard fully functional
   - [ ] Alerts configured
   - [ ] Backup plan ready
   - [ ] First week strategy defined

---

**Remember**: The goal is not just to pass the evaluation but to develop consistent, risk-managed trading habits that will succeed in the funded account phase.

*Created: 2025-01-06*
*Target Start Date: [TO BE DETERMINED]*
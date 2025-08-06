#!/usr/bin/env python3
"""
Add notification support to position monitor for trade closes
"""

# Create an updated version of the check_and_close_position method
updated_method = '''
    async def check_and_close_position(self, position, current_price):
        """Check if position should be closed and handle closure with notifications"""
        symbol = position['symbol']
        side = position['side']
        entry_price = position['entry']
        tp_price = position['tp']
        sl_price = position['sl']
        trade_id = position['id']
        
        should_close = False
        exit_price = current_price
        exit_reason = None
        
        # Calculate current P&L
        if side.upper() in ['BUY', 'LONG']:
            current_pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            # Check trailing stop
            trailing_result = self.trailing_manager.check_position(
                trade_id, symbol, side, entry_price, current_price, sl_price
            )
            
            if trailing_result['should_close']:
                should_close = True
                exit_price = trailing_result['exit_price']
                exit_reason = 'trailing'
            elif current_price >= tp_price:
                should_close = True
                exit_price = tp_price
                exit_reason = 'tp'
            elif current_price <= sl_price:
                should_close = True
                exit_price = sl_price
                exit_reason = 'sl'
                
        else:  # SELL/SHORT
            current_pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            trailing_result = self.trailing_manager.check_position(
                trade_id, symbol, side, entry_price, current_price, sl_price
            )
            
            if trailing_result['should_close']:
                should_close = True
                exit_price = trailing_result['exit_price']
                exit_reason = 'trailing'
            elif current_price <= tp_price:
                should_close = True
                exit_price = tp_price
                exit_reason = 'tp'
            elif current_price >= sl_price:
                should_close = True
                exit_price = sl_price
                exit_reason = 'sl'
        
        if should_close:
            logger.info(f"Closing position {trade_id} for {symbol} - Reason: {exit_reason}")
            
            # Close the position in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate final P&L
            if side.upper() in ['BUY', 'LONG']:
                pnl = exit_price - entry_price
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                pnl = entry_price - exit_price
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100
            
            # Get position size (default to 1000 if not found)
            position_size = position.get('position_size', 1000)
            pnl_dollar = position_size * (pnl_pct / 100)
            
            # Update trade record
            cursor.execute("""
                UPDATE trades 
                SET result = ?, pnl = ?, exit_time = ?, exit_price = ?, profit_loss = ?
                WHERE id = ?
            """, (exit_reason, pnl_dollar, datetime.now(), exit_price, pnl_pct, trade_id))
            
            # Get updated account stats
            cursor.execute("""
                SELECT COUNT(*) as total_trades,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(pnl) as total_pnl
                FROM trades
                WHERE result != 'open'
            """)
            stats = cursor.fetchone()
            
            # Calculate win rate
            win_rate = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
            
            # Get today's P&L
            cursor.execute("""
                SELECT SUM(pnl) as daily_pnl
                FROM trades
                WHERE DATE(exit_time) = DATE('now')
                AND result != 'open'
            """)
            daily_pnl = cursor.fetchone()[0] or 0
            
            conn.commit()
            conn.close()
            
            # Send notification
            try:
                from telegram_notifier import notifier
                
                trade_data = {
                    'id': trade_id,
                    'symbol': symbol,
                    'side': side,
                    'entry': entry_price,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'pnl': pnl_dollar,
                    'pnl_pct': pnl_pct,
                    'duration': self.calculate_duration(position.get('timestamp')),
                    'new_balance': 10000 + stats[2],  # Initial capital + total P&L
                    'daily_pnl': daily_pnl,
                    'win_rate': win_rate
                }
                
                notifier.notify_trade_closed(trade_data)
                
                # If trailing stop was updated, send that notification too
                if trailing_result.get('sl_updated'):
                    notifier.notify_trailing_update({
                        'id': trade_id,
                        'symbol': symbol,
                        'current_price': current_price,
                        'current_profit_pct': current_pnl_pct,
                        'old_sl': sl_price,
                        'new_sl': trailing_result['new_sl'],
                        'locked_profit_pct': trailing_result.get('locked_profit_pct', 0)
                    })
                    
            except Exception as e:
                logger.error(f"Failed to send trade close notification: {e}")
            
            logger.info(f"Position closed: {symbol} - P&L: ${pnl_dollar:.2f} ({pnl_pct:.2f}%)")
            
    def calculate_duration(self, entry_time):
        """Calculate trade duration"""
        try:
            if isinstance(entry_time, str):
                entry_dt = datetime.fromisoformat(entry_time)
            else:
                entry_dt = entry_time
            
            duration = datetime.now() - entry_dt
            hours = duration.total_seconds() / 3600
            
            if hours < 1:
                return f"{int(duration.total_seconds() / 60)} minutes"
            elif hours < 24:
                return f"{hours:.1f} hours"
            else:
                return f"{duration.days} days"
        except:
            return "Unknown"
'''

print("Position monitor notification update created!")
print("\nThis update adds notifications for:")
print("- Trade closures (TP hit, SL hit, trailing stop)")
print("- Trailing stop updates")
print("- Complete trade statistics in notifications")
print("\nTo apply, replace the check_and_close_position method in position_monitor.py")
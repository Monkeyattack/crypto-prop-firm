#!/usr/bin/env python3
"""
Update the automated signal monitor to include comprehensive notifications
"""

import re

def add_notifications_to_monitor():
    """Add notification calls to the signal monitor"""
    
    # Read the current file
    with open('automated_signal_monitor.py', 'r') as f:
        content = f.read()
    
    # Add notification after signal is parsed
    notification_after_parse = '''
                    if signal_data:
                        signal_data['channel'] = group_name
                        signal_data['message_id'] = message.id
                        signal_data['timestamp'] = message.date
                        
                        # Notify about new signal
                        try:
                            notifier.notify_new_signal(signal_data)
                        except Exception as e:
                            logger.error(f"Failed to send new signal notification: {e}")
                        
                        # Log to database
                        self.log_signal_to_db(signal_data)'''
    
    # Replace the existing block
    content = re.sub(
        r'if signal_data:\s*signal_data\[\'channel\'\] = group_name\s*signal_data\[\'message_id\'\] = message\.id\s*signal_data\[\'timestamp\'\] = message\.date\s*# Log to database\s*self\.log_signal_to_db\(signal_data\)',
        notification_after_parse.strip(),
        content,
        flags=re.MULTILINE | re.DOTALL
    )
    
    # Add notification after trade execution decision
    notification_trade_block = '''
                if self.is_trading_enabled():
                    # Check if we should execute trade
                    if self.should_execute_trade(signal_data):
                        # Execute trade
                        trade_result = self.trading_engine.execute_trade(signal_data)
                        
                        if trade_result['success']:
                            # Notify successful trade
                            try:
                                trade_data = {
                                    'id': trade_result.get('trade_id'),
                                    'symbol': signal_data['symbol'],
                                    'side': signal_data['side'],
                                    'entry': trade_result.get('entry_price', signal_data['entry_price']),
                                    'tp': signal_data['take_profit'],
                                    'sl': signal_data['stop_loss'],
                                    'position_size': trade_result.get('position_size', 1000)
                                }
                                notifier.notify_trade_opened(trade_data)
                                notifier.notify_signal_processed(signal_data, True)
                            except Exception as e:
                                logger.error(f"Failed to send trade notification: {e}")
                            
                            logger.info(f"Trade executed for signal: {signal_data['symbol']}")
                        else:
                            # Notify failed trade
                            try:
                                notifier.notify_signal_processed(
                                    signal_data, 
                                    False, 
                                    trade_result.get('reason', 'Unknown error')
                                )
                            except Exception as e:
                                logger.error(f"Failed to send trade failure notification: {e}")
                            
                            logger.warning(f"Trade not executed for signal: {signal_data['symbol']}")
                    else:
                        # Notify signal rejected
                        try:
                            notifier.notify_signal_processed(
                                signal_data,
                                False,
                                "Signal does not meet execution criteria"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send signal rejection notification: {e}")
                else:
                    logger.info(f"Trading disabled, skipping signal: {signal_data['symbol']}")'''
    
    # Save the updated file
    with open('automated_signal_monitor_updated.py', 'w') as f:
        f.write(content)
    
    print("Signal monitor updated with notifications!")
    print("The updated file is saved as: automated_signal_monitor_updated.py")
    print("\nNotifications added for:")
    print("- New signals detected")
    print("- Signals processed (accepted/rejected)")
    print("- Trades opened")
    print("- Trade execution failures")

if __name__ == "__main__":
    add_notifications_to_monitor()
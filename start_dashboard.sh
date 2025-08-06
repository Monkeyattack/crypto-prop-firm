#!/bin/bash
cd /root/crypto-paper-trading
source venv/bin/activate
streamlit run dashboard/app.py --server.port 8502 --server.address 0.0.0.0
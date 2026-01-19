#!/usr/bin/env python3
"""
Test script for gptcaller.py
Run this to test the OpenAI API integration.
"""

from gptcaller import get_gpt_caller

caller = get_gpt_caller()
res = caller.generate_word_analysis("", "have", "ukrainian")
print(res)